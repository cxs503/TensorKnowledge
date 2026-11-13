#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-174-01 独立自检器：不信任生产脚本的自述，重新取源、重算哈希、逐条反查定位。

对应合同 acceptance（逐条落成机器可判的 check）：
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

与平台门（ops/knowledge_factory/gates.py）语义一致但**独立实现**：
  * 哈希真值从 API 重新拉 tensor_reports.markdown 现算，不读 producer 产物里的值；
  * 定位率按「quote 逐字子串命中」判定，不做换行归一化；
  * 引用计数用另一条代码路径（str.count）复核，交叉检验扫描器。

产物：artifacts/kf/wp-174-01/verification.json
退出码：0=全部 check 通过；1=有失败（如实反映，不粉饰）
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "..", "docs", "kf", "wp-174-01")
PKG = os.path.abspath(PKG)

PACKAGE_ID = "wp-174-01"
TASK_TYPE = "01"
REPORT_ID = "174"
CONTRACT_SOURCE_HASH = (
    "sha256:80399c1b032528fcf6e3e1a9cf08ad6b68bb68920b622223fc5062ec4f0287e3"
)
CONTRACT_CHARS = 4258
MIN_QUOTE_CHARS = 12  # 与平台 gates.min_quote_chars 一致


def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def fetch_markdown() -> tuple:
    """独立重取源（与生产脚本不同进程、不同读取时刻）。"""
    import urllib.request

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + "/tensor/reports/" + REPORT_ID,
        headers={"Authorization": "Bearer " + token},
    )
    rec = json.load(urllib.request.urlopen(req))
    return rec["markdown"], rec


