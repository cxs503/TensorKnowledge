#!/usr/bin/env python3
"""Independent re-check of the wp-297-01 delivery (run after build_report.py).

Re-derives everything from the delivered artefacts instead of trusting the
builder: parses the fenced json block out of docs/kf-wp-297-01.md, resolves
every locator against the source snapshot, and recomputes the source hash.
Exit code 0 = every check passed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DOC = REPO / "docs" / "kf-wp-297-01.md"
EXPECTED_HASH = "426c49ee6920408fa082092a086ef85edf1da0d566a63dfad66dba81549cc77a"
REPORT_ID = "297"

text = DOC.read_text(encoding="utf-8")
snapshot = (OUT / f"source_report_{REPORT_ID}.md").read_text(encoding="utf-8")
manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
result_file = json.loads((OUT / "kf_result.wp-297-01.json").read_text(encoding="utf-8"))
payload = json.loads(Path("/tmp/report_wp29701.json").read_text(encoding="utf-8"))

checks: list[tuple[str, bool, object]] = []


def add(name: str, ok: bool, detail: object = "") -> None:
    checks.append((name, bool(ok), detail))


blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
add("exactly_one_json_block", len(blocks) == 1, {"found": len(blocks)})

embedded = json.loads(blocks[0]) if blocks else None
add("embedded_block_is_valid_json", embedded is not None, {})
add(
    "embedded_block_matches_result_file",
    embedded == result_file,
    {"block_keys": sorted(embedded or {}), "file_keys": sorted(result_file)},
)
add(
    "result_top_level_structure",
    list((embedded or {}).keys()) == ["package_id", "task_type", "report_id", "provenance", "outputs"],
    list((embedded or {}).keys()),
)
add(
    "result_package_binding",
    (embedded or {}).get("package_id") == "wp-297-01"
    and (embedded or {}).get("task_type") == "01-asset-registration"
    and str((embedded or {}).get("report_id")) == REPORT_ID,
    {k: (embedded or {}).get(k) for k in ("package_id", "task_id", "task_type", "report_id")},
)

sha_snapshot = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
add(
    "provenance_hash_matches_snapshot_bytes",
    (embedded or {}).get("provenance", {}).get("source_hash") == f"sha256:{sha_snapshot}" == f"sha256:{EXPECTED_HASH}",
    {"snapshot": sha_snapshot, "contract": EXPECTED_HASH},
)

ids = [a["asset_id"] for a in manifest["assets"]] + [c["claim_id"] for c in manifest["claims"]]
add("manifest_ids_unique", len(ids) == len(set(ids)), {"n": len(ids)})

bad = [
    (a["asset_id"], l)
    for a in manifest["assets"]
    for l in a["locators"]
    if snapshot[l["char_start"] : l["char_end"]] != l["quote"] or snapshot.count("\n", 0, l["char_start"]) + 1 != l["line"]
]
add("locators_resolve_in_snapshot", not bad, {"failures": bad})

add(
    "no_claim_verified",
    all(c["status"] != "verified" for c in manifest["claims"]),
    sorted({c["status"] for c in manifest["claims"]}),
)
add(
    "claims_have_evidence",
    all(bool(c.get("evidence")) for c in manifest["claims"]),
    [c["claim_id"] for c in manifest["claims"]],
)
add("report_title", payload["title"] == "KF-RESULT wp-297-01", payload["title"])
add(
    "report_tags",
    "kf-wp:wp-297-01" in payload["tags"],
    payload["tags"],
)
add(
    "payload_markdown_is_doc",
    payload["markdown"] == text,
    {"payload_chars": len(payload["markdown"]), "doc_chars": len(text)},
)
add(
    "manifest_sha_matches_outputs",
    result_file["outputs"]["asset_manifest.json"]["sha256"]
    == hashlib.sha256((OUT / "asset_manifest.json").read_bytes()).hexdigest(),
    result_file["outputs"]["asset_manifest.json"]["sha256"],
)
add(
    "single_report_scope",
    {manifest["source"]["report_id"]} == {REPORT_ID},
    manifest["source"]["report_id"],
)

for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {json.dumps(detail, ensure_ascii=False)[:160]}")
failed = [n for n, ok, _ in checks if not ok]
(OUT / "verify_delivery.json").write_text(
    json.dumps({"all_ok": not failed, "failed": failed, "checks": [{"check": n, "ok": ok, "detail": d} for n, ok, d in checks]},
               ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"all_ok={not failed} failed={failed}")
sys.exit(0 if not failed else 1)