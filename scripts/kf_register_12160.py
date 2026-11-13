#!/usr/bin/env python3
"""wp-12160-01 · 01-asset-registration for report_id=12160.

Registers the *source asset instance* (report 12160 markdown) and enumerates every
parseable attachment / artifact the markdown references, with a verbatim, uniquely
resolving locator (char span + line span) for each.  No extraction, no claim
generation, no verification: claims=[] by contract.

Zero-hand-copy discipline: every quote in the manifest is produced by searching the
fetched markdown bytes; nothing is retyped.  The sha256 of the fetched markdown is
recomputed here and compared with the hash pinned in the work-package contract
(contracts/wp-12160-01.yaml).

Usage (one-shot reproduction):
    python3 scripts/kf_register_12160.py --out docs/kf/wp-12160-01

Source resolution order:
  1. --source-file  (a byte copy of the markdown, e.g. docs/kf/wp-12160-01/source_markdown.md)
  2. platform API   GET $TENSOR_API_BASE/tensor/reports/12160  (Bearer token from
                    /auth/login with $TENSOR_AGENT_USER/$TENSOR_AGENT_PASS)
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import json
import os
import re
import subprocess
import sys
import urllib.request

PKG = "wp-12160-01"
TASK = "01-asset-registration"
REPORT_ID = "12160"
SCENARIO = "p73w3-n02-eexi-maturity"
SOURCE_URI = "tensor://reports/12160"
WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# bounded, read-only roots probed when checking whether a referenced path exists
PROBE_ROOTS = [
    WORKTREE,
    "/root/ship-performance-platform",
    "/root/ship-performance-platform-incoming/ship-performance-platform",
]
CODE_DIRS = ["backend", "modules", "physics", "api", "tests", "scripts", "schemas"]


# --------------------------------------------------------------------------- io
def fetch_source(source_file: str | None) -> tuple[str, str, dict]:
    if source_file:
        with open(source_file, "rb") as fh:
            raw = fh.read()
        meta_path = os.path.join(os.path.dirname(os.path.abspath(source_file)), "source_record.json")
        meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
        return raw.decode("utf-8"), f"file:{source_file}", meta
    base = os.environ["TENSOR_API_BASE"]
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    tok = tok.get("access_token") or tok.get("token") or tok.get("data", {}).get("access_token")
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + tok}
    )
    rec = json.load(urllib.request.urlopen(req))
    meta = {k: v for k, v in rec.items() if k != "markdown"}
    return rec["markdown"], f"api:{base}/tensor/reports/{REPORT_ID}", meta


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------- locating
class Doc:
    def __init__(self, md: str):
        self.md = md
        self.line_starts = [0]
        for i, ch in enumerate(md):
            if ch == "\n":
                self.line_starts.append(i + 1)
        self.sections = []  # (char_start, char_end, title)
        heads = [(m.start(), m.group(0)) for m in re.finditer(r"^## .*$", md, re.M)]
        for idx, (start, title) in enumerate(heads):
            end = heads[idx + 1][0] if idx + 1 < len(heads) else len(md)
            self.sections.append((start, end, title.strip("# ").strip()))

    def line_of(self, pos: int) -> int:
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo  # 0-based

    def section_of(self, pos: int) -> str:
        for start, end, title in self.sections:
            if start <= pos < end:
                return title
        return "(preamble)"

    def table_blocks(self) -> list[dict]:
        """Group consecutive pipe rows into tables and attach the nearest heading above."""
        lines = self.md.splitlines(keepends=True)
        starts, pos = [], 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        blocks, cur = [], []
        for idx, ln in enumerate(lines):
            if ln.lstrip().startswith("|"):
                cur.append(idx)
            elif cur:
                blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)
        out = []
        for rows in blocks:
            first = rows[0]
            pos0 = starts[first]
            heading = ""
            for j in range(first - 1, -1, -1):
                if lines[j].startswith("#"):
                    heading = lines[j].strip("# \n").strip()
                    break
            section = self.section_of(pos0)
            ncols = len([c for c in lines[first].strip().strip("|").split("|")])
            out.append({
                "section": section,
                "heading": heading,
                "first_row": lines[first].strip("\n"),
                "pipe_rows": len(rows),
                "data_rows": max(0, len(rows) - 2),
                "cols": ncols,
            })
        return out

    def count(self, quote: str) -> int:
        return self.md.count(quote)

    def occurrences(self, quote: str) -> list[int]:
        out, i = [], self.md.find(quote)
        while i >= 0:
            out.append(i)
            i = self.md.find(quote, i + 1)
        return out

    def locator(self, quote: str, section: str | None = None) -> dict:
        """Char-span locator.  If the quote is ambiguous, widen it line-by-line
        (right first, then left) until it matches the document exactly once; the
        widening is recorded in `context_expanded_lines` so the reader can tell a
        bare-symbol locator from a context-padded one."""
        occ = self.occurrences(quote)
        if not occ:
            raise SystemExit(f"quote not found in markdown: {quote!r}")
        anchor = occ[0]
        if section and len(occ) > 1:
            inside = [o for o in occ if self.section_of(o).startswith(section[:6])]
            if inside:
                anchor = inside[0]
        unique = len(occ) == 1
        expanded = 0
        if not unique:
            li = self.line_of(anchor)
            lj = self.line_of(anchor + len(quote) - 1)
            nlines = len(self.line_starts)
            for k in range(1, 7):
                lo = max(0, li - k)
                hi = min(nlines - 1, lj + k)
                start = self.line_starts[lo]
                end = self.line_starts[hi + 1] if hi + 1 < nlines else len(self.md)
                cand = self.md[start:end].strip("\n")
                if cand.count(quote) and len(self.occurrences(cand)) == 1:
                    quote, unique, expanded = cand, True, k
                    break
        start = self.md.find(quote)
        end = start + len(quote)
        return {
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": self.line_of(start),
            "end_line": self.line_of(end - 1),
            "quote": quote,
            "unique": unique,
            "occurrences_in_source": len(self.occurrences(quote)),
            "context_expanded_lines": expanded,
        }


# ------------------------------------------------------------- probe sources
def probe_path(rel_path: str) -> dict:
    """Is a report-referenced relative path present in any bounded read-only root?"""
    probe = {r: os.path.exists(os.path.join(r, rel_path)) for r in PROBE_ROOTS}
    return probe


def grep_symbol(symbol: str) -> dict:
    """Count textual occurrences of a dotted symbol in this worktree's code dirs."""
    roots = [os.path.join(WORKTREE, d) for d in CODE_DIRS if os.path.isdir(os.path.join(WORKTREE, d))]
    hits = {}
    for root in roots:
        try:
            # self-reference guard: this package's own scripts quote the symbols
            # verbatim, so they are excluded from the hit count.
            out = subprocess.run(
                ["grep", "-rFl", "--include=*.py",
                 "--exclude=kf_register_12160.py", "--exclude=kf_selfcheck_12160.py",
                 "--exclude=test_kf_wp_12160_01.py", symbol, root],
                capture_output=True, text=True, timeout=120,
            ).stdout.split()
        except (OSError, subprocess.SubprocessError):
            out = []
        hits[os.path.relpath(root, WORKTREE)] = len(out)
    return hits


