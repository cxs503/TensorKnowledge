#!/usr/bin/env python3
"""Work package wp-6184-01 (task_type=01-asset-registration) — asset registration only.

Scope guard: touches ONLY report_id=6184 (tensor://reports/6184, field=markdown).
No extraction, no classification, no claims are generated (objective.claims may be empty),
nothing is marked verified (verification is the platform gate's job).

Every locator quote is *sliced out of the fetched markdown* (never retyped from memory),
so each `quote` is a literal substring of the source by construction, `start_char`/
`end_char` are exact Python str offsets, and line numbers are 1-based.

Usage:
  python3 scripts/kf/wp6184_register_assets.py build     # fetch -> docs/kf/wp-6184-01/asset_manifest.json
  python3 scripts/kf/wp6184_register_assets.py verify    # independent re-check of the written manifest
  python3 scripts/kf/wp6184_register_assets.py build verify
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-6184-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "6184"
SOURCE_URI = "tensor://reports/6184"
SOURCE_FIELD = "markdown"
# Pinned by the work-package contract (input.source_hash / input.chars / input.title).
EXPECTED_HASH = "f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c"
EXPECTED_CHARS = 2406
EXPECTED_TITLE = (
    "IN28-I1 EEXI/CII 合规评估引擎：MEPC 全口径实现 + 12 船型验证"
    "（算术误差 0.00%，外部基准欠账）"
)
EXPECTED_SCENARIO = "green_navigation_eexi_cii_compliance"

REPO = Path(__file__).resolve().parents[2]
# docs/ survives the mission push gate (artifacts/ does not), so deliverables live here.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
SNAPSHOT = OUT_DIR / "source_snapshot.md"
SCHEMA = OUT_DIR / "asset_manifest.schema.json"

# ------------------------------------------------------------------ asset table
# mode:
#   document  -> whole markdown is the asset
#   line      -> quote = the single line containing `needle`
#   block     -> quote = from the line containing `needle` to the end of that
#                contiguous non-empty block (tables, list runs)
#   slice     -> quote = substring of the line containing `needle`, bounded by
#                `start_marker` .. `end_marker` (both inclusive, markers verbatim)
ASSETS = [
    dict(
        asset_id="A01",
        asset_class="source_document",
        label="report 6184 markdown 原文（本工作包的唯一输入）",
        in_report_section="whole document (§1–§7)",
        mode="document",
        resolution="resolved_in_source",
        note=(
            "注册对象本身：source_uri=tensor://reports/6184, field=markdown。"
            "sha256 与契约 input.source_hash 逐字节一致（见 integrity），chars 与契约一致。"
        ),
    ),
    dict(
        asset_id="A02",
        asset_class="code_pointer",
        label="fleet.py（12 船主尺度/载重/装机/设计点 + provenance）",
        in_report_section="§1 案例",
        mode="slice",
        needle="fleet.py",
        start_marker="全部写入",
        end_marker="provenance`",
        resolution="referenced_unresolved",
        note=(
            "报告正文指向的代码工件；报告未内嵌该文件内容，平台亦无随报告附件可取 → "
            "仅登记引用，不做内容断言。"
        ),
    ),
    dict(
        asset_id="A03",
        asset_class="code_module",
        label="backend/modules/eexi_cii_compliance（引擎模块：regulatory/eexi/cii/fleet/route/benchmarks）",
        in_report_section="§2 怎么做的",
        mode="line",
        needle="backend/modules/eexi_cii_compliance",
        resolution="referenced_unresolved",
        note="模块路径与其子模块清单为报告自述；本工序不读代码、不做实现层核验。",
    ),
    dict(
        asset_id="A04",
        asset_class="artifact_file",
        label="artifacts/in28_i1/checks.json（15 项判据检查结果）",
        in_report_section="§3 结果（首条 bullet）",
        mode="line",
        needle="artifacts/in28_i1/checks.json",
        resolution="referenced_unresolved",
        note=(
            "判据 15/15 的唯一原始证据文件；报告只给路径不给内容，"
            "附件端点探测见 source.platform_attachment_probes → 不可取。"
        ),
    ),
    dict(
        asset_id="A05",
        asset_class="embedded_data_table",
        label="EEXI/要求/裕度%/AER/2024 评级 11 船型数值表",
        in_report_section="§3 结果",
        mode="block",
        needle="| 船型 | EEXI |",
        resolution="resolved_in_source",
        note=(
            "markdown 内嵌表格即数据本体（11 行船型 + 表头/分隔行）；"
            "客船缺行与正文『适用 11/12』一致，可作为下游抽取的源表。"
        ),
    ),
    dict(
        asset_id="A06",
        asset_class="embedded_data_table",
        label="误差判定表（量/基准/相对误差/<3%？，6 行）",
        in_report_section="§6 误差判定",
        mode="block",
        needle="| 量 | 基准 | 相对误差 |",
        resolution="resolved_in_source",
        note="内嵌即本体；逐船 AER 一行显式写『离线不可得 / WITHHELD 欠账』，不确定性被保留。",
    ),
    dict(
        asset_id="A07",
        asset_class="figure",
        label="四联图 in28i1_figures_1to4.png（EEXI attained vs required｜CII 评级矩阵｜AER vs 文献区间｜Holtrop n_eff）",
        in_report_section="§4 图",
        mode="line",
        needle="四联图内嵌",
        resolution="referenced_unresolved",
        note=(
            "报告 record.figures 声明 1 张 png（name=in28i1_figures_1to4.png），"
            "但 markdown 未内嵌 base64、平台无图字节可取 → 图资产登记为未解析，登记其声明存在。"
        ),
    ),
    dict(
        asset_id="A08",
        asset_class="code_module",
        label="benchmarks（文献区间来源，标记 WITHHELD）",
        in_report_section="§2 怎么做的",
        mode="slice",
        needle="`benchmarks`（文献区间，WITHHELD）",
        start_marker="`benchmarks`",
        end_marker="WITHHELD）",
        resolution="referenced_unresolved",
        note="区间锚点自身被作者标为 WITHHELD（未回读决议/文献原文），本工序照录该状态，不上调。",
    ),
    dict(
        asset_id="A09",
        asset_class="external_standard",
        label="IMO 决议 MEPC.333(76) / MEPC.328(76) / MEPC.335(76)（达到值 / 要求值 / EPL 反解）",
        in_report_section="§2 怎么做的",
        mode="slice",
        needle="MEPC.333(76)",
        start_marker="（达到值",
        end_marker="MEPC.335(76)）",
        resolution="referenced_unresolved",
        note="外部规范原文不在报告内、本工序离线不可得；仅登记报告声明的映射关系（哪条决议管哪一层）。",
    ),
    dict(
        asset_id="A10",
        asset_class="external_dataset",
        label="GISIS / VeriFuel 逐船 AER 外部基准点值",
        in_report_section="§6 误差判定",
        mode="line",
        needle="GISIS/VeriFuel",
        resolution="referenced_unresolved",
        note=(
            "报告显式记『离线不可得』+『无法判定（WITHHELD 欠账）』："
            "该项被登记为缺口而非已证，保留不确定性。"
        ),
    ),
]


# ------------------------------------------------------------------ platform I/O
def _base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def _req(url: str, token: str | None = None, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def login() -> str:
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    return json.loads(_req(_base() + "/auth/login", data=body))["access_token"]


def fetch_report() -> dict:
    tok = login()
    raw = _req(f"{_base()}/tensor/reports/{REPORT_ID}", token=tok)
    rec = json.loads(raw)
    return rec.get("data", rec) if isinstance(rec, dict) else rec


def probe(url: str, tok: str) -> dict:
    """Record HTTP status/bytes of an optional attachment endpoint; never fatal."""
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return {"http_status": e.code, "bytes": len(e.read() or b"")}
    except Exception as e:  # network/parse — record, don't crash the registration
        return {"error": type(e).__name__ + ": " + str(e)[:120]}


# ------------------------------------------------------------------ locators
def line_starts(md: str) -> list[int]:
    starts, pos = [0], 0
    for ln in md.split("\n"):
        pos += len(ln) + 1
        starts.append(pos)
    return starts


def line_of(starts: list[int], char: int) -> int:
    lo = 0
    for i, s in enumerate(starts):
        if s <= char:
            lo = i
    return lo + 1  # 1-based


def make_locator(md: str, spec: dict) -> dict:
    mode = spec["mode"]
    starts = line_starts(md)
    if mode == "document":
        start, end = 0, len(md)
    else:
        needle = spec["needle"]
        idxs = [i for i in range(len(md)) if md.startswith(needle, i)]
        if len(idxs) != 1:
            raise SystemExit(f"[{spec['asset_id']}] needle {needle!r} matched {len(idxs)} times (need 1)")
        anchor = idxs[0]
        lstart = starts[line_of(starts, anchor) - 1]
        if mode == "line":
            start = lstart
            nl = md.find("\n", anchor)
            end = len(md) if nl < 0 else nl
        elif mode == "block":
            start = lstart
            pos, end = lstart, len(md)
            while pos <= len(md):
                nl = md.find("\n", pos)
                line_end = len(md) if nl < 0 else nl
                if not md[pos:line_end].strip():
                    end = pos - 1 if pos > 0 else 0
                    break
                pos = line_end + 1
        elif mode == "slice":
            sm, em = spec["start_marker"], spec["end_marker"]
            nl = md.find("\n", anchor)
            line_end = len(md) if nl < 0 else nl
            line = md[lstart:line_end]
            a = line.find(sm)
            if a < 0:
                raise SystemExit(f"[{spec['asset_id']}] start_marker {sm!r} not on anchor line")
            b = line.find(em, a)
            if b < 0:
                raise SystemExit(f"[{spec['asset_id']}] end_marker {em!r} not after start on anchor line")
            start = lstart + a
            end = lstart + b + len(em)
        else:
            raise SystemExit(f"unknown mode {mode}")
    quote = md[start:end]
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": line_of(starts, start),
        "end_line": line_of(starts, max(end - 1, 0)),
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


# ------------------------------------------------------------------ build
def build() -> int:
    rec = fetch_report()
    md = rec["markdown"]
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()

    assets = []
    for spec in ASSETS:
        loc = make_locator(md, spec)
        assets.append(
            {
                "asset_id": spec["asset_id"],
                "asset_class": spec["asset_class"],
                "label": spec["label"],
                "in_report_section": spec["in_report_section"],
                "locator": loc,
                "resolution": spec["resolution"],
                "resolution_check": {
                    "check": (
                        "verbatim substring present at [start_char,end_char] and unique in markdown"
                        if spec["resolution"] == "resolved_in_source"
                        else "path/name literal present in markdown; asset bytes not retrievable here"
                    ),
                    "result": "resolved" if spec["resolution"] == "resolved_in_source" else "unresolved",
                },
                "note": spec["note"],
            }
        )

    tok = login()
    probes = {
        "GET /tensor/reports/6184/artifacts": probe(f"{_base()}/tensor/reports/6184/artifacts", tok),
        "GET /tensor/reports/6184/figures/in28i1_figures_1to4.png": probe(
            f"{_base()}/tensor/reports/6184/figures/in28i1_figures_1to4.png", tok
        ),
    }

    by_class = Counter(a["asset_class"] for a in assets)
    by_res = Counter(a["resolution"] for a in assets)
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "contract_hash": EXPECTED_HASH,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "chars": len(md),
            "contract_chars": EXPECTED_CHARS,
            "chars_matches_contract": len(md) == EXPECTED_CHARS,
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": md.count("\n") + (0 if md.endswith("\n") else 1),
            "title": rec.get("title"),
            "title_matches_contract": rec.get("title") == EXPECTED_TITLE,
            "scenario_key": rec.get("scenario_key"),
            "scenario_matches_contract": rec.get("scenario_key") == EXPECTED_SCENARIO,
            "record_id": rec.get("id"),
            "record_status": rec.get("status"),
            "record_tags": rec.get("tags", []),
            "platform_figures": rec.get("figures", []),
            "fetched_via": "GET /api/v1/tensor/reports/6184 (Bearer auth)",
            "platform_attachment_probes": probes,
            "line_counting": "1-based logical lines of markdown; char offsets are Python str indices (UTF-8 decoded)",
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "ids_unique": len({a["asset_id"] for a in assets}) == len(assets),
            "claims_all_evidenced_or_unresolved": True,
            "notes": (
                "本工序不做抽取、不生成知识 claim（objective.register_assets 为唯一目标）；"
                "claims 空数组是合法完整结果，不标任何结论为 verified。"
            ),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SNAPSHOT.write_text(md, encoding="utf-8")
    print(f"[build] {MANIFEST.relative_to(REPO)}  assets={len(assets)}  sha256={digest}")
    return 0


# ------------------------------------------------------------------ verify
def verify() -> int:
    """Independent re-check: re-derive from the source bytes, not from the build code path."""
    checks: list[dict] = []

    def chk(name: str, ok: bool, detail: str):
        checks.append({"check": name, "result": "pass" if ok else "FAIL", "detail": detail})

    raw = MANIFEST.read_text(encoding="utf-8")
    try:
        man = json.loads(raw)
        chk("valid_json", True, f"{len(raw)} bytes parsed")
    except Exception as e:
        chk("valid_json", False, str(e))
        man = {}

    # 1) schema
    schema_ok, schema_detail = False, "schema file missing"
    if SCHEMA.exists():
        try:
            import jsonschema  # noqa: PLC0415

            jsonschema.validate(man, json.loads(SCHEMA.read_text(encoding="utf-8")))
            schema_ok, schema_detail = True, f"jsonschema.validate pass against {SCHEMA.name}"
        except ImportError:
            schema_ok, schema_detail = False, "jsonschema module not installed"
        except Exception as e:
            schema_detail = f"{type(e).__name__}: {str(e)[:300]}"
    chk("schema_pass", schema_ok, schema_detail)

    # 2) source hash — recompute from the platform record when reachable, else the snapshot
    md, hash_src, platform_ok = None, "snapshot", None
    try:
        rec = fetch_report()
        md = rec["markdown"]
        platform_ok = hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
        hash_src = "platform refetch"
    except Exception as e:
        hash_src = f"snapshot (platform unreachable: {type(e).__name__})"
    if md is None and SNAPSHOT.exists():
        md = SNAPSHOT.read_text(encoding="utf-8")
    snap_hash_ok = md is not None and hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    chk(
        "source_hash_matches",
        bool(snap_hash_ok) and bool(man.get("source", {}).get("hash") == EXPECTED_HASH),
        f"recomputed={EXPECTED_HASH} source={hash_src} platform_match={platform_ok} "
        f"manifest_hash={man.get('source', {}).get('hash')}",
    )

    # 3) locators resolvable against the source bytes
    bad = []
    if md is not None:
        for a in man.get("assets", []):
            q, loc = a["locator"]["quote"], a["locator"]
            span_ok = md[loc["start_char"]: loc["end_char"]] == q
            cnt = md.count(q)
            if not (span_ok and cnt == 1 and loc["unique"] is True):
                bad.append(f"{a['asset_id']}(span_ok={span_ok},count={cnt})")
        chk("source_locator_resolvable", not bad, "all quotes resolve + unique" if not bad else "; ".join(bad))
    else:
        chk("source_locator_resolvable", False, "no source bytes available (platform down, no snapshot)")

    # 4) no duplicate ids
    ids = [a["asset_id"] for a in man.get("assets", [])]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    chk("no_duplicate_ids", not dup and len(ids) == len(set(ids)), f"{len(ids)} ids, dupes={dup}")

    # 5) claims evidence discipline (empty array is the declared-legal case here)
    claims = man.get("claims", [])
    bad_claims = [
        c.get("claim_id")
        for c in claims
        if not c.get("evidence_locator") and not c.get("status")
    ]
    chk(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        not bad_claims,
        f"claims={len(claims)} (empty=legal for 01-asset-registration); offenders={bad_claims}",
    )

    # 6) consistency extras
    chk(
        "counts_consistent",
        man.get("counts", {}).get("assets") == len(ids),
        f"counts.assets={man.get('counts', {}).get('assets')} len(assets)={len(ids)}",
    )
    verified_marks = [k for k in ('"verified": true', '"status": "verified"', "verified=true") if k in raw]
    chk(
        "no_verified_marks",
        not verified_marks,
        "no claim/asset marked verified by this package" if not verified_marks else f"found {verified_marks}",
    )

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "source_hash": "sha256:" + EXPECTED_HASH,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "acceptance": checks,
        "all_pass": all(c["result"] == "pass" for c in checks),
        "note": "verification here = self-check of the 01-asset-registration acceptance list; "
        "claim-level verification stays with the platform gate (this package emits no claims).",
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print(f"[{c['result']:4s}] {c['check']}: {c['detail']}")
    print(f"[verify] all_pass={verdict['all_pass']} -> {VERDICT.relative_to(REPO)}")
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "verify"]
    rc = 0
    for a in acts:
        if a == "build":
            rc |= build()
        elif a == "verify":
            rc |= verify()
        else:
            raise SystemExit(f"unknown action {a}")
    sys.exit(rc)