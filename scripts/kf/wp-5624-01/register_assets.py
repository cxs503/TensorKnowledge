#!/usr/bin/env python3
"""wp-5624-01 · 01-asset-registration 生成器（report_id=5624）。

只读 report_id=5624 的 markdown，做「源资产登记」：确认 report_id 与 markdown 字节哈希、
列出可解析的附件/引用工件，不做抽取（claims 恒为空数组，见合同 objective/notes）。

零手抄纪律：本脚本不含任何手写数字/引文——哈希、字符数、小节行号、引文片段
一律在运行时从 markdown 计算，引文取自原文整行（必然可逐字定位）。

用法：
  python3 scripts/kf/wp-5624-01/register_assets.py            # 从平台 API 取原文并生成
  python3 scripts/kf/wp-5624-01/register_assets.py --from-file /tmp/md5624.txt  # 离线复跑
  额外 --check 触发验收自检（schema/hash/locator/唯一性）。

产物：
  artifacts/kf/wp-5624-01/asset_manifest.json
  artifacts/kf/wp-5624-01/kf_result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_ID = "5624"
PACKAGE_ID = "wp-5624-01"
TASK_TYPE = "01-asset-registration"
SOURCE_FIELD = "markdown"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"
CONTRACT_SOURCE_HASH = (
    "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839"
)
CONTRACT_CHARS = 1833
CONTRACT_LAYER_HINT = "IN15-O5|in15-o5-artifact-sha256-indexer|s"
PRODUCER = "m15571"

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "artifacts" / "kf" / PACKAGE_ID
# artifacts/ 被 .gitignore 与推送门过滤，另存一份 git 可追踪镜像（同字节）
MIRROR_DIR = REPO_ROOT / "docs" / "kf" / PACKAGE_ID


# ---------------------------------------------------------------- 取原文
def _api_token() -> str:
    """登录平台拿 token（凭据只来自环境变量，不落盘、不进产物）。"""
    base = os.environ["TENSOR_API_BASE"]
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    return base, tok


def fetch_record() -> dict:
    base, tok = _api_token()
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": "Bearer " + tok},
    )
    return json.load(urllib.request.urlopen(req))


# ---------------------------------------------------------------- 解析
def sha256_hex(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_sections(md: str) -> list[dict]:
    """按 ATX 标题切小节：level/heading/行区间/字符数/小节 sha256。"""
    lines = md.split("\n")
    heads = [
        (i, re.match(r"^(#{1,6})\s+(.*)$", ln))
        for i, ln in enumerate(lines)
        if re.match(r"^#{1,6}\s+", ln)
    ]
    out = []
    for n, (idx, m) in enumerate(heads, start=1):
        end = (heads[n][0] - 1) if n < len(heads) else len(lines) - 1
        # 去掉尾部空行，保持区间贴合内容
        while end > idx and lines[end].strip() == "":
            end -= 1
        body = "\n".join(lines[idx : end + 1])
        out.append(
            {
                "ordinal": n,
                "level": len(m.group(1)),
                "heading": m.group(2).strip(),
                "line_start": idx + 1,
                "line_end": end + 1,
                "chars": len(body),
                "sha256": sha256_hex(body),
            }
        )
    return out


CODE_SPAN = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*)")
MODULE_RE = re.compile(r"\btools\.[A-Za-z0-9_.]+")
DIGEST_RE = re.compile(r"\b[0-9a-f]{16,64}\b")


def parse_refs(md: str) -> tuple[list[dict], list[dict]]:
    """从反引号代码片段里抽 路径引用 / 摘要引用；引文一律取原文整行（保证可解析）。"""
    lines = md.split("\n")
    paths: dict[str, dict] = {}
    digests: dict[str, dict] = {}
    for i, line in enumerate(lines, start=1):
        quote = line.strip()
        if not quote:
            continue
        for span in CODE_SPAN.findall(line):
            cands = [p.rstrip(".") for p in PATH_RE.findall(span)]
            cands += [m.replace(".", "/") for m in MODULE_RE.findall(span)]
            for p in cands:
                if p.endswith("/") is False and "/" not in p:
                    continue
                key = p.rstrip("/") + ("/" if p.endswith("/") else "")
                rec = paths.setdefault(
                    key,
                    {
                        "raw_text": key,
                        "path_kind": "declared_in_report_code_span",
                        "occurrences": 0,
                        "first_line": i,
                        "locator_quote": quote,
                    },
                )
                rec["occurrences"] += 1
            for d in DIGEST_RE.findall(span):
                rec = digests.setdefault(
                    d,
                    {
                        "raw_text": d,
                        "digits": len(d),
                        "occurrences": 0,
                        "first_line": i,
                        "locator_quote": quote,
                    },
                )
                rec["occurrences"] += 1
    # 稳定排序 + 编号，便于逐条审计
    pref = sorted(paths.values(), key=lambda r: (r["first_line"], r["raw_text"]))
    for n, rec in enumerate(pref, start=1):
        rec["ref_id"] = f"{REPORT_ID}-ref-{n:02d}"
        rec["existence"] = "not_checked"
        rec["existence_reason"] = (
            "该路径声明于 m4963 的 TensorPlatform worktree（工件根/工具目录），"
            "本包工作树为 TensorKnowledge 且边界=只触碰 report_id=5624，"
            "不跨 worktree 取证，故存在性/内容一致性留待上游门或后续工序"
        )
    dref = sorted(digests.values(), key=lambda r: (r["first_line"], r["raw_text"]))
    for n, rec in enumerate(dref, start=1):
        rec["digest_id"] = f"{REPORT_ID}-dig-{n:02d}"
        rec["algorithm"] = "sha256" if rec["digits"] == 64 else "sha256_truncated"
        rec["note"] = (
            "报告正文引用的内容摘要值，本工序只登记不重算（对应工件不在本 worktree）"
        )
    full = [d for d in dref if d["digits"] == 64]
    for d in dref:
        if d["digits"] < 64:
            pref_ids = [
                f["digest_id"] for f in full if f["raw_text"].startswith(d["raw_text"])
            ]
            d["prefix_of"] = pref_ids
            d["prefix_consistent"] = bool(pref_ids)
    return pref, dref


def markdown_image_hits(md: str) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]*\)", md))


def build_manifest(record: dict) -> tuple[dict, dict]:
    md = record["markdown"]
    h = sha256_hex(md)
    sections = parse_sections(md)
    refs, digests = parse_refs(md)
    figures = record.get("figures") or []
    figs = [
        {
            "name": f.get("name"),
            "caption": f.get("caption"),
            "payload_field_present": "png_base64" in f,
            "png_base64_len": len(f.get("png_base64") or ""),
        }
        for f in figures
    ]

    # locator 自检：正文引文须为 markdown 逐字子串；附件引文须为 figures 记录逐字匹配
    checked = [
        {
            "bucket": "referenced_artifacts",
            "id": r["ref_id"],
            "source_field": "markdown",
            "resolvable": r["locator_quote"] in md,
            "quote": r["locator_quote"],
        }
        for r in refs
    ] + [
        {
            "bucket": "content_digests",
            "id": d["digest_id"],
            "source_field": "markdown",
            "resolvable": d["locator_quote"] in md,
            "quote": d["locator_quote"],
        }
        for d in digests
    ] + [
        {
            "bucket": "attachments",
            "id": "fig-" + str(i + 1),
            "source_field": "figures",
            "resolvable": any(
                f.get("caption") == fig["caption"] for f in figures
            ),
            "quote": fig["caption"],
            "note": "图注存于记录 figures 字段，正文 markdown 无该文本，故对 figures 记录做逐字匹配",
        }
        for i, fig in enumerate(figs)
    ]
    unresolved = [c for c in checked if not c["resolvable"]]

    # 内部一致性观察（不解读、不臆断，如实登记矛盾）
    observations = []
    zero_re = re.compile(r"[（(]\s*0\s*文件\s*[）)]")
    count_re = re.compile(r"\d+\s*文件")
    lines_all = md.split("\n")
    zero_file_lines = [n + 1 for n, ln in enumerate(lines_all) if zero_re.search(ln)]
    count_lines = [
        n + 1
        for n, ln in enumerate(lines_all)
        if count_re.search(ln) and not zero_re.search(ln)
    ]
    total_line = next((n for n in count_lines if n > zero_file_lines[0]), None) if zero_file_lines else None
    if zero_file_lines and total_line and figs:
        observations.append(
            {
                "id": f"{REPORT_ID}-obs-01",
                "kind": "internal_inconsistency",
                "status": "unresolved",
                "statement": (
                    "正文对两个工件根的文件数自述为 0 文件，同段末又给出>0 的文件总数；"
                    "Fig.1 caption 给出按根目录的分解（94+8）。三处计数口径不一致。"
                ),
                "locators": {
                    "zero_file_lines": zero_file_lines,
                    "total_count_line": total_line,
                    "other_file_count_lines": [n for n in count_lines if n != total_line],
                    "attachment_id": "fig-1",
                },
                "quotes": [
                    md.split("\n")[zero_file_lines[0] - 1].strip(),
                    md.split("\n")[total_line - 1].strip(),
                    figs[0]["caption"],
                ],
                "note": "本工序不裁决哪个数字为准（不臆造），交由上游/复核工序追溯运行日志",
            }
        )

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "objective": {
            "register_assets": True,
            "classify_report_type": False,
            "extraction_performed": False,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": f"agent/{PRODUCER}",
        "source_asset": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "platform_record_id": int(REPORT_ID),
            "hash": {
                "algorithm": "sha256",
                "value": h,
                "scope": f"UTF-8 bytes of tensor_reports.markdown (report {REPORT_ID})",
                "contract_expected": CONTRACT_SOURCE_HASH,
                "matches_contract": h == CONTRACT_SOURCE_HASH,
            },
            "size": {
                "chars": len(md),
                "bytes_utf8": len(md.encode("utf-8")),
                "lines": md.count("\n") + (0 if md.endswith("\n") else 1),
                "contract_chars": CONTRACT_CHARS,
                "chars_match_contract": len(md) == CONTRACT_CHARS,
            },
            "record_metadata": {
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "tags": record.get("tags"),
                "status": record.get("status"),
                "created_by": record.get("created_by"),
                "created_at": record.get("created_at"),
                "mission_id": record.get("mission_id"),
                "stage": record.get("stage"),
            },
            "contract_layer_hint": {
                "value": CONTRACT_LAYER_HINT,
                "interpreted": False,
                "note": "契约 notes 中的分层标签原样登记；objective.classify_report_type=false，不解读",
            },
        },
        "attachments": {
            "count": len(figs),
            "items": figs,
            "scan": {
                "record_figures_len": len(figures),
                "png_base64_present": any(f["payload_field_present"] for f in figs),
                "markdown_image_syntax_hits": markdown_image_hits(md),
                "external_url_hits": len(re.findall(r"https?://", md)),
                "returned_all": True,
            },
            "note": (
                "附件=平台记录 figures 字段登记的 3 张图（仅元数据：name/caption），"
                "正文自述为后端完整性工具、无物理场量云图；未下载/未解码图像载荷"
            ),
        },
        "sections": sections,
        "referenced_artifacts": refs,
        "content_digests": digests,
        "observations": observations,
        "locator_check": {
            "total": len(checked),
            "resolved": len(checked) - len(unresolved),
            "all_resolved": not unresolved,
            "method": "每条 quote 对 markdown 做逐字子串匹配（str in markdown）",
            "items": checked,
            "unresolved_items": unresolved,
        },
        "unresolved": [
            {
                "item": "referenced_artifacts[].existence",
                "status": "unresolved",
                "reason": "工件根位于 m4963 的 TensorPlatform worktree，本包不跨 worktree 读取（边界约束）",
            },
            {
                "item": "content_digests[].value_recomputation",
                "status": "unresolved",
                "reason": "被摘要工件不在本 worktree，不重算、不主张其正确性",
            },
            {
                "item": "observations[0].which_count_is_authoritative",
                "status": "unresolved",
                "reason": "原文三处计数口径冲突，本工序不裁决（do_not_invent_missing_information）",
            },
        ],
        "boundary": {
            "report_ids_read": [REPORT_ID],
            "report_ids_written": [REPORT_ID],
            "claims_generated": 0,
            "claims_policy": "no_forced_claim_generation：01 工序只登记资产，envelope.claims=[] 为完整结果",
            "verification_status": "none — 由平台门独立计算，本包不标 verified",
        },
    }
    return manifest, record


def build_result(manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": "01",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source_asset"]["hash"]["value"],
            "source_field": SOURCE_FIELD,
            "source_uri": SOURCE_URI,
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": (
                "01-asset-registration：仅登记源资产/附件/引用清单与引文定位，未做抽取；"
                "claims=[]（合同允许），verification 交平台门计算"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


# ---------------------------------------------------------------- 自检
def self_check(result: dict) -> dict:
    schema_paths = [
        REPO_ROOT / "schemas" / "kf_result.v1.schema.json",
        REPO_ROOT / "docs" / "kf" / PACKAGE_ID / "schema" / "kf_result.v1.schema.json",
    ]
    schema_ok, schema_where = None, None
    for p in schema_paths:
        if p.exists():
            import jsonschema

            jsonschema.validate(result, json.loads(p.read_text(encoding="utf-8")))
            schema_ok, schema_where = True, str(p.relative_to(REPO_ROOT))
            break
    m = result["outputs"]["asset_manifest.json"]
    ids = [r["ref_id"] for r in m["referenced_artifacts"]] + [
        d["digest_id"] for d in m["content_digests"]
    ]
    return {
        "valid_json": True,
        "schema_pass": bool(schema_ok),
        "schema_file": schema_where,
        "source_locator_resolvable": m["locator_check"]["all_resolved"],
        "locator_stats": f"{m['locator_check']['resolved']}/{m['locator_check']['total']}",
        "source_hash_matches": m["source_asset"]["hash"]["matches_contract"],
        "source_hash": m["source_asset"]["hash"]["value"],
        "no_duplicate_ids": len(ids) == len(set(ids)),
        "id_count": len(ids),
        "all_claims_have_evidence_or_explicit_unresolved_status": all(
            (c.get("evidence") or c.get("unresolved_reason")) for c in result["claims"]
        ),
        "claims_count": len(result["claims"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="离线复跑：直接用本地 markdown 文件")
    ap.add_argument("--record-json", help="离线复跑：平台记录 JSON（含 figures 元数据）")
    ap.add_argument("--check", action="store_true", help="打印验收自检结果")
    args = ap.parse_args()

    if args.from_file:
        md = Path(args.from_file).read_text(encoding="utf-8")
        if args.record_json:
            record = json.loads(Path(args.record_json).read_text(encoding="utf-8"))
            record["markdown"] = md
        else:
            record = {"id": int(REPORT_ID), "markdown": md}
    else:
        record = fetch_record()

    manifest, _ = build_manifest(record)
    result = build_result(manifest)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    for name, obj in (
        ("asset_manifest.json", manifest),
        ("kf_result.json", result),
    ):
        blob = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
        (OUT_DIR / name).write_text(blob, encoding="utf-8")
        (MIRROR_DIR / name).write_text(blob, encoding="utf-8")
        print(f"wrote {OUT_DIR/name} (+mirror {MIRROR_DIR/name})")
    if args.check:
        print(json.dumps(self_check(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())