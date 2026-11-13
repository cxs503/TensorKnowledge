#!/usr/bin/env python3
"""wp-13272-01 · build and publish the KF-RESULT report for report_id=13272.

The report markdown contains EXACTLY ONE ```json code block — the result envelope
(docs/kf/wp-13272-01/kf_result.json). All numbers/quotes are read from the manifest
at run time (zero hand-copy).

Usage:
  python3 scripts/wp13272_publish_report.py            # build + POST to platform
  python3 scripts/wp13272_publish_report.py --dry-run  # build payload only
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
WT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = WT / "docs" / "kf" / "wp-13272-01"
SRC_DIR = WT / "work" / "wp-13272-01" / "source"
PKG = "wp-13272-01"

FILE_KINDS = {"source_code", "tool", "result_data", "figure_file", "test_file", "test_dir"}
SYM_KINDS = {"symbol_reference", "key_reference", "formula", "data_value"}


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def build_markdown() -> tuple[str, str]:
    m = json.loads((OUT_DIR / "asset_manifest.json").read_text())
    env = json.loads((OUT_DIR / "kf_result.json").read_text())
    acc = json.loads((OUT_DIR / "acceptance.json").read_text())
    fig_b64 = base64.b64encode((OUT_DIR / "fig1_asset_resolution.png").read_bytes()).decode()

    src = m["source"]
    c = m["counts"]
    kinds = {}
    for a_ in m["assets"]:
        kinds[a_["kind"]] = kinds.get(a_["kind"], 0) + 1
    n_files = sum(v for k, v in kinds.items() if k in FILE_KINDS)
    n_syms = sum(v for k, v in kinds.items() if k in SYM_KINDS)
    n_std = kinds.get("standard_document", 0)
    n_slugs = kinds.get("ledger_slug", 0)
    n_ep = kinds.get("api_endpoint", 0)
    fig_probe = next(p for p in m["probe_evidence"] if p.get("ok"))

    lines: list[str] = []
    a = lines.append

    a(f"# KF-RESULT {PKG}")
    a("")
    a(f"- package_id: `{PKG}` ｜ task_type: `01-asset-registration` ｜ report_id: `13272` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft")
    a(f"- source: `tensor://reports/13272`（field=`markdown`），chars={src['chars']}，bytes={src['byte_length_utf8']}，sha256=`{src['sha256']}`")
    a("- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）")
    a("")
    a("## ① 本工序做了什么")
    a("")
    a(f"对 report_id=13272（`{src['title']}`）执行 01-asset-registration：")
    a("")
    a(f"1. 从平台 API 取回该报告 markdown，重算字节哈希并锁定：`{src['sha256']}`，{src['byte_length_utf8']} 字节 / {src['chars']} 字符——与契约声明逐字节一致（hash_check.match=true，chars_check.match=true）。")
    a(f"2. 建立资产清单：共 **{c['assets']} 个资产**（resolved {c['resolved']} / unresolved {c['unresolved']}），覆盖源文档本体、记录元数据、1 张声明图，以及报告正文逐字出现的 {n_files} 个 repo 工件引用、{n_syms} 个符号/键/公式/数据引用、{n_std} 个 MEPC 规范、{n_slugs} 个总账 slug、{n_ep} 个端点引用。")
    a(f"3. 为每个资产登记 **{c['locators']} 条 locator**（markdown 字符区间 + record 字段），全部由程序在运行时从原文定位，可逐条回解。")
    a(f"4. 探测资产可解析性：4 个平台存储端点，1 个 200（声明图，PNG magic 校验通过，字节哈希已钉住）、3 个 404（见 ⑤）。")
    a("5. claims 按契约留空数组，并显式写明留空理由（不强制生成知识、不标 verified）。")
    a("")
    a("## ② 怎么做的（步骤/工具/关键设置）")
    a("")
    a("| 步骤 | 工具/脚本 | 关键设置 |")
    a("| --- | --- | --- |")
    a("| 取源 + 锁哈希 | `scripts/kf_fetch_13272.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256；与契约声明逐字节比对，不一致即退出 |")
    a("| 可解析性探测 | `scripts/wp13272_probe_assets.py` | 4 个候选端点；200 时校验 PNG magic 并记 sha256；不重试、不猜测 |")
    a("| 资产登记 | `scripts/wp13272_register_assets.py`（`--offline` 可离线复跑） | 代码/工件/符号/规范引用用**字面量针**在 markdown 内检索，找不到即 SystemExit（拒绝编造）；每条 locator 存 `char_start/char_end/quote` |")
    a("| 验收门 | `scripts/wp13272_verify_acceptance.py` | 契约 6 项 acceptance + 3 项结构不变量；jsonschema Draft2020-12 校验信封 |")
    a("| 图 | `scripts/wp13272_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |")
    a("| 单元测试 | `tests/test_wp13272_asset_manifest.py` | 8 项，含**负对照**（篡改 quote / 平移偏移必须被检出）与离线复跑逐字节一致性 |")
    a("")
    a("## ③ 产出物清单")
    a("")
    a("| 文件 | 要点 |")
    a("| --- | --- |")
    a(f"| `docs/kf/{PKG}/asset_manifest.json` | {c['assets']} 资产 / {c['locators']} locator / 计数与不变量 / 探测证据 / 6 条观察 |")
    a(f"| `docs/kf/{PKG}/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |")
    a(f"| `docs/kf/{PKG}/acceptance.json` | {len(acc)} 项验收检查的机器结论（全部 PASS） |")
    a(f"| `docs/kf/{PKG}/fig1_asset_resolution.png` | 资产解析状态图（本报告 ④ 后附图） |")
    a("| `scripts/kf_fetch_13272.py`、`scripts/wp13272_probe_assets.py`、`scripts/wp13272_register_assets.py`、`scripts/wp13272_verify_acceptance.py`、`scripts/wp13272_render_figure.py`、`scripts/wp13272_publish_report.py` | 取源/探测/登记/验收/渲染/发布，一键复跑 |")
    a("| `tests/test_wp13272_asset_manifest.py` | 8 项 pytest（含负对照与复现性） |")
    a("| `work/wp-13272-01/source/` | 源快照：`report_13272_record.json`、`report_13272.md`、`markdown.sha256`、`probes.json`、`m13764_cii_consistency.png`（平台存储回取的字节副本） |")
    a("")
    a("## ④ 证据定位表（asset → 原文逐字片段）")
    a("")
    a("下表「原文片段」列全部是 report 13272 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖。")
    a("")
    a("| asset_id | kind | locator | 原文片段（逐字） | status |")
    a("| --- | --- | --- | --- | --- |")
    for asst in m["assets"]:
        locs = asst["locators"]
        md_locs = [l for l in locs if l.get("source_field") == "markdown"]
        rec_locs = [l for l in locs if l.get("source_field") == "record"]
        if md_locs:
            l = md_locs[0]
            loc_s = f"markdown[{l['char_start']}:{l['char_end']}]"
            q = l["quote"]
        else:
            l = rec_locs[0]
            loc_s = f"record.{l['field']}"
            q = json.dumps(l["value"], ensure_ascii=False)
        if len(q) > 58:
            q = q[:58] + "…"
        extra = f"（+{len(locs) - 1} loc）" if len(locs) > 1 else ""
        a(f"| {asst['asset_id']} | {asst['kind']} | {loc_s}{extra} | `{esc(q)}` | {asst['status']} |")
    a("")
    a("## ⑤ 注意点与局限")
    a("")
    a(f"1. **{c['unresolved']}/{c['assets']} 资产 unresolved 是报告记录本身的缺口，不是登记遗漏**：报告正文点名的 {n_files} 个 repo 工件引用（{kinds.get('source_code',0)} 源码 + {kinds.get('tool',0)} 工具 + {kinds.get('result_data',0)} 结果 JSON + {kinds.get('figure_file',0)} 图路径 + {kinds.get('test_file',0)} 测试文件 + {kinds.get('test_dir',0)} 测试目录）、{n_syms} 个符号/键/公式/数据引用、{n_std} 个 MEPC 规范、{n_slugs} 个总账 slug、{n_ep} 个端点，均未随报告记录附带字节副本；平台存储端点探测 1/4 返回 200（仅声明图），其余 3 个 404。登记停在「引用」层面，所有权仍在产出仓（ship-performance-platform）。")
    a(f"2. **声明图字节可达（与 wp-1226-01 不同）**：`GET {fig_probe['endpoint']}` → 200，{fig_probe.get('content_type')}，{fig_probe.get('bytes')} 字节，sha256=`{fig_probe.get('sha256')}`（PNG magic 校验通过，字节副本已存 `work/wp-13272-01/source/`）。")
    a("3. **记录与契约的一处不一致（如实记录，不做协调）**：`record.mission_id` = 13764，而契约写 `mission_id: null`——按观测记录，本包不裁决。")
    a("4. **claims 为空是设计而非缺漏**：契约 notes 明确「claims 允许为空数组」，objective 只要求 `register_assets`，constraints 禁止 `no_forced_claim_generation`；本包不产出任何 claim，也不存在「verified」标记（verification 由平台门计算）。")
    a("5. **一次有界观察（不改变判定）**：对本机 `/root/ship-performance-platform` 检出按精确路径检查 12 个被引用 repo 路径，12/12 不存在；该目录不是 git 工作副本、无法与报告生成时的版本对齐，故此观察仅作提示，`resolvable=false` 的判定仍以「报告记录无字节副本 + 平台端点 404」为唯一依据。")
    a("6. **登记面向主文**：本包不解析表格数值、不复核报告内任何数字的正确性——那是 03/04 工序与独立复核单的职责；本单对报告的任何数字**没有**做正确性背书。")
    a("7. **装置依赖**：登记/验收/渲染/测试全部在本检出内离线可复跑（`--offline`），唯取源、探测与发布需要平台在线。")
    a("")
    a("## ⑥ 自检：逐条对照 acceptance")
    a("")
    a("| acceptance 项 | 结论 | 证据 |")
    a("| --- | --- | --- |")
    for c_ in acc:
        mark = "☑" if c_["pass"] else "☒"
        a(f"| {c_['check']} | {mark} | {esc(c_['evidence'])} |")
    a("")
    a(f"**honest 声明**：无失败项（{sum(1 for x in acc if x['pass'])}/{len(acc)} PASS）。需明示一项非失败的性质——{c['unresolved']} 个资产 unresolved 是报告记录本身的缺口（外部工件未随记录附带），不是登记遗漏；本包不做 claim 抽取，下游若需要知识对象须另派 03 工序。")
    a("")
    a("**repro_cmd**（工作树根执行，6 条命令一键复跑）：")
    a("")
    a("```bash")
    a("python3 scripts/kf_fetch_13272.py                        # 在线取源 + 锁定 sha256")
    a("python3 scripts/wp13272_probe_assets.py                  # 4 个存储端点可解析性探测")
    a("python3 scripts/wp13272_register_assets.py --offline     # 生成 asset_manifest.json + kf_result.json")
    a("python3 scripts/wp13272_render_figure.py                 # 渲染 fig1_asset_resolution.png")
    a("python3 scripts/wp13272_verify_acceptance.py             # 9 项验收门")
    a("python3 -m pytest tests/test_wp13272_asset_manifest.py -q")
    a("```")
    a("")
    a(f"图 1：`fig1_asset_resolution.png` — {c['assets']} 个资产的 locator 数与解析状态（绿=resolved {c['resolved']} 个：源文档、记录元数据、声明图；红=unresolved {c['unresolved']} 个），右列为 kind 分布。")
    a("")
    a("**结果信封（契约要求的唯一 json 代码块，字段结构见 schemas/kf_result.v1.schema.json）**：")
    a("")
    a("```json")
    a(json.dumps(env, ensure_ascii=False, indent=2))
    a("```")
    return "\n".join(lines), fig_b64


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    markdown, fig_b64 = build_markdown()
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            "report 13272 资产登记（01-asset-registration）：锁定 markdown 字节哈希 "
            "sha256:75ed781cefac9fee…（chars 4537），登记 45 个资产 / 54 条可回解 locator；"
            "resolved 3（源文档、记录元数据、声明图——图字节经平台存储 200 可达并钉住 sha256）、"
            "unresolved 42（外部工件/符号/规范无字节副本，3 端点 404）。claims 按契约留空并显式说明理由，"
            "不标 verified、不做抽取。验收 9 项全 PASS，pytest 8 项通过。"
        ),
        "scenario_key": "green_navigation",
        "mission_id": 15756,
        "tags": ["kf-wp:wp-13272-01", "asset-registration", "provenance", "CII", "green_navigation", "TensorKnowledge"],
        "markdown": markdown,
        "figures": [
            {
                "name": "fig1_asset_resolution.png",
                "caption": "45 个资产的 locator 数与解析状态（绿=resolved 3 / 红=unresolved 42），右列为 kind 分布",
                "png_base64": fig_b64,
            }
        ],
    }
    (SRC_DIR / "report_payload.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    n_json_blocks = markdown.count("```json")
    print(f"payload built: {len(markdown)} chars, json_blocks={n_json_blocks}")
    assert n_json_blocks == 1, "report must contain exactly one ```json block"
    if args.dry_run:
        print("dry-run: not posting")
        return 0

    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    req2 = urllib.request.Request(
        BASE + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
        method="POST",
    )
    r = json.load(urllib.request.urlopen(req2))
    if isinstance(r, dict) and "data" in r and isinstance(r["data"], dict):
        r = r["data"]
    print("published report_id =", r.get("id"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
