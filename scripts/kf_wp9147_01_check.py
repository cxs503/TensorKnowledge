"""wp-9147-01 acceptance checker: recompute all six contract acceptance items from artifacts.

Each item is computed, not asserted. Results land in docs/kf/wp-9147-01/acceptance_check.json,
which is the machine source of the report's section ⑥ table (rendered by scripts/kf_wp9147_01_result.py).

Checks
  1 valid_json                : asset_manifest.json + kf_result.json parse as JSON
  2 schema_pass               : both validate with jsonschema (rebound manifest pin + kf_result.v1)
  3 source_locator_resolvable : every quote re-slices to itself at its declared char span, count==1,
                                spans inside the document, line spans consistent with the slice
  4 source_hash_matches       : sha256(source.md bytes) == manifest hash == contract hash
  5 no_duplicate_ids          : asset_id unique
  6 all_claims_have_evidence_or_explicit_unresolved_status : vacuous here (claims == []), reported
                                as such instead of being dressed up as "evidence completeness proven"

Usage: python3 scripts/kf_wp9147_01_check.py   (exit 0 = all pass, 1 = any fail)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import sys

import jsonschema

PKG = pathlib.Path("docs/kf/wp-9147-01")
CONTRACT_HASH = "754d613193b8da4880f56371095812b6865d4d376bdca5edb8ab4f4ceb6d0ff6"


def main() -> int:
    items = []

    def add(item: str, ok: bool, evidence: str) -> None:
        items.append({"item": item, "pass": bool(ok), "evidence": evidence})

    # ---- 1 valid_json
    try:
        manifest = json.loads((PKG / "asset_manifest.json").read_text())
        envelope = json.loads((PKG / "kf_result.json").read_text())
        add("valid_json", True, "json.loads OK on asset_manifest.json 与 kf_result.json")
    except Exception as exc:  # noqa: BLE001
        print("FATAL: invalid json:", exc, file=sys.stderr)
        return 1

    # ---- 2 schema_pass
    try:
        ms = json.loads((PKG / "asset_manifest.wp-9147-01.schema.json").read_text())
        jsonschema.validate(manifest, ms)
        jsonschema.validate(envelope, json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text()))
        add("schema_pass", True,
            "asset_manifest 过 asset_manifest.wp-9147-01.schema.json（由仓内 asset_manifest.v1 派生）；"
            "信封过 schemas/kf_result.v1.schema.json（jsonschema.validate）")
    except Exception as exc:  # noqa: BLE001
        add("schema_pass", False, f"jsonschema.validate 失败: {exc}")

    # ---- 3 source_locator_resolvable
    md = (PKG / "source.md").read_bytes().decode("utf-8")
    lines = md.splitlines()
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        s, e = loc["start_char"], loc["end_char"]
        ok = (
            md[s:e] == q
            and md.count(q) == 1
            and 0 <= s < e <= len(md)
            and loc["unique"] is True
            and (q == md if loc["method"] == "document"
                 else q == "\n".join(lines[loc["start_line"]:loc["end_line"] + 1]))
        )
        if not ok:
            bad.append(a["asset_id"])
    add("source_locator_resolvable", not bad,
        f'{len(manifest["assets"])} 个资产的引文全部按声明 [start_char,end_char) 逐字切回、'
        f'唯一、行窗自洽；失败项={bad or "无"}')

    # ---- 4 source_hash_matches
    recomputed = hashlib.sha256((PKG / "source.md").read_bytes()).hexdigest()
    h_ok = (
        recomputed == manifest["source"]["hash"] == CONTRACT_HASH
        and envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
        and (PKG / "sha256.txt").read_text().strip() == "sha256:" + CONTRACT_HASH
    )
    add("source_hash_matches", h_ok,
        f"sha256(source.md)={recomputed[:16]}… 与 manifest.source.hash / 契约 754d6131… 及 "
        f"provenance.source_hash 三方一致={h_ok}")

    # ---- 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)),
        f'{len(ids)} 个 asset_id，去重后 {len(set(ids))} 个')

    # ---- 6 claims evidence / explicit status
    empty = manifest["claims"] == []
    all_ok = all(("evidence_locator" in c) or c.get("status") for c in manifest["claims"])
    add("all_claims_have_evidence_or_explicit_unresolved_status", empty or all_ok,
        ("claims=[] （契约允许，本工序不抽取 claim）→ 该项**空真**成立，"
         "不等于证据完备性已被证明" if empty else f"{len(manifest['claims'])} 条 claim 均带定位或状态"))

    total = len(items)
    passed = sum(1 for i in items if i["pass"])
    out = {
        "package_id": "wp-9147-01",
        "report_id": "9147",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "schema_source": "docs/kf/wp-9147-01/asset_manifest.wp-9147-01.schema.json + "
                         "schemas/kf_result.v1.schema.json",
        "items": items,
        "passed": passed,
        "total": total,
        "all_pass": passed == total,
    }
    (PKG / "acceptance_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    for i in items:
        print(("PASS " if i["pass"] else "FAIL ") + i["item"] + " :: " + i["evidence"])
    print(f"{passed}/{total} acceptance items pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())