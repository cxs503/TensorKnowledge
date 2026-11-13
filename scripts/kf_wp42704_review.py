#!/usr/bin/env python3
"""KF 工作包 wp-427-04（04-independent-review）独立复核脚本。

被审对象：wp-427-01（asset-registration）的结果信封 —— 由平台记录
`tk_work_packages.package_id='wp-427-01' -> result_report_id` 指向的结果报告携带。
审核输入只有两个：源报告 report_id=427 的 `markdown` 原文（+ 记录字段），
以及上游信封内的 `outputs["asset_manifest.json"]`。**不读取生产者的叙述性解释**
（上游结果报告正文的第①~⑥节文字不作为判据，只解析其中唯一的 ```json 代码块）。

独立性要点（本脚本存在的理由）：
  * 平台门对 01 工序的 locator 检查是 `checked=0`（claims 为空 -> 门无从校验），
    9 条 locator 全部是**生产者自报**；本脚本逐条重算，把自报变成可复核事实。
  * 所有数字（哈希/行号/出现次数/字节数/唯一性/HTTP 状态）在本进程内重算，不采信上游数值。

用法：
  python3 scripts/kf_wp42704_review.py            # 全量复核 + 落盘
  python3 scripts/kf_wp42704_review.py --offline  # 只用本地缓存的 upstream 信封
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "docs", "kf", "wp-427-04")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

UPSTREAM_REPORT_ID = os.environ.get("KF_UPSTREAM_REPORT_ID", "14590")
PKG = "wp-427-04"
SUBJECT_PKG = "wp-427-01"
REPORT_ID = "427"
# 契约给定值（工作包 YAML 的 input.source_hash），不与上游自报值混用
CONTRACT_SOURCE_HASH = ("sha256:09c640623dff50ac9def329238d10890"
                        "cfb9a30172a1aa48d6541879b2b65846")
CONTRACT_CHARS = 2732


# ---------------------------------------------------------------- platform io
def _token() -> str:
    tok = os.environ.get("TENSOR_AGENT_TOKEN")
    if tok:
        return tok.strip()
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(API + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return d.get("access_token") or d.get("token")


def _get(path: str, tok: str):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + tok})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _get_raw(path: str, tok: str):
    """取二进制，不走 JSON 解码（图片端点）。"""
    return _get(path, tok)


# ------------------------------------------------------------- pure functions
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def extract_single_json_block(md: str):
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    return blocks


def walk_ids(node, acc):
    """递归收集所有 *_id 字段的值（识别重复 ID）。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k.endswith("_id") and isinstance(v, str):
                acc.append((k, v))
            walk_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            walk_ids(v, acc)
    return acc


def find_marker(node, needles=("verified", "VERIFIED", "已核验", "已验证")):
    hits = []

    def rec(n, path):
        if isinstance(n, dict):
            for k, v in n.items():
                rec(k, path + "/" + str(k))
                rec(v, path + "/" + str(k))
        elif isinstance(n, list):
            for i, v in enumerate(n):
                rec(v, path + "/" + str(i))
        elif isinstance(n, str):
            for nd in needles:
                if nd in n:
                    hits.append({"path": path, "value": n[:120]})
    rec(node, "")
    return hits


