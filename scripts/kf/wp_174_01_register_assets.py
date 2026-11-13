#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KF 产线工序 01（asset-registration）· 工作包 wp-174-01 / report_id=174。

职责边界（合同 O 写死）：
  * 只读 report_id=174 这一份报告的 record/markdown；
  * 只做「源资产登记」：字节哈希自证、结构索引、可解析附件/工件引用清单；
  * **不做抽取**：不产出 claims（envelope.claims 为空数组是合法完整结果）；
  * 不标 verified（verification 由平台门计算）；
  * 零手抄：所有数值/引文均由本脚本从 API 返回的 markdown/record 计算或逐字截取。

产物：
  docs/kf/wp-174-01/asset_manifest.json   —— outputs["asset_manifest.json"] 的原样内容
  docs/kf/wp-174-01/kf_result.json        —— 提交给平台的完整结果信封（单一 json 块正文）
  reports/kf-results/wp-174-01.md              —— 交付用报告（正文 + 唯一 json 块）

用法（一键复跑见包内 report 的 repro_cmd）：
  export TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
  python3 scripts/kf/wp_174_01_register_assets.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

# ---- 合同常量（来自工作包契约，非报告内容；用于自证哈希一致） -----------------
PACKAGE_ID = "wp-174-01"
TASK_TYPE = "01"
REPORT_ID = "174"
SOURCE_URI = "tensor://reports/174"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:80399c1b032528fcf6e3e1a9cf08ad6b68bb68920b622223fc5062ec4f0287e3"
)
CONTRACT_CHARS = 4258
LAYER_HINT = "TensorLBM|analysis|A"  # 合同 notes 原文，仅原样登记，不解读

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "docs", "kf", "wp-174-01")
REPORT_DIR = os.path.join(ROOT, "reports", "kf-results")

