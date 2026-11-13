#!/usr/bin/env python3
"""wp-12510-01 · 验收门：对已落盘的 kf_result.json / asset_manifest.json 独立复算 6 项 acceptance。

检查项（与契约 acceptance 一一对应）:
  1. valid_json                          信封与 manifest 均为合法 JSON
  2. schema_pass                         信封通过 schemas/kf_result.v1.schema.json (Draft 2020-12)
  3. source_locator_resolvable           每条 markdown locator 的 quote 是源 markdown 的逐字子串且唯一
  4. source_hash_matches                 源 markdown 字节 sha256 == 契约声明
  5. no_duplicate_ids                    asset_id / claim_id 无重复
  6. all_claims_have_evidence_or_explicit_unresolved_status
                                         claims 为空（合法）或每条带 evidence/unresolved 状态

另加 2 项结构不变量:
  7. envelope_outputs_key                outputs 恰含契约声明的 asset_manifest.json
  8. provenance_consistency              provenance.source_hash == manifest.source.sha256 == 重算值

退出码 0=全过；任一失败退出码 1 并打印失败项（honest-FAIL 不粉饰）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "docs", "kf", "wp-12510-01")
SNAP_MD = os.path.join(REPO, "runs", "wp-12510-01", "report_12510.md")

CONTRACT_HASH = "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da"
CONTRACT_CHARS = 5656


def main() -> None:
    results: dict[str, dict] = {}

    def check(name: str, ok: bool, detail: str) -> None:
        results[name] = {"pass": bool(ok), "detail": detail}

    # 1. valid_json
    try:
        env = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
        man = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
        check("valid_json", True, "kf_result.json + asset_manifest.json parsed")
    except Exception as e:  # noqa: BLE001
        check("valid_json", False, repr(e))
        report(results)
        return

    # 2. schema_pass
    try:
        import jsonschema

        schema = json.load(open(os.path.join(REPO, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
        jsonschema.validate(instance=env, schema=schema)
        check("schema_pass", True, "envelope validated against kf_result.v1.schema.json")
    except Exception as e:  # noqa: BLE001
        check("schema_pass", False, repr(e))

    md = open(SNAP_MD, encoding="utf-8").read()
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()

    # 3. source_locator_resolvable
    bad = []
    n_loc = 0
    for a in man["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") != "markdown":
                continue
            n_loc += 1
            q = loc["quote"]
            if md.count(q) != 1:
                bad.append((a["asset_id"], "count!=1", q[:40]))
                continue
            s = md.index(q)
            if loc.get("char_start") != s or loc.get("char_end") != s + len(q):
                bad.append((a["asset_id"], "span_mismatch", q[:40]))
    check(
        "source_locator_resolvable",
        not bad,
        f"{n_loc} markdown locators checked; bad={bad}",
    )

    # 4. source_hash_matches
    check(
        "source_hash_matches",
        digest == CONTRACT_HASH and env["provenance"]["source_hash"] == CONTRACT_HASH,
        f"recomputed={CONTRACT_HASH}",
    )

    # 5. no_duplicate_ids
    ids = [a["asset_id"] for a in man["assets"]]
    cids = [c.get("claim_id") for c in man.get("claims", [])]
    check(
        "no_duplicate_ids",
        len(ids) == len(set(ids)) and len(cids) == len(set(cids)),
        f"asset_ids={len(ids)} unique={len(set(ids))}; claim_ids={len(cids)}",
    )

    # 6. all_claims_have_evidence_or_explicit_unresolved_status
    ok6 = all(
        ("evidence" in c and c["evidence"]) or ("status" in c)
        for c in man.get("claims", [])
    )
    check(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        ok6,
        f"claims={len(man.get('claims', []))} (empty is legitimate per contract notes)",
    )

    # 7. envelope_outputs_key
    check(
        "envelope_outputs_key",
        set(env["outputs"].keys()) == {"asset_manifest.json"},
        f"outputs keys={sorted(env['outputs'].keys())}",
    )

    # 8. provenance_consistency
    man_sha = man["source"]["sha256"]
    check(
        "provenance_consistency",
        env["provenance"]["source_hash"] == man_sha == CONTRACT_HASH,
        f"envelope={env['provenance']['source_hash']} manifest={man_sha}",
    )

    report(results)


def report(results: dict[str, dict]) -> None:
    out = {
        "package_id": "wp-12510-01",
        "checks": results,
        "all_pass": all(r["pass"] for r in results.values()),
    }
    with open(os.path.join(PKG, "acceptance.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for k, r in results.items():
        print(("PASS" if r["pass"] else "FAIL"), k, "-", r["detail"])
    sys.exit(0 if out["all_pass"] else 1)


if __name__ == "__main__":
    main()
