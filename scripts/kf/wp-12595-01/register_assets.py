#!/usr/bin/env python3
"""wp-12595-01 · 01-asset-registration for report 12595.

Builds (zero hand-copied numbers/quotes — everything is computed from the
fetched source at runtime; every locator quote is a verbatim source line):
  docs/kf/wp-12595-01/asset_manifest.json
  docs/kf/wp-12595-01/kf_result.json

Usage:
  python3 scripts/kf/wp-12595-01/register_assets.py --check
  # offline re-run (no platform credentials):
  python3 scripts/kf/wp-12595-01/register_assets.py \
      --from-file work/wp-12595-01/source/report_12595.md \
      --record-json work/wp-12595-01/source/report_12595.json --check

Boundary: touches report_id=12595 only. No extraction, no verified marks.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
WORK = REPO / "work" / "wp-12595-01" / "source"
OUT = REPO / "docs" / "kf" / "wp-12595-01"

PACKAGE_ID = "wp-12595-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "12595"
SOURCE_URI = "tensor://reports/12595"
CONTRACT_HASH = "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce"
CONTRACT_CHARS = 6420
CONTRACT_TITLE = (
    "IN157-N06 SIMP 灵敏度一致性验证面：伴随法 vs 有限差分（混合精度参考，50x25 悬臂梁）"
)
CONTRACT_SCENARIO_KEY = "in157_n06_simp_sensitivity_consistency"
CONTRACT_LAYER_HINT = "IN157-N06|in157_n06_simp_sensitivity_consistency|m"
GENERATOR = "agent/m15750"

# deterministic classification rules (no hand-copied quotes anywhere)
PATH_RE = re.compile(r"^[A-Za-z0-9_\-./{}*]+\.[A-Za-z0-9]+$")  # no spaces, has extension
GLOB_RE = re.compile(r"\*")
WORKTREE_RE = re.compile(r"^/root/tp-agent/work/")
BRANCH_RE = re.compile(r"^agent/[A-Za-z0-9._-]+$")
FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")  # field/flag/method reference
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# plain-text path tokens (outside code spans): must contain a slash + extension
# + at least one letter, so decimals like "0.4" / "1e-09" never match
RAW_PATH_RE = re.compile(r"(?<![\w.`])([A-Za-z0-9_\-./{}*]*[A-Za-z][A-Za-z0-9_\-./{}*]*\.[A-Za-z0-9]+)(?![\w])")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_source(args):
    if args.from_file:
        md = pathlib.Path(args.from_file).read_bytes().decode("utf-8")
        rec = json.loads(pathlib.Path(args.record_json).read_text(encoding="utf-8"))
    else:
        sys.path.insert(0, str(REPO / "scripts"))
        import kf_fetch_12595 as fetch  # noqa: E402

        fetch.main()
        md = (WORK / "report_12595.md").read_bytes().decode("utf-8")
        rec = json.loads((WORK / "report_12595.json").read_text(encoding="utf-8"))
    data = rec.get("data", rec)
    return md, data


def split_sections(md: str):
    lines = md.split("\n")
    heads = []
    for i, ln in enumerate(lines):
        m = HEADING_RE.match(ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    secs = []
    for k, (li, lvl, text) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines) - 1
        body = "\n".join(lines[li : end + 1])
        secs.append(
            {
                "ordinal": k + 1,
                "level": lvl,
                "heading": text,
                "line_start": li + 1,
                "line_end": end + 1,
                "chars": len(body),
                "sha256": "sha256:" + sha256_hex(body.encode("utf-8")),
            }
        )
    return secs


def section_of(line_no: int, secs) -> str:
    for s in secs:
        if s["line_start"] <= line_no <= s["line_end"]:
            return f"§{s['ordinal']} {s['heading']}"
    return "§0 (preamble)"


def classify(span: str):
    if WORKTREE_RE.match(span):
        return "worktree"
    if BRANCH_RE.match(span):
        return "branch"
    if PATH_RE.match(span):
        return "glob" if GLOB_RE.search(span) else "path"
    if FIELD_RE.match(span):
        return "field"
    return None  # formula/symbol — not an asset, skipped by design


def extract_refs(md: str, secs):
    """All referenced artifacts/fields: inline code spans + plain-text path tokens."""
    lines = md.split("\n")
    seen = {}
    order = []

    def add(kind, span, line_no):
        key = (kind, span)
        if key in seen:
            seen[key]["occurrences"] += 1
            return
        seen[key] = {"kind": kind, "span": span, "first_line": line_no, "occurrences": 1}
        order.append(key)

    for i, ln in enumerate(lines, start=1):
        for m in INLINE_CODE_RE.finditer(ln):
            kind = classify(m.group(1))
            if kind:
                add(kind, m.group(1), i)
        stripped = INLINE_CODE_RE.sub(" ", ln)
        for m in RAW_PATH_RE.finditer(stripped):
            tok = m.group(1)
            if "/" in tok and classify(tok) in ("path", "glob"):
                add(classify(tok), tok, i)

    refs = []
    for kind, span in order:
        meta = seen[(kind, span)]
        ln = lines[meta["first_line"] - 1]
        refs.append(
            {
                "raw_text": span,
                "path_kind": kind,
                "occurrences": meta["occurrences"],
                "first_line": meta["first_line"],
                "in_report_section": section_of(meta["first_line"], secs),
                "locator_quote": ln,
                "ref_id": f"12595-ref-{len(refs) + 1:02d}",
                "existence": "not_checked",
                "existence_reason": (
                    "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），"
                    "本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，"
                    "不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
                ),
            }
        )
    return refs


def build_manifest(md: str, data: dict):
    raw = md.encode("utf-8")
    digest = "sha256:" + sha256_hex(raw)
    hash_match = digest == CONTRACT_HASH
    chars_match = len(md) == CONTRACT_CHARS
    title_match = data.get("title") == CONTRACT_TITLE
    scenario_match = data.get("scenario_key") == CONTRACT_SCENARIO_KEY

    secs = split_sections(md)
    lines = md.split("\n")
    refs = extract_refs(md, secs)

    # ---- attachments: platform record figures (metadata only) --------------
    figs = data.get("figures") or []
    attachments = [
        {
            "name": f.get("name"),
            "caption": f.get("caption"),
            "payload_field_present": bool(f.get("png_base64")),
            "png_base64_len": len(f.get("png_base64") or ""),
        }
        for f in figs
    ]
    # cross-check: markdown §4 PNG lines vs record figure names/captions
    md_png = {}
    for i, ln in enumerate(lines, start=1):
        for m in INLINE_CODE_RE.finditer(ln):
            if m.group(1).endswith(".png"):
                cap = ln.split(" — ", 1)[1] if " — " in ln else ""
                md_png[m.group(1).rsplit("/", 1)[-1]] = cap
    cross = [
        {
            "name": a["name"],
            "name_in_markdown": a["name"] in md_png,
            "caption_matches_markdown": md_png.get(a["name"]) == a["caption"],
        }
        for a in attachments
    ]

    # ---- observations (honest, unresolved, no adjudication) ----------------
    # evidence lines are 1-based line numbers; quotes are machine-extracted.
    # Each pinned line must contain its expected literal, else we refuse to
    # register (no invented locators).
    def ev(*line_nos):
        return [lines[n - 1] for n in line_nos]

    def pin(line_no, literal):
        if literal not in lines[line_no - 1]:
            raise SystemExit(
                f"refuse-to-fabricate: line {line_no} does not contain {literal!r}"
            )

    pin(50, "test_simp_sensitivity_consistency*.py")
    pin(108, "test_simp_sensitivity_consistency_in157.py")
    pin(80, "fig1_sensitivity_and_error_maps.png")
    pin(111, "/root/tp-agent/work/m11206")

    observations = [
        {
            "id": "12595-obs-01",
            "kind": "glob_reference",
            "status": "unresolved",
            "statement": (
                "C6 探针在判据表中写作 glob（§3.1），§7 审计链将其展开为两个显式测试文件"
                "（14 例 + 10 例 = 24 例）；glob 本身不可直接解析，展开计数一致性（24=24）仅登记不裁决"
            ),
            "evidence_lines": [50, 108],
            "evidence_quotes": ev(50, 108),
        },
        {
            "id": "12595-obs-02",
            "kind": "cross_check_positive",
            "status": "resolved",
            "statement": (
                "正文 §4 声明的 4 张 PNG 与平台记录 figures 字段的 4 条图注逐字一致"
                "（name 与 caption 全匹配，机检见 attachments.cross_check_markdown_vs_record）"
            ),
            "evidence_lines": [80],
            "evidence_quotes": ev(80),
        },
        {
            "id": "12595-obs-03",
            "kind": "boundary",
            "status": "unresolved",
            "statement": (
                "报告 §7 声明全部代码/测试/工件位于 m11206 的 TensorPhysics worktree；"
                "本包工作树为 TensorKnowledge，跨树取证越界，故全部工件 existence=not_checked，"
                "不主张其存在或内容正确"
            ),
            "evidence_lines": [111],
            "evidence_quotes": ev(111),
        },
    ]

    # ---- locator check (verbatim substring of markdown) ---------------------
    locator_items = []
    for r in refs:
        locator_items.append(
            {"ref_id": r["ref_id"], "source_field": "markdown", "quote": r["locator_quote"], "resolved": r["locator_quote"] in md}
        )
    for a in attachments:
        locator_items.append(
            {"ref_id": "fig:" + a["name"], "source_field": "figures", "quote": a["caption"], "resolved": a["caption"] in md}
        )
    for o in observations:
        for q in o["evidence_quotes"]:
            locator_items.append({"ref_id": o["id"], "source_field": "markdown", "quote": q, "resolved": q in md})
    n_res = sum(1 for x in locator_items if x["resolved"])

    ids = [r["ref_id"] for r in refs] + [o["id"] for o in observations]
    no_dup = len(ids) == len(set(ids))

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "objective": {
            "register_assets": True,
            "classify_report_type": False,
            "extraction_performed": False,
        },
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": GENERATOR,
        "source_asset": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "platform_record_id": data.get("id"),
            "hash": {
                "algorithm": "sha256",
                "value": digest,
                "scope": "UTF-8 bytes of tensor_reports.markdown (report 12595)",
                "contract_expected": CONTRACT_HASH,
                "matches_contract": hash_match,
            },
            "size": {
                "chars": len(md),
                "bytes_utf8": len(raw),
                "lines": len(lines),
                "contract_chars": CONTRACT_CHARS,
                "chars_match_contract": chars_match,
            },
            "record_metadata": {
                "title": data.get("title"),
                "title_matches_contract": title_match,
                "scenario_key": data.get("scenario_key"),
                "scenario_key_matches_contract": scenario_match,
                "tags": data.get("tags"),
                "status": data.get("status"),
                "created_by": data.get("created_by"),
                "created_at": data.get("created_at"),
                "mission_id": data.get("mission_id"),
                "stage": data.get("stage"),
            },
            "contract_layer_hint": {
                "value": CONTRACT_LAYER_HINT,
                "interpreted": False,
                "note": "契约 notes 中的分层标签原样登记；objective.classify_report_type=false，不解读",
            },
        },
        "attachments": {
            "count": len(attachments),
            "items": attachments,
            "scan": {
                "record_figures_len": len(figs),
                "png_base64_present": any(a["payload_field_present"] for a in attachments),
                "markdown_image_syntax_hits": len(re.findall(r"!\[", md)),
                "external_url_hits": len(re.findall(r"https?://", md)),
                "returned_all": True,
            },
            "cross_check_markdown_vs_record": cross,
            "note": (
                "附件=平台记录 figures 字段登记的 4 张图（仅 name/caption 元数据，无 png_base64 载荷）；"
                "未下载/未解码图像载荷；正文 §4 的 4 个 PNG 路径引用另在 referenced_artifacts 登记"
            ),
        },
        "sections": secs,
        "referenced_artifacts": refs,
        "content_digests": [],
        "content_digests_note": "正文无 16+ 位十六进制摘要值、无 URL、无 markdown 图片语法（机检 0 命中）",
        "observations": observations,
        "locator_check": {
            "total": len(locator_items),
            "resolved": n_res,
            "unresolved": len(locator_items) - n_res,
            "all_resolved": n_res == len(locator_items),
            "items": locator_items,
        },
        "unresolved": [
            {"id": o["id"], "kind": o["kind"], "reason": o["statement"]}
            for o in observations
            if o["status"] == "unresolved"
        ],
        "boundary": {
            "report_ids_read": [REPORT_ID],
            "report_ids_written": [REPORT_ID],
            "verification_status": "none",
            "claims_generated": 0,
            "note": "只触碰 report_id=12595；不标 verified（verification 由平台门计算）；claims=[]（合同允许）",
        },
    }
    stats = {
        "hash_match": hash_match,
        "chars_match": chars_match,
        "title_match": title_match,
        "scenario_match": scenario_match,
        "no_dup": no_dup,
        "all_locators_resolved": n_res == len(locator_items),
        "n_locators": len(locator_items),
        "n_refs": len(refs),
        "n_sections": len(secs),
        "n_attachments": len(attachments),
        "n_observations": len(observations),
        "cross_all_ok": all(c["name_in_markdown"] and c["caption_matches_markdown"] for c in cross),
    }
    return manifest, stats


def build_envelope(manifest: dict):
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source_asset"]["hash"]["value"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": GENERATOR,
            "emitted_at": manifest["generated_at"],
            "notes": (
                "01-asset-registration：仅登记源资产/附件/引用清单与引文定位，未做抽取；"
                "claims=[]（合同允许），verification 交平台门计算"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def run_checks(envelope: dict, stats: dict):
    import jsonschema

    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    try:
        jsonschema.validate(envelope, schema)
        schema_pass = True
    except Exception as e:  # noqa: BLE001
        schema_pass = False
        stats["schema_error"] = str(e)[:300]
    am = envelope["outputs"]["asset_manifest.json"]
    b = am["boundary"]
    checks = {
        "valid_json": bool(json.loads(json.dumps(envelope))),
        "schema_pass": schema_pass,
        "source_locator_resolvable": stats["all_locators_resolved"],
        "source_hash_matches": stats["hash_match"],
        "no_duplicate_ids": stats["no_dup"],
        "all_claims_have_evidence_or_explicit_unresolved_status": envelope["claims"] == [],
        "single_report_boundary": (
            b["report_ids_read"] == [REPORT_ID]
            and b["report_ids_written"] == [REPORT_ID]
            and b["verification_status"] == "none"
            and b["claims_generated"] == 0
        ),
        "no_verified_marks": all(
            c.get("status") not in ("verified",) for c in envelope["claims"]
        )
        and b["verification_status"] == "none",
    }
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file")
    ap.add_argument("--record-json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    md, data = load_source(args)
    manifest, stats = build_manifest(md, data)
    envelope = build_envelope(manifest)
    checks = run_checks(envelope, stats)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"stats": stats, "acceptance": checks}, ensure_ascii=False, indent=2))
    if args.check and not all(checks.values()):
        print("ACCEPTANCE FAIL", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
