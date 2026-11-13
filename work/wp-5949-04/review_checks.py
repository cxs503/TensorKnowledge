#!/usr/bin/env python3
"""wp-5949-04 独立审核：对 wp-5949-01 的资产登记包做可复算对抗性检查。

独立性来源：本脚本**重新**从平台 API 取 report 5949 原文（不复用上游 source_5949.md），
再对上游 kf_result.json / asset_manifest.json 逐项重算。上游产物取自 git 对象
（分支 agent/m15584，commit b88b3c9），只读，不修改。

用法：
  python3 work/wp-5949-04/review_checks.py \
      --upstream-ref agent/m15584 --out work/wp-5949-04/checks.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

CONTRACT_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
CONTRACT_CHARS = 12605
FORBIDDEN_KEY_RE = re.compile(
    r"^(verified|verification_status|verification_level|is_verified|gate_confirmed)$", re.I
)
UP = "docs/kf/wp-5949-01"


def git_show(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{ref}:{path}"], check=True, capture_output=True
    ).stdout


def git_exists(ref: str, path: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{ref}:{path}"],
            capture_output=True,
        ).returncode
        == 0
    )


def fetch_report(report_id: str) -> dict:
    base = os.environ["TENSOR_API_BASE"]
    cred = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=cred, headers={"Content-Type": "application/json"}
    )
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        f"{base}/tensor/reports/{report_id}",
        headers={"Authorization": "Bearer " + token},
    )
    return json.load(urllib.request.urlopen(req))


def scan_forbidden(obj, path="") -> list[str]:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if FORBIDDEN_KEY_RE.match(k):
                hits.append(f"{path}.{k}")
            hits.extend(scan_forbidden(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_forbidden(v, f"{path}[{i}]"))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream-ref", default="agent/m15584")
    ap.add_argument("--out", default="work/wp-5949-04/checks.json")
    args = ap.parse_args()

    checks: dict[str, dict] = {}

    # ---- 独立取原文 ----
    rec = fetch_report("5949")
    md = rec["markdown"]
    md_bytes = md.encode("utf-8")
    live_hash = hashlib.sha256(md_bytes).hexdigest()
    checks["C1_source_identity"] = {
        "pass": live_hash == CONTRACT_HASH and len(md) == CONTRACT_CHARS,
        "detail": f"live sha256={live_hash} chars={len(md)} bytes={len(md_bytes)}",
    }

    envelope = json.loads(git_show(args.upstream_ref, f"{UP}/kf_result.json"))
    manifest = json.loads(git_show(args.upstream_ref, f"{UP}/asset_manifest.json"))

    # 上游 source 副本与独立取的原文逐字节一致（防止上游用别的字节算 locator）
    up_src = git_show(args.upstream_ref, f"{UP}/source_5949.md")
    checks["C2_upstream_source_copy"] = {
        "pass": hashlib.sha256(up_src).hexdigest() == live_hash and up_src == md_bytes,
        "detail": f"upstream copy sha256={hashlib.sha256(up_src).hexdigest()}",
    }

    # ---- locator 逐条重算（字节级） ----
    loc_fail, line_fail, non_unique, checked = [], [], [], 0
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc.get("start_char"), loc.get("end_char"), loc.get("quote", "")
        if s is None or e is None:
            loc_fail.append({"asset": a["asset_id"], "why": "no_offsets"})
            continue
        checked += 1
        if not (0 <= s <= e <= len(md)):
            loc_fail.append({"asset": a["asset_id"], "why": "out_of_range"})
            continue
        if md[s:e] != q:
            loc_fail.append({"asset": a["asset_id"], "why": "slice_ne_quote"})
            continue
        # 行号一致性：start_char 之前换行数 +1 应等于 start_line
        exp_line = md[:s].count("\n") + 1
        if exp_line != loc.get("start_line"):
            line_fail.append(
                {"asset": a["asset_id"], "expected": exp_line, "declared": loc.get("start_line")}
            )
        n = md.count(q)
        if n != 1 and loc.get("method") != "document":
            non_unique.append({"asset": a["asset_id"], "count": n, "declared_unique": loc.get("unique")})
    # 区分 coordinate 语义：document 级 locator（整篇跨度 + 首行 quote）另行计数
    doc_fail, doc_count = [], 0
    wire_fail = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") == "document":
            doc_count += 1
            ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
            if not ok:
                doc_fail.append(a["asset_id"])
            if not (loc.get("start_line", 0) and loc.get("end_line", 0)):
                wire_fail.append({"asset": a["asset_id"], "start_line": loc.get("start_line")})
    checks["C3_locator_slices"] = {
        "pass": not loc_fail,
        "detail": f"checked={checked} failing={loc_fail}（document 级 {doc_count} 条另计于 C3b）",
    }
    checks["C3b_document_locators"] = {
        "pass": not doc_fail and not wire_fail,
        "detail": (
            f"document 级 asset={doc_count} 字节相等失败={doc_fail}"
            f"（全篇跨度 0..{len(md)} 对比首行 quote → 必然不等，属坐标混用）；"
            f"line 字段为 0 者={wire_fail}"
        ),
    }
    search_miss = [a["asset_id"] for a in manifest["assets"] if a["locator"]["quote"] not in md]
    checks["C3c_quotes_searchable"] = {
        "pass": not search_miss,
        "detail": f"按子串检索 23 条 quote，未命中={search_miss}",
    }
    checks["C4_locator_line_numbers"] = {"pass": not line_fail, "detail": f"mismatch={line_fail}"}
    checks["C5_quote_uniqueness"] = {
        "pass": not non_unique,
        "detail": f"non_unique={non_unique} declared_checked={manifest['integrity']['quote_uniqueness']['checked']}",
    }

    # ---- 声明哈希前缀 ----
    dig_fail = []
    for d in manifest["declared_digests"]["items"]:
        s, e, q = d["start_char"], d["end_char"], d["quote"]
        ok = md[s:e] == q and d["digest_prefix"] in q and d["declared_hex_chars"] == len(d["digest_prefix"])
        if not ok:
            dig_fail.append(d["label"])
    dig_line_relative = []
    for d in manifest["declared_digests"]["items"]:
        line_start = md.rfind("\n", 0, md.find(d["quote"])) + 1
        dig_line_relative.append(
            {
                "label": d["label"],
                "declared": [d["start_char"], d["end_char"]],
                "doc_absolute": [md.find(d["quote"]), md.find(d["quote"]) + len(d["quote"])],
                "slice_at_declared": md[d["start_char"]:d["end_char"]],
                "matches_line_relative": (
                    md[line_start + d["start_char"]: line_start + d["end_char"]].startswith(
                        d["digest_prefix"]
                    )
                ),
            }
        )
    checks["C6b_digest_offset_semantics"] = {
        "pass": all(
            x["declared"] == x["doc_absolute"] for x in dig_line_relative
        ),
        "detail": dig_line_relative,
    }

    checks["C6_declared_digests"] = {
        "pass": not dig_fail and manifest["declared_digests"]["count"] == len(
            manifest["declared_digests"]["items"]
        ),
        "detail": (
            f"items={len(manifest['declared_digests']['items'])} "
            f"verifiable={manifest['declared_digests']['verifiable']} failing={dig_fail} "
            "(前缀 16 位且工件不在树内 → 不可复算，属登记声明而非证据)"
        ),
    }

    # ---- 计数 / id / 词表 ----
    ids = [a["asset_id"] for a in manifest["assets"]]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    counts_ok = (
        c["assets"] == len(manifest["assets"]) == 23
        and dict(sorted(c["by_class"].items())) == dict(sorted(by_class.items()))
        and dict(sorted(c["by_resolution"].items())) == dict(sorted(by_res.items()))
        and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    )
    checks["C7_counts_consistency"] = {
        "pass": counts_ok and len(set(ids)) == len(ids),
        "detail": f"assets={len(manifest['assets'])} unique_ids={len(set(ids))} by_resolution={by_res}",
    }

    # ---- 解析判定的可反驳性：标成 unresolved 的目标是否真不在上游树内 ----
    wrong_res = []
    for a in manifest["assets"]:
        path = a.get("path_reference")
        if not path:
            continue
        exists = git_exists(args.upstream_ref, path)
        if a["resolution"] == "referenced_unresolved" and exists:
            wrong_res.append({"asset": a["asset_id"], "path": path, "why": "存在却标未解析"})
    checks["C8_resolution_falsifiable"] = {
        "pass": not wrong_res,
        "detail": f"path_assets={sum(1 for a in manifest['assets'] if a.get('path_reference'))} wrong={wrong_res}",
    }

    # ---- claims 与自封验证字段 ----
    fb_manifest = scan_forbidden(manifest)
    fb_env = scan_forbidden(envelope)
    checks["C9_no_self_verification_fields"] = {
        "pass": not fb_manifest and not fb_env,
        "detail": f"manifest_hits={fb_manifest} envelope_hits={fb_env}",
    }
    checks["C10_claims_empty"] = {
        "pass": manifest.get("claims") == [] and "claims" not in envelope,
        "detail": (
            f"manifest.claims={manifest.get('claims')} envelope_has_claims_key={'claims' in envelope} "
            "(信封省略 claims；报告正文称 claims 为空数组——空/缺键语义等价，记差异不记缺陷)"
        ),
    }

    # ---- 信封 vs 官方 schema ----
    sys.path.insert(0, ".")
    import jsonschema  # noqa: PLC0415

    schema = json.load(open("schemas/kf_result.v1.schema.json"))
    try:
        jsonschema.validate(envelope, schema)
        env_ok, env_err = True, ""
    except jsonschema.ValidationError as exc:
        env_ok, env_err = False, str(exc).split("\n")[0]
    checks["C11_envelope_against_canonical_schema"] = {
        "pass": env_ok,
        "detail": env_err or "valid vs schemas/kf_result.v1.schema.json",
    }

    # ---- outputs 值是否为文件内容 ----
    out = envelope["outputs"]["asset_manifest.json"]
    file_bytes = git_show(args.upstream_ref, f"{UP}/asset_manifest.json")
    ptr_ok = (
        out.get("sha256") == hashlib.sha256(file_bytes).hexdigest()
        and out.get("bytes") == len(file_bytes)
        and out.get("asset_count") == len(manifest["assets"])
    )
    checks["C12_outputs_pointer_dereference"] = {
        "pass": ptr_ok,
        "detail": (
            f"outputs 值键={sorted(out)}；sha256 可与 {UP}/asset_manifest.json 对上="
            f"{out.get('sha256') == hashlib.sha256(file_bytes).hexdigest()}；"
            "但值是**指针**不是内容对象（schema 描述要求内容对象）"
        ),
    }

    # ---- 图资产 ----
    figs = rec.get("figures") or []
    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    checks["C13_figures"] = {
        "pass": len(figs) == len(fig_assets) == 2
        and all(f.get("png_base64") is None for f in figs)
        and all(a["resolution"] == "resolved_in_source" for a in fig_assets),
        "detail": (
            f"platform_figures={len(figs)} manifest_figure_assets={len(fig_assets)} "
            f"payload_keys={[sorted(f) for f in figs]}"
        ),
    }

    # ---- 报告形态 ----
    report_md = git_show(args.upstream_ref, f"{UP}/report.md").decode()
    json_blocks = re.findall(r"```json\n(.*?)```", report_md, re.S)
    same = json_blocks and json.loads(json_blocks[0]) == envelope
    up_rec = fetch_report("14660")
    checks["C14_report_single_json_block"] = {
        "pass": len(json_blocks) == 1 and bool(same),
        "detail": (
            f"json_blocks={len(json_blocks)} equals_envelope={bool(same)} "
            f"upstream_api_title={up_rec['title']!r} "
            f"upstream_api_tags={up_rec['tags']} "
            f"upstream_status={up_rec['status']}"
        ),
    }
    checks["C17_upstream_kf_wp_tag"] = {
        "pass": up_rec["title"] == "KF-RESULT wp-5949-01" and "kf-wp:wp-5949-01" in up_rec["tags"],
        "detail": f"title/tag check on report 14660",
    }
    checks["C18_figure_captions"] = {
        "pass": [
            {"index": i, "name": f.get("name"), "caption": f.get("caption")}
            for i, f in enumerate(figs)
        ]
        == [
            {"index": i, "name": g["name"], "caption": g.get(caption_key)}
            for i, (g, caption_key) in enumerate(
                zip(manifest["source"]["platform_figures"], ["caption"] * len(figs))
            )
        ],
        "detail": "manifest.source.platform_figures 与平台 figures[] 的 name/caption 逐字比对",
    }

    # ---- 报告正文事实性核查（对抗性：可被反证的具体断言） ----
    schemas_here = subprocess.run(
        ["git", "ls-tree", args.upstream_ref, "schemas/"], capture_output=True, text=True
    ).stdout
    claim_no_schema = "本仓没有契约所称的 `schemas/kf_result.v1.schema.json`" in report_md
    schema_present = "kf_result.v1.schema.json" in schemas_here
    checks["C15_report_claim_repo_schema_absent"] = {
        "pass": not (claim_no_schema and schema_present),
        "detail": (
            f"报告有该断言={claim_no_schema} 上游 commit 树内该文件存在={schema_present}"
        ),
    }
    verif_txt = git_show(args.upstream_ref, f"{UP}/verification.json").decode()
    checks["C16_verification_attribution"] = {
        "pass": "平台侧独立复算" not in report_md,
        "detail": (
            "报告称 verification.json 为「平台侧独立复算」；实际由本包 "
            "scripts/kf/build_asset_manifest_5949.py verify 子命令（生产者会话内）产出，"
            f"含 verified_at/all_pass={json.loads(verif_txt)['all_pass']}——非平台门签发"
        ),
    }

    checks["summary"] = {
        "pass": all(v["pass"] for k, v in checks.items() if k != "summary"),
        "n_checks": len([k for k in checks if k != "summary"]),
        "n_fail": [k for k, v in checks.items() if k != "summary" and not v["pass"]],
    }
    with open(args.out, "w") as fh:
        json.dump(checks, fh, ensure_ascii=False, indent=2)
    print(json.dumps(checks["summary"], ensure_ascii=False))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())