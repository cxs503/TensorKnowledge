"""采集层：连库执行 spec 里的全部只读查询，落一份自带 SQL 原文的快照。

快照结构（``kpi-kb-verify-rate/snapshot@1``）：
    schema / spec_version / spec_sha256 / collected_at_utc / db_fingerprints / raw / sql / errors

不可复算的设计被有意排除：快照里除了 ``collected_at_utc``（不入指纹）之外没有任何
"运行期才确定"的字段，因此同一份快照在任何机器上都产出同一份 result。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import spec
from .backend import BackendUnavailable, PsqlBackend
from .compute import snapshot_fingerprint

SCHEMA = "kpi-kb-verify-rate/snapshot@1"


class CollectionError(RuntimeError):
    """有查询取不回来——拒绝交付「半份快照」（缺项会被误读成 0）。"""


def _dispatch(backend: PsqlBackend, kind: str, sql: str):
    if kind == "scalar":
        return backend.scalar(sql)
    if kind == "map":
        return backend.map(sql)
    if kind == "row":
        return backend.row(sql)
    if kind == "json":
        return backend.json(sql)
    if kind == "rows":
        return backend.rows(sql)
    raise ValueError(f"未知 kind: {kind}")


def collect(user: str | None = None, timeout: float = 60.0,
            clock=lambda: _dt.datetime.now(_dt.timezone.utc),
            db_map: dict[str, str] | None = None) -> dict:
    """db_map 只给基准测试用（把 spec 里的逻辑库名指到 scratch 库），默认 None=真库。"""
    dbs = sorted({q["db"] for q in spec.QUERIES.values()})
    physical = {db: (db_map or {}).get(db, db) for db in dbs}
    backends = {db: PsqlBackend(physical[db], user=user, timeout=timeout) for db in dbs}
    raw: dict = {}
    errors: dict[str, str] = {}
    for qid, q in spec.QUERIES.items():
        try:
            raw[qid] = _dispatch(backends[q["db"]], q["kind"], q["sql"])
        except (BackendUnavailable, Exception) as exc:  # 记录后统一抛，便于排障
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            errors[qid] = f"{type(exc).__name__}: {exc}"
    if errors:
        raise CollectionError(
            "采集失败，拒绝产出半份快照：\n" + "\n".join(
                f"  - {k}: {v}" for k, v in sorted(errors.items())))

    snap = {
        "schema": SCHEMA,
        "spec_version": spec.SPEC_VERSION,
        "spec_sha256": spec.SPEC_SHA256,
        "collected_at_utc": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db_fingerprints": {db: {"database": physical[db], "readonly": True,
                                 "queries": sum(1 for q in spec.QUERIES.values() if q["db"] == db)}
                            for db in dbs},
        "raw": raw,
        "sql": {qid: q["sql"] for qid, q in sorted(spec.QUERIES.items())},
        "errors": {},
    }
    snap["snapshot_sha256"] = snapshot_fingerprint(snap)
    return snap


def write_snapshot(snapshot: dict, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def write_tsv_dumps(snapshot: dict, out_dir: str | Path) -> list[Path]:
    """把分布型原始数据摊成 TSV —— 让审阅者能直接用 psql/awk 复核，而不是信 JSON。"""
    out = Path(out_dir) / "data"
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for qid in ("ko_by_status", "ko_by_level", "evidence_kinds", "verdict_gate_states"):
        value = snapshot["raw"].get(qid)
        if not isinstance(value, dict):
            continue
        p = out / f"{qid}.tsv"
        lines = ["label\tvalue"] + [f"{k}\t{v}" for k, v in value.items()]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(p)
    return paths