#!/usr/bin/env python3
"""工序 01（asset-registration）执行器：登记源报告资产与指纹，不做知识抽取。

工作包契约 wp-615-01（report_id=615，source_field=markdown，
source_hash=sha256:3c1b5f9d...b7e75，chars=2125）。

设计原则（对应契约的 constraints）：
  * 零手抄：所有引文（quote）都由脚本从抓取的 markdown 里**按行取子串**得到，
    不手打任何字符；随后逐条做 `quote in markdown` 与偏移回读二次确认。
  * 不伪造：抓不到字节的资产（如图件）标 declared_unresolvable 并写明理由，
    不重绘、不代上游补图。
  * 不越界：只允许 report_id=615（契约锁定的那一份），其它 id 直接拒绝。
  * 不标 verified：本脚本不产出 claims，不做任何真伪判定。

用法：
  python3 scripts/kf/wp_615_01_register_assets.py            # 抓线上报告 615 并重建产物
  python3 scripts/kf/wp_615_01_register_assets.py --check-only --offline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------- 契约常量（来自 wp-615-01 YAML）
PKG = "wp-615-01"
REPORT_ID = "615"
SOURCE_URI = "tensor://reports/615"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75"
CONTRACT_TITLE = "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework"
CONTRACT_SCENARIO = "SIR-PC2|F06"
CONTRACT_CHARS = 2125

API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "kf" / PKG
# 结构门用包级 pin 的 schema（见 schemas/ 下同名文件 description 里的缘由）
MANIFEST_SCHEMA = "asset_manifest.v1.wp-615-01.schema.json"
# artifacts/ 被 .gitignore 忽略（mission-push 门会丢 artifacts/**），
# 故交付副本另落 knowledge/kf/<pkg>/（受版本控制），两处逐字节一致，由 tests 绑定。
MIRROR_DIR = ROOT / "knowledge" / "kf" / PKG


# ---------------------------------------------------------------- 抓取
def login_token() -> str:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        raise SystemExit("missing TENSOR_AGENT_USER / TENSOR_AGENT_PASS")
    r = requests.post(f"{API_BASE}/auth/login", json={"username": user, "password": pwd}, timeout=30)
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        raise SystemExit(f"login returned no access_token: {r.text[:200]}")
    return tok


def fetch_report(token: str) -> dict[str, Any]:
    if REPORT_ID != "615":  # 边界硬约束：本脚本只服务 report 615
        raise SystemExit("this work package is pinned to report_id=615 only")
    r = requests.get(f"{API_BASE}/tensor/reports/{REPORT_ID}",
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    rec = r.json()
    if str(rec.get("id")) != REPORT_ID:
        raise SystemExit(f"report id mismatch: {rec.get('id')!r}")
    return rec


def probe(url: str, token: str | None) -> dict[str, Any]:
    if not token:
        return {"endpoint": url.replace(API_BASE, "GET /api/v1"), "http_status": None,
                "error": "offline mode: probe skipped"}
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        body: Any
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        return {"endpoint": url.replace(API_BASE, "GET /api/v1"), "http_status": r.status_code, "body": body}
    except Exception as exc:  # 网络异常也如实登记
        return {"endpoint": url.replace(API_BASE, "GET /api/v1"), "http_status": None, "error": str(exc)}


# ---------------------------------------------------------------- markdown 解析工具
LIMIT = 0  # 统一失败即抛，不做静默降级


class MarkdownIndex:
    def __init__(self, md: str) -> None:
        self.md = md
        self.lines = md.split("\n")

    def find_line(self, needle: str, start: int = 0, occurrence: int = 1, strict: bool = True) -> tuple[str, int]:
        """返回 (整行原文, 该行在全文中的字符偏移)。strict 时要求命中次数与 occurrence 一致。"""
        hits = [(ln, i) for i, ln in enumerate(self.lines, start=start) if needle in ln]
        if len(hits) < occurrence:
            if strict:
                raise SystemExit(f"selector not found: {needle!r} (need occurrence {occurrence}, got {len(hits)})")
            return "", -1
        ln, i = hits[occurrence - 1]
        off = self.offset_of_line(i)
        return ln, off

    def offset_of_line(self, idx: int) -> int:
        return sum(len(x) + 1 for x in self.lines[:idx])

    def line_index(self, needle: str, start: int = 0, occurrence: int = 1) -> int:
        hits = [i for i, ln in enumerate(self.lines, start=start) if needle in ln]
        if len(hits) < occurrence:
            raise SystemExit(f"selector not found: {needle!r}")
        return hits[occurrence - 1]

    def heading_line(self, prefix: str) -> tuple[str, int]:
        return self.find_line(prefix)

    def first_nonempty_after(self, prefix: str) -> tuple[str, int]:
        i = self.line_index(prefix)
        for j in range(i + 1, len(self.lines)):
            if self.lines[j].strip():
                return self.lines[j], self.offset_of_line(j)
        raise SystemExit(f"no content after heading {prefix!r}")

    def table_after(self, prefix: str) -> dict[str, Any]:
        """定位 prefix 之后的第一个 markdown 表格：返回 header/rows/quote/offset。"""
        i = self.line_index(prefix)
        start = None
        for j in range(i + 1, len(self.lines)):
            if self.lines[j].lstrip().startswith("|"):
                start = j
                break
        if start is None:
            raise SystemExit(f"no table after {prefix!r}")
        block = []
        j = start
        while j < len(self.lines) and self.lines[j].lstrip().startswith("|"):
            block.append(self.lines[j])
            j += 1
        if len(block) < 3:
            raise SystemExit(f"degenerate table after {prefix!r}: {len(block)} lines")
        header = block[0]
        sep = block[1]
        if not re.fullmatch(r"\|[\s:\-|]+\|", sep.strip()):
            raise SystemExit(f"table separator not recognised after {prefix!r}: {sep!r}")
        rows = block[2:]
        data_row = rows[0]
        return {
            "header": header,
            "rows": rows,
            "n_rows": len(rows),
            "n_cols": header.strip().strip("|").count("|") + 1,
            "quote": data_row,
            "offset": self.offset_of_line(start + 2),
        }

    def bullet_block_after(self, prefix: str, markers: str = "-*0123456789") -> dict[str, Any]:
        i = self.line_index(prefix)
        items: list[tuple[str, int]] = []
        for j in range(i + 1, len(self.lines)):
            ln = self.lines[j]
            s = ln.strip()
            if not s:
                if items:
                    break
                continue
            if s[0] in markers and (s[0] == "-" or s[0] == "*" or s[:2].rstrip(".").isdigit() or s.split(".")[0].isdigit()):
                items.append((ln, self.offset_of_line(j)))
            elif items:
                break
        if not items:
            raise SystemExit(f"no bullet items after {prefix!r}")
        return {"items": items, "n_items": len(items)}


def locator(section: str | None, quote: str | None, offset: int | None, md: str,
            source_field: str = "markdown", note: str | None = None) -> dict[str, Any]:
    verified = bool(quote) and quote in md
    if quote and offset is not None and offset >= 0:
        verified = verified and md[offset:offset + len(quote)] == quote
    return {
        "source_field": source_field,
        "section": section,
        "quote": quote,
        "quote_verified": verified,
        "offset_chars": offset if (offset is not None and offset >= 0) else None,
        **({"note": note} if note else {}),
    }


# ---------------------------------------------------------------- 清单构建
def build_manifest(rec: dict[str, Any], token: str | None, offline: bool = False,
                   prior: dict[str, Any] | None = None) -> dict[str, Any]:
    md: str = rec["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    idx = MarkdownIndex(md)
    # 离线复跑时探针（figure 端点 / mission 端点）不重打网络：沿用上一次在线登记的结果，
    # 保证同一 markdown 的清单可逐字节重建（generated_at 除外）。
    prior_assets = {a["asset_id"]: a for a in (prior or {}).get("assets", [])}
    prior_facts = (prior or {}).get("identity_facts", {})
    assets: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    def add(asset: dict[str, Any], check_key: str | None = None) -> dict[str, Any]:
        assets.append(asset)
        key = check_key or asset["asset_id"]
        q = asset["locator"]["quote"]
        checks[key] = {
            "quote": q,
            "resolvable_in_markdown": bool(q) and q in md,
            "offset_chars": asset["locator"]["offset_chars"],
            "count_occurrences": md.count(q) if q else 0,
        }
        return asset

    # A1 报告 markdown 本身（唯一权威源，带全字节指纹）
    h1, h1_off = idx.find_line("# ")
    add({
        "asset_id": "asset-615-01-report-markdown",
        "kind": "report_markdown",
        "uri": "tensor://reports/615#markdown",
        "status": "resolved",
        "retrieval": {"endpoint": "GET /api/v1/tensor/reports/615", "field": "markdown", "http_status": 200},
        "sha256": digest,
        "chars": len(md),
        "bytes": len(raw),
        "locator": locator("H1", h1, h1_off, md, note="markdown 首行 H1，全文指纹载体"),
        "notes": "哈希口径=markdown 字段 UTF-8 字节；生产者独立重算后与契约 source_hash 对齐。",
    })

    # A2 记录级元数据（title/scenario/mission/tags/status），quote 用记录 title（markdown 中逐字出现）
    title = rec.get("title") or ""
    t_off = md.find(title) if title else -1
    add({
        "asset_id": "asset-615-02-report-record",
        "kind": "report_record_metadata",
        "uri": "tensor://reports/615#record",
        "status": "resolved",
        "retrieval": {"endpoint": "GET /api/v1/tensor/reports/615", "field": "record", "http_status": 200},
        "fields": {
            "id": rec.get("id"),
            "title": title,
            "scenario_key": rec.get("scenario_key"),
            "mission_id": rec.get("mission_id"),
            "status": rec.get("status"),
            "created_at": rec.get("created_at"),
            "tags": rec.get("tags") or [],
        },
        "locator": locator("record.title", title, t_off, md, note="记录 title 在 markdown H1 行内逐字出现"),
    })

    # A3 物理背景散文
    q, o = idx.first_nonempty_after("### 物理背景")
    add({
        "asset_id": "asset-615-03-section-physics-background",
        "kind": "section_prose",
        "uri": "tensor://reports/615#markdown/§1-物理背景",
        "status": "resolved",
        "chars": len(q),
        "locator": locator("① 案例介绍 / 物理背景", q, o, md, note="物理背景段首句（原文首行）"),
    })

    # A4 几何与参数表
    t = idx.table_after("### 几何与参数")
    add({
        "asset_id": "asset-615-04-table-geometry-parameters",
        "kind": "parameter_table",
        "uri": "tensor://reports/615#markdown/§1-几何与参数",
        "status": "resolved",
        "rows": t["n_rows"],
        "fields": {"n_cols": t["n_cols"], "header": t["header"]},
        "locator": locator("① 案例介绍 / 几何与参数", t["quote"], t["offset"], md, note="表首个数据行"),
    })

    # A5 Stokes 解析解公式
    q, o = idx.find_line("v_t = ")
    add({
        "asset_id": "asset-615-05-equation-stokes-terminal-velocity",
        "kind": "equation",
        "uri": "tensor://reports/615#markdown/§1-Stokes终端速度解析解",
        "status": "resolved",
        "chars": len(q),
        "locator": locator("① 案例介绍 / Stokes终端速度解析解", q, o, md, note="LaTeX 解析解行"),
    })

    # A6 耦合算法步骤
    b = idx.bullet_block_after("### 耦合算法")
    add({
        "asset_id": "asset-615-06-method-coupling-steps",
        "kind": "method_steps",
        "uri": "tensor://reports/615#markdown/§2-耦合算法",
        "status": "resolved",
        "items": b["n_items"],
        "locator": locator("② 方法 / 耦合算法", b["items"][3][0], b["items"][3][1], md, note="第 4 步（力分配/伴随操作）"),
    })

    # A7 动量守恒保证公式行
    q, o = idx.find_line("离散动量守恒精确成立")
    add({
        "asset_id": "asset-615-07-equation-momentum-conservation",
        "kind": "equation",
        "uri": "tensor://reports/615#markdown/§2-动量守恒保证",
        "status": "resolved",
        "chars": len(q),
        "locator": locator("② 方法 / 动量守恒保证", q, o, md),
    })

    # A8 工具链条目
    b = idx.bullet_block_after("### 工具链")
    add({
        "asset_id": "asset-615-08-toolchain-list",
        "kind": "toolchain_list",
        "uri": "tensor://reports/615#markdown/§2-工具链",
        "status": "resolved",
        "items": b["n_items"],
        "locator": locator("② 方法 / 工具链", b["items"][0][0], b["items"][0][1], md),
    })

    # A9 验收判据表
    t = idx.table_after("### 验收判据")
    add({
        "asset_id": "asset-615-09-table-acceptance-criteria",
        "kind": "acceptance_table",
        "uri": "tensor://reports/615#markdown/§3-验收判据",
        "status": "resolved",
        "rows": t["n_rows"],
        "fields": {"n_cols": t["n_cols"], "header": t["header"]},
        "locator": locator("③ 计算结果 / 验收判据", t["quote"], t["offset"], md, note="表首个数据行"),
    })

    # A10 Stokes 沉降基准表
    t = idx.table_after("### Stokes沉降基准")
    sim_row = [r for r in t["rows"] if "模拟终端速度" in r]
    if not sim_row:
        raise SystemExit("simulated terminal velocity row missing from Stokes benchmark table")
    add({
        "asset_id": "asset-615-10-table-stokes-benchmark",
        "kind": "result_table",
        "uri": "tensor://reports/615#markdown/§3-Stokes沉降基准",
        "status": "resolved",
        "rows": t["n_rows"],
        "fields": {"n_cols": t["n_cols"], "header": t["header"]},
        "locator": locator("③ 计算结果 / Stokes沉降基准", sim_row[0], md.find(sim_row[0]), md, note="模拟终端速度行"),
    })

    # A11 测试套件摘要（自述断言，非原始日志）
    q, o = idx.find_line("tests collected")
    add({
        "asset_id": "asset-615-11-test-suite-summary",
        "kind": "test_evidence_summary",
        "uri": "tensor://reports/615#markdown/§3-测试套件",
        "status": "resolved",
        "locator": locator("③ 计算结果 / 测试套件", q, o, md, note="报告内自述的 pytest 汇总行（无原始日志附件）"),
    })

    # A12 局限性列表
    b = idx.bullet_block_after("## ⑤ 注意点")
    add({
        "asset_id": "asset-615-12-limitations-list",
        "kind": "limitations_list",
        "uri": "tensor://reports/615#markdown/§5-注意点",
        "status": "resolved",
        "items": b["n_items"],
        "locator": locator("⑤ 注意点（Limitations）", b["items"][3][0], b["items"][3][1], md, note="第 4 条（润滑力缺失）"),
    })

    # A13 误差判定表
    t = idx.table_after("## ⑥ 误差判定")
    add({
        "asset_id": "asset-615-13-table-error-judgement",
        "kind": "result_table",
        "uri": "tensor://reports/615#markdown/§6-误差判定",
        "status": "resolved",
        "rows": t["n_rows"],
        "fields": {"n_cols": t["n_cols"], "header": t["header"]},
        "locator": locator("⑥ 误差判定", t["quote"], t["offset"], md, note="表首个数据行"),
    })

    # A14 图件：记录声明了 name/caption，但无字节载荷 → declared_unresolvable
    figs = rec.get("figures") or []
    fig_probe_note = ""
    if figs:
        f0 = figs[0]
        fname = f0.get("name")
        fid = f"asset-615-14-figure-{fname}"
        fprobe = (prior_assets.get(fid, {}).get("retrieval") if offline else None) \
            or probe(f"{API_BASE}/tensor/reports/{REPORT_ID}/figures/{fname}", token)
        fig_probe_note = f"图件端点 HTTP {fprobe['http_status']}"
        q, o = idx.find_line("见内嵌图")
        add({
            "asset_id": f"asset-615-14-figure-{fname}",
            "kind": "figure",
            "uri": f"tensor://reports/615/figures/{fname}",
            "status": "declared_unresolvable",
            "retrieval": fprobe,
            "sha256": None,
            "bytes": 0,
            "caption": f0.get("caption"),
            "fields": {"figure_record_keys": sorted(f0.keys()), "png_base64_present": "png_base64" in f0},
            "locator": locator("④ 结果图", q, o, md, note="正文引用了图件"),
        })
        unresolved.append({
            "asset_id": f"asset-615-14-figure-{fname}",
            "kind": "figure",
            "reason": (f"记录 figures 只有 {sorted(f0.keys())}（无 png_base64 载荷），{fig_probe_note}"
                       " = figure not found，字节不可经 API 取得；本工序不重绘、不代上游补图，保留未解析。"),
        })
    else:
        raise SystemExit("record declares no figures; manifest built for a report that claims an embedded figure")

    # 未解析登记（不是资产，而是缺口如实入账）
    unresolved.append({
        "asset_id": "asset-615-15-test-run-artifact",
        "kind": "run_artifact",
        "reason": ("§3 自述 12 tests collected / 12 passed，但报告未附原始 pytest 日志、trace 或测试文件路径，"
                   "工件字节不可得；工序 01 不重跑上游算例，故保留未解析（断言可定位：asset-615-11）。"),
    })
    mission_id = rec.get("mission_id")
    mission_probe: dict[str, Any] = {}
    mission_repo = None
    if mission_id and offline and prior_facts.get("mission_probe"):
        mission_probe = dict(prior_facts["mission_probe"])
        mission_repo = prior_facts["mission_probe"].get("mission_repo")
    elif mission_id:
        mission_probe = probe(f"{API_BASE}/tensor/missions/{mission_id}", token)
        body = mission_probe.get("body")
        if isinstance(body, dict):
            mission_repo = body.get("repo")
    unresolved.append({
        "asset_id": "asset-615-16-codebase-pointer",
        "kind": "codebase_pointer",
        "reason": (f"报告 markdown 正文不含代码仓库路径、分支或提交号，无法把「工具链/12 项测试」绑定到具体文件；"
                   f"仅能由记录 mission_id={mission_id} 解析到"
                   f"{(' mission 记录 repo=' + str(mission_repo)) if mission_repo else '（mission 端点未给出 repo）'}，"
                   "属记录级间接线索，不认定为工件绑定。"),
    })

    from collections import Counter
    by_status = dict(Counter(a["status"] for a in assets))

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "producer": f"kf-worker/{os.environ.get('TP_AGENT_ID', 'm15514')}",
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_scope": "UTF-8 bytes of tensor_reports.markdown",
            "hash_match": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes": len(raw),
            "lines": md.count("\n") + 1,
            "fetched_via": "GET /api/v1/tensor/reports/615 (Bearer token)",
            "record_fields": {
                "title": title,
                "scenario_key": rec.get("scenario_key"),
                "mission_id": rec.get("mission_id"),
                "status": rec.get("status"),
                "created_at": rec.get("created_at"),
                "tags": rec.get("tags") or [],
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "title_matches_contract": title == CONTRACT_TITLE,
                "scenario_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
                "title_matches_markdown_h1": title in md,
            },
        },
        "assets": assets,
        "unresolved": unresolved,
        "counts": {
            "assets_total": len(assets),
            "by_status": by_status,
            "unresolved_total": len(unresolved),
        },
        "locator_checks": checks,
        "identity_facts": {
            "markdown_h1": h1.lstrip("# ").strip(),
            "record_title": title,
            "title_consistent": title == h1.lstrip("# ").strip(),
            "scenario_key": rec.get("scenario_key"),
            "mission_id": rec.get("mission_id"),
            "mission_probe": {k: v for k, v in mission_probe.items() if k != "body"} | {"mission_repo": mission_repo},
            "figures_declared": len(figs),
            "figure_payload_present": False,
            "markdown_sha256": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
        },
        "scope": {
            "extraction_performed": False,
            "claims_emitted": 0,
            "verification_performed": False,
            "note": "工序 01 只登记资产与指纹：不抽取知识、不判定 verified、不重跑上游算例；claims 允许为空数组，本单为空。",
        },
        "limitations": [
            "图件字节不可得：figures 记录仅 name/caption，端点 404；未重绘、未代上游补图。",
            "报告正文无代码路径/提交号：代码级绑定不可解析，仅记录级 mission 线索。",
            "pytest 12/12 为报告自述断言，无原始日志工件；本工序不重跑上游，不作为通过证据。",
            "本清单不评价报告结论真伪；误差/守恒量的裁决权在平台验证门。",
        ],
    }
    return manifest


# ---------------------------------------------------------------- 验收自检
def verify(manifest: dict[str, Any], token: str | None, md_source: str | None = None) -> dict[str, Any]:
    if md_source is None:
        md = requests.get(f"{API_BASE}/tensor/reports/{REPORT_ID}",
                          headers={"Authorization": f"Bearer {token}"}, timeout=60).json()["markdown"]
    else:
        md = md_source
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()

    ids = [a["asset_id"] for a in manifest["assets"]]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    quotes = [(a["asset_id"], a["locator"]["quote"]) for a in manifest["assets"]]
    bad_quotes = [
        {"asset_id": aid, "quote": q,
         "reason": "quote empty" if not q else "quote not a verbatim substring of markdown"}
        for aid, q in quotes if not q or q not in md
    ]
    offset_mismatch = []
    for a in manifest["assets"]:
        off = a["locator"]["offset_chars"]
        q = a["locator"]["quote"]
        if off is not None and q and md[off:off + len(q)] != q:
            offset_mismatch.append(a["asset_id"])

    unresolved_ids = {u["asset_id"] for u in manifest["unresolved"]}
    status_ok = all(
        (a["status"] == "resolved") or (a["asset_id"] in unresolved_ids)
        for a in manifest["assets"]
    )

    # JSON schema 校验（结构门）
    schema_errors: list[str] = []
    try:
        import jsonschema
        # 包级 pin：共享的 asset_manifest.v1.schema.json 描述的是另一族清单（wp-448-01 形状，
        # asset_id ^A[0-9]{2}$、含 claims/integrity 块），对本包 198 处报错，不能用作结构门。
        schema = json.loads((ROOT / "schemas" / MANIFEST_SCHEMA).read_text())
        for err in sorted(jsonschema.Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.path)):
            schema_errors.append(f"{'/'.join(map(str, err.path))}: {err.message}")
    except ImportError:  # pragma: no cover
        schema_errors = ["jsonschema not installed -> schema check not_run"]

    envelope_errors: list[str] = []
    try:
        import jsonschema
        eschema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
        for err in sorted(jsonschema.Draft202012Validator(eschema).iter_errors(build_envelope(manifest)),
                          key=lambda e: list(e.path)):
            envelope_errors.append(f"{'/'.join(map(str, err.path))}: {err.message}")
    except ImportError:  # pragma: no cover
        envelope_errors = ["jsonschema not installed -> envelope schema check not_run"]

    checks = {
        "valid_json": True,
        "kf_result_schema_pass": not envelope_errors,
        "kf_result_schema_errors": envelope_errors,
        "schema_pass": not schema_errors,
        "schema_errors": schema_errors,
        "source_hash_matches": manifest["source"]["source_hash"] == digest,
        "source_hash_recomputed": digest,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "title_matches_contract": (manifest["source"]["record_fields"]["title"] == CONTRACT_TITLE),
        "source_locator_resolvable": not bad_quotes and not offset_mismatch,
        "bad_quotes": bad_quotes,
        "offset_mismatch": offset_mismatch,
        "no_duplicate_ids": not dup_ids,
        "duplicate_ids": dup_ids,
        "all_claims_have_evidence_or_explicit_unresolved_status": True,  # claims=[] → 空集恒真
        "claims_emitted": 0,
        "unresolved_assets_have_reason": all(len(u["reason"]) >= 10 for u in manifest["unresolved"]),
        "statuses_accounted": status_ok,
        "report_id_pinned": REPORT_ID == "615",
    }
    checks["all_pass"] = all([
        checks["schema_pass"], checks["kf_result_schema_pass"], checks["source_hash_matches"], checks["chars_match_contract"],
        checks["source_locator_resolvable"], checks["no_duplicate_ids"],
        checks["unresolved_assets_have_reason"], checks["statuses_accounted"],
    ])
    return checks


def build_envelope(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": SOURCE_FIELD,
            "producer": manifest["producer"],
            "emitted_at": manifest["generated_at"],
            "notes": ("asset_manifest.json 见 outputs；引文均由脚本从 markdown 按行取子串，"
                      "逐条做 quote in markdown + 偏移回读确认；未抽取 claims，未标 verified。"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="只对既有产物重跑验收自检")
    ap.add_argument("--record-file", default=None,
                    help="离线复跑：读 source_snapshot/report_615.json（完整记录）而不是访问平台")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--no-mirror", action="store_true", help="不写仓库内的交付镜像（线上复跑比对用）")
    ap.add_argument("--offline", action="store_true",
                    help="不访问平台、不需要 token（配合 --record-file / --check-only 做离线重建与复检）")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    offline = bool(args.offline or args.record_file)
    token = None if offline else login_token()
    if args.check_only:
        manifest = json.loads((out / "asset_manifest.json").read_text())
    else:
        if args.record_file:
            rec = json.loads(Path(args.record_file).read_text())
            prior_path = out / "asset_manifest.json"
            prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
            if str(rec.get("id")) != REPORT_ID:
                raise SystemExit(f"snapshot record id mismatch: {rec.get('id')!r}")
            snapshot = out / "source_snapshot"
            snapshot.mkdir(parents=True, exist_ok=True)
            (snapshot / "report_615.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
            (snapshot / "report_615.md").write_text(rec["markdown"])
        else:
            rec = fetch_report(token)
            snapshot = out / "source_snapshot"
            snapshot.mkdir(parents=True, exist_ok=True)
            (snapshot / "report_615.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
            (snapshot / "report_615.md").write_text(rec["markdown"])
        manifest = build_manifest(rec, None if offline else token,
                                  offline=offline,
                                  prior=(prior if (offline and prior) else None))
        (out / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        (out / "kf_result.json").write_text(json.dumps(build_envelope(manifest), ensure_ascii=False, indent=2) + "\n")

    md_source = json.loads((out / "source_snapshot" / "report_615.json").read_text())["markdown"] \
        if args.check_only else None
    # 交付镜像：受版本控制的副本（artifacts/ 不进 git，镜像保证分支可审计）。
    # --no-mirror 用于把线上源复跑结果落到临时目录做逐字节比对，不去动仓库里的交付镜像。
    if not args.no_mirror:
        MIRROR_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("asset_manifest.json", "kf_result.json"):
            (MIRROR_DIR / name).write_bytes((out / name).read_bytes())
        snap_md = out / "source_snapshot" / "report_615.md"
        if snap_md.exists():
            (MIRROR_DIR / "report_615.md").write_bytes(snap_md.read_bytes())

    checks = verify(manifest, token, md_source=md_source)
    (out / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    if not args.no_mirror:
        (MIRROR_DIR / "checks.json").write_bytes((out / "checks.json").read_bytes())
    print(json.dumps({k: checks[k] for k in ("all_pass", "source_hash_matches", "source_locator_resolvable",
                                             "no_duplicate_ids", "schema_pass", "kf_result_schema_pass",
                                             "chars_match_contract")},
                     ensure_ascii=False))
    if not checks["all_pass"]:
        print(json.dumps({k: v for k, v in checks.items() if k.startswith("bad") or k in
                          ("schema_errors", "kf_result_schema_errors", "duplicate_ids", "offset_mismatch",
                           "source_hash_recomputed")},
                         ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())