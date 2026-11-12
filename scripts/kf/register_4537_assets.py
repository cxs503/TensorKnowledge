#!/usr/bin/env python3
"""KF work package wp-4537-01 — asset registration for report 4537 (zero extraction).

Registers the source asset (report markdown, byte-hash pinned), the platform record
metadata, the declared figure, and every file/path the report *references*, each with
an exact character-span locator into the markdown (span + snippet sha256), so that the
gate can re-resolve every locator independently.

Hard rules honoured here:
  * only report_id=4537 is read; nothing is written outside the worktree;
  * no claim is generated (claims==[]); no conclusion is marked verified;
  * every quoted fragment is sliced out of the fetched markdown programmatically
    (no hand-typed quotes anywhere in this script).

Usage:
    python3 scripts/kf/register_4537_assets.py            # fetch -> verify -> build
    python3 scripts/kf/register_4537_assets.py --from-cache   # rebuild from cached copy
Exit code 0 = all internal checks pass.
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

REPORT_ID = "4537"
CONTRACT_SOURCE_URI = "tensor://reports/4537"
CONTRACT_SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
CONTRACT_CHARS = 7931
CONTRACT_LAYER_HINT = "CI修复|tensorfem_pr128_ci_lint_fix|m"
PACKAGE_ID = "wp-4537-01"

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "kf" / "wp-4537-01"  # tracked: artifacts/ is dropped by the push gate
CACHE_MD = ROOT / "runs" / "m15537_wp4537_01" / "source_report_4537.md"
CACHE_RECORD = ROOT / "runs" / "m15537_wp4537_01" / "report_record_4537.json"

FILE_SUFFIXES = (
    ".py",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".log",
    ".sh",
    ".json",
    ".png",
    ".cfg",
    ".txt",
)
HEX7 = re.compile(r"^[0-9a-f]{7,40}$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_record() -> dict:
    base = os.environ["TENSOR_API_BASE"]
    user = os.environ["TENSOR_AGENT_USER"]
    password = os.environ["TENSOR_AGENT_PASS"]

    def _post(url: str, body: dict) -> dict:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def _get(url: str, token: str) -> bytes:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    token = _post(f"{base}/auth/login", {"username": user, "password": password})["access_token"]
    # read-only GET on exactly one report id; no other report id is touched
    return json.loads(_get(f"{base}/tensor/reports/{REPORT_ID}", token))


def span_records(md: str, needle: str) -> list[dict]:
    """All exact occurrences of `needle`, as [start, end) + snippet digest."""
    out: list[dict] = []
    start = 0
    while True:
        i = md.find(needle, start)
        if i < 0:
            break
        out.append(
            {
                "span": [i, i + len(needle)],
                "snippet_sha256": "sha256:" + sha256_hex(needle.encode("utf-8")),
                "quote": needle,
            }
        )
        start = i + 1
    return out


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or "x"


def parse_sections(md: str) -> list[dict]:
    heads = []
    for m in re.finditer(r"(?m)^(#{1,4})[ \t]+(.+?)[ \t]*$", md):
        heads.append(
            {
                "level": len(m.group(1)),
                "heading": m.group(2),
                "char_span": [m.start(), m.end()],
                "heading_span": [m.start(2), m.end(2)],
                "heading_sha256": "sha256:" + sha256_hex(m.group(2).encode("utf-8")),
            }
        )
    for idx, h in enumerate(heads):
        h["section_span"] = [
            h["char_span"][0],
            heads[idx + 1]["char_span"][0] if idx + 1 < len(heads) else len(md),
        ]
    return heads


def classify_token(tok: str) -> str | None:
    """Map a backticked token to an asset kind, or None if it is an inline code fragment."""
    if any(ch.isspace() for ch in tok):
        return "inline_code"  # command line / message string / code fragment: not an artifact
    if tok.startswith("--") or tok.startswith("-"):
        return None
    if "/" not in tok and not tok.endswith(FILE_SUFFIXES):
        if HEX7.match(tok):
            return "vcs_commit"
        return None
    if tok.endswith("/"):
        return "path_directory"
    if tok.endswith(FILE_SUFFIXES):
        return "path_file" if "/" in tok else "path_basename_shorthand"
    if re.match(r"^[a-z0-9._-]+/[A-Za-z0-9._-]+$", tok):  # e.g. agent/m3891
        return "vcs_branch"
    return None


def build(md: str, record: dict) -> dict:
    md_bytes = md.encode("utf-8")
    digest = sha256_hex(md_bytes)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    assets: list[dict] = []

    # ---- asset 1: the authoritative source text -------------------------------
    first_line = md.split("\n", 1)[0]
    assets.append(
        {
            "asset_id": f"asset-{REPORT_ID}-report-markdown",
            "kind": "report_markdown",
            "name": "tensor_reports.markdown",
            "logical_ref": CONTRACT_SOURCE_URI + "#markdown",
            "media_type": "text/markdown; charset=utf-8",
            "status": "resolved",
            "payload": {
                "present": True,
                "chars": len(md),
                "bytes_utf8": len(md_bytes),
                "sha256": "sha256:" + digest,
                "hash_scope": f"UTF-8 bytes of tensor_reports.markdown (report {REPORT_ID})",
            },
            "retrieval": {
                "endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}",
                "field": "markdown",
                "cache": str(CACHE_MD.relative_to(ROOT)),
            },
            "locator": {
                "source_field": "markdown",
                "span": [0, len(md)],
                "quote": first_line,
                "note": "全文字节范围即资产本体；quote=首行，用于快速定位同一 markdown",
            },
            "notes": "本工序唯一权威源；哈希由本脚本独立重算，并与契约 source_hash/ chars 逐字对齐。",
        }
    )

    # ---- asset 2: platform record metadata ------------------------------------
    record_view = {
        "id": record.get("id"),
        "title": record.get("title"),
        "scenario_key": record.get("scenario_key"),
        "mission_id": record.get("mission_id"),
        "status": record.get("status"),
        "created_by": record.get("created_by"),
        "created_at": record.get("created_at"),
        "stage": record.get("stage"),
        "tags": record.get("tags"),
        "summary_sha256": "sha256:" + sha256_hex((record.get("summary") or "").encode("utf-8")),
        "summary_chars": len(record.get("summary") or ""),
    }
    title = record.get("title") or ""
    title_spans = span_records(md, title) if title else []
    assets.append(
        {
            "asset_id": f"asset-{REPORT_ID}-record",
            "kind": "report_record_metadata",
            "name": "tensor_reports row",
            "logical_ref": CONTRACT_SOURCE_URI + "#record",
            "media_type": "application/json",
            "status": "resolved",
            "payload": record_view,
            "retrieval": {"endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}", "field": "record"},
            "locator": {
                "source_field": "record",
                "markdown_quote_spans": title_spans,
                "note": (
                    "记录层字段（title/scenario_key/tags/…）来自平台记录本身；"
                    "记录 title 在 markdown 正文中的逐字出现次数如实登记（0 次也照写，不补写标题）"
                ),
            },
            "notes": "只登记、不解读；objective.classify_report_type=false，故不推断报告类型。",
        }
    )

    # ---- asset 3..n: declared figure(s) --------------------------------------
    figures = record.get("figures") or []
    for i, fig in enumerate(figures):
        name = fig.get("name") or f"figure-{i + 1}"
        caption = fig.get("caption") or ""
        cap_spans = span_records(md, caption) if caption else []
        head = caption.split("：", 1)[0] if "：" in caption else caption[:12]
        head_spans = span_records(md, head) if head else []
        assets.append(
            {
                "asset_id": f"asset-{REPORT_ID}-figure-{i + 1}",
                "kind": "report_figure",
                "name": name,
                "logical_ref": CONTRACT_SOURCE_URI + f"#figures[{i}]",
                "media_type": "image/png",
                "status": "declared_metadata_only",
                "payload": {
                    "present": False,
                    "reason": "平台 GET /tensor/reports/{id} 的 figures[] 仅返回 name/caption，无 png 字节亦无 png_base64；本工序不臆造哈希",
                    "caption": caption,
                    "caption_chars": len(caption),
                    "caption_sha256": "sha256:" + sha256_hex(caption.encode("utf-8"))
                    if caption
                    else None,
                },
                "locator": {
                    "source_field": "record",
                    "record_path": f"figures[{i}].name",
                    "markdown_caption_spans": cap_spans,
                    "markdown_head_spans": head_spans,
                    "note": "caption 在 markdown 中的逐字出现区间（若正文未复述 caption，则为空数组，如实留白）",
                },
                "notes": "图形本体未随接口返回 → status=declared_metadata_only（unresolved，不送分）。",
            }
        )

    # ---- referenced file paths / vcs refs / commands --------------------------
    token_hits: dict[str, list[dict]] = {}
    for m in re.finditer(r"`([^`\n]+)`", md):
        tok = m.group(1)
        kind = classify_token(tok)
        if kind in (None, "inline_code"):
            continue
        token_hits.setdefault(f"{kind}\x00{tok}", []).append(
            {
                "span": [m.start(), m.end()],
                "token_span": [m.start(1), m.end(1)],
                "snippet_sha256": "sha256:" + sha256_hex(tok.encode("utf-8")),
                "quote": tok,
            }
        )

    inline_code_index: list[dict] = []
    for m in re.finditer(r"`([^`\n]+)`", md):
        tok = m.group(1)
        if classify_token(tok) != "inline_code":
            continue
        inline_code_index.append(
            {
                "token": tok,
                "span": [m.start(1), m.end(1)],
                "snippet_sha256": "sha256:" + sha256_hex(tok.encode("utf-8")),
                "kind": "command_line"
                if tok.split(" ")[0]
                in {"ruff", "git", "bash", "pytest", "python", "python3", "yaml.safe_load"}
                else "message_or_snippet",
            }
        )

    seen_ids: set[str] = {a["asset_id"] for a in assets}
    status_by_kind = {
        "path_file": "declared_only",
        "path_directory": "declared_only",
        "path_basename_shorthand": "declared_shorthand",
        "vcs_branch": "declared_metadata_only",
        "vcs_commit": "declared_metadata_only",
    }
    for key in sorted(token_hits):
        kind, tok = key.split("\x00", 1)
        hits = token_hits[key]
        if kind == "path_directory" and "/" not in tok:
            kind = "path_directory_shorthand"
        asset_id = f"asset-{REPORT_ID}-{slug(kind)}-{slug(tok)}"
        if asset_id in seen_ids:  # pragma: no cover - slug collisions guarded
            asset_id += "-" + sha256_hex(tok.encode())[:6]
        seen_ids.add(asset_id)

        # external resolvability: does the referenced path exist in *this* worktree?
        wt_path = ROOT / tok.rstrip("/")
        exists_here = tok.endswith(FILE_SUFFIXES) and "/" in tok and wt_path.exists()
        asset = {
            "asset_id": asset_id,
            "kind": kind,
            "name": tok,
            "logical_ref": ("worktree://" + tok) if exists_here else ("unresolved-ref://" + tok),
            "media_type": "text/plain" if exists_here else None,
            "status": "resolved" if exists_here else status_by_kind.get(kind, "declared_only"),
            "payload": {
                "present": bool(exists_here),
                "occurrences": len(hits),
                "bytes_utf8": len(wt_path.read_bytes()) if exists_here else None,
                "sha256": ("sha256:" + sha256_hex(wt_path.read_bytes())) if exists_here else None,
            },
            "locator": {
                "source_field": "markdown",
                "occurrences": [
                    {
                        "span": h["token_span"],
                        "snippet_sha256": h["snippet_sha256"],
                        "quote": h["quote"],
                    }
                    for h in hits
                ],
                "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解",
            },
            "notes": (
                "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
                if not exists_here
                else "本工作树内可直接解析的工件"
            ),
        }
        if kind.startswith("path_directory"):
            asset["notes"] = "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        if kind == "path_basename_shorthand":
            asset["notes"] = (
                "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
            )
        if kind in ("vcs_branch", "vcs_commit"):
            asset["notes"] = "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        assets.append(asset)

    # ---- attachments scan ----------------------------------------------------
    md_images = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", md))
    md_urls = len(re.findall(r"https?://[^\s)`]+", md))
    attachment_scan = {
        "record_figures_len": len(figures),
        "markdown_image_syntax_hits": md_images,
        "markdown_url_hits": md_urls,
        "markdown_url_samples": re.findall(r"https?://[^\s)`]+", md)[:5],
        "returned_all": True,
        "note": "扫描范围=记录 figures[] + markdown 图片语法 + markdown 明文 URL；结果全量登记，不做过滤",
    }

    # ---- claims: deliberately empty ------------------------------------------
    claims: list[dict] = []

    by_status: dict[str, int] = {}
    for a in assets:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    by_kind: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1

    unresolved = [
        {
            "asset_id": a["asset_id"],
            "name": a["name"],
            "status": a["status"],
            "reason": a["payload"].get("reason") or a["notes"],
        }
        for a in assets
        if a["status"] != "resolved"
    ]

    checks = {
        "source_hash_matches_contract": "sha256:" + digest == CONTRACT_SOURCE_HASH,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "all_locators_resolve": all(
            md[s:e] == occ["quote"]
            for a in assets
            for occ in (
                a["locator"].get("occurrences", [])
                + a["locator"].get("markdown_caption_spans", [])
                + a["locator"].get("markdown_head_spans", [])
                + a["locator"].get("markdown_quote_spans", [])
            )
            for s, e in [occ["span"]]
        )
        if assets
        else False,
        "no_duplicate_asset_ids": len({a["asset_id"] for a in assets}) == len(assets),
        "claims_empty": claims == [],
        "no_inline_code_in_assets": all(a["kind"] != "inline_code" for a in assets),
        "inline_code_spans_resolve": all(
            md[s:e] == it["token"] for it in inline_code_index for s, e in [it["span"]]
        ),
        "no_verification_marked": all("verified" not in a["status"] for a in assets),
        "single_report_scope": record.get("id") == int(REPORT_ID),
    }

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": "01-asset-registration",
        "lane": "C",
        "objective": {
            "register_assets": True,
            "classify_report_type": False,
            "extraction_performed": False,
        },
        "generated_at": now,
        "generator": "scripts/kf/register_4537_assets.py",
        "generator_inputs": {
            "report_id": REPORT_ID,
            "source_uri": CONTRACT_SOURCE_URI,
            "source_field": CONTRACT_SOURCE_FIELD,
            "contract_expected_sha256": CONTRACT_SOURCE_HASH,
            "contract_expected_chars": CONTRACT_CHARS,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": CONTRACT_SOURCE_URI,
            "source_field": CONTRACT_SOURCE_FIELD,
            "sha256": "sha256:" + digest,
            "contract_declared_sha256": CONTRACT_SOURCE_HASH,
            "source_hash_matches": "sha256:" + digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "lines": len(md.split("\n")),
            "contract_declared_chars": CONTRACT_CHARS,
            "chars_match": len(md) == CONTRACT_CHARS,
            "hash_scope": f"UTF-8 bytes of tensor_reports.markdown (report {REPORT_ID})",
            "retrieval": {
                "endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}",
                "field": "markdown",
            },
            "record": record_view,
            "first_line": first_line,
            "headings_count": len(parse_sections(md)),
            "sections": parse_sections(md),
            "section_span_definition": "char_span=标题行本身；section_span=[标题起点, 下一个任意级标题起点)——即标题块，不含子标题下属内容（不做层级展开，避免过度解读）",
            "contract_layer_hint": {
                "value": CONTRACT_LAYER_HINT,
                "interpreted": False,
                "note": "契约 notes 原文登记；objective.classify_report_type=false，不解读分层标签",
            },
        },
        "attachment_scan": attachment_scan,
        "inline_code_index": {
            "count": len(inline_code_index),
            "note": "行内代码片段（命令/告警串/配置片段）索引：只给定位，不计为工件，故不进 assets",
            "items": inline_code_index,
        },
        "asset_counts": {
            "total": len(assets),
            "by_status": by_status,
            "by_kind": by_kind,
            "unresolved": len(unresolved),
        },
        "assets": assets,
        "claims": claims,
        "unresolved": unresolved,
        "checks": checks,
        "repro": {
            "cmd": "python3 scripts/kf/register_4537_assets.py && python3 -m pytest tests/test_kf_wp4537_01.py -q",
            "rebuild_from_cache": "python3 scripts/kf/register_4537_assets.py --from-cache",
            "env": ["TENSOR_API_BASE", "TENSOR_AGENT_USER", "TENSOR_AGENT_PASS"],
            "note": "重跑会重新拉取 report 4537 并重算哈希；--from-cache 用 runs/ 缓存复算（离线可跑）",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--from-cache", action="store_true", help="rebuild from the cached markdown+record"
    )
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_MD.parent.mkdir(parents=True, exist_ok=True)

    if args.from_cache:
        md = CACHE_MD.read_text(encoding="utf-8")
        record = json.loads(CACHE_RECORD.read_text(encoding="utf-8"))
    else:
        record = fetch_record()
        md = record["markdown"]
        CACHE_MD.write_text(md, encoding="utf-8")
        record_meta = {k: v for k, v in record.items() if k != "markdown"}
        CACHE_RECORD.write_text(json.dumps(record_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = build(md, record)
    manifest_path = OUT_DIR / "asset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["sha256"],
            "source_field": CONTRACT_SOURCE_FIELD,
            "source_uri": CONTRACT_SOURCE_URI,
            "producer": "scripts/kf/register_4537_assets.py",
            "emitted_at": manifest["generated_at"],
            "notes": "source_hash=本脚本对 markdown UTF-8 字节独立重算的 sha256；与契约声明一致（见 checks）。",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": manifest["claims"],
    }
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "manifest": str(manifest_path.relative_to(ROOT)),
                "checks": manifest["checks"],
                "asset_counts": manifest["asset_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(manifest["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
