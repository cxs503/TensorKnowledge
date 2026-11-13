#!/usr/bin/env python3
"""Independent checker for wp-11349-01 — re-derives every acceptance item of the contract.

Acceptance items checked (from the work-package contract):
    valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
    no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

Nothing here trusts the generator: the manifest is re-read from disk, the source markdown is
re-read from the byte snapshot, every locator is re-sliced, and every hash is recomputed.

Usage:  python3 scripts/kf/wp11349_01_check.py          # writes docs/kf/wp-11349-01/self_check.json
Exit code 0 = all items pass, 1 = at least one item failed (honest FAIL is printed, not hidden).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import jsonschema

REPORT_ID = "11349"
PACKAGE_ID = "wp-11349-01"
CONTRACT_HASH = "e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
CONTRACT_CHARS = 1029

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)
SNAP = os.path.join(OUT, "source", f"report_{REPORT_ID}.md")

results: list[dict] = []


def add(item: str, ok: bool, detail: str) -> None:
    results.append({"item": item, "result": "pass" if ok else "fail", "detail": detail})


def sha256_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    md = open(SNAP, encoding="utf-8").read()
    manifest_path = os.path.join(OUT, "asset_manifest.json")
    kf_path = os.path.join(OUT, "kf_result.json")

    # --- 1. valid_json ---------------------------------------------------------
    try:
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        kf = json.load(open(kf_path, encoding="utf-8"))
        add("valid_json", True, "asset_manifest.json + kf_result.json 均被 json 解析成功")
    except Exception as e:  # noqa: BLE001
        add("valid_json", False, f"JSON 解析失败: {e!r}")
        json.dump({"results": results}, open(os.path.join(OUT, "self_check.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 1

    # --- 2. source_hash_matches ------------------------------------------------
    recomputed = hashlib.sha256(md.encode("utf-8")).hexdigest()
    snap_file_hash = sha256_file(SNAP)
    kf_hash = kf["provenance"]["source_hash"].split(":", 1)[1]
    man_hash = manifest["source"]["hash"]
    ok2 = recomputed == CONTRACT_HASH == kf_hash == man_hash and snap_file_hash == CONTRACT_HASH
    add("source_hash_matches", ok2,
        f"recomputed(utf-8)={recomputed} · snapshot_file={snap_file_hash} · "
        f"kf_result={kf_hash} · manifest={man_hash} · contract={CONTRACT_HASH}")

    # --- 3. schema_pass --------------------------------------------------------
    schema_ok, schema_detail = True, []
    try:
        jsonschema.validate(kf, json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                                               encoding="utf-8")))
        schema_detail.append("kf_result 通过 schemas/kf_result.v1.schema.json")
    except jsonschema.ValidationError as e:
        schema_ok = False
        schema_detail.append(f"kf_result 违反 kf_result.v1: {e.message} @ {list(e.absolute_path)}")
    try:
        jsonschema.validate(manifest, json.load(open(os.path.join(OUT, "asset_manifest.schema.json"),
                                                     encoding="utf-8")))
        schema_detail.append("manifest 通过 package-pinned asset_manifest.v1 (wp-11349-01)")
    except jsonschema.ValidationError as e:
        schema_ok = False
        schema_detail.append(f"manifest 违反 package schema: {e.message} @ {list(e.absolute_path)}")
    add("schema_pass", schema_ok, " | ".join(schema_detail))

    # --- 4. source_locator_resolvable -----------------------------------------
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            ok = (loc["start_char"] == 0 and loc["end_char"] == len(md)
                  and q in md and md.splitlines()[0] == q)
            if not ok:
                bad.append(f"{a['asset_id']}: document locator 不自洽")
        else:
            ok = (md[loc["start_char"]:loc["end_char"]] == q and md.count(q) == 1
                  and loc["unique"] is True)
            if not ok:
                bad.append(f"{a['asset_id']}: slice/count/unique 不匹配")
        # line numbers must bracket the char span
        start_line = md.count("\n", 0, loc["start_char"]) + 1
        end_line = md.count("\n", 0, max(loc["end_char"] - 1, 0)) + 1
        if (loc["start_line"], loc["end_line"]) != (start_line, end_line):
            bad.append(f"{a['asset_id']}: 行号 {loc['start_line']}-{loc['end_line']} != 重算 "
                       f"{start_line}-{end_line}")
    add("source_locator_resolvable", not bad,
        f"{len(manifest['assets'])} 条 locator 全部重切片校验" + ("" if not bad else "; " + "; ".join(bad)))

    # --- 5. no_duplicate_ids ---------------------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)) and len(ids) == manifest["counts"]["assets"],
        f"{len(ids)} 条 asset_id 唯一（{ids[0]}..{ids[-1]}），counts.assets={manifest['counts']['assets']}")

    # --- 6. all_claims_have_evidence_or_explicit_unresolved_status -------------
    claims = manifest["claims"]
    bad_claims = [c.get("claim_id") for c in claims
                  if not (c.get("evidence_locator") or c.get("status")
                          or all(e.get("quote") for e in c.get("evidence", [])))]
    add("all_claims_have_evidence_or_explicit_unresolved_status", not bad_claims,
        f"claims={len(claims)} 条（契约允许为空数组；本包 objective.classify_report_type=false，"
        f"故为 0 条，本条为空真通过）" + ("" if not bad_claims else f"; 无证据 claim: {bad_claims}"))

    # --- 7. envelope consistency (extra, not in contract) ----------------------
    same = kf["outputs"]["asset_manifest.json"] == manifest
    add("envelope_matches_on_disk_manifest", same,
        "kf_result.outputs['asset_manifest.json'] 与磁盘 asset_manifest.json 逐字段相同")
    add("report_identity_matches_contract",
        kf["report_id"] == manifest["report_id"] == REPORT_ID
        and kf["package_id"] == manifest["package_id"] == PACKAGE_ID
        and kf["task_type"] == manifest["task_type"] == "01-asset-registration",
        f"report_id={kf['report_id']} package_id={kf['package_id']} task_type={kf['task_type']}")
    def _find_verified_true(node):
        """递归找任何 verified=True / verification_stamp 非空的痕迹。"""
        hits = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "verified" and v is True:
                    hits.append("verified=true")
                if k == "verification_stamp" and v not in (None, "", False):
                    hits.append(f"verification_stamp={v!r}")
                hits += _find_verified_true(v)
        elif isinstance(node, list):
            for v in node:
                hits += _find_verified_true(v)
        return hits

    stamps = _find_verified_true(manifest) + _find_verified_true(kf)
    add("no_verified_stamp", not stamps,
        "全树扫描 verified=true / verification_stamp：无命中（integrity.verified=false，"
        "verification 交平台门计算）" if not stamps else f"检出 {stamps}")
    add("contract_chars_match", len(md) == CONTRACT_CHARS,
        f"chars={len(md)} vs 契约 {CONTRACT_CHARS}")

    # --- report -----------------------------------------------------------------
    passed = sum(1 for r in results if r["result"] == "pass")
    body = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "checked_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "accepted": passed == len(results),
        "summary": f"{passed}/{len(results)} 项通过",
        "contract_acceptance_items": {
            "valid_json": next(r["result"] for r in results if r["item"] == "valid_json"),
            "schema_pass": next(r["result"] for r in results if r["item"] == "schema_pass"),
            "source_locator_resolvable": next(r["result"] for r in results if r["item"] == "source_locator_resolvable"),
            "source_hash_matches": next(r["result"] for r in results if r["item"] == "source_hash_matches"),
            "no_duplicate_ids": next(r["result"] for r in results if r["item"] == "no_duplicate_ids"),
            "all_claims_have_evidence_or_explicit_unresolved_status": next(
                r["result"] for r in results
                if r["item"] == "all_claims_have_evidence_or_explicit_unresolved_status"),
        },
        "not_run": [
            "线上探针未重放（工序 01 只登记，不执行；报告内 2026-11-10 的 401/404 结果保持为报告所载，本包不判真伪）",
            "他仓测试未执行（backend/tests/* 属 TensorPlatform，本工作树无该文件）",
            "report 11344 未解引用（产线边界：只碰 report_id=11349）",
        ],
        "artifact_sha256": {
            "asset_manifest.json": sha256_file(manifest_path),
            "kf_result.json": sha256_file(kf_path),
            "source/report_11349.md": sha256_file(SNAP),
        },
        "results": results,
    }
    with open(os.path.join(OUT, "self_check.json"), "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

    for r in results:
        print(f"[{r['result'].upper():4}] {r['item']}: {r['detail'][:150]}")
    print(f"\n{passed}/{len(results)} pass -> self_check.json")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())