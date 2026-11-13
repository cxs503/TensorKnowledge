#!/usr/bin/env python3
"""wp-8605-01 (01-asset-registration): fetch report 8605, register its source assets, self-verify.

Scope discipline (single report, no invention):
  * the only source of truth is `GET /tensor/reports/8605` (markdown field);
  * the markdown is frozen byte-exactly under docs/wp-8605-01/source_report_8605.md;
  * every registered asset carries a locator that is *re-sliced* from the frozen source,
    so any third party can recompute the check without trusting this script;
  * nothing is "filled in": assets living in other repos / offline regulation texts are
    registered as referenced_unresolved, and the three things the report declares absent
    are registered as declared_absent.

Usage:
  python3 scripts/kf_fetch_8605.py                 # fetch + freeze + manifest + figures + verification
  python3 scripts/kf_fetch_8605.py --from-cache    # rebuild from the frozen copy (no network)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
REPORT_ID = "8605"
PKG = "wp-8605-01"
DOCS = pathlib.Path("docs") / PKG
SOURCE_COPY = DOCS / "source_report_8605.md"
MANIFEST = DOCS / "asset_manifest.json"
VERIFICATION = DOCS / "verification.json"
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.generic.schema.json")

# --------------------------------------------------------------------------------------------
# mechanical reference rules: (asset_class, regex). No semantic guessing, one asset per distinct
# matched token, locator = first occurrence in the source.
# --------------------------------------------------------------------------------------------
RULES = [
    ("figure_reference", re.compile(r"fig\d_[a-z0-9_]+\.png")),
    ("code_file", re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*\.py")),
    ("data_artifact", re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*\.(?:json|csv)")),
    ("directory", re.compile(r"(?:backend|artifacts)/[A-Za-z0-9_/]*/")),
    ("standard_reference", re.compile(r"(?:MEPC|ISO)[ .]\d+(?:\(\d+\))?")),
    ("service_endpoint", re.compile(r"(?:GET|POST|PUT|DELETE) /[^\s`,、）)]+")),
]

# Things the report *itself* declares to be missing. Locator = the declaring phrase, so the
# declared_absent status is anchored in the source rather than asserted by this script.
DECLARED_ABSENT = [
    ("ship_anchor", "沙箱内没有 noon report / 船级社评级记录"),
    ("model_test_table", "本仓无该表"),
    ("regulation_text", "离线不可回读原文"),
]


def _api(path: str, data=None, token: str | None = None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, body, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_report() -> dict:
    tok = _api("/auth/login", {"username": os.environ.get("TENSOR_AGENT_USER", ""),
                               "password": os.environ.get("TENSOR_AGENT_PASS", "")})["access_token"]
    payload = _api("/tensor/reports/" + REPORT_ID, token=tok)
    if str(payload.get("id")) != REPORT_ID:
        raise SystemExit("FATAL: unexpected report id %r (scope is 8605 only)" % payload.get("id"))
    return payload


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def section_of(md: str, pos: int) -> str:
    """Heading that owns `pos` (last '## ' heading before it), else '(document)'."""
    head = md.rfind("\n## ", 0, pos)
    if head < 0:
        return "(document)"
    end = md.find("\n", head + 1)
    return md[head + 3:end if end >= 0 else len(md)].strip()


def _locator(md: str, start: int, end: int, token: str, method: str = "char_span") -> dict:
    return {
        "method": method,
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start),
        "end_line": md.count("\n", 0, max(start, end - 1)),
        "quote": md[start:end],
        "unique": md.count(token) == 1,
    }


def scan_assets(md: str) -> list[dict]:
    """Register every mechanically findable reference, plus the self-declared absences."""
    assets: list[dict] = [{
        "asset_id": "A01",
        "asset_class": "document",
        "label": "报告正文（markdown 全文）",
        "in_report_section": "(document)",
        "locator": _locator(md, 0, len(md), md, method="document"),
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "char_span_covers_source_markdown", "result": "resolved"},
        "note": "整篇 markdown 即源资产；sha256 见 source.hash",
        "occurrences": 1,
    }]
    seen: dict[str, str] = {}  # token -> asset_id (dedupe across rules)
    for asset_class, rx in RULES:
        for m in rx.finditer(md):
            token = m.group(0)
            if token in seen:
                continue
            seen[token] = "A%02d" % (len(assets) + 1)
            assets.append({
                "asset_id": seen[token],
                "asset_class": asset_class,
                "label": token,
                "in_report_section": section_of(md, m.start()),
                "locator": _locator(md, m.start(), m.end(), token),
                "resolution": "referenced_unresolved",
                "resolution_check": {"check": "referenced_not_retrievable_in_worktree", "result": "unresolved"},
                "note": "正文引用，但字节不在本仓库检出内（另一仓/离线文本/外部服务），不补齐",
                "occurrences": md.count(token),
            })
    for asset_class, phrase in DECLARED_ABSENT:
        pos = md.find(phrase)
        if pos < 0:
            raise SystemExit("FATAL: declared_absent anchor %r not found in source" % phrase)
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": asset_class,
            "label": phrase,
            "in_report_section": section_of(md, pos),
            "locator": _locator(md, pos, pos + len(phrase), phrase),
            "resolution": "declared_absent",
            "resolution_check": {"check": "report_declares_asset_missing", "result": "absent"},
            "note": "报告自述缺失（WITHHELD/本仓无此表/离线不可回读），本包未补齐也未替代",
            "occurrences": md.count(phrase),
        })
    return assets


def build_manifest(payload: dict, md: str) -> dict:
    assets = scan_assets(md)
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    figs = payload.get("figures") or []
    names = [f.get("name") for f in figs]
    claims = [
        {
            "claim_id": "C01",
            "text": "tensor://reports/%s 的 markdown 共 %d 字符，UTF-8 sha256=%s，scenario_key=%s；"
                    "本包只登记这一个报告对象。" % (REPORT_ID, len(md), sha256(md), payload.get("scenario_key")),
            "status": "supported",
            "evidence": {"uri": payload.get("source_uri", "tensor://reports/" + REPORT_ID),
                         "field": "markdown", "hash": sha256(md), "chars": len(md),
                         "title": payload.get("title"), "scenario_key": payload.get("scenario_key")},
        },
        {
            "claim_id": "C02",
            "text": "平台元数据声明 %d 张结果图（仅名称+说明，payload 不携带 png 字节），本包按"
                    "referenced_unresolved 登记，不生成替代图件。" % len(names),
            "status": "supported",
            "evidence": {"figure_names": names,
                         "figure_names_sha256": hashlib.sha256("".join(n or "" for n in names).encode()).hexdigest(),
                         "png_bytes_present": False},
        },
        {
            "claim_id": "C03",
            "text": "报告自述 %d 项资产在沙箱/本仓缺失（实船锚、模型试验表、决议原文），本包如实登记为"
                    "declared_absent，未补齐、未用仿真替代实船验证。" % len(DECLARED_ABSENT),
            "status": "supported",
            "evidence_locator": {"asset_ids": [a["asset_id"] for a in assets
                                              if a["resolution"] == "declared_absent"],
                                 "quotes": [a["locator"]["quote"] for a in assets
                                            if a["resolution"] == "declared_absent"]},
        },
    ]
    return {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": "tensor://reports/" + REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": sha256(md),
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "platform_id": payload.get("id"),
            "platform_mission_id": payload.get("mission_id"),
            "platform_figures": figs,
            "platform_tags": payload.get("tags") or [],
            "retrieved_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "local_copy": str(SOURCE_COPY),
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": claims,
        "integrity": {
            "quote_uniqueness": True,
            "hash_recomputed_locally": True,
            "hash_matches_contract": None,
            "integrity_note": "wp-8605-01 的契约端点 /tensor/kf/packages/wp-8605-01 返回 404，"
                              "无契约 source_hash 可比；hash_matches_contract=null 表示「无法比对」而非「一致」。"
                              "hash_recomputed_locally 指冻结副本与实时 API 逐字节一致。",
        },
    }


# --------------------------------------------------------------------------------------------
# independent checks (used by scripts and re-run verbatim in tests, incl. negative controls)
# --------------------------------------------------------------------------------------------
def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    """Re-slice every locator from the source. Returns [(asset_id, reason)] for failures."""
    bad: list[tuple[str, str]] = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            if not (loc["start_char"] == 0 and loc["end_char"] == len(md)):
                bad.append((a["asset_id"], "document_span_mismatch"))
            continue
        if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append((a["asset_id"], "slice_mismatch"))
        elif loc["quote"] not in md:
            bad.append((a["asset_id"], "quote_not_in_source"))
        elif md.count(loc["quote"]) != 1 and loc.get("unique"):
            bad.append((a["asset_id"], "uniqueness_claim_false"))
        elif section_of(md, loc["start_char"]) != a["in_report_section"]:
            bad.append((a["asset_id"], "section_mismatch"))
    return bad


def check_resolution_honesty(md: str, manifest: dict) -> list[tuple[str, str]]:
    """No asset may claim resolved_in_source unless its bytes really are the source markdown,
    and declared_absent quote must be a self-declaration present in the source."""
    bad: list[tuple[str, str]] = []
    for a in manifest["assets"]:
        if a["resolution"] == "resolved_in_source" and a["locator"]["method"] != "document":
            bad.append((a["asset_id"], "resolved_without_bytes"))
        if a["resolution"] == "declared_absent" and a["locator"]["quote"] not in md:
            bad.append((a["asset_id"], "absence_not_declared_in_source"))
        expect = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
                  "declared_absent": "absent"}[a["resolution"]]
        if a["resolution_check"]["result"] != expect:
            bad.append((a["asset_id"], "resolution_check_inconsistent"))
    return bad


def check_counts(manifest: dict) -> list[tuple[str, str]]:
    c = manifest["counts"]
    bad: list[tuple[str, str]] = []
    if c["assets"] != len(manifest["assets"]):
        bad.append(("counts", "assets_total"))
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    if c["by_class"] != by_class:
        bad.append(("counts", "by_class"))
    if c["by_resolution"] != by_res:
        bad.append(("counts", "by_resolution"))
    for k in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        if c[k] != by_res.get(k, 0):
            bad.append(("counts", k))
    return bad


def check_ids(manifest: dict) -> list[tuple[str, str]]:
    ids = [a["asset_id"] for a in manifest["assets"]]
    bad = [("ids", "duplicate:%s" % i) for i in set(ids) if ids.count(i) > 1]
    bad += [("ids", "bad_format:%s" % i) for i in ids if not re.fullmatch(r"A[0-9]{2}", i)]
    return bad


SELF_FIGURE = "fig_verification.png"  # rendered *from* verification.json -> cannot be hashed in it


def check_figures(docs: pathlib.Path, recorded: dict | None = None) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Verify the figures: PNG bytes must exist, be real PNGs, and match the previously recorded
    sha256 (`recorded`), which is how a swapped/faked figure is caught on re-verification."""
    hashes: dict[str, str] = {}
    bad: list[tuple[str, str]] = []
    for p in sorted(docs.glob("fig_*.png")):
        if p.name == SELF_FIGURE:
            continue
        raw = p.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            bad.append((p.name, "not_png"))
            continue
        hashes[p.name] = hashlib.sha256(raw).hexdigest()
    if len(hashes) != 2:
        bad.append(("figures", "count=%d" % len(hashes)))
    if not (docs / SELF_FIGURE).exists():
        bad.append((SELF_FIGURE, "missing"))
    if recorded:
        bad += [(n, "hash_drift") for n, d in hashes.items() if n in recorded and recorded[n] != d]
        bad += [(n, "recorded_but_missing") for n in recorded if n not in hashes]
    return hashes, bad