# --------------------------------------------------------------- asset build
def build_assets(doc: Doc) -> list[dict]:
    assets: list[dict] = []

    def add(asset_class, label, quote, check, result, note, **extra):
        loc = doc.locator(quote)
        item = {
            "asset_class": asset_class,
            "label": label,
            "in_report_section": doc.section_of(loc["start_char"]),
            "locator": loc,
            "resolution": result,
            "resolution_check": {"check": check, **extra.pop("check_extra", {})},
            "note": note,
        }
        item["resolution_check"]["result"] = {
            "resolved_in_source": "resolved",
            "referenced_unresolved": "unresolved",
            "declared_absent": "absent",
        }[result]
        item.update(extra)
        assets.append(item)

    # A01 — the source instance itself (document-level locator)
    assets.append({
        "asset_class": "source_instance",
        "label": SOURCE_URI,
        "in_report_section": "(document)",
        "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": len(doc.md),
            "start_line": 0,
            "end_line": doc.line_of(len(doc.md) - 1),
            "quote": doc.md[:60],
            "unique": True,
        },
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "sha256(markdown utf-8 bytes) recomputed", "result": "resolved"},
        "note": "报告本体；locator.method=document，char span 覆盖全文，quote 为全文首行（识别用摘录，"
                "不等于 span 内容）；字节哈希见 integrity.hash_recomputed_locally，与契约 source_hash "
                "比对见 integrity.hash_matches_contract",
    })

    # A02..A07 — referenced repo artifacts (paths)
    path_assets = [
        ("generator_script", "artifacts/eexi_closed_loop/run_eexi_closed_loop.py",
         "报告自述的生成脚本（表内数字由它程序化注入）"),
        ("data_artifact", "artifacts/eexi_closed_loop.json",
         "报告自述的数据工件：几何/工况/逐段误差/审计表/敏感度的唯一来源"),
        ("figure", "artifacts/eexi_closed_loop/figs/fig1_resistance_breakdown.png", "图1 阻力分项+参考点审计标记"),
        ("figure", "artifacts/eexi_closed_loop/figs/fig2_efficiency_chain.png", "图2 推进效率分解 vs 公开 QPC"),
        ("figure", "artifacts/eexi_closed_loop/figs/fig3_error_budget.png", "图3 逐段误差+RSS vs 5% 目标线"),
        ("figure", "artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png", "图4 EEXI 水平+单位代数回归闸门"),
    ]
    for asset_class, rel, note in path_assets:
        probe = probe_path(rel)
        add(asset_class, rel, rel,
            f"os.path.exists over bounded roots {probe}",
            "referenced_unresolved",
            note + "；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
            check_extra={"present_in_roots": probe, "probe_roots": PROBE_ROOTS})

    # A08..A14 — code modules / functions / tests referenced as the single source of each link
    symbols = [
        ("code_module", "physics.holtrop.mennen", "阻力段唯一来源（Holtrop-Mennen 1984 实现）"),
        ("code_module", "modules.propeller_bemt", "敞水/桨模型模块（与 η_H 的 Taylor 式同源）"),
        ("code_function", "modules.propeller_bemt.solve_n_for_thrust", "T(1-t)=R_T 闭合反解转速 n"),
        ("code_module", "api.green_shipping", "SFOC→CO₂ 化学计量与 EEXI attained 指数所在模块"),
        ("code_function", "api.green_shipping._gn_attained_index", "1852 倍单位缺陷的宿主函数（报告称已修复）"),
        ("code_function", "unit_conformance()", "单位一致性闸门（缺陷双侧锁定之一）"),
        ("test", "tests/test_eexi_closed_loop.py", "缺陷回归测试（双侧锁定的另一侧）"),
    ]
    for asset_class, sym, note in symbols:
        if "/" in sym:
            probe = probe_path(sym)
            check = f"os.path.exists over bounded roots {probe}"
        else:
            probe = grep_symbol(sym)
            check = (f"grep -rFl --include=*.py --exclude=kf_register_12160.py "
                     f"--exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py '{sym}' "
                     f"over worktree code dirs {probe} (self-reference excluded)")
        add(asset_class, sym, sym, check, "referenced_unresolved",
            note + "；工作包内未加载/未执行该符号，其行为既未确认也未否证",
            check_extra={"probe_result": probe})

    # A15..A16 — external standards (cited, text not available offline)
    for std, note in [
        ("MEPC.328(76)", "EEXI 规则母文件（报告引用计算法）"),
        ("MEPC.350(78)", "EEXI 计算方法修正案"),
    ]:
        add("external_standard", std, std,
            "standard document not part of the markdown / not available offline",
            "referenced_unresolved",
            note + "；离线不可回读原文，本包不据此做任何合规性陈述")

    # A17..A19 — declared trace identifiers / upstream provenance claim
    add("upstream_commit_claim", "7017a6235", "7017a6235",
        "git cat-file in this worktree (TensorKnowledge) cannot prove a ship-performance-platform commit",
        "referenced_unresolved",
        "报告声明的生成时上游 HEAD（ship-performance-platform），并自注「提交后可能落后一代」；"
        "本包无法验证该提交存在性或其内容，仅登记为声明")
    add("trace_identifier", "p73w3-n02-eexi-maturity", "p73w3-n02-eexi-maturity",
        "identifier declared inside the source", "resolved_in_source",
        "战役节点 id，与契约 scenario_key 一致" if True else "")
    add("trace_identifier", "m10589", "m10589", "identifier declared inside the source",
        "resolved_in_source", "报告所属任务 id（与工作包 mission_id=15743 不同：本包是后者的产线工序）")

    # A20..A22 — machine-readable field keys the report exposes for downstream parsing
    for key, note in [
        ("ships[*].provenance", "几何/工况逐字段出处（上游 JSON 的 provenance 数组）"),
        ("sensitivity", "容量/SFOC 一次齐次敏感度"),
        ("reference_input_mode", "阻力改为试验/CFD 输入模式下的残差开关"),
        ("method_band", "误差预算里「无实测则用文献带宽」的显式标签"),
        ("total_resistance_kN", "标模库阻力列字段名"),
        ("delivered_power_kW", "标模库自航功率列字段名"),
    ]:
        add("schema_field_key", key, f"`{key}`", "field key appears verbatim in markdown",
            "resolved_in_source", note + "；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释")

    # A23 — rule coefficients declared NOT readable offline (explicit absence)
    q = "规则侧系数（参考线/削减率）离线不可回读原文"
    add("rule_coefficient_set", "EEDI/EEXI 参考线+削减率", q,
        "report explicitly declares offline unavailability", "declared_absent",
        "报告自述该组系数离线不可回读，证据等级 WITHHELD；本包沿用该声明，不补齐、不猜测")

    # A24 — inline aggregate verdict JSON (parseable in-source payload)
    m = re.search(r"`(\{\"a\": \{\"per_ship\".*?\})`", doc.md)
    if m:
        payload = m.group(1)
        try:
            parsed = json.loads(payload)
            ok = isinstance(parsed, dict) and set(parsed) == {"a", "b", "c", "d"}
        except json.JSONDecodeError:
            ok = False
        assets.append({
            "asset_class": "embedded_json_block",
            "label": "判据聚合 verdict JSON（§3.4 末）",
            "in_report_section": doc.section_of(m.start(1)),
            "locator": doc.locator(payload),
            "resolution": "resolved_in_source",
            "resolution_check": {
                "check": "json.loads(quote) succeeded and keys == {a,b,c,d}",
                "result": "resolved" if ok else "unresolved",
            },
            "note": "可机读的裁决聚合块；本包只登记其可解析性，不重算也不改写其裁决",
        })

    # A25.. — embedded markdown tables, one asset per table block
    for block in doc.table_blocks():
        quote = block["first_row"]
        loc = doc.locator(quote, section=block["section"])
        assets.append({
            "asset_class": "embedded_table",
            "label": f"{block['heading'] or block['section']} · 表（{block['data_rows']} 数据行 × "
                     f"{block['cols']} 列）",
            "in_report_section": block["section"],
            "locator": loc,
            "resolution": "resolved_in_source",
            "resolution_check": {
                "check": "table block located by header row; pipe-row count with header+separator excluded",
                "result": "resolved",
            },
            "note": f"父标题={block['heading']!r}；| 行 {block['pipe_rows']} 个 ⇒ {block['data_rows']} 数据行，"
                    f"{block['cols']} 列。本包只登记可解析性，不复述表内数字",
            "table_rows": block["data_rows"],
            "parent_heading": block["heading"],
        })

    for i, a in enumerate(assets, start=1):
        a["asset_id"] = f"A{i:02d}"
    return assets


