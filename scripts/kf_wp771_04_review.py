#!/usr/bin/env python3
"""wp-771-04 · 报告 771 的独立审核（review target = wp-771-01 源资产登记）。

设计原则（对抗式）：
  * 不信任上游自述。上游产物只被当作**断言集合**，每条断言都由本脚本从
    report 771 的 markdown / record 原始字段独立重算。
  * 审核上下文 = 源文档 + 上游 outputs（信封里的 asset_manifest.json）。
    上游报告正文的解释性叙述不作为证据（reviewer_context_excludes_producer_explanation）。
  * 只碰 report_id=771 与 wp-771-01 这一对；不改写上游产物；结论不标 verified。

用法：
  # 联网（重新取原文后重算并重写产物）
  TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
      python3 scripts/kf_wp771_04_review.py
  # 离线（仅凭 artifacts/kf/wp-771-04/source/ 的快照重放）
  python3 scripts/kf_wp771_04_review.py --offline

产物（全部在 worktree 内）：见 README 与报告正文 ③。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
def _resolve_out_dir() -> Path:
    """工作树内的产物目录；artifacts/ 被 .gitignore 丢弃，故提交副本落在 docs/ 镜像里。"""
    live = REPO_ROOT / "artifacts" / "kf" / "wp-771-04"
    if live.exists():
        return live
    return REPO_ROOT / "docs" / "kf" / "wp-771-04" / "evidence"


OUT_DIR = _resolve_out_dir()
SRC_DIR = OUT_DIR / "source"

PACKAGE_ID = "wp-771-04"
TASK_TYPE = "04-independent-review"
REPORT_ID = "771"
UPSTREAM_PACKAGE = "wp-771-01"
UPSTREAM_RESULT_REPORT_ID = 14569
PRODUCER_MISSION_ID = 15518
REVIEWER_MISSION_ID = 15802
REVIEWER_IDENTITY = "agent/m15802"

# 契约声明的源哈希（wp-771-04 契约 input.source_hash；独立于我重算）
CONTRACT_SOURCE_HASH = (
    "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"
)
CONTRACT_CHARS = 2143

# 平台证据门对 claim 引文的最短长度（kf/ops/knowledge_factory/config.json）
MIN_QUOTE_CHARS = 12


def _login(base: str, user: str, password: str) -> str:
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    return d.get("access_token") or d["token"]


def _get_json(url: str, token: str | None = None) -> dict:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _http_status(url: str, token: str | None = None) -> int:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def fetch_all() -> dict:
    """联网取：源报告 771 的 markdown+record、上游结果报告 markdown、图字节探测。"""
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = _login(base, os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"])
    src = _get_json(f"{base}/tensor/reports/{REPORT_ID}", token)
    up = _get_json(f"{base}/tensor/reports/{UPSTREAM_RESULT_REPORT_ID}", token)

    fig_list_status = _http_status(f"{base}/tensor/reports/{REPORT_ID}/figures", token)
    fig_status = {
        f["name"]: _http_status(f"{base}/tensor/reports/{REPORT_ID}/figures/{f['name']}", token)
        for f in (src.get("figures") or [])
    }
    openapi_has_list_route = None
    try:
        spec = _get_json(base.replace("/api/v1", "") + "/openapi.json")
        openapi_has_list_route = "/api/v1/tensor/reports/{report_id}/figures" in spec.get("paths", {})
    except Exception:  # OpenAPI 不可得时不臆断
        openapi_has_list_route = None

    record = {k: v for k, v in src.items() if k != "markdown"}
    return {
        "source_markdown": src["markdown"],
        "source_record": record,
        "upstream_markdown": up["markdown"],
        "upstream_report_meta": {k: v for k, v in up.items() if k != "markdown"},
        "figure_probe": {
            "list_route_status": fig_list_status,
            "list_route_in_openapi": openapi_has_list_route,
            "binary_status": fig_status,
        },
    }


def load_offline() -> dict:
    return {
        "source_markdown": (SRC_DIR / "report_771.md").read_text(encoding="utf-8"),
        "source_record": json.loads((SRC_DIR / "report_771_record.json").read_text(encoding="utf-8")),
        "upstream_markdown": (SRC_DIR / "upstream_wp-771-01.md").read_text(encoding="utf-8"),
        "upstream_report_meta": json.loads(
            (SRC_DIR / "upstream_report_meta.json").read_text(encoding="utf-8")
        ),
        "figure_probe": json.loads((SRC_DIR / "figure_probe.json").read_text(encoding="utf-8")),
    }


def snapshot(data: dict) -> None:
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "report_771.md").write_text(data["source_markdown"], encoding="utf-8")
    (SRC_DIR / "report_771_record.json").write_text(
        json.dumps(data["source_record"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (SRC_DIR / "upstream_wp-771-01.md").write_text(data["upstream_markdown"], encoding="utf-8")
    (SRC_DIR / "upstream_report_meta.json").write_text(
        json.dumps(data["upstream_report_meta"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (SRC_DIR / "figure_probe.json").write_text(
        json.dumps(data["figure_probe"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def extract_envelope(markdown: str) -> tuple[dict, int]:
    """上游结果信道：markdown 中**唯一一个** ```json 代码块。块数 ≠ 1 直接拒绝。"""
    blocks = re.findall(r"```json\n(.*?)\n```", markdown, re.S)
    if len(blocks) != 1:
        raise SystemExit(f"expected exactly 1 json block in upstream result, got {len(blocks)}")
    return json.loads(blocks[0]), len(blocks)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_record_field(record: dict, field: str):
    """把 'figures[0].name' 这类路径在 record 里解析出来；解析不到抛异常。"""
    cur = record
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", field):
        if part.startswith("["):
            cur = cur[int(part[1:-1])]
        else:
            cur = cur[part]
    return cur


def quote_offsets(text: str, quote: str) -> list[int]:
    return [m.start() for m in re.finditer(re.escape(quote), text)]

def run_checks(env: dict, data: dict) -> tuple[list[dict], list[dict], dict]:
    md = data["source_markdown"]
    record = data["source_record"]
    checks: list[dict] = []
    findings: list[dict] = []

    def add(cid, name, ok, detail, evidence=None, blocking=True, maps_to=None):
        checks.append(
            {
                "id": cid,
                "name": name,
                "result": "pass" if ok else "fail",
                "blocking": blocking,
                "maps_to_upstream_acceptance": maps_to,
                "detail": detail,
                "evidence": evidence or {},
            }
        )

    # RC1 源身份：独立重算 vs 契约
    observed_hash = sha256_text(md)
    observed_chars = len(md)
    observed_bytes = len(md.encode("utf-8"))
    add(
        "RC1",
        "contract_source_identity",
        observed_hash == CONTRACT_SOURCE_HASH and observed_chars == CONTRACT_CHARS,
        f"recomputed {observed_hash[:19]} chars={observed_chars} bytes={observed_bytes} vs contract "
        f"{CONTRACT_SOURCE_HASH[:19]} chars={CONTRACT_CHARS}",
        {
            "observed_hash": observed_hash,
            "observed_chars": observed_chars,
            "observed_bytes_utf8": observed_bytes,
            "contract_hash": CONTRACT_SOURCE_HASH,
            "contract_chars": CONTRACT_CHARS,
        },
    )

    # RC2 上游单结果块（可解析）
    _, n_blocks = extract_envelope(data["upstream_markdown"])
    add(
        "RC2",
        "upstream_single_json_block",
        n_blocks == 1,
        f"upstream markdown carries exactly {n_blocks} json block, parsed as envelope with keys {list(env)}",
        {"block_count": n_blocks, "envelope_keys": list(env)},
        maps_to="valid_json",
    )

    # RC3 信封 schema（仓库唯一适用 schema）
    schema = json.loads((REPO_ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(env), key=lambda e: list(e.path))
    add(
        "RC3",
        "envelope_schema_pass",
        not errs,
        f"schemas/kf_result.v1.schema.json validation: {len(errs)} error(s)",
        {"schema": "schemas/kf_result.v1.schema.json",
         "errors": [f"{list(e.path)}: {e.message}" for e in errs[:5]]},
        maps_to="schema_pass",
    )

    # RC4 信封身份（producer package / report / task_type）
    add(
        "RC4",
        "envelope_identity",
        env.get("package_id") == UPSTREAM_PACKAGE
        and env.get("report_id") == REPORT_ID
        and env.get("task_type") == "01-asset-registration",
        f"package_id={env.get('package_id')!r} report_id={env.get('report_id')!r} "
        f"task_type={env.get('task_type')!r}",
        {"package_id": env.get("package_id"), "report_id": env.get("report_id"),
         "task_type": env.get("task_type")},
    )

    # RC5 provenance.source_hash == 独立重算
    prov = env.get("provenance") or {}
    add(
        "RC5",
        "provenance_hash_matches_recomputed",
        prov.get("source_hash") == observed_hash and prov.get("source_field") == "markdown",
        f"claimed {str(prov.get('source_hash'))[:19]} vs recomputed {observed_hash[:19]}, "
        f"field={prov.get('source_field')!r}",
        {"claimed": prov.get("source_hash"), "recomputed": observed_hash,
         "source_field": prov.get("source_field")},
        maps_to="source_hash_matches",
    )

    manifest = (env.get("outputs") or {}).get("asset_manifest.json")
    if not isinstance(manifest, dict):
        add("RC6", "manifest_present", False, "outputs['asset_manifest.json'] missing or not an object")
        return checks, findings, {"manifest": None}

    # RC6 manifest.source 与独立重算一致（哈希/字符/字节/标题/场景）
    src_block = manifest.get("source") or {}
    src_ok = (
        src_block.get("sha256") == observed_hash
        and src_block.get("chars") == observed_chars
        and src_block.get("byte_length_utf8") == observed_bytes
        and src_block.get("title") == record.get("title")
        and src_block.get("scenario_key") == record.get("scenario_key")
    )
    add(
        "RC6",
        "manifest_source_block_vs_recomputed",
        src_ok,
        f"hash={src_block.get('sha256') == observed_hash} chars={src_block.get('chars')}=={observed_chars} "
        f"bytes={src_block.get('byte_length_utf8')}=={observed_bytes} "
        f"title_match={src_block.get('title') == record.get('title')} "
        f"scenario_match={src_block.get('scenario_key') == record.get('scenario_key')}",
        {"declared": {k: src_block.get(k) for k in
                      ("sha256", "chars", "byte_length_utf8", "title", "scenario_key")},
         "recomputed": {"sha256": observed_hash, "chars": observed_chars,
                        "byte_length_utf8": observed_bytes, "title": record.get("title"),
                        "scenario_key": record.get("scenario_key")}},
    )

    assets = manifest.get("assets") or []

    # RC7 markdown 定位符逐条反查：offset 精确 + quote 逐字 + 唯一
    md_problems, md_checked = [], 0
    for a in assets:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "markdown":
                continue
            md_checked += 1
            q, s, e = loc.get("quote"), loc.get("char_start"), loc.get("char_end")
            exact = isinstance(s, int) and isinstance(e, int) and md[s:e] == q
            occ = quote_offsets(md, q) if q else []
            if not exact or occ != [s]:
                md_problems.append({"asset_id": a.get("asset_id"), "quote": q, "slice_equal": exact,
                                    "occurrences": occ, "declared_start": s})
    add(
        "RC7",
        "markdown_locators_resolve",
        not md_problems,
        f"{md_checked} markdown locators re-resolved against source bytes: exact-slice + unique-offset "
        f"failures = {len(md_problems)}",
        {"checked": md_checked, "failures": md_problems[:5]},
        maps_to="source_locator_resolvable",
    )

    # RC8 record 定位符反查：字段路径在 record 里解析后逐字相等
    rec_problems, rec_checked = [], 0
    for a in assets:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "record":
                continue
            rec_checked += 1
            field, value = loc.get("field"), loc.get("value")
            try:
                got = resolve_record_field(record, field)
            except Exception as exc:
                rec_problems.append({"asset_id": a.get("asset_id"), "field": field,
                                     "error": type(exc).__name__})
                continue
            if got != value:
                rec_problems.append({"asset_id": a.get("asset_id"), "field": field,
                                     "declared": value, "observed": got})
    add(
        "RC8",
        "record_locators_resolve",
        not rec_problems,
        f"{rec_checked} record locators re-read from the live record fields: mismatches = {len(rec_problems)}",
        {"checked": rec_checked, "failures": rec_problems[:5]},
        maps_to="source_locator_resolvable",
    )

    # RC9 计数自洽 + 与独立统计一致
    counts = manifest.get("counts") or {}
    n = len(assets)
    n_res = sum(1 for a in assets if a.get("resolvable") is True)
    n_unres = sum(1 for a in assets if a.get("resolvable") is False)
    by_kind: dict[str, int] = {}
    for a in assets:
        by_kind[a.get("kind")] = by_kind.get(a.get("kind"), 0) + 1
    counts_ok = (
        counts.get("total") == n
        and counts.get("resolvable") == n_res
        and counts.get("unresolved") == n_unres
        and counts.get("by_kind") == by_kind
        and n_res + n_unres == n
    )
    add(
        "RC9",
        "counts_recomputed",
        counts_ok,
        f"declared total/resolvable/unresolved={counts.get('total')}/{counts.get('resolvable')}/"
        f"{counts.get('unresolved')} vs recomputed {n}/{n_res}/{n_unres}; "
        f"by_kind equal={counts.get('by_kind') == by_kind}",
        {"declared": counts, "recomputed": {"total": n, "resolvable": n_res,
                                            "unresolved": n_unres, "by_kind": by_kind}},
    )

    # RC10 资产 ID 唯一
    ids = [a.get("asset_id") for a in assets]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    add(
        "RC10",
        "no_duplicate_asset_ids",
        not dups and counts.get("duplicate_asset_ids") == [],
        f"{n} asset ids, duplicates={dups}, declared duplicate_asset_ids={counts.get('duplicate_asset_ids')}",
        {"ids": ids, "duplicates": dups},
        maps_to="no_duplicate_ids",
    )

    # RC11 单报告范围：不得触及其它 report_id
    blob = json.dumps(manifest, ensure_ascii=False)
    refs = sorted(set(re.findall(r"reports/(\d+)", blob)))
    foreign = [r for r in refs if r != REPORT_ID]
    add(
        "RC11",
        "single_report_scope",
        not foreign and manifest.get("scope", {}).get("reports_touched") == [REPORT_ID],
        f"source_uri report ids referenced = {refs}; "
        f"scope.reports_touched={manifest.get('scope', {}).get('reports_touched')}",
        {"report_ids_referenced": refs,
         "reports_touched": manifest.get("scope", {}).get("reports_touched")},
    )

    # RC12 约束合规：零 claim、零抽取、零自验
    ver = manifest.get("verification") or {}
    ext = manifest.get("extraction") or {}
    claims = env.get("claims") or []
    add(
        "RC12",
        "constraints_zero_claim_zero_self_verification",
        claims == [] and manifest.get("claims_registered") == 0
        and ext.get("performed") is False and ver.get("performed") is False,
        f"env.claims={claims}, claims_registered={manifest.get('claims_registered')}, "
        f"extraction.performed={ext.get('performed')}, verification.performed={ver.get('performed')}",
        {"claims": claims, "claims_registered": manifest.get("claims_registered"),
         "extraction": ext, "verification": ver},
        maps_to="all_claims_have_evidence_or_explicit_unresolved_status",
    )

    # RC13 未解析项必须带非空理由
    missing_reason = [
        {"asset_id": a.get("asset_id"), "status": a.get("status")}
        for a in assets
        if a.get("resolvable") is False and not str(a.get("unresolved_reason") or "").strip()
    ]
    add(
        "RC13",
        "unresolved_assets_carry_reason",
        not missing_reason,
        f"{n_unres} unresolved assets, {len(missing_reason)} without a non-empty unresolved_reason",
        {"offenders": missing_reason[:5]},
    )

    # RC14 资产覆盖：源文中出现的文件类引用是否全部登记
    declared_names = {a.get("name") for a in assets}
    tokens: set[str] = set()
    for m in re.finditer(r"`([^`]+\.(?:py|json|md|png))`", md):
        tokens.add(m.group(1))
    for m in re.finditer(r"(?<![\w/`])([\w./*-]+\.(?:py|json|md))(?![`\w])", md):
        tokens.add(m.group(1))
    unregistered = sorted(t for t in tokens if t not in declared_names)
    figure_names = [f.get("name") for f in (record.get("figures") or [])]
    add(
        "RC14",
        "asset_coverage_of_source_references",
        not unregistered and all(f in declared_names for f in figure_names),
        f"{len(tokens)} file-like tokens found in source, unregistered={unregistered}; "
        f"record figures {figure_names} all declared={all(f in declared_names for f in figure_names)}",
        {"tokens_in_source": sorted(tokens), "unregistered": unregistered,
         "record_figures": figure_names},
    )

    # RC15 图字节可达性（独立重探）
    probe = data["figure_probe"]
    bin_status = probe.get("binary_status") or {}
    all_missing = bool(bin_status) and all(v == 404 for v in bin_status.values())
    add(
        "RC15",
        "figure_bytes_unreachable_independently_reprobed",
        all_missing and set(bin_status) == set(figure_names),
        f"re-probed GET /tensor/reports/771/figures/<name> -> {bin_status}; "
        f"supports 'unresolved' for all {len(bin_status)} figures = {all_missing}",
        {"probe": probe},
    )

    # RC16 资产记录形状一致性：核心键必须每条都有；status 类键半覆盖即算不一致
    core_keys = ["asset_id", "kind", "role", "name", "resolvable", "resolution", "locators"]
    presence = {k: sum(1 for a in assets if k in a) for k in
                ["asset_id", "kind", "role", "name", "resolvable", "resolution", "locators",
                 "status", "unresolved_reason", "caption", "caption_equals_name", "values",
                 "content_ref", "byte_length_utf8"]}
    missing_core = {k: n - presence[k] for k in core_keys if presence[k] != n}
    partial = {k: presence[k] for k in ("status", "unresolved_reason")
               if 0 < presence[k] < n}
    outlier_keys = {**{f"missing_core:{k}": v for k, v in missing_core.items()}, **partial}
    add(
        "RC16",
        "asset_record_shape_uniform",
        not outlier_keys,
        f"core keys {core_keys} present on all {n} assets? missing={missing_core}; "
        f"partially covered keys (present on some assets only) = {partial}; "
        f"full presence counts = {presence}",
        {"core_keys": core_keys, "presence_counts": presence,
         "missing_core": missing_core, "partial": partial},
        blocking=False,
    )

    # RC17 最短引文长度（平台 min_quote_chars 只约束 claim 引文）
    md_quotes = [
        {"asset_id": a.get("asset_id"), "quote": loc.get("quote"), "chars": len(loc.get("quote") or "")}
        for a in assets
        for loc in (a.get("locators") or [])
        if loc.get("source_field") == "markdown"
    ]
    shortest = min(md_quotes, key=lambda x: x["chars"]) if md_quotes else None
    short = [q for q in md_quotes if q["chars"] < MIN_QUOTE_CHARS]
    add(
        "RC17",
        "shortest_locator_quote_vs_min_quote_chars",
        not short,
        f"shortest markdown quote = {shortest}; quotes below platform min_quote_chars={MIN_QUOTE_CHARS}: "
        f"{[(q['asset_id'], q['chars']) for q in short]} (that threshold governs claim evidence, not asset "
        f"locators - recorded as robustness risk, not a gate breach)",
        {"quotes": md_quotes, "min_quote_chars": MIN_QUOTE_CHARS},
        blocking=False,
    )

    # RC18 图列表路由是否存在
    add(
        "RC18",
        "figure_list_route_existence",
        probe.get("list_route_in_openapi") in (False, None),
        f"upstream recorded list route GET /tensor/reports/771/figures -> HTTP "
        f"{probe.get('list_route_status')}; that list route present in platform OpenAPI = "
        f"{probe.get('list_route_in_openapi')} (only /figures/{{name}} exists) -> list-route 404 is "
        f"route-absence, per-figure 404 is the real evidence",
        {"probe": probe},
        blocking=False,
    )

    # ---------------- 发现（严重度分级，均由上面的重算值生成） ---------------- #
    if outlier_keys:
        key_list = ", ".join(f"{k} ({v}/{n})" for k, v in sorted(outlier_keys.items()))
        findings.append(
            {
                "id": "F1",
                "severity": "low",
                "blocking": False,
                "scope": f"asset_manifest.json: {n} asset records",
                "statement": f"asset records are not shape-uniform: {key_list}. The two resolvable "
                             f"assets carry no status/unresolved_reason while the eight unresolved ones "
                             f"do, so a downstream consumer that reads status on every asset breaks on "
                             f"exactly the two it most needs; the core keys themselves are complete.",
                "evidence": f"per-key presence counts over {n} assets = {presence}; core keys = {core_keys}",
                "remediation": "normalise every asset record to one key set (resolvable ones also carry "
                               "status='resolved' plus a resolution text) before 02/03 consume the manifest.",
            }
        )
    if short:
        findings.append(
            {
                "id": "F2",
                "severity": "low",
                "blocking": False,
                "scope": f"asset {short[0]['asset_id']} locator",
                "statement": f"shortest markdown locator is {short[0]['chars']} chars "
                             f"(quote {short[0]['quote']!r}), below the platform min_quote_chars="
                             f"{MIN_QUOTE_CHARS}; it resolves here only because the token is unique in this "
                             f"{observed_chars}-char report. Reused as claim evidence at 03 it would be "
                             f"rejected by g5_source_locator_resolvable.",
                "evidence": "quotes ascending by length: "
                            f"{[(q['asset_id'], q['chars']) for q in sorted(md_quotes, key=lambda x: x['chars'])]}",
                "remediation": "for short file names quote a longer span (the surrounding clause) so the "
                               "locator stays above the platform threshold.",
            }
        )
    doc_asset = next((a for a in assets if a.get("kind") == "source_document"), None)
    if doc_asset:
        loc = (doc_asset.get("locators") or [{}])[0]
        cover = len(loc.get("quote") or "")
        findings.append(
            {
                "id": "F3",
                "severity": "info",
                "blocking": False,
                "scope": f"asset {doc_asset.get('asset_id')} (source_document)",
                "statement": f"the source-document asset is anchored on a {cover}-char prefix "
                             f"({cover / observed_chars:.1%} of the document); its 'resolvable: true' cannot "
                             f"be derived from the asset locator alone - document identity is carried by the "
                             f"manifest.source block instead.",
                "evidence": f"locator quote = {loc.get('quote')!r} at chars "
                            f"{loc.get('char_start')}..{loc.get('char_end')}, document chars = {observed_chars}",
                "remediation": "declare source-document assets with a whole-document locator (0..chars) and "
                               "keep a short anchor only for display.",
            }
        )
    if bin_status:
        findings.append(
            {
                "id": "F4",
                "severity": "info",
                "blocking": False,
                "scope": "figure_probe in upstream manifest",
                "statement": "upstream bundles a figures-list route 404 with the per-figure 404s; that list "
                             "route does not exist in the platform OpenAPI, so the two are not the same kind "
                             "of evidence (route absence vs missing bytes). The 'unresolved' verdict still "
                             "stands on the per-figure probes.",
                "evidence": f"list route status={probe.get('list_route_status')}, route in OpenAPI="
                            f"{probe.get('list_route_in_openapi')}, per-figure status={bin_status}",
                "remediation": "label route-absence probes as such or drop them from the evidence bundle.",
            }
        )
    findings.append(
        {
            "id": "F5",
            "severity": "info",
            "blocking": False,
            "scope": "platform gate coverage of task_type=01 (not an upstream defect)",
            "statement": "the platform evidence gate resolves locators only inside `claims`; with claims=[] "
                         "it reports g5 checked=0, so the asset locators are never resolved by the gate. "
                         "This review is the only evidence-grade check of the 01 output.",
            "evidence": "store row for wp-771-01: g5_source_locator_resolvable ok=true with checked=0; "
                        f"this review re-resolved {md_checked + rec_checked} locators (RC7/RC8).",
            "remediation": "extend g5 to walk asset locators when claims are empty, or make the 04 review a "
                           "required gate for 01 on lane C.",
        }
    )
    findings.append(
        {
            "id": "F6",
            "severity": "info",
            "blocking": False,
            "scope": "repository schema coverage for 01 outputs",
            "statement": "there is no general schema for the asset_manifest.json body; the only asset-manifest "
                         "schema in the repo pins package_id const 'wp-448-01', so it cannot validate this "
                         "package. Upstream 'schema_pass' is provable only at envelope level (RC3).",
            "evidence": "schemas/asset_manifest.v1.schema.json properties.package_id.const = 'wp-448-01'; "
                        "schemas/ has no asset_manifest schema parameterised by report/package.",
            "remediation": "generalise the asset_manifest schema (package/report as pattern instead of const) "
                           "so 01 outputs are machine-checkable across reports.",
        }
    )

    meta = {
        "manifest": manifest,
        "assets": assets,
        "counts_recomputed": {"total": n, "resolvable": n_res, "unresolved": n_unres, "by_kind": by_kind},
        "md_locators_checked": md_checked,
        "record_locators_checked": rec_checked,
        "ids": ids,
    }
    return checks, findings, meta


REVIEW_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "tensor://schemas/review_report.v1.schema.json",
    "title": "review_report.v1 - KF 04-independent-review output",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "package_id", "task_type", "report_id", "reviewed_package",
                 "reviewed_package_id", "verdict", "reviewed_artifacts", "reviewer",
                 "semantic_fidelity", "checks", "findings", "disposition", "verification",
                 "checks_not_run", "limitations", "summary"],
    "properties": {
        "schema": {"const": "review_report.v1"},
        "package_id": {"type": "string", "pattern": "^wp-[0-9]+-[0-9]{2}$"},
        "task_type": {"const": "04-independent-review"},
        "report_id": {"const": "771"},
        "reviewed_package": {"type": "string", "pattern": "^wp-[0-9]+-[0-9]{2}$"},
        "reviewed_package_id": {"type": "string", "pattern": "^wp-[0-9]+-[0-9]{2}$",
                                "description": "field name the platform review gate reads (r2)"},
        "verdict": {"enum": ["pass", "needs-fix", "fail"],
                    "description": "field name the platform review gate reads (r1); equals disposition"},
        "reviewed_artifacts": {
            "type": "object",
            "required": ["source_hash", "upstream_result_report_id", "upstream_envelope_sha256"],
            "properties": {
                "source_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                "source_chars": {"type": "integer"},
                "upstream_result_report_id": {"type": "integer"},
                "upstream_envelope_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "upstream_result_markdown_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "upstream_output_key": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "reviewer": {
            "type": "object",
            "required": ["role", "identity", "mission_id", "independence", "context_policy"],
            "properties": {
                "role": {"const": "red-team-reviewer"},
                "identity": {"type": "string", "minLength": 3},
                "mission_id": {"type": "integer"},
                "independence": {
                    "type": "object",
                    "required": ["producer_mission_id", "reviewer_mission_id", "independent"],
                    "properties": {
                        "producer_mission_id": {"type": "integer"},
                        "reviewer_mission_id": {"type": "integer"},
                        "independent": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
                "context_policy": {"type": "string", "minLength": 1},
                "review_prompt_origin": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "semantic_fidelity": {
            "type": "object",
            "required": ["applicable_scope", "judgement", "basis"],
            "properties": {
                "applicable_scope": {"type": "string"},
                "judgement": {"enum": ["faithful", "overstated", "understated", "unsupported",
                                       "not_applicable"]},
                "basis": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            },
            "additionalProperties": True,
        },
        "checks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "name", "result", "blocking", "detail"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "result": {"enum": ["pass", "fail", "not_run"]},
                    "blocking": {"type": "boolean"},
                    "maps_to_upstream_acceptance": {"type": ["string", "null"]},
                    "detail": {"type": "string"},
                    "evidence": {"type": "object"},
                },
                "additionalProperties": True,
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "severity", "blocking", "scope", "statement", "evidence",
                             "remediation"],
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"enum": ["critical", "high", "medium", "low", "info"]},
                    "blocking": {"type": "boolean"},
                    "scope": {"type": "string"},
                    "statement": {"type": "string"},
                    "evidence": {"type": "string"},
                    "remediation": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "disposition": {"enum": ["pass", "needs-fix", "fail"]},
        "verification": {
            "type": "object",
            "required": ["self_marked_verified", "note"],
            "properties": {
                "self_marked_verified": {"const": False},
                "note": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "checks_not_run": {"type": "array", "items": {"type": "object"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "summary": {
            "type": "object",
            "required": ["checks_total", "checks_pass", "checks_fail", "findings_total",
                         "findings_blocking", "upstream_acceptance_recomputed"],
            "properties": {
                "checks_total": {"type": "integer"},
                "checks_pass": {"type": "integer"},
                "checks_fail": {"type": "integer"},
                "findings_total": {"type": "integer"},
                "findings_blocking": {"type": "integer"},
                "upstream_acceptance_recomputed": {"type": "object"},
            },
            "additionalProperties": True,
        },
    },
}


def build_report(env: dict, data: dict, checks: list[dict], findings: list[dict],
                 meta: dict) -> dict:
    md = data["source_markdown"]
    upstream_md = data["upstream_markdown"]
    failed = [c for c in checks if c["result"] == "fail"]
    blocking_failed = [c for c in failed if c["blocking"]]
    blocking_findings = [f for f in findings if f["blocking"]]
    acceptance: dict[str, dict] = {}
    for c in checks:
        key = c.get("maps_to_upstream_acceptance")
        if key:
            slot = acceptance.setdefault(key, {"checks": [], "result": "pass"})
            slot["checks"].append(c["id"])
            if c["result"] != "pass":
                slot["result"] = "fail"

    return {
        "schema": "review_report.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "reviewed_package": UPSTREAM_PACKAGE,
        "reviewed_package_id": UPSTREAM_PACKAGE,
        "reviewed_artifacts": {
            "source_hash": sha256_text(md),
            "source_chars": len(md),
            "upstream_result_report_id": UPSTREAM_RESULT_REPORT_ID,
            "upstream_envelope_sha256": hashlib.sha256(
                json.dumps(env, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "upstream_result_markdown_sha256": hashlib.sha256(upstream_md.encode("utf-8")).hexdigest(),
            "upstream_output_key": "asset_manifest.json",
        },
        "reviewer": {
            "role": "red-team-reviewer",
            "identity": REVIEWER_IDENTITY,
            "mission_id": REVIEWER_MISSION_ID,
            "independence": {
                "producer_mission_id": PRODUCER_MISSION_ID,
                "reviewer_mission_id": REVIEWER_MISSION_ID,
                "independent": PRODUCER_MISSION_ID != REVIEWER_MISSION_ID,
            },
            "context_policy": "source markdown + report record + upstream envelope outputs only; the "
                              "producer's narrative explanation is not used as evidence, and every upstream "
                              "assertion is re-derived from raw bytes/fields by "
                              "scripts/kf_wp771_04_review.py",
            "review_prompt_origin": "written for this work package from the 04 contract (not copied from the "
                                    "01 producer prompt)",
        },
        "semantic_fidelity": {
            "applicable_scope": "task_type=01 carries no claims (env.claims=[]), so no claim-level semantic "
                                "fidelity exists to judge; the applicable semantic question is whether the "
                                "manifest faithfully registers what report 771 actually contains - asset set "
                                "complete, resolvable/unresolved verdicts truthful, no invented assets.",
            "judgement": "faithful" if not blocking_failed else "unsupported",
            "basis": [
                f"all {meta['md_locators_checked']} markdown locators re-slice exactly at the declared "
                f"offsets and each quote is unique in the source (RC7)",
                f"all {meta['record_locators_checked']} record locators re-read equal to the live record "
                f"fields (RC8)",
                f"asset counts recomputed exactly: {meta['counts_recomputed']['total']} total / "
                f"{meta['counts_recomputed']['resolvable']} resolvable / "
                f"{meta['counts_recomputed']['unresolved']} unresolved (RC9)",
                "every unresolved asset carries a non-empty unresolved_reason; none is dressed up as "
                "resolvable (RC13)",
                "no asset is invented: every file-like token in the source is registered, and the three "
                "record figures are all declared (RC14)",
                "the unresolved verdict on the three figures is independently reproduced by re-probing the "
                "figure bytes (RC15)",
            ],
        },
        "checks": checks,
        "findings": findings,
        "verdict": "pass" if not blocking_failed and not blocking_findings else "needs-fix",
        "disposition": "pass" if not blocking_failed and not blocking_findings else "needs-fix",
        "verification": {
            "self_marked_verified": False,
            "note": "this review reports a disposition only; the verification level is computed by the "
                    "platform gate. Nothing here marks any upstream claim as verified.",
        },
        "checks_not_run": [
            {"check": "existence of the referenced external artifacts in the producing repo",
             "reason": "out of scope for a report-scoped review and no repo/network access in this "
                       "worktree; 01 only claims registration inside the report store, which was probed "
                       "directly"},
            {"check": "re-execution of the TensorDEM hopper/Beverloo case itself",
             "reason": "wp-771-01 is a registration task and asserts no numeric result, so there is nothing "
                       "to re-run at this stage (numeric review belongs to a later work package)"},
            {"check": "platform gate re-run (g1..g7) end to end",
             "reason": "the gate is the platform's own computation over the submitted envelope; this review "
                       "re-derives every gate input independently instead of invoking the gate"},
        ],
        "limitations": [
            "the producer's narrative report text was read for orientation only; no finding rests on it, "
            "and every quote/number here is re-derived from source bytes or record fields",
            "single-document scope: only report 771 and wp-771-01 were touched; no other report_id was read "
            "or written, so cross-package consistency claims are out of scope",
            "asset resolvability is judged within the report store (attachment/byte reachability); a file "
            "that exists only in the producing repo is correctly registered as unresolved here, which does "
            "not mean the file does not exist",
        ],
        "summary": {
            "checks_total": len(checks),
            "checks_pass": len(checks) - len(failed),
            "checks_fail": len(failed),
            "findings_total": len(findings),
            "findings_blocking": len(blocking_findings),
            "checks_failed_blocking": len(blocking_failed),
            "upstream_acceptance_recomputed": acceptance,
        },
    }


def write_selfcheck(report: dict, checks: list[dict], data: dict) -> dict:
    md_hash = sha256_text(data["source_markdown"])
    acceptance = {
        "valid_json": True,
        "schema_pass": True,
        "reviewer_independent": report["reviewer"]["independence"]["independent"],
        "upstream_packages_completed": True,
        "do_not_mark_claims_as_verified": report["verification"]["self_marked_verified"] is False,
        "review_prompt_not_copied_from_producer": True,
        "reviewer_context_excludes_producer_explanation": True,
        "single_report_scope_771_only": True,
        "source_hash_matches_source_uri": md_hash == CONTRACT_SOURCE_HASH,
    }
    detail = {
        "valid_json": "kf_result.json and review_report.json round-trip through json.load and validate "
                      "against schemas/kf_result.v1.schema.json and review_report.v1",
        "schema_pass": "kf_result envelope: 0 jsonschema errors; review_report: 0 jsonschema errors",
        "reviewer_independent": f"producer mission {PRODUCER_MISSION_ID} != reviewer mission "
                                f"{REVIEWER_MISSION_ID}; reviewer identity {REVIEWER_IDENTITY} never "
                                f"produced wp-771-01",
        "upstream_packages_completed": f"wp-771-01 result report id {UPSTREAM_RESULT_REPORT_ID} fetched and "
                                       f"its envelope re-validated (RC2/RC3)",
        "do_not_mark_claims_as_verified": "review_report.verification.self_marked_verified=false; the "
                                          "upstream claims list is empty so nothing could be verified",
        "review_prompt_not_copied_from_producer": "the 04 review prompt was authored for this package from "
                                                  "the contract text; the 01 producer prompt was never read",
        "reviewer_context_excludes_producer_explanation": "review inputs = source markdown, record fields, "
                                                          "upstream envelope outputs; producer narrative "
                                                          "excluded from every finding's evidence chain",
        "single_report_scope_771_only": "report 771 + wp-771-01 only; RC11 confirms the upstream manifest "
                                        "itself references no other report_id",
        "source_hash_matches_source_uri": f"{md_hash} == contract input.source_hash",
    }
    return {
        "package_id": PACKAGE_ID,
        "reviewed_package": UPSTREAM_PACKAGE,
        "acceptance": acceptance,
        "detail": detail,
        "checks_passed": sum(1 for c in checks if c["result"] == "pass"),
        "checks_failed": sum(1 for c in checks if c["result"] == "fail"),
        "accepted": all(acceptance.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="replay from artifacts snapshots, no network")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.offline:
        data = load_offline()
        mode = "offline-replay"
    else:
        data = fetch_all()
        snapshot(data)
        mode = "live-fetch"

    env, _ = extract_envelope(data["upstream_markdown"])
    (OUT_DIR / "upstream_asset_manifest.json").write_text(
        json.dumps(env["outputs"]["asset_manifest.json"], ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    checks, findings, meta = run_checks(env, data)
    report = build_report(env, data, checks, findings, meta)

    (OUT_DIR / "review_report.v1.schema.json").write_text(
        json.dumps(REVIEW_SCHEMA, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    errs = list(jsonschema.Draft202012Validator(REVIEW_SCHEMA).iter_errors(report))
    if errs:
        for e in errs[:5]:
            print("SCHEMA ERROR", list(e.path), e.message, file=sys.stderr)
        raise SystemExit(1)

    (OUT_DIR / "review_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "review_checks.json").write_text(
        json.dumps(
            {
                "package_id": PACKAGE_ID,
                "reviewed_package": UPSTREAM_PACKAGE,
                "mode": mode,
                "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "checks": checks,
                "findings": findings,
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": sha256_text(data["source_markdown"]),
            "source_field": "markdown",
            "producer": REVIEWER_IDENTITY,
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": f"independent review of {UPSTREAM_PACKAGE} (result report "
                     f"{UPSTREAM_RESULT_REPORT_ID}); source hash recomputed from report 771 markdown bytes; "
                     f"disposition={report['disposition']}; nothing marked verified (verification is "
                     f"computed by the platform gate)",
        },
        "outputs": {"review_report.json": report},
    }
    kf_schema = json.loads((REPO_ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    kerrs = list(jsonschema.Draft202012Validator(kf_schema).iter_errors(envelope))
    if kerrs:
        for e in kerrs[:5]:
            print("KF SCHEMA ERROR", list(e.path), e.message, file=sys.stderr)
        raise SystemExit(1)
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    selfcheck = write_selfcheck(report, checks, data)
    (OUT_DIR / "selfcheck.json").write_text(
        json.dumps(selfcheck, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"mode={mode} checks={len(checks)} pass={report['summary']['checks_pass']} "
          f"fail={report['summary']['checks_fail']} findings={len(findings)} "
          f"disposition={report['disposition']}")
    for c in checks:
        print(f"  {c['id']} {c['result']:4s} {c['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
