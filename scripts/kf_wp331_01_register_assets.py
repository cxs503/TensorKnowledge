#!/usr/bin/env python3
"""wp-331-01 (01-asset-registration) 资产登记器 —— 只登记，不抽取。

契约要点（package_id=wp-331-01, lane=C）：
- 只碰 report_id=331；断言 markdown 字节 sha256 与契约 source_hash 一致；
- 列出可解析的附件/工件（报告 markdown / 报告记录 / 图件 / 被提及的 schema 工件），
  逐个给出检索端点、HTTP 状态、字节数与 sha256（可得时）；
- 不可解析的资产**保留为 unresolved 并写明理由**（不发明信息、不伪造资产）；
- claims 留空数组（本工序不做抽取）。

零手抄：manifest 里的 locator 引文全部由 ``locate_line`` 在源码文本里按锚点
提取（逐字取自上游 markdown），不做人工转写。

用法：
  TENSOR_API_BASE/... TENSOR_AGENT_USER/... TENSOR_AGENT_PASS/... \
  python3 scripts/kf_wp331_01_register_assets.py \
      --out-dir docs/kf/wp-331-01 --emit-envelope /tmp/kf_envelope.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPORT_ID = "331"
PACKAGE_ID = "wp-331-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = ("sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717")
PRODUCER = "tensor-agent m15506 (knowledge-factory worker, lane C)"
# 平台图件目录（只读探测，用于说明 404 不是瞬时故障）
DEFAULT_FIGURE_ROOT = "/root/tensor-ecosystem/TensorPlatform/backend/uploads/tensor_reports"
# 候选工件只读扫描根（找不到就保持 unresolved，不猜）
DEFAULT_SCAN_ROOT = "/root/tensor-ecosystem"


# ---------------------------------------------------------------- HTTP helpers
def _token(base: str) -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (user and pwd):
        return None
    body = json.dumps({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    return d.get("access_token") or d.get("token")


def _get(base: str, path: str, token: str | None) -> tuple[int, bytes]:
    headers = {"Authorization": "Bearer " + token} if token else {}
    req = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ------------------------------------------------------------- text utilities
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def locate_line(markdown: str, anchor: str) -> str:
    """返回 markdown 中含 anchor 的第一行（去首尾空白），逐字取自源文本。

    找不到即抛错——宁可失败，也不许凭记忆写引文。
    """
    for line in markdown.split("\n"):
        if anchor in line:
            return line.strip()
    raise KeyError(f"anchor not found in source markdown: {anchor!r}")


def _asset(asset_id: str, kind: str, uri: str, status: str, **kw) -> dict:
    rec = {"asset_id": asset_id, "kind": kind, "uri": uri, "status": status}
    rec.update(kw)
    return rec


def probe_figure_dir(figure_root: str) -> dict:
    root = Path(figure_root)
    if not root.is_dir():
        return {"root": figure_root, "exists": False}
    own = root / REPORT_ID
    return {"root": figure_root, "exists": True,
            "report_subdir_present": own.is_dir(),
            "sibling_report_dirs": len([p for p in root.iterdir() if p.is_dir()])}


def scan_candidates(scan_root: str, filename: str) -> list[dict]:
    root = Path(scan_root)
    if not root.is_dir():
        return []
    hits = []
    for p in root.glob(f"*/schemas/{filename}"):
        try:
            b = p.read_bytes()
        except OSError:
            continue
        hits.append({"path": str(p), "bytes": len(b),
                     "sha256": hashlib.sha256(b).hexdigest()})
    return sorted(hits, key=lambda h: h["path"])


# ------------------------------------------------------------------- builder
def build(base: str, figure_root: str = DEFAULT_FIGURE_ROOT,
          scan_root: str = DEFAULT_SCAN_ROOT) -> tuple[dict, str]:
    token = _token(base)
    code, raw = _get(base, f"/tensor/reports/{REPORT_ID}", token)
    if code != 200:
        raise SystemExit(f"report fetch failed: HTTP {code} {raw[:200]!r}")
    record = json.loads(raw)
    md = record.get("markdown") or ""

    actual = sha256_text(md)
    if actual != EXPECTED_HASH:
        raise SystemExit(f"source hash mismatch: claimed={EXPECTED_HASH} actual={actual}")

    record_title = record.get("title")
    h1 = locate_line(md, "# M404")
    h1_text = h1.lstrip("# ").strip()

    assets: list[dict] = [
        _asset(
            f"asset-{REPORT_ID}-report-markdown", "report_markdown",
            f"tensor://reports/{REPORT_ID}#markdown", "resolved",
            retrieval={"endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}",
                       "field": "markdown", "http_status": code},
            sha256=actual, chars=len(md), bytes_utf8=len(md.encode("utf-8")),
            locator={"source_field": "markdown", "quote": h1, "note": "markdown 首行 H1"},
            notes="本工序唯一权威源；字节哈希由生产者独立重算并与契约 source_hash 对齐。",
        ),
        _asset(
            f"asset-{REPORT_ID}-report-record", "report_record_metadata",
            f"tensor://reports/{REPORT_ID}#record", "resolved",
            retrieval={"endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}",
                       "field": "record", "http_status": code},
            fields={"id": record.get("id"), "title": record_title,
                    "scenario_key": record.get("scenario_key"),
                    "status": record.get("status"),
                    "mission_id": record.get("mission_id"),
                    "created_at": record.get("created_at"),
                    "tags": record.get("tags")},
            locator={"source_field": "record", "quote": None,
                     "note": "元数据字段取自记录，markdown 正文无对应字样"},
            notes=f"记录 title 与 markdown H1 不一致（记录='{record_title}'；"
                  f"H1='{h1_text}'）：两者分别登记，不做改写、不做归并。",
        ),
    ]

    fig_dir = probe_figure_dir(figure_root)
    for fig in record.get("figures") or []:
        name = fig.get("name")
        fcode, fbody = _get(base, f"/tensor/reports/{REPORT_ID}/figures/{name}", token)
        ok = fcode == 200 and bool(fbody)
        assets.append(_asset(
            f"asset-{REPORT_ID}-figure-{name}", "figure",
            f"tensor://reports/{REPORT_ID}/figures/{name}",
            "resolved" if ok else "declared_unresolvable",
            retrieval={"endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}/figures/{name}",
                       "http_status": fcode,
                       "error_body": None if ok else fbody.decode("utf-8", "replace")[:120],
                       "figure_dir_probe": fig_dir},
            sha256=hashlib.sha256(fbody).hexdigest() if ok else None,
            bytes=len(fbody) if ok else 0,
            caption=fig.get("caption"),
            locator={"source_field": "markdown",
                     "quote": locate_line(md, "See attached:"),
                     "note": "图件在 markdown ④ Figures 段被引用"},
            unresolved_reason=None if ok else (
                f"记录声明了图件 {name}，但检索端点返回 HTTP {fcode}（figure not found），"
                f"且服务端图件目录下无 report {REPORT_ID} 子目录"
                f"（同级报告目录 {fig_dir.get('sibling_report_dirs')} 个）——字节不可得；"
                "不伪造、不重绘、不代上游补图。"),
        ))

    schema_name = "dem_fem_coupling_v1.json"
    candidates = scan_candidates(scan_root, schema_name)
    assets.append(_asset(
        f"asset-{REPORT_ID}-schema-dem_fem_coupling_v1", "schema_artifact",
        f"tensor://reports/{REPORT_ID}#artifact:{schema_name}",
        "unresolved_candidate_found" if candidates else "mentioned_unresolved",
        retrieval={"endpoint": None, "http_status": None,
                   "candidate_scan": {"scan_root": scan_root,
                                      "pattern": f"*/schemas/{schema_name}",
                                      "hits": candidates}},
        locator={"source_field": "record", "quote": None,
                 "note": "工件文件名只在记录 summary 出现；markdown 正文只剩"
                         "「Schema  validates against jsonschema」（文件名被剥离）"},
        unresolved_reason=(
            "平台无「报告→附件」绑定端点，markdown 正文无文件名/URI，字节不可经 API 取得；"
            + (f"只读扫描在 {candidates[0]['path']} 找到同名候选（sha256 "
               f"{candidates[0]['sha256'][:16]}…），但与报告 331 的版本绑定只是间接证据，"
               "不据此认定同一工件。" if candidates else "只读扫描未发现同名候选文件。")
            + " 本工序不反推工件内容，保留未解析。"),
    ))

    md_quotes = {
        "honest_fail": locate_line(md, "**Honest-FAIL**"),
        "parameters": locate_line(md, "**Parameters**"),
        "metrics_exponent_row": locate_line(md, "| Exponent |"),
        "schema_mention": locate_line(md, "Schema  validates"),
        "figure_mention": locate_line(md, "See attached:"),
    }
    md_bytes = md.encode("utf-8")
    quote_check = {k: {"quote": v,
                       "resolvable_in_markdown": (v in md),
                       "offset_bytes": md_bytes.find(v.encode("utf-8"))}
                   for k, v in md_quotes.items()}

    counts: dict[str, int] = {}
    for a in assets:
        counts[a["status"]] = counts.get(a["status"], 0) + 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "lane": "C",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "report_id": REPORT_ID,
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "source_hash": actual,
            "expected_source_hash": EXPECTED_HASH,
            "hash_matches": True,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "title_record": record_title,
            "title_markdown_h1": h1_text,
            "title_fields_consistent": (record_title or "").strip() == h1_text,
            "scenario_key": record.get("scenario_key"),
        },
        "assets": assets,
        "unresolved": [
            {"asset_id": a["asset_id"], "status": a["status"],
             "reason": a.get("unresolved_reason")}
            for a in assets if a["status"] != "resolved"
        ],
        "asset_status_counts": counts,
        "locator_checks": quote_check,
        "scope": {
            "extraction_performed": False,
            "claims_emitted": 0,
            "note": "工序 01 只登记资产与指纹；不抽取知识、不判定 verified、不重跑上游算例。",
        },
    }, md


def envelope(manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": "01",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": "hash 由生产者从平台 markdown 字段 utf-8 字节独立重算；"
                     "平台门会再独立重算一次。",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="docs/kf/wp-331-01")
    ap.add_argument("--emit-envelope", default=None)
    ap.add_argument("--figure-root", default=DEFAULT_FIGURE_ROOT)
    ap.add_argument("--scan-root", default=DEFAULT_SCAN_ROOT)
    args = ap.parse_args(argv)

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    manifest, md = build(base, args.figure_root, args.scan_root)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snap = out / "source_snapshot"
    snap.mkdir(exist_ok=True)
    (snap / f"report_{REPORT_ID}.markdown").write_text(md, encoding="utf-8")

    env = envelope(manifest)
    if args.emit_envelope:
        Path(args.emit_envelope).write_text(
            json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"source_hash   : {manifest['source']['source_hash']}  match=True")
    print(f"chars/bytes   : {manifest['source']['chars']} / {manifest['source']['bytes_utf8']}")
    print(f"assets        : {len(manifest['assets'])}  status={manifest['asset_status_counts']}")
    for a in manifest["assets"]:
        print(f"  - {a['asset_id']:<48} {a['status']}")
    print("claims        : 0 (工序 01 不抽取)")
    print(f"written       : {out/'asset_manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())