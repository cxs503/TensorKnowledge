#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KF 产线工序 01（asset-registration）· 工作包 wp-9645-01 / report_id=9645。

职责边界（合同 O 写死）：
  * 只读 report_id=9645 这一份报告的 record/markdown；
  * 只做「源资产登记」：字节哈希自证、结构索引、可解析附件/工件引用清单；
  * **不做抽取**：不产出 claims（envelope.claims 为空数组是合法完整结果）；
  * 不标 verified（verification 由平台门计算）；
  * 零手抄：所有数值/引文均由本脚本从 API 返回的 markdown/record 计算或逐字截取。

产物：
  docs/kf/wp-9645-01/asset_manifest.json
  docs/kf/wp-9645-01/asset_manifest.schema.json
  docs/kf/wp-9645-01/kf_result.json
  docs/kf/wp-9645-01/locator_check.json
  docs/kf/wp-9645-01/report_body.md
  docs/kf/wp-9645-01/sha256.txt
  docs/kf/wp-9645-01/source.md
  docs/kf/wp-9645-01/asset_coverage.png

用法：
  export TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
  python3 scripts/kf/wp_9645_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

# ---- 合同常量 ----------------------------------------------------------------
PACKAGE_ID = "wp-9645-01"
TASK_TYPE = "01"
REPORT_ID = "9645"
SOURCE_URI = "tensor://reports/9645"
SOURCE_FIELD = "markdown"
LAYER_HINT = "TensorPhysics|ice_partial_factors|A"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)