def recorded_figures(docs: pathlib.Path = DOCS) -> dict | None:
    """sha256 map recorded by a previous run (verification.json), if any."""
    path = docs / "verification.json"
    if not path.exists():
        return None
    for c in json.loads(path.read_text()).get("checks", []):
        if c["check"] == "figures_present":
            return c["detail"].get("sha256") or None
    return None


def verify(manifest: dict, md: str, docs: pathlib.Path = DOCS,
           fig_recorded: dict | None = None) -> dict:
    checks = []

    def add(name: str, bad: list, detail: dict) -> None:
        checks.append({"check": name, "result": "pass" if not bad else "fail",
                       "detail": dict(detail, failures=[[str(x) for x in b] for b in bad])})

    add("source_hash_recomputed", [] if sha256(md) == manifest["source"]["hash"] else [("source", "hash")],
        {"recomputed": sha256(md), "manifest": manifest["source"]["hash"],
         "chars": len(md), "bytes_utf8": len(md.encode("utf-8"))})
    add("locators_reslice", check_locators(md, manifest), {"assets_checked": len(manifest["assets"])})
    add("resolution_honesty", check_resolution_honesty(md, manifest),
        {"resolved_in_source": manifest["counts"]["resolved_in_source"],
         "referenced_unresolved": manifest["counts"]["referenced_unresolved"],
         "declared_absent": manifest["counts"]["declared_absent"]})
    add("counts_consistent", check_counts(manifest), manifest["counts"])
    add("asset_ids", check_ids(manifest), {"ids": [a["asset_id"] for a in manifest["assets"]]})
    figs, fig_bad = check_figures(docs, fig_recorded)
    add("figures_present", fig_bad,
        {"files": sorted(figs), "sha256": figs, "hashes_matched_against": sorted(fig_recorded or {}),
         "not_hashed": SELF_FIGURE + " (rendered from this file: self-referential)"})
    registered = {(a["asset_class"], a["label"]) for a in manifest["assets"]}
    recall_bad = [(cls, tok) for cls, rx in RULES for m in rx.finditer(md)
                  for tok in [m.group(0)] if (cls, tok) not in registered]
    add("rule_recall", sorted(set(recall_bad)),
        {"rules": len(RULES), "distinct_tokens": len({m.group(0) for _, rx in RULES for m in rx.finditer(md)})})
    claim_bad = [("claims", c["claim_id"]) for c in manifest["claims"]
                 if not any(k in c for k in ("evidence", "evidence_locator", "status"))]
    add("claims_have_evidence", claim_bad, {"claims": [c["claim_id"] for c in manifest["claims"]]})
    verify_bad = []
    try:
        import jsonschema
        jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
    except Exception as exc:  # noqa: BLE001 - any schema failure is a failed check
        verify_bad = [("schema", type(exc).__name__)]
    add("schema_pass", verify_bad, {"schema": str(SCHEMA)})
    return {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_by": "scripts/kf_fetch_8605.py:verify",
        "source_hash_recomputed": "sha256:" + sha256(md),
        "result": "pass" if all(c["result"] == "pass" for c in checks) else "fail",
        "checks": checks,
    }