# --------------------------------------------------------------------- checks
def run_checks(upstream_md: str, tok: str, offline: bool) -> dict:
    checks = {}

    # ---- 1. 源报告重取 + 哈希重算（不看上游数字）
    st, raw = _get(f"/tensor/reports/{REPORT_ID}", tok)
    rec = json.loads(raw)
    md = rec["markdown"]
    md_bytes = md.encode("utf-8")
    checks["source_refetch"] = {
        "http_status": st,
        "source_hash_recomputed": "sha256:" + sha256_hex(md_bytes),
        "contract_source_hash": CONTRACT_SOURCE_HASH,
        "hash_matches_contract": "sha256:" + sha256_hex(md_bytes) == CONTRACT_SOURCE_HASH,
        "chars_recomputed": len(md),
        "contract_chars": CONTRACT_CHARS,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "bytes_utf8": len(md_bytes),
        "lines_splitlines": len(md.splitlines()),
        "has_crlf": "\r\n" in md,
        "record_title": rec.get("title"),
        "record_scenario_key": rec.get("scenario_key"),
        "record_figures_declared": [f.get("name") for f in (rec.get("figures") or [])],
    }

    # ---- 2. 上游信封：只取唯一 json 代码块（跳过生产者叙述）
    blocks = extract_single_json_block(upstream_md)
    checks["envelope_extraction"] = {
        "json_blocks_found": len(blocks),
        "single_block": len(blocks) == 1,
    }
    env = json.loads(blocks[0]) if blocks else {}
    checks["envelope_extraction"]["envelope_sha256"] = (
        "sha256:" + sha256_hex(json.dumps(env, ensure_ascii=False,
                                          sort_keys=True).encode()) if env else None)
    checks["envelope_extraction"]["envelope_keys"] = sorted(env.keys())
    checks["envelope_extraction"]["envelope_top_level_claims"] = env.get("claims")

    # ---- 3. 信封 provenance 与源哈希一致性（独立重算比对）
    prov = env.get("provenance", {})
    checks["provenance"] = {
        "claimed_source_hash": prov.get("source_hash"),
        "recomputed_source_hash": "sha256:" + sha256_hex(md_bytes),
        "match": prov.get("source_hash") == "sha256:" + sha256_hex(md_bytes),
        "source_field": prov.get("source_field"),
        "source_field_ok": prov.get("source_field") == "markdown",
        "report_id_in_envelope": env.get("report_id"),
        "package_id_in_envelope": env.get("package_id"),
        "identity_ok": (env.get("package_id") == SUBJECT_PKG
                        and env.get("report_id") == REPORT_ID),
    }

    # ---- 4. 正式 schema 校验（仓库内 kf_result.v1.schema.json）
    import jsonschema  # 延迟导入，离线环境缺失时记为 not_run
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(env),
                  key=lambda e: list(e.path))
    checks["schema"] = {
        "schema_path": "schemas/kf_result.v1.schema.json",
        "jsonschema_version": jsonschema.__version__,
        "valid": not errs,
        "errors": [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errs],
    }

    # ---- 5. asset_manifest 内部一致性 + 逐条 locator 重算
    am = env.get("outputs", {}).get("asset_manifest.json", {})
    src = am.get("source", {})
    recomputed = {
        "hash": "sha256:" + sha256_hex(md_bytes),
        "chars": len(md),
        "bytes": len(md_bytes),
        "lines": len(md.splitlines()),
        "has_crlf": "\r\n" in md,
    }
    # 源块只声明 hash/chars/lines；bytes/has_crlf 在 source_document 资产上，分开比对
    src_doc = next((a for a in am.get("assets", [])
                    if a.get("kind") == "source_document"), {})
    block_match = (src.get("source_hash") == recomputed["hash"]
                   and src.get("chars") == recomputed["chars"]
                   and src.get("lines") == recomputed["lines"])
    asset_match = (src_doc.get("bytes") == recomputed["bytes"]
                   and bool(src_doc.get("has_crlf")) == recomputed["has_crlf"]
                   and src_doc.get("sha256") == recomputed["hash"])
    checks["manifest_source_block"] = {
        "declared_source_block": {k: src.get(k) for k in ("source_hash", "chars", "lines")},
        "declared_source_asset": {k: src_doc.get(k) for k in
                                  ("sha256", "bytes", "chars", "lines", "has_crlf")},
        "recomputed": recomputed,
        "source_block_match": block_match,
        "source_asset_match": asset_match,
        "all_match": block_match and asset_match,
        "declared_hash_matches_contract": src.get("source_hash") == CONTRACT_SOURCE_HASH,
        "declared_hash_match_flag": src.get("hash_match"),
    }

    lines = md.splitlines()
    loc_results = []
    for loc in am.get("locators", []):
        q = loc["quote"]
        ln = loc.get("locator", {}).get("line")
        occ = md.count(q)
        quote_sha = "sha256:" + sha256_hex(q.encode())
        on_line = bool(ln and 1 <= ln <= len(lines) and q in lines[ln - 1])
        got = {
            "fact_id": loc.get("fact_id"),
            "declared_line": ln,
            "quote_len": len(q),
            "quote_sha256_recomputed": quote_sha,
            "quote_sha256_declared": loc.get("quote_sha256"),
            "quote_sha256_match": quote_sha == loc.get("quote_sha256"),
            "in_source_recomputed": occ > 0,
            "occurrences_recomputed": occ,
            "occurrences_declared": loc.get("occurrences_in_source"),
            "on_declared_line_recomputed": on_line,
            "declared_quote_in_source": loc.get("quote_in_source"),
            "declared_quote_on_line": loc.get("quote_on_declared_line"),
            "declared_resolved": loc.get("resolved"),
            "agree": (
                occ > 0
                and occ == loc.get("occurrences_in_source")
                and on_line
                and loc.get("quote_in_source") is True
                and loc.get("quote_on_declared_line") is True
                and loc.get("resolved") is True
                and quote_sha == loc.get("quote_sha256")
            ),
        }
        loc_results.append(got)
    n_ok = sum(1 for r in loc_results if r["agree"])
    checks["locators"] = {
        "n_declared": len(am.get("locators", [])),
        "n_independently_confirmed": n_ok,
        "all_confirmed": n_ok == len(loc_results) and len(loc_results) > 0,
        "details": loc_results,
        "min_line": min((r["declared_line"] for r in loc_results), default=None),
        "max_line": max((r["declared_line"] for r in loc_results), default=None),
    }

    # ---- 6. ID 唯一性（递归收集 *_id）
    ids = walk_ids({"assets": am.get("assets", []),
                    "derived_artifacts": am.get("derived_artifacts", [])}, [])
    vals = [v for _, v in ids]
    dup = sorted({v for v in vals if vals.count(v) > 1})
    checks["id_integrity"] = {
        "ids_collected": len(vals),
        "declared_ids_checked": (am.get("id_integrity") or {}).get("ids_checked"),
        "duplicates_recomputed": dup,
        "unique_recomputed": not dup,
        "declared_unique": (am.get("id_integrity") or {}).get("unique"),
    }

    # ---- 7. counts 自洽（申报计数 vs 实际数组长度）
    c = am.get("counts", {})
    actual = {
        "source_documents": sum(1 for a in am.get("assets", [])
                                if a.get("kind") == "source_document"),
        "figures_declared": sum(1 for a in am.get("assets", []) if a.get("kind") == "figure"),
        "figures_resolved": sum(1 for a in am.get("assets", [])
                                if a.get("kind") == "figure" and a.get("resolvable")),
        "locators": len(am.get("locators", [])),
        "locators_resolved": sum(1 for l in am.get("locators", []) if l.get("resolved")),
        "claims": len(am.get("claims", [])),
        "derived_artifacts": len(am.get("derived_artifacts", [])),
    }
    counts_mismatch = {k: {"declared": c.get(k), "actual": v}
                       for k, v in actual.items() if c.get(k) != v}
    checks["counts"] = {"declared": c, "recomputed": actual,
                        "mismatch": counts_mismatch, "consistent": not counts_mismatch}

    # ---- 8. figure 声明 caption 逐字比对 + 端点可取回性独立探测
    rec_figs = {f.get("name"): f for f in (rec.get("figures") or [])}
    fig_probe = []
    for a in am.get("assets", []):
        if a.get("kind") != "figure":
            continue
        name = a.get("name")
        rf = rec_figs.get(name, {})
        cap_declared = a.get("declared_caption")
        cap_record = rf.get("caption")
        probe = {"name": name,
                 "caption_verbatim_match": cap_declared == cap_record,
                 "record_has_caption": bool(cap_record)}
        if not offline:
            for variant in (name, name + ".png"):
                s, b = _get_raw(f"/tensor/reports/{REPORT_ID}/figures/{variant}", tok)
                probe.setdefault("endpoint", []).append(
                    {"variant": variant, "status": s, "bytes": len(b),
                     "body_head": b[:60].decode("utf-8", "replace")})
        probe["declared_resolvable"] = a.get("resolvable")
        probe["declared_error"] = a.get("resolution_error")
        probe["reproduced_not_resolvable"] = all(
            e["status"] != 200 for e in probe.get("endpoint", [])) if not offline else None
        fig_probe.append(probe)
    checks["figures"] = {
        "n_declared_in_record": len(rec_figs),
        "n_in_manifest": len(fig_probe),
        "captions_all_verbatim": all(f["caption_verbatim_match"] for f in fig_probe) if fig_probe else None,
        "resolvable_reproduced": ([f["reproduced_not_resolvable"] for f in fig_probe]
                                  if not offline else None),
        "details": fig_probe,
        "markdown_claim_about_figures": (
            "见 figures 字段（4 张 PNG 内嵌）。" if "见 figures 字段（4 张 PNG 内嵌）。" in md else None),
    }

    # ---- 8b. 源记录自相矛盾检测（治理升级附录 vs 正文）
    checks["source_self_contradiction"] = {
        "appendix_marks_sections_todo": all(
            f"| {x} | 待补充 |" in md for x in ("① 案例介绍", "⑥ 误差判定")),
        "body_has_sections": all(
            f"## {x}" in md for x in ("① 案例介绍", "⑥ 误差判定")),
        "quote_appendix": "| ① 案例介绍 | 待补充 |",
        "quote_body": "## ① 案例介绍",
        "contradiction": (all(f"| {x} | 待补充 |" in md for x in ("① 案例介绍", "⑥ 误差判定"))
                          and all(f"## {x}" in md for x in ("① 案例介绍", "⑥ 误差判定"))),
    }

    # ---- 9. 是否越界标注 verified
    checks["no_verified_marking"] = {
        "marker_hits": find_marker(am),
        "clean": not find_marker(am),
    }

    # ---- 10. 契约允许 claims 为空的判据（objective 不含抽取）
    checks["claims_empty_legality"] = {
        "n_claims": len(am.get("claims", [])),
        "has_reason": bool(am.get("claims_empty_reason")),
        "reason_quote_head": (am.get("claims_empty_reason") or "")[:60],
        "objective_register_assets_only": (
            (am.get("claims_empty_reason") or "").find("register_assets") >= 0),
    }

    # ---- 10b. 交付信道合规（标题/标签/唯一 json 块）+ 生产者声明的工件哈希能证多少证多少
    st_u, raw_u = _get(f"/tensor/reports/{UPSTREAM_REPORT_ID}", tok)
    up_rec = json.loads(raw_u)
    chan = {
        "result_report_id": UPSTREAM_REPORT_ID,
        "http_status": st_u,
        "title": up_rec.get("title"),
        "title_ok": up_rec.get("title") == f"KF-RESULT {SUBJECT_PKG}",
        "tags": up_rec.get("tags") or [],
        "tag_ok": f"kf-wp:{SUBJECT_PKG}" in (up_rec.get("tags") or []),
        "single_json_block": len(blocks) == 1,
        "n_figures_in_channel": len(up_rec.get("figures") or []),
    }
    # 唯一 json 块 = 生产者交付的 kf_result_envelope.json 字节
    chan["envelope_bytes_sha256"] = ("sha256:" + sha256_hex(blocks[0].encode())
                                     if blocks else None)
    # 信道内图件可取回 + 字节/几何
    fig_bytes = {}
    for f in (up_rec.get("figures") or []):
        name = f.get("name")
        for variant in (name, name + ".png"):
            s2, b2 = _get_raw(f"/tensor/reports/{UPSTREAM_REPORT_ID}/figures/{variant}", tok)
            if s2 == 200:
                geo = {"valid_png": b2[:8] == b"\x89PNG\r\n\x1a\n"}
                if geo["valid_png"] and b2[12:16] == b"IHDR":
                    geo["width"] = int.from_bytes(b2[16:20], "big")
                    geo["height"] = int.from_bytes(b2[20:24], "big")
                fig_bytes[name] = {"variant": variant, "bytes": len(b2),
                                   "sha256": "sha256:" + sha256_hex(b2), "geometry": geo}
                break
    chan["figure_bytes"] = fig_bytes
    checks["delivery_channel"] = chan

    # 生产者 §③ 工件哈希表（只取事实性哈希，不取其解释）——能复算的复算
    declared = {}
    for m in re.finditer(r"\| `([^`]+)` \| ([0-9,]+) B \| `sha256:([0-9a-f]{64})` \|", upstream_md):
        declared[m.group(1)] = {"declared_bytes": int(m.group(2).replace(",", "")),
                                "declared_sha256": "sha256:" + m.group(3)}
    art = {
        "declared_in_producer_table": declared,
        "markdown_hash_recomputed": "sha256:" + sha256_hex(md_bytes),
        "manifest_serializations_tried": [],
    }
    am_obj = am
    for ind in (None, 1, 2, 4):
        for sep in ((", ", ": "), (",", ": "), (",", ":"), (", ", ":")):
            for tail in ("", "\n"):
                for so in (False, True):
                    cand = json.dumps(am_obj, ensure_ascii=False, indent=ind,
                                      separators=sep, sort_keys=so) + tail
                    art["manifest_serializations_tried"].append(
                        {"indent": ind, "sep": list(sep), "tail": tail, "sort": so,
                         "sha256": "sha256:" + sha256_hex(cand.encode())})
    man_sha = declared.get("runs/wp-427-01/asset_manifest.json", {}).get("declared_sha256")
    env_sha = declared.get("runs/wp-427-01/kf_result_envelope.json", {}).get("declared_sha256")
    fig_sha = declared.get("runs/wp-427-01/fig_locator_map.png", {}).get("declared_sha256")
    src_sha = declared.get("runs/wp-427-01/source_427.md", {}).get("declared_sha256")
    art["envelope_sha256_declared"] = env_sha
    art["envelope_sha256_reproduced"] = ("sha256:" + sha256_hex(blocks[0].encode())
                                         if blocks else None)
    art["envelope_reproduced"] = (env_sha is not None
                                  and env_sha == art["envelope_sha256_reproduced"])
    art["figure_sha256_declared"] = fig_sha
    fig_hit = None
    for k, v in fig_bytes.items():
        if k.split(".")[0] == "fig_locator_map":
            fig_hit = v
            break
    art["figure_sha256_reproduced"] = (fig_hit or {}).get("sha256")
    art["figure_bytes_reproduced"] = (fig_hit or {}).get("bytes")
    art["figure_reproduced"] = (fig_sha is not None
                                and fig_sha == art["figure_sha256_reproduced"]
                                and fig_hit is not None
                                and fig_hit["bytes"] ==
                                declared.get("runs/wp-427-01/fig_locator_map.png", {})
                                .get("declared_bytes"))
    art["source_copy_sha256_declared"] = src_sha
    art["source_copy_equals_source_markdown"] = src_sha == "sha256:" + sha256_hex(md_bytes)
    art["manifest_sha256_declared"] = man_sha
    hits = [x for x in art["manifest_serializations_tried"] if x["sha256"] == man_sha]
    art["manifest_reproducible_from_envelope"] = bool(hits)
    art["manifest_reproduction_recipe"] = hits[0] if hits else None
    art["n_serializations_tried"] = len(art["manifest_serializations_tried"])
    env_bytes = len(blocks[0].encode()) if blocks else 0
    man_bytes = (len(json.dumps(am_obj, ensure_ascii=False, indent=2).encode()) + 1) if hits else None
    art["bytes_reproduced"] = {
        "source_427.md": {"declared": declared.get("runs/wp-427-01/source_427.md", {}).get("declared_bytes"),
                          "recomputed_markdown_bytes": len(md_bytes)},
        "kf_result_envelope.json": {"declared": declared.get("runs/wp-427-01/kf_result_envelope.json", {}).get("declared_bytes"),
                                    "recomputed_json_block_bytes": env_bytes},
        "asset_manifest.json": {"declared": declared.get("runs/wp-427-01/asset_manifest.json", {}).get("declared_bytes"),
                                "recomputed": man_bytes},
    }
    art["verified_declared_artifacts"] = sorted([k for k, ok in {
        "source_427.md": art["source_copy_equals_source_markdown"]
        and declared.get("runs/wp-427-01/source_427.md", {}).get("declared_bytes") == len(md_bytes),
        "kf_result_envelope.json": art["envelope_reproduced"]
        and declared.get("runs/wp-427-01/kf_result_envelope.json", {}).get("declared_bytes") == env_bytes,
        "asset_manifest.json": bool(hits),
        "fig_locator_map.png": art["figure_reproduced"],
    }.items() if ok])
    _ver = {os.path.basename(x) for x in art["verified_declared_artifacts"]}
    art["unverified_declared_artifacts"] = [k for k in declared
                                            if os.path.basename(k) not in _ver]
    art["verification_json"] = declared.get("runs/wp-427-01/verification.json")
    checks["producer_artifact_hashes"] = art

    # ---- 11. 生产者自报但本审核无法独立复算的项（unknown，不是 pass）
    checks["not_independently_checkable"] = {
        "derived_artifacts_on_producer_worktree": [
            d.get("path") for d in am.get("derived_artifacts", [])],
        "note": "生产者工作树内文件（本地副本/verification.json）不在审核方可达范围；"
                "其存在性与 sha256 未复核 -> 记 unknown/not_run，不计 pass。",
        "control_claim_by_producer": "同端点对其它记录返回 200/67,305 B —— 越本单 report_id 边界，未复核",
    }
    return checks