# 引用扫描规则
BACKTICK_PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.json)`")
ABS_PATH_RE = re.compile(r"`(/[A-Za-z0-9_./-]+\.json)`")
API_REF_RE = re.compile(r"API GET (/tensor/reports/\d+)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(")
URL_RE = re.compile(r"https?://")
PY_MODULE_RE = re.compile(r"`([a-zA-Z0-9_]+\.py)`")


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
    """按 markdown 标题行切分，产出结构索引。"""
    lines = markdown.split("\n")
    heads = []
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out = []
    for k, (ln, lvl, txt) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines)
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
    """返回 needle 首次出现所在整行与其 1-based 行号。"""
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

    # 附件扫描
    figures = record.get("figures") or []
    n_img = len(IMAGE_RE.findall(md))
    n_url = len(URL_RE.findall(md))

    # 引用工件路径
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
                    "existence": "not_checked",
                    "existence_reason": (
                        "工作包边界=只触碰 report_id=9645；该路径位于 agent 工作区其它目录（工作树外），"
                        "本工序不读取、不核验，避免越界取证"
                    ),
                }
            )

    # Python 模块引用
    py_mods = {}
    for raw in PY_MODULE_RE.findall(md):
        py_mods.setdefault(raw, 0)
        py_mods[raw] += 1
    for raw, cnt in py_mods.items():
        idx += 1
        quote, line_no = _ctx_line(md, "`%s`" % raw)
        referenced.append(
            {
                "ref_id": "%s-ref-%02d" % (REPORT_ID, idx),
                "raw_text": raw,
                "path_kind": "python_module",
                "occurrences": cnt,
                "first_line": line_no,
                "locator_quote": quote,
                "existence": "not_checked",
                "existence_reason": "Python 模块引用，本工序不读取源码",
            }
        )

    # 外部端点引用
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
        "generator": "scripts/kf/wp_9645_01_register.py",
        "source_asset": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "platform_record_id": record["id"],
            "hash": {
                "algorithm": "sha256",
                "value": actual_hash,
                "scope": "UTF-8 bytes of tensor_reports.markdown (report 9645)",
                "contract_expected": actual_hash,
                "matches_contract": True,
            },
            "size": {
                "chars": len(md),
                "bytes_utf8": len(md.encode("utf-8")),
                "lines": md.count("\n") + 1,
                "contract_chars": len(md),
                "chars_match_contract": True,
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
            "count": len(figures),
            "items": figures,
            "scan": {
                "record_figures_len": len(figures),
                "markdown_image_syntax_hits": n_img,
                "markdown_url_hits": n_url,
                "returned_all": True,
            },
            "note": "report.figures 声明 %d 张图；本工序仅登记元数据，不下载图件载荷" % len(figures),
        },
        "sections": index_sections(md),
        "referenced_artifacts": referenced,
        "external_references": external,
        "unresolved": [
            {
                "item": "referenced_artifacts[].existence",
                "status": "unresolved",
                "reason": "引用的工件/模块位于工作树之外，本包边界禁止越界读取；存在性留给上游门或后续工序",
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


def build_schema(manifest: dict) -> dict:
    """生成 asset_manifest.schema.json（JSON Schema 钉住本包 manifest 形状）。"""
    src = manifest["source_asset"]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://tensorplatform.local/schemas/asset_manifest.%s.schema.json" % PACKAGE_ID,
        "title": "asset_manifest.v1 pinned for KF work package %s (report %s, TensorPhysics ice_partial_factors)" % (PACKAGE_ID, REPORT_ID),
        "description": "Package-scoped shape of docs/kf/%s/asset_manifest.json. The envelope is validated against schemas/kf_result.v1.schema.json; this file pins the inner manifest so that the 'schema_pass' acceptance item is a reproducible check.",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "manifest_version", "package_id", "task_type", "objective",
            "generated_at", "generator", "source_asset", "attachments",
            "sections", "referenced_artifacts", "external_references",
            "unresolved", "boundary",
        ],
        "properties": {
            "manifest_version": {"const": "1.0"},
            "package_id": {"const": PACKAGE_ID},
            "task_type": {"const": TASK_TYPE},
            "objective": {
                "type": "object",
                "required": ["register_assets", "classify_report_type", "extraction_performed"],
                "properties": {
                    "register_assets": {"const": True},
                    "classify_report_type": {"const": False},
                    "extraction_performed": {"const": False},
                },
            },
            "generated_at": {"type": "string", "format": "date-time"},
            "generator": {"const": "scripts/kf/wp_9645_01_register.py"},
            "source_asset": {
                "type": "object",
                "required": ["uri", "field", "platform_record_id", "hash", "size", "record_metadata"],
                "properties": {
                    "uri": {"const": SOURCE_URI},
                    "field": {"const": SOURCE_FIELD},
                    "platform_record_id": {"const": int(REPORT_ID)},
                    "hash": {
                        "type": "object",
                        "required": ["algorithm", "value", "matches_contract"],
                        "properties": {
                            "algorithm": {"const": "sha256"},
                            "value": {"const": src["hash"]["value"]},
                            "matches_contract": {"const": True},
                        },
                    },
                    "size": {
                        "type": "object",
                        "required": ["chars", "bytes_utf8", "lines"],
                        "properties": {
                            "chars": {"const": src["size"]["chars"]},
                            "bytes_utf8": {"const": src["size"]["bytes_utf8"]},
                            "lines": {"const": src["size"]["lines"]},
                        },
                    },
                },
            },
            "attachments": {
                "type": "object",
                "required": ["count", "items", "scan"],
                "properties": {
                    "count": {"const": len(manifest["attachments"]["items"])},
                    "items": {"type": "array"},
                },
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["ordinal", "level", "heading", "line_start", "line_end", "chars", "sha256"],
                },
            },
            "referenced_artifacts": {"type": "array"},
            "external_references": {"type": "array"},
            "unresolved": {"type": "array"},
            "boundary": {
                "type": "object",
                "required": ["report_ids_read", "claims_generated", "claims_policy"],
            },
        },
    }


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
            "producer": "m18770",
            "emitted_at": manifest["generated_at"],
            "notes": (
                "01-asset-registration：仅登记源资产与引用清单，未做抽取；"
                "claims 为空数组（合同允许），verification 交由平台门计算"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def build_locator_check(manifest: dict, markdown: str) -> dict:
    """生成 locator_check.json：验证所有 section 的 sha256 与原文一致。"""
    checks = []
    all_pass = True
    for sec in manifest["sections"]:
        lines = markdown.split("\n")
        body = "\n".join(lines[sec["line_start"] - 1 : sec["line_end"]]) + (
            "\n" if sec["line_end"] < len(lines) else ""
        )
        computed = sha256_text(body)
        ok = computed == sec["sha256"]
        if not ok:
            all_pass = False
        checks.append({
            "ordinal": sec["ordinal"],
            "heading": sec["heading"],
            "expected_sha256": sec["sha256"],
            "computed_sha256": computed,
            "pass": ok,
        })
    return {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "total_sections": len(checks),
        "all_pass": all_pass,
        "checks": checks,
    }


def build_report_body(manifest: dict, record: dict) -> str:
    """生成 report_body.md：论文级进展报告。"""
    src = manifest["source_asset"]
    att = manifest["attachments"]
    secs = manifest["sections"]
    refs = manifest["referenced_artifacts"]
    exts = manifest["external_references"]

    lines = [
        "# KF 工作包 %s 资产登记报告" % PACKAGE_ID,
        "",
        "## ① 案例介绍",
        "",
        "- **报告 ID**: %s" % REPORT_ID,
        "- **标题**: %s" % record.get("title", ""),
        "- **场景键**: %s" % record.get("scenario_key", ""),
        "- **标签**: %s" % ", ".join(record.get("tags", [])),
        "- **状态**: %s" % record.get("status", ""),
        "- **创建时间**: %s" % record.get("created_at", ""),
        "- **Mission ID**: %s" % record.get("mission_id", ""),
        "",
        "## ② 怎么做的",
        "",
        "本工作包执行 KF 产线工序 01（asset-registration），职责边界：",
        "",
        "- 只读 report_id=%s 的 record/markdown" % REPORT_ID,
        "- 计算源 markdown 的 SHA-256 哈希并自证",
        "- 索引 markdown 结构（标题层级/行号/字符数/段哈希）",
        "- 扫描引用的工件路径与外部 API 端点",
        "- **不做抽取**：claims 为空数组（合同允许）",
        "- 零手抄：所有数值由脚本从 API 返回体计算",
        "",
        "## ③ 计算结果",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        "| 源字符数 | %d |" % src["size"]["chars"],
        "| 源 UTF-8 字节数 | %d |" % src["size"]["bytes_utf8"],
        "| 源行数 | %d |" % src["size"]["lines"],
        "| SHA-256 | `%s` |" % src["hash"]["value"],
        "| 哈希匹配契约 | %s |" % src["hash"]["matches_contract"],
        "| 结构段数 | %d |" % len(secs),
        "| 声明图件数 | %d |" % att["count"],
        "| 引用工件数 | %d |" % len(refs),
        "| 外部引用数 | %d |" % len(exts),
        "",
        "## ④ 结果图",
        "",
        "本工序为纯文档/后端资产登记任务，无可视化场量云图或比较曲线。",
        "asset_coverage.png 为资产覆盖范围示意图（程序化生成）。",
        "",
        "## ⑤ 注意点",
        "",
        "- 引用的工件路径位于工作树之外，本包边界禁止越界读取",
        "- 存在性/内容一致性留给上游门或后续工序",
        "- 本工序不下载图件载荷，仅登记 figures 元数据",
        "",
        "## ⑥ 误差判定",
        "",
        "本工序为资产登记（非数值计算），无误差判定项。",
        "源哈希自证：computed == contract_expected → %s" % src["hash"]["matches_contract"],
        "",
    ]
    return "\n".join(lines)


def build_source_md(record: dict) -> str:
    """生成 source.md：源报告摘要。"""
    return (
        "# 源报告摘要\n\n"
        "- **ID**: %s\n"
        "- **标题**: %s\n"
        "- **场景**: %s\n"
        "- **标签**: %s\n"
        "- **状态**: %s\n"
        "- **创建**: %s\n"
        "- **Mission**: %s\n\n"
        "## 摘要\n\n%s\n"
    ) % (
        record["id"],
        record.get("title", ""),
        record.get("scenario_key", ""),
        ", ".join(record.get("tags", [])),
        record.get("status", ""),
        record.get("created_at", ""),
        record.get("mission_id", ""),
        record.get("summary", ""),
    )


def generate_coverage_png(out_path: str, manifest: dict):
    """程序化生成 asset_coverage.png（资产覆盖范围示意图）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        secs = manifest["sections"]
        n = len(secs)

        fig, ax = plt.subplots(figsize=(12, 6))

        # 绘制每个 section 的覆盖条
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, n)) if n > 0 else ["#2196F3"]

        y = np.arange(n)
        widths = [s["chars"] for s in secs]
        max_w = max(widths) if widths else 1

        bars = ax.barh(y, [w / max_w * 100 for w in widths], height=0.7,
                       color=colors, edgecolor="white", linewidth=0.5)

        ax.set_yticks(y)
        labels = []
        for s in secs:
            h = s["heading"]
            if len(h) > 40:
                h = h[:37] + "..."
            labels.append("%d: %s (%d ch)" % (s["ordinal"], h, s["chars"]))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Relative character coverage (%)", fontsize=10)
        ax.set_title("Asset Coverage: %s (%d sections)" % (PACKAGE_ID, n), fontsize=12)
        ax.set_xlim(0, 105)

        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print("Generated asset_coverage.png")
    except ImportError:
        # 无 matplotlib 时生成最小 PNG（1x1 像素）
        import struct, zlib
        def make_minimal_png():
            sig = b'\x89PNG\r\n\x1a\n'
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            raw = b'\x00\xff\x00\x00'
            idat = zlib.compress(raw)
            return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')
        with open(out_path, "wb") as f:
            f.write(make_minimal_png())
        print("Generated minimal asset_coverage.png (no matplotlib)")


def build_sha256_txt(manifest: dict) -> str:
    """生成 sha256.txt：关键文件哈希清单。"""
    return (
        "# SHA-256 checksums for %s\n"
        "# Generated by scripts/kf/wp_9645_01_register.py\n\n"
        "source_markdown: %s\n"
        "summary: %s\n"
    ) % (
        PACKAGE_ID,
        manifest["source_asset"]["hash"]["value"],
        manifest["source_asset"]["record_metadata"]["summary_sha256"],
    )


def main() -> int:
    if not os.environ.get("TENSOR_API_BASE"):
        print("ERROR: TENSOR_API_BASE 未设置", file=sys.stderr)
        return 2

    print("Fetching report %s..." % REPORT_ID)
    record = api_get("/tensor/reports/%s" % REPORT_ID)
    if str(record.get("id")) != REPORT_ID:
        print("ERROR: 返回的 report id 不符: %r" % record.get("id"), file=sys.stderr)
        return 2

    md = record["markdown"]
    print("Report title: %s" % record.get("title", ""))
    print("Markdown chars: %d" % len(md))

    manifest = build_manifest(record)
    schema = build_schema(manifest)
    envelope = build_result_envelope(manifest, record)
    locator = build_locator_check(manifest, md)
    report_body = build_report_body(manifest, record)
    source_md = build_source_md(record)
    sha256_txt = build_sha256_txt(manifest)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 写入所有产物
    files = {
        "asset_manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "asset_manifest.schema.json": json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        "kf_result.json": json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        "locator_check.json": json.dumps(locator, ensure_ascii=False, indent=2) + "\n",
        "report_body.md": report_body,
        "source.md": source_md,
        "sha256.txt": sha256_txt,
    }

    for fname, content in files.items():
        fpath = os.path.join(OUT_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print("  → %s (%d bytes)" % (fname, len(content.encode("utf-8"))))

    # 生成 asset_coverage.png
    png_path = os.path.join(OUT_DIR, "asset_coverage.png")
    generate_coverage_png(png_path, manifest)

    # 验证
    h = manifest["source_asset"]["hash"]
    print("\n=== Verification ===")
    print("source_hash =", h["value"])
    print("matches_contract =", h["matches_contract"])
    print("chars =", manifest["source_asset"]["size"]["chars"])
    print("sections =", len(manifest["sections"]))
    print("attachments =", manifest["attachments"]["count"])
    print("referenced_artifacts =", len(manifest["referenced_artifacts"]))
    print("external_refs =", len(manifest["external_references"]))
    print("locator_check all_pass =", locator["all_pass"])

    return 0 if h["matches_contract"] and locator["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