# ------------------------------------------------------------------- assemble
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(WORKTREE, "docs/kf", PKG))
    ap.add_argument("--source-file", default=None)
    ap.add_argument("--contract", default=os.path.join(WORKTREE, "contracts", PKG + ".yaml"))
    args = ap.parse_args()

    md, origin, meta = fetch_source(args.source_file)
    doc = Doc(md)
    digest = sha256_hex(md)

    contract_hash, contract_meta = None, {}
    if os.path.exists(args.contract):
        for ln in open(args.contract, encoding="utf-8"):
            m = re.match(r"\s*source_hash:\s*(sha256:[0-9a-f]{64})", ln)
            if m and not contract_hash:
                contract_hash = m.group(1)
            for key in ("report_id", "scenario_key", "chars", "source_uri", "source_field"):
                m = re.match(rf"\s*{key}:\s*'?([^'\n]+?)'?\s*$", ln)
                if m:
                    contract_meta[key] = m.group(1)
                    break

    assets = build_assets(doc)

    ids = [a["asset_id"] for a in assets]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    non_unique = [a["label"] for a in assets if a["locator"]["method"] == "char_span" and not a["locator"]["unique"]]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key") or contract_meta.get("scenario_key"),
            "record_fields_from": f"{origin.split('#')[0]} (record metadata, markdown excluded)",
            "record_status": meta.get("status"),
            "record_mission_id": meta.get("mission_id"),
            "record_tags": meta.get("tags"),
            "record_figures": meta.get("figures"),
            "fetched_from": origin,
            "contract_hash": contract_hash,
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
        "claims": [],
        "integrity": {
            "quote_uniqueness": {
                "all_char_span_quotes_unique": not non_unique,
                "non_unique_labels": non_unique,
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": (contract_hash == "sha256:" + digest) if contract_hash else None,
            "no_duplicate_ids": not dup_ids,
            "duplicate_ids": dup_ids,
            "contract_cross_checks": {
                "chars_recomputed": len(md),
                "chars_in_contract": contract_meta.get("chars"),
                "chars_match": str(len(md)) == str(contract_meta.get("chars")),
                "report_id_match": str(contract_meta.get("report_id")) == REPORT_ID,
                "scenario_key_match": contract_meta.get("scenario_key") == (meta.get("scenario_key")),
                "source_uri_match": contract_meta.get("source_uri") == SOURCE_URI,
                "source_field_match": contract_meta.get("source_field") == "markdown",
            },
        },
        "claims_policy": "claims=[] by contract (objective.register_assets=true, no extraction, no forced claim generation); "
                         "no statement of the report is verified or refuted here — verification is computed by the platform gate.",
    }

    os.makedirs(args.out, exist_ok=True)
    if meta:
        with open(os.path.join(args.out, "source_record.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
    # keep a byte copy of the source next to the manifest so the package is self-contained
    # and self-checkable offline (no-op when --source-file already points there)
    dst = os.path.join(args.out, "source_markdown.md")
    if args.source_file and os.path.abspath(args.source_file) != os.path.abspath(dst):
        shutil.copyfile(args.source_file, dst)
    elif not args.source_file:
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(md)
    with open(os.path.join(args.out, "asset_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    result = {
        "package_id": PKG,
        "task_type": TASK,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + digest,
            "source_field": "markdown",
            "producer": "scripts/kf_register_12160.py",
            "notes": f"fetched_from={origin}; chars={len(md)}; bytes_utf8={len(md.encode('utf-8'))}; "
                     "contract hash compared in integrity.hash_matches_contract",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    with open(os.path.join(args.out, "kf_result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(json.dumps({"sha256": digest, "chars": len(md), "bytes": len(md.encode()),
                      "assets": len(assets), "by_class": by_class, "by_res": by_res,
                      "dup_ids": dup_ids, "non_unique": non_unique,
                      "hash_matches_contract": manifest["integrity"]["hash_matches_contract"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())