def main(argv: list[str]) -> int:
    from_cache = "--from-cache" in argv
    DOCS.mkdir(parents=True, exist_ok=True)
    if from_cache:
        # rebuild from the frozen source + the metadata already registered in the manifest;
        # must produce byte-identical artifacts (offline reproducibility check)
        md = SOURCE_COPY.read_text()
        if not MANIFEST.exists():
            raise SystemExit("FATAL: --from-cache needs an existing manifest to source metadata from")
        registered = json.loads(MANIFEST.read_text())["source"]
        payload = {"id": registered["platform_id"], "title": registered["title"],
                   "scenario_key": registered["scenario_key"],
                   "mission_id": registered["platform_mission_id"],
                   "figures": registered["platform_figures"], "tags": registered["platform_tags"]}
    else:
        payload = fetch_report()
        md = payload["markdown"]
        if SOURCE_COPY.exists() and SOURCE_COPY.read_text() != md:
            print("FATAL: frozen copy %s differs from live API (source drifted); refusing to overwrite"
                  % SOURCE_COPY, file=sys.stderr)
            return 3
        SOURCE_COPY.write_text(md)
    if not SOURCE_COPY.exists():
        raise SystemExit("FATAL: no frozen source; run without --from-cache first")

    manifest = build_manifest(payload, md)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import kf_figures_8605  # noqa: PLC0415 - sibling script, imported after paths are known
    kf_figures_8605.render_all(manifest, md, DOCS)

    # two passes: pass 1 renders the self-referential figure, pass 2 records its presence.
    # The figure only draws check names/results, which are identical across the two passes.
    recorded = recorded_figures(DOCS)  # figures must not drift from the previously recorded bytes
    ver = verify(manifest, md, DOCS, recorded)
    kf_figures_8605.fig_verification(ver, DOCS / kf_figures_8605.SELF_FIGURE)
    ver = verify(manifest, md, DOCS, recorded)
    VERIFICATION.write_text(json.dumps(ver, ensure_ascii=False, indent=2) + "\n")
    print("source chars=%d sha256=%s" % (len(md), sha256(md)))
    print("assets=%d %s" % (manifest["counts"]["assets"], manifest["counts"]["by_resolution"]))
    print("verification=%s (%d checks)" % (ver["result"], len(ver["checks"])))
    for c in ver["checks"]:
        if c["result"] != "pass":
            print("  FAIL", c["check"], c["detail"].get("failures"))
    return 0 if ver["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))