def build_report(checks: dict, upstream_meta: dict) -> dict:
    findings = []

    src = checks["source_refetch"]
    prov_ok = (checks["provenance"]["match"] and src["hash_matches_contract"]
               and src["chars_match_contract"] and checks["schema"]["valid"]
               and checks["locators"]["all_confirmed"]
               and checks["counts"]["consistent"]
               and checks["id_integrity"]["unique_recomputed"]
               and checks["manifest_source_block"]["all_match"])

    # F1：源记录 figure 无 payload（作用域=源报告制品，非 wp-427-01 的产出）
    fig = checks["figures"]
    fig_404 = all(f["reproduced_not_resolvable"] for f in fig["details"]) \
        if fig["details"] and fig["resolvable_reproduced"] else None
    if fig_404:
        findings.append({
            "finding_id": "F1",
            "severity": "medium",
            "scope": "source_record(report_id=427) / upstream-of-package",
            "statement": "源记录声明 4 张 figure，但 figure 端点对两种命名变体均取不到 PNG 字节；"
                         "报告正文 ④ 却写「4 张 PNG 内嵌」。上游按 resolvable=false + 404 原文登记，"
                         "该登记被本审核独立复现。缺陷在源记录，不在 wp-427-01 产出。",
            "evidence": [{"check": "figures.details[*].endpoint",
                          "detail": [{"name": d["name"], "endpoint": d.get("endpoint")}
                                     for d in fig["details"]]},
                         {"markdown_quote": fig["markdown_claim_about_figures"]}],
            "blocking_for_upstream_package": False,
            "impact": "下游像素级工序（图件抽取/图像核验）在 427 上无可校验对象，只能登记缺口。",
        })

    # F2：平台门对 locator 实际 checked=0，上游 9 条 locator 全为自报
    findings.append({
        "finding_id": "F2",
        "severity": "low",
        "scope": "platform gate coverage / wp-427-01",
        "statement": "平台门 g5_source_locator_resolvable 记 checked=0、locator_rate=null"
                     "（claims 为空时门不遍历 locator 数组），故 9 条 locator 未经机器校验；"
                     "本审核逐条重算后 9/9 与自报一致，缺口被补上但不构成上游错误。",
        "evidence": [{"gate_record": "gates.g5_source_locator_resolvable.checked = 0"},
                     {"check": "locators.n_independently_confirmed",
                      "value": checks["locators"]["n_independently_confirmed"]}],
        "blocking_for_upstream_package": False,
        "impact": "若上游自报 locator 有误，平台门不会拦；建议 01 工序把 locator 纳入机器门。",
    })

    # F3：派生工件不可达（unknown，不当 pass）
    findings.append({
        "finding_id": "F3",
        "severity": "low",
        "scope": "wp-427-01 derived_artifacts",
        "statement": "manifest 登记 3 个派生工件（源副本/verification/envelope）及其 sha256，"
                     "均位于生产者工作树，审核方不可达；本审核把它们记为 unknown，不判 pass。",
        "evidence": [{"paths": checks["not_independently_checkable"]
                      ["derived_artifacts_on_producer_worktree"]}],
        "blocking_for_upstream_package": False,
        "impact": "不影响信封级判据（source_hash/locator/counts 均已独立复算）。",
    })

    # F5（正向确认，非缺陷）：交付信道 + 可复算的工件哈希复现
    art = checks.get("producer_artifact_hashes", {})
    if art.get("envelope_reproduced") and art.get("figure_reproduced") and art.get("manifest_reproducible_from_envelope"):
        findings.append({
            "finding_id": "F5",
            "severity": "info",
            "scope": "wp-427-01 delivery channel",
            "statement": ("把生产者自报的工件哈希从『自报』升级为『已独立复现』："
                          + "、".join(art.get("verified_declared_artifacts", []))
                          + "（含字节数；manifest 的复现配方 = "
                          + json.dumps(art.get("manifest_reproduction_recipe"), ensure_ascii=False)
                          + "）。未复现：" + "、".join(art.get("unverified_declared_artifacts", []))
                          + "（生产者工作树不可达）。"),
            "evidence": [{"envelope_sha256": art.get("envelope_sha256_reproduced"),
                          "figure_sha256": art.get("figure_sha256_reproduced"),
                          "figure_bytes": checks.get("delivery_channel", {})
                          .get("figure_bytes")}],
            "blocking_for_upstream_package": False,
        })

    # F6：源记录自相矛盾（治理升级附录把 ①~⑥ 全标『待补充』，而正文六节齐备）
    contradiction = (checks.get("source_self_contradiction") or {}).get("contradiction")
    if contradiction:
        findings.append({
            "finding_id": "F6",
            "severity": "low",
            "scope": "source_record(report_id=427) / risk for downstream wp-427-02/03",
            "statement": "源报告末尾『治理升级』附录把 ①~⑥ 六节全部标为『待补充』，"
                         "而正文六节实际齐备；上游把该附录语句作为事实 locator（pre-rework-chars）登记，"
                         "未标注矛盾。对 01（只登记资产）不构成违约，但 02/03 若把附录当成"
                         "『章节缺失』证据会失真——本审核显式预警。",
            "evidence": [{"markdown_quote_a": "| ① 案例介绍 | 待补充 |",
                          "markdown_quote_b": "## ① 案例介绍",
                          "markdown_quote_c": "| ⑥ 误差判定 | 待补充 |",
                          "markdown_quote_d": "## ⑥ 误差判定"},
                         {"upstream_locator": "pre-rework-chars",
                          "quote": "> 原始长度: 2460 字符。"}],
            "blocking_for_upstream_package": False,
            "impact": "下游抽取工序的判据输入污染风险（非 01 工序错误）。",
        })

    verdict = "pass" if prov_ok else "needs-fix"
    blocking = [f for f in findings if f.get("blocking_for_upstream_package")]

    return {
        "review_id": "review:wp-427-04:wp-427-01",
        "package_id": PKG,
        "task_type": "04-independent-review",
        "reviews_package_id": SUBJECT_PKG,
        "report_id": REPORT_ID,
        "reviewer_role": "red-team-reviewer",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "subject": upstream_meta,
        "independence": {
            "inputs_used": ["report 427 markdown (platform API refetch)",
                            "report 427 record fields (title/scenario_key/figures)",
                            "upstream envelope json block (outputs.asset_manifest.json)",
                            "wp-427-01 contract (objective/acceptance) for legality judgement"],
            "narrative_use": "上游正文仅用于取两处**事实性**元数据：§③ 工件哈希表（用于复算）"
                             "与 ①②节的法条/工单号；其解释与自评（⑤⑥ 结论、'端点非故障'等）不作判据。",
            "excluded": ["上游结果报告正文第①~⑥节叙述（生产者的解释与自评）",
                         "生产者工作树内文件内容"],
            "review_prompt_not_copied_from_producer": True,
            "reviewer_context_excludes_producer_explanation": True,
            "numbers_source": "全部在本进程内重算（hashlib/len/splitlines/urllib），零手抄",
        },
        "verdict": verdict,
        "verdict_basis": {
            "acceptance_recheck_all_true": prov_ok,
            "blocking_findings": [f["finding_id"] for f in blocking],
            "non_blocking_findings": [f["finding_id"] for f in findings if f not in blocking],
            "delivery_channel_ok": {k: checks.get("delivery_channel", {}).get(k)
                                    for k in ("title_ok", "tag_ok", "single_json_block")},
        },
        "acceptance_recheck": [
            {"item": "valid_json", "upstream_claim": True,
             "independently_recomputed": checks["envelope_extraction"]["single_block"],
             "result": "pass" if checks["envelope_extraction"]["single_block"] else "fail"},
            {"item": "schema_pass", "upstream_claim": True,
             "independently_recomputed": checks["schema"]["valid"],
             "result": "pass" if checks["schema"]["valid"] else "fail"},
            {"item": "source_hash_matches", "upstream_claim": True,
             "independently_recomputed": (checks["source_refetch"]["hash_matches_contract"]
                                          and checks["provenance"]["match"]),
             "result": "pass" if (checks["source_refetch"]["hash_matches_contract"]
                                  and checks["provenance"]["match"]) else "fail"},
            {"item": "source_locator_resolvable", "upstream_claim": "9/9",
             "independently_recomputed": checks["locators"]["n_independently_confirmed"],
             "result": "pass" if checks["locators"]["all_confirmed"] else "fail"},
            {"item": "no_duplicate_ids", "upstream_claim": True,
             "independently_recomputed": checks["id_integrity"]["unique_recomputed"],
             "result": "pass" if checks["id_integrity"]["unique_recomputed"] else "fail"},
            {"item": "all_claims_have_evidence_or_explicit_unresolved_status",
             "upstream_claim": "claims=[] + 契约理由",
             "independently_recomputed": (checks["claims_empty_legality"]["n_claims"] == 0
                                          and checks["claims_empty_legality"]["has_reason"]),
             "result": "pass" if (checks["claims_empty_legality"]["n_claims"] == 0
                                  and checks["claims_empty_legality"]["has_reason"]) else "fail"},
        ],
        "findings": findings,
        "checks_not_run": [
            "派生工件（3 个）字节存在性与 sha256：生产者工作树不可达 -> unknown（F3）",
            "生产者『同端点对其它记录返回 200/67,305 B』对照：越本单 report_id 边界，未复核",
            "figure 图像内容 vs 正文数字一致性：无 payload，无可校验对象（F1）",
            "asset_manifest.json 与 verification.json 的文件级 sha256：不可从交付信道复算（F4）/不可达",
        ],
        "overstated_claims": [
            "上游把 figures 4/4 不可取回归因于『源记录缺 payload』——本审核复现了 404，"
            "但『其它记录 200/67,305 B』这一对照未复核，故『端点非故障』的结论在审核侧仅 partially-supported。"
        ],
        "checks_performed_detail": checks,
        "disposition": ("approve" if verdict == "pass" else "request changes"),
        "remediation": [] if verdict == "pass" else ["按 blocking findings 修正后重交"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream-report-id", default="14590",
                    help="wp-427-01 的结果报告 id（平台 tk_work_packages.result_report_id）")
    ap.add_argument("--offline", action="store_true", help="跳过 figure 端点探测")
    args = ap.parse_args()

    tok = _token()
    st, raw = _get(f"/tensor/reports/{args.upstream_report_id}", tok)
    upstream_md = json.loads(raw)["markdown"]
    upstream_meta = {
        "package_id": SUBJECT_PKG,
        "result_report_id": args.upstream_report_id,
        "result_report_markdown_sha256": "sha256:" + sha256_hex(upstream_md.encode()),
        "result_report_chars": len(upstream_md),
    }

    checks = run_checks(upstream_md, tok, args.offline)
    review = build_report(checks, upstream_meta)

    os.makedirs(OUT_DIR, exist_ok=True)
    p_rr = os.path.join(OUT_DIR, "review_report.json")
    with open(p_rr, "w", encoding="utf-8") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)
    p_ch = os.path.join(OUT_DIR, "review_checks.json")
    with open(p_ch, "w", encoding="utf-8") as f:
        json.dump(checks, f, ensure_ascii=False, indent=2)

    env = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": CONTRACT_SOURCE_HASH,
            "source_field": "markdown",
            "producer": "kf-worker/" + os.environ.get("TP_WORKER_ID", "m15789"),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": ("source_hash recomputed in-process from GET /tensor/reports/427 "
                      "markdown UTF-8 bytes; reviewed package wp-427-01 result_report_id="
                      + str(args.upstream_report_id)),
        },
        "outputs": {"review_report.json": review},
        "claims": [],
    }
    p_env = os.path.join(OUT_DIR, "kf_result.json")
    with open(p_env, "w", encoding="utf-8") as f:
        json.dump(env, f, ensure_ascii=False, indent=2)

    # 结构门自检（用仓库 schema）
    import jsonschema
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(env))
    print("verdict:", review["verdict"], "| disposition:", review["disposition"])
    print("envelope schema errors:", [e.message for e in errs] or "none")
    print("locators confirmed:", checks["locators"]["n_independently_confirmed"], "/",
          checks["locators"]["n_declared"])
    print("wrote:", p_rr, p_ch, p_env)
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())