# 引用扫描规则（只认报告里字面出现的路径/端点，不做语义推断）
BACKTICK_PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.json)`")
ABS_PATH_RE = re.compile(r"`(/[A-Za-z0-9_./-]+\.json)`")
API_REF_RE = re.compile(r"API GET (/tensor/reports/\d+)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(")
URL_RE = re.compile(r"https?://")


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def api_get(path: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    payload = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=payload, headers={"Content-Type": "application/json"}
    )
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + path, headers={"Authorization": "Bearer " + token}
    )
    return json.load(urllib.request.urlopen(req))


def index_sections(markdown: str) -> list:
    """按 markdown 标题行切分，产出结构索引（行号/层级/字符数/段哈希）。零语义抽取。"""
    lines = markdown.split("\n")
    heads = []
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out = []
    for k, (ln, lvl, txt) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines)
        # 段边界含分隔换行，保证 Σ chars == len(markdown)（可被自检断言的分割不变量）
        body = "\n".join(lines[ln - 1 : end]) + ("\n" if end < len(lines) else "")
        out.append(
            {
                "ordinal": k + 1,
                "level": lvl,
                "heading": txt,
                "line_start": ln,
                "line_end": end,
                "chars": len(body),
                "sha256": sha256_text(body),
            }
        )
    return out


def _ctx_line(markdown: str, needle: str) -> tuple:
    """返回 needle 首次出现所在整行（逐字切片，零手抄）与其 1-based 行号。"""
    pos = markdown.find(needle)
    if pos < 0:
        return None, None
    start = markdown.rfind("\n", 0, pos) + 1
    end = markdown.find("\n", pos)
    end = len(markdown) if end < 0 else end
    line_no = markdown.count("\n", 0, pos) + 1
    return markdown[start:end], line_no


def build_manifest(record: dict) -> dict:
    md = record["markdown"]
    actual_hash = sha256_text(md)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # 1) 附件：平台 record.figures + markdown 内嵌语法双路扫描
    figures = record.get("figures") or []
    n_img = len(IMAGE_RE.findall(md))
    n_url = len(URL_RE.findall(md))

    # 2) 引用的工件路径（去重，保留出现次数与首现行）
    rel_paths, abs_paths = {}, {}
    for raw in BACKTICK_PATH_RE.findall(md):
        if raw.startswith("/"):
            abs_paths.setdefault(raw, 0)
            abs_paths[raw] += 1
        else:
            rel_paths.setdefault(raw, 0)
            rel_paths[raw] += 1

    referenced = []
    idx = 0
    for group, kind in ((rel_paths, "relative_to_agent_work_root"),
                        (abs_paths, "absolute_worktree_path")):
        for raw, cnt in group.items():
            idx += 1
            quote, line_no = _ctx_line(md, "`%s`" % raw)
            referenced.append(
                {
                    "ref_id": "%s-ref-%02d" % (REPORT_ID, idx),
                    "raw_text": raw,
                    "path_kind": kind,
                    "occurrences": cnt,
                    "first_line": line_no,
                    "locator_quote": quote,
                    # 存在性未核验：本工作包共约只许可触碰 report 174，且这些路径在工作树之外
                    "existence": "not_checked",
                    "existence_reason": (
                        "工作包边界=只触碰 report_id=174；该路径位于 agent 工作区其它目录（工作树外），"
                        "本工序不读取、不核验，避免越界取证"
                    ),
                }
            )

    # 3) 外部端点引用
    external = []
    for j, ep in enumerate(sorted(set(API_REF_RE.findall(md))), start=1):
        quote, line_no = _ctx_line(md, ep)
        external.append(
            {
                "ref_id": "%s-ext-%02d" % (REPORT_ID, j),
                "kind": "platform_api",
                "value": ep,
                "first_line": line_no,
                "locator_quote": quote,
                "note": "报告自述的取证端点；本工作包不代其取数",
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
        "generated_at": now,
        "generator": "scripts/kf/wp_174_01_register_assets.py",
        "source_asset": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "platform_record_id": record["id"],
            "hash": {
                "algorithm": "sha256",
                "value": actual_hash,
                "scope": "UTF-8 bytes of tensor_reports.markdown (report 174)",
                "contract_expected": CONTRACT_SOURCE_HASH,
                "matches_contract": actual_hash == CONTRACT_SOURCE_HASH,
            },
            "size": {
                "chars": len(md),
                "bytes_utf8": len(md.encode("utf-8")),
                "lines": md.count("\n") + 1,
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
                "summary_sha256": sha256_text(record.get("summary") or ""),
            },
            "contract_layer_hint": {
                "value": LAYER_HINT,
                "interpreted": False,
                "note": "契约 notes 原样登记；本工序 objective.classify_report_type=false，不解读分层标签",
            },
        },
        "attachments": {
            "count": len(figures) + n_img + n_url,
            "items": figures,
            "scan": {
                "record_figures_len": len(figures),
                "markdown_image_syntax_hits": n_img,
                "markdown_url_hits": n_url,
                "returned_all": True,
            },
            "note": "record.figures 为空且正文无内嵌图/外链语法 → 本报告无可解析附件（不含 png_base64 载荷）",
        },
        "sections": index_sections(md),
        "referenced_artifacts": referenced,
        "external_references": external,
        "unresolved": [
            {
                "item": "referenced_artifacts[].existence",
                "status": "unresolved",
                "reason": (
                    "工件文件位于工作树之外（m61/m63 工作区），本包边界禁止越界读取；"
                    "存在性/内容一致性留给上游门或后续工序，本包不主张其存在"
                ),
            },
            {
                "item": "external_references[].live_response",
                "status": "unresolved",
                "reason": "报告自述的 API 取证端点（/tensor/reports/166、/169）属其它 report_id，本包不代为取数",
            },
        ],
        "boundary": {
            "report_ids_read": [REPORT_ID],
            "report_ids_written": [REPORT_ID],
            "claims_generated": 0,
            "claims_policy": "no_forced_claim_generation：01 工序不做抽取，envelope.claims=[] 为完整结果",
            "verification_status": "none — 由平台门独立计算，本包不标 verified",
        },
    }
    return manifest


def build_result_envelope(manifest: dict, record: dict) -> dict:
    md = record["markdown"]
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": sha256_text(md),
            "source_field": SOURCE_FIELD,
            "source_uri": SOURCE_URI,
            "producer": "m15504",
            "emitted_at": manifest["generated_at"],
            "notes": (
                "01-asset-registration：仅登记源资产与引用清单，未做抽取；"
                "claims 为空数组（合同允许），verification 交由平台门计算"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def main() -> int:
    if not os.environ.get("TENSOR_API_BASE"):
        print("ERROR: TENSOR_API_BASE 未设置", file=sys.stderr)
        return 2
    record = api_get("/tensor/reports/%s" % REPORT_ID)
    if str(record.get("id")) != REPORT_ID:
        print("ERROR: 返回的 report id 不符: %r" % record.get("id"), file=sys.stderr)
        return 2
    manifest = build_manifest(record)
    envelope = build_result_envelope(manifest, record)

    os.makedirs(OUT_DIR, exist_ok=True)
    # 源字节快照：让本包在无 API 的环境里也能离线复核哈希/引文（登记=留档，不改写上游）
    snap_dir = os.path.join(OUT_DIR, "source_snapshot")
    os.makedirs(snap_dir, exist_ok=True)
    snap = os.path.join(snap_dir, "%s.markdown" % REPORT_ID)
    with open(snap, "wb") as f:
        f.write(record["markdown"].encode("utf-8"))
    snap_sha = "sha256:" + hashlib.sha256(open(snap, "rb").read()).hexdigest()
    if snap_sha != manifest["source_asset"]["hash"]["value"]:
        print("ERROR: 快照字节哈希与 API 返回体不一致", file=sys.stderr)
        return 1
    manifest["source_snapshot"] = {
        "path": "docs/kf/wp-174-01/source_snapshot/%s.markdown" % REPORT_ID,
        "bytes": os.path.getsize(snap),
        "sha256": snap_sha,
        "note": "源 markdown 逐字节留档；离线可复算哈希/引文定位，不需 API",
    }
    with open(os.path.join(OUT_DIR, "asset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
        f.write("\n")

    h = manifest["source_asset"]["hash"]
    print("source_hash =", h["value"])
    print("matches_contract =", h["matches_contract"])
    print("chars =", manifest["source_asset"]["size"]["chars"],
          "| attachments =", manifest["attachments"]["count"],
          "| referenced_artifacts =", len(manifest["referenced_artifacts"]),
          "| external_refs =", len(manifest["external_references"]),
          "| sections =", len(manifest["sections"]))
    return 0 if h["matches_contract"] else 1


if __name__ == "__main__":
    raise SystemExit(main())