def collect_quotes(node, path="$") -> list:
    """递归收集 manifest 中所有 locator_quote，用于逐字反查。"""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "locator_quote" and isinstance(v, str):
                out.append({"path": path + "/" + k, "quote": v})
            else:
                out.extend(collect_quotes(v, path + "/" + k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(collect_quotes(v, "%s[%d]" % (path, i)))
    return out


def collect_ids(node, path="$") -> list:
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("ref_id", "claim_id", "ordinal") and isinstance(v, (str, int)):
                out.append((path + "/" + k, str(v)))
            else:
                out.extend(collect_ids(v, path + "/" + k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(collect_ids(v, "%s[%d]" % (path, i)))
    return out


def main() -> int:
    checks = []

    def chk(cid, ok, **detail):
        checks.append({"check": cid, "ok": bool(ok), **detail})

    # --- c1 valid_json -----------------------------------------------------
    try:
        with open(os.path.join(PKG, "kf_result.json"), encoding="utf-8") as f:
            env = json.load(f)
        with open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8") as f:
            man = json.load(f)
        chk("c1_valid_json", True, files=["kf_result.json", "asset_manifest.json"])
    except Exception as e:  # noqa: BLE001
        chk("c1_valid_json", False, error=repr(e))
        json.dump({"checks": checks, "ok": False}, open(os.path.join(PKG, "verification.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 1

    # --- c2 schema_pass ----------------------------------------------------
    schema_path = os.path.join(PKG, "schema", "kf_result.v1.schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    schema_sha = sha256_text(open(schema_path, encoding="utf-8").read())
    try:
        import jsonschema

        val = jsonschema.Draft202012Validator(schema)
        errs = sorted(val.iter_errors(env), key=lambda e: list(e.path))
        chk("c2_schema_pass", not errs,
            validator="jsonschema.Draft202012Validator",
            schema_sha256=schema_sha,
            n_errors=len(errs),
            first_error=(None if not errs else {
                "path": "/".join(str(p) for p in errs[0].path),
                "message": errs[0].message[:200]}))
    except ImportError:
        need = ("package_id", "task_type", "report_id", "provenance", "outputs")
        miss = [k for k in need if k not in env]
        chk("c2_schema_pass", not miss, degraded=True, validator="not_installed", missing=miss)

    # --- c3 identity -------------------------------------------------------
    bad = []
    if env.get("package_id") != PACKAGE_ID:
        bad.append("package_id")
    if str(env.get("report_id")) != REPORT_ID:
        bad.append("report_id")
    if str(env.get("task_type")) != TASK_TYPE:
        bad.append("task_type")
    if man.get("package_id") != PACKAGE_ID:
        bad.append("manifest.package_id")
    chk("c3_identity", not bad, mismatched=bad)

    # --- c4 source_hash_matches（独立重取重算） -----------------------------
    md, record = fetch_markdown()
    actual = sha256_text(md)
    claimed = (env.get("provenance") or {}).get("source_hash")
    chk("c4_source_hash_matches", claimed == actual == CONTRACT_SOURCE_HASH,
        claimed=claimed, recomputed=actual, contract=CONTRACT_SOURCE_HASH)
    chk("c4b_source_field", (env.get("provenance") or {}).get("source_field") == "markdown",
        field=(env.get("provenance") or {}).get("source_field"))
    chk("c4c_source_chars", len(md) == CONTRACT_CHARS == man["source_asset"]["size"]["chars"],
        recomputed_chars=len(md), contract_chars=CONTRACT_CHARS,
        manifest_chars=man["source_asset"]["size"]["chars"])

    # --- c5 source_locator_resolvable（quote 逐字反查） --------------------
    quotes = collect_quotes(man)
    resolved, missing, short = [], [], []
    for q in quotes:
        text = q["quote"] or ""
        if len(text) < MIN_QUOTE_CHARS:
            short.append({**q, "chars": len(text)})
        elif text in md:
            resolved.append(q["path"])
        else:
            missing.append(q)
    chk("c5_source_locator_resolvable", not missing and not short,
        checked=len(quotes), resolved=len(resolved),
        locator_rate=(len(resolved) / len(quotes)) if quotes else None,
        missing=[m["path"] for m in missing][:5],
        too_short=[s["path"] for s in short][:5])

    # --- c5b claims 证据/显式未解析 ----------------------------------------
    claims = env.get("claims") or []
    offenders = []
    for c in claims:
        ev = c.get("evidence") or []
        if not ev and not (c.get("status") == "unresolved"
                           and str(c.get("unresolved_reason", "")).strip()):
            offenders.append(c.get("claim_id"))
    chk("c5c_all_claims_have_evidence_or_explicit_unresolved_status", not offenders,
        n_claims=len(claims), offenders=offenders,
        note="01 工序合同允许 claims=[]（不抽取），零条即为完整结果")

    # --- c6 no_duplicate_ids ----------------------------------------------
    ids = collect_ids(man)
    vals = [v for _, v in ids]
    dup = sorted({v for v in vals if vals.count(v) > 1})
    claim_ids = [c.get("claim_id") for c in claims]
    foreign = [c for c in claim_ids if not str(c).startswith(REPORT_ID)]
    chk("c6_no_duplicate_ids", not dup and not foreign,
        n_ids=len(vals), duplicates=dup[:5], claim_namespace_violations=foreign[:5])

    # --- c7 引用计数交叉复核（另一条代码路径） ------------------------------
    # 计数口径=反引号包裹的字面量（manifest.occurrences 的语义）；
    # 裸子串计数会被更长的绝对路径包含而虚高，故同时记 raw_substring_count 备查。
    count_bad, cross = [], []
    for r in man["referenced_artifacts"]:
        literal = "`" + r["raw_text"] + "`"
        direct = md.count(literal)
        cross.append({"ref_id": r["ref_id"], "manifest": r["occurrences"],
                      "backticked_count": direct,
                      "raw_substring_count": md.count(r["raw_text"])})
        if direct != r["occurrences"]:
            count_bad.append({"ref_id": r["ref_id"], "manifest": r["occurrences"],
                              "backticked_count": direct})
    chk("c7_occurrence_counts_crosschecked", not count_bad,
        scope="backticked_literal", mismatches=count_bad, counts=cross)

    # --- c10 结构索引分割不变量：Σ 段字符 == 源 markdown 字符数 ------------
    sec_sum = sum(s["chars"] for s in man["sections"])
    chk("c10_sections_partition_markdown", sec_sum == len(md),
        section_chars_sum=sec_sum, markdown_chars=len(md),
        delta=len(md) - sec_sum,
        note="段字符含分隔换行；相等 ⇒ 索引无遗漏无重叠")

    # --- c8 附件扫描复核 ---------------------------------------------------
    n_img = md.count("![")
    chk("c8_attachments_recount", (man["attachments"]["count"] == 0
                                   and len(record.get("figures") or []) == 0
                                   and n_img == 0),
        manifest_count=man["attachments"]["count"],
        record_figures=len(record.get("figures") or []),
        markdown_image_hits=n_img)

    # --- c9 边界：只登记了 174 ---------------------------------------------
    touched = set(man["boundary"]["report_ids_read"]) | set(man["boundary"]["report_ids_written"])
    chk("c9_boundary_single_report", touched == {REPORT_ID}, touched=sorted(touched))

    ok = all(c["ok"] for c in checks)
    out = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"),
        "verifier": "scripts/kf/wp_174_01_verify.py",
        "independence": {
            "source_refetched": True,
            "hash_recomputed_from_api_response": True,
            "manifest_self_reported_hash_not_trusted": True,
            "note": "平台门仍为最终裁决方；本文件只是本包自检，不构成 verified 标记",
        },
        "gate_replica_reference": {
            "platform_gate_source": "TensorPlatform ops/knowledge_factory/gates.py",
            "min_quote_chars": MIN_QUOTE_CHARS,
        },
        "checks": checks,
        "ok": ok,
        "n_checks": len(checks),
        "n_failed": sum(1 for c in checks if not c["ok"]),
    }
    with open(os.path.join(PKG, "verification.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"])
    print("ok =", ok, "| failed =", out["n_failed"], "/", out["n_checks"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())