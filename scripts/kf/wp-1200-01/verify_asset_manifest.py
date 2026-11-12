#!/usr/bin/env python3
"""wp-1200-01 独立复核器（adversarial 视角）

只吃**交付物**（asset_manifest.json / result_envelope.json）+ 重新获取的源 markdown，
不使用生成脚本的任何内部定义，重算判据：

  1) source_hash_matches   —— 对源 markdown 字节重算 sha256，与 manifest 与信封 provenance 比对
  2) valid_json            —— 两个 JSON 可解析
  3) schema_pass           —— 信封按 kf_result.v1.schema.json 校验
  4) source_locator_resolvable —— 每条 locator 的 quote 必须 == md[char_start:char_end] 且 ⊆ md，
                                  行号与 char_start 自洽；工件 anchor 必须逐字落在其行内
  5) no_duplicate_ids
  6) all_claims_have_evidence_or_explicit_unresolved_status（并校验 status 枚举、
     unresolved 必须带 unresolved_reason、evidence quote 逐字）
  7) 无 verified 标记（verification 由平台门计算）

用法：
  python3 scripts/kf/wp-1200-01/verify_asset_manifest.py [--source PATH]
退出码 0=全部 PASS；1=有 FAIL。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = "wp-1200-01"
REPORT_ID = "1200"
STATUS_ENUM = {"supported", "partially-supported", "unresolved", "refuted"}

HERE = Path(__file__).resolve().parent


def _worktree(p: Path) -> Path:
    for q in (p, *p.parents):
        if (q / ".git").exists():
            return q
    raise SystemExit("[init] 未找到工作树根（.git）")


WORKTREE = _worktree(HERE)
OUT = WORKTREE / "docs" / "kf" / PKG
SCHEMA_PATH = WORKTREE / "schemas" / "kf_result.v1.schema.json"


def fetch_source(explicit: str | None) -> tuple[str, str]:
    if explicit:
        return Path(explicit).read_text(encoding="utf-8"), f"local:{explicit}"
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r).get("access_token")
    url = f"{base}/tensor/reports/{REPORT_ID}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["markdown"], f"api:{url}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="源 markdown 路径（缺省走 API 重取）")
    args = ap.parse_args()

    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    md, src = fetch_source(args.source)
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()

    # ---- 1/2 JSON 可解析
    try:
        manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
        envelope = json.loads((OUT / "result_envelope.json").read_text(encoding="utf-8"))
        add("valid_json", True, "asset_manifest.json / result_envelope.json 解析成功")
    except Exception as e:  # noqa: BLE001
        add("valid_json", False, f"{type(e).__name__}: {e}")
        print(json.dumps({"checks": checks, "all_pass": False}, ensure_ascii=False, indent=2))
        return 1

    # ---- 3 信封 schema
    try:
        import jsonschema
        jsonschema.validate(envelope, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
        add("schema_pass", True, "kf_result.v1.schema.json 校验通过")
    except Exception as e:  # noqa: BLE001
        add("schema_pass", False, f"{type(e).__name__}: {e}")

    # ---- 4 哈希
    m_hash = manifest.get("source", {}).get("sha256")
    p_hash = envelope.get("provenance", {}).get("source_hash")
    add("source_hash_matches", m_hash == recomputed == p_hash,
        f"recomputed={recomputed} manifest={m_hash} envelope={p_hash} source={src}")

    # ---- 4' locator 可解析
    locs: list[tuple[str, dict]] = [("title", manifest["source"]["title_locator"])]
    locs += [(f"schema:{e['ref_id']}", e["locator"]) for e in manifest.get("registered_schema_elements", [])]
    locs += [(f"metric:{m['metric_id']}", m["locator"]) for m in manifest.get("registered_metric_locators", [])]
    for a in manifest.get("attachments", []):
        for i, loc in enumerate(a.get("mentioned_at", [])):
            locs.append((f"attach:{a['asset_id']}#{i}", loc))

    bad: list[str] = []
    for name, loc in locs:
        quote = loc.get("quote", "")
        span = md[loc.get("char_start", -1):loc.get("char_end", -1)]
        line_ok = md.count("\n", 0, loc.get("char_start", 0)) + 1 == loc.get("line_start")
        if not (quote and quote == span and quote in md and line_ok):
            bad.append(name)
    add("source_locator_resolvable", not bad,
        f"{len(locs)} 个 locator 逐字可解析" if not bad else f"失败: {bad}")

    anchor_bad = []
    for a in manifest.get("attachments", []):
        for loc in a.get("mentioned_at", []):
            if not (loc.get("anchor_text") == a["ref"]
                    and loc.get("char_start", 0) <= loc.get("anchor_char_start", -1)
                    and loc.get("anchor_char_end", -1) <= loc.get("char_end", -1)
                    and loc.get("anchor_text", "") == md[loc.get("anchor_char_start", -1):loc.get("anchor_char_end", -1)]):
                anchor_bad.append(a.get("asset_id"))
    add("artifact_anchor_in_locator", not anchor_bad,
        "工件 token 逐字落在引用行内" if not anchor_bad else f"失败: {anchor_bad}")

    # ---- 5 id 唯一（manifest 全域 + 信封 claims 与 manifest claims 一致）
    ids: list[str] = ["asset-report-1200"]
    ids += [e["ref_id"] for e in manifest.get("registered_schema_elements", [])]
    ids += [m["metric_id"] for m in manifest.get("registered_metric_locators", [])]
    ids += [a["asset_id"] for a in manifest.get("attachments", [])]
    ids += [c["claim_id"] for c in manifest.get("claims", [])]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    same_claims = envelope.get("claims") == manifest.get("claims")
    add("no_duplicate_ids", not dup and same_claims,
        f"{len(ids)} 个 id 唯一；信封 claims 与 manifest claims 一致={same_claims}"
        if not dup else f"重复: {dup}")

    # ---- 6 claims 证据/未决
    probs = []
    for c in envelope.get("claims", []):
        if c.get("status") not in STATUS_ENUM:
            probs.append(f"{c.get('claim_id')}:status")
        ev = c.get("evidence", [])
        if not ev and not c.get("unresolved_reason"):
            probs.append(f"{c.get('claim_id')}:no-evidence-no-reason")
        if c.get("status") == "unresolved" and not c.get("unresolved_reason"):
            probs.append(f"{c.get('claim_id')}:unresolved-no-reason")
        for e in ev:
            if e.get("quote") not in md:
                probs.append(f"{c.get('claim_id')}:quote-not-verbatim")
    add("all_claims_have_evidence_or_explicit_unresolved_status", not probs,
        f"{len(envelope.get('claims', []))} 条 claim 合规" if not probs else f"问题: {probs}")

    # ---- 7 无 verified 标记
    add("no_verified_marking",
        '"verified": true' not in json.dumps(envelope, ensure_ascii=False).replace('"verified":true', '"verified": true'),
        "未标记 verified（verification 由平台门计算）")

    # ---- 范围：只登记 report 1200
    add("report_id_scope", envelope.get("report_id") == REPORT_ID and manifest.get("source", {}).get("report_id") == REPORT_ID,
        f"report_id={envelope.get('report_id')}")

    result = {"checks": checks, "all_pass": all(c["result"] == "PASS" for c in checks),
              "source_used": src, "recomputed_hash": recomputed}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())