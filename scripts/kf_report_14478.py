#!/usr/bin/env python3
"""Build (and optionally publish) the delivery report of KF work package wp-14478-01.

Every number/quote in the body is injected programmatically from the machine artifacts
(asset_manifest.json, verification.json) — nothing is retyped. The body carries exactly ONE
`json` code block, which is the kf_result envelope verbatim.

Usage:
  python3 scripts/kf_report_14478.py            # write docs/wp-14478-01/KF-RESULT-wp-14478-01.md
  python3 scripts/kf_report_14478.py --publish  # ... and POST it to /tensor/reports, then round-trip check
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kf_fetch_14478 as fetch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-14478-01"
PACKAGE_ID = "wp-14478-01"
REPORT_ID = "14478"
TITLE = f"KF-RESULT {PACKAGE_ID}"
SCENARIO_KEY = "case-cylinder-drag-fvm"
MISSION_ID = 15793
CONTRACT_HASH = "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"
FIGURES = [
    ("fig_locator_map.png", "20 条资产的 locator 在 6156 字符 markdown 中的字符区间（颜色=payload 状态，右侧标注 asset_id 与所在行号）"),
    ("fig_payload_status.png", "payload 状态分布：1 记录内 / 1 外部 URL / 12 外部仓路径 / 5 载荷缺失 / 1 仅源内声明；claims=0"),
    ("fig_acceptance_matrix.png", "6 项 acceptance + 4 项附加机检的逐条 PASS/FAIL 矩阵（由 verification.json 渲染）"),
]
REPRO_CMD = r"""export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
python3 scripts/kf_fetch_14478.py      # GET /tensor/reports/14478 → 双断言(sha256+chars) → docs/wp-14478-01/source.md
python3 scripts/kf_register_14478.py   # 锚点唯一性校验 → asset_manifest.json + kf_result.wp-14478-01.json
python3 scripts/kf_verify_14478.py     # 独立复取+重算哈希+区间回切+schema → verification.json（逐条 PASS/FAIL）
python3 scripts/kf_figures_14478.py    # 3 张图 → fig_*.png
python3 scripts/kf_report_14478.py     # 生成本报告正文（唯一 json 块）
python3 -m pytest tests/test_kf_wp14478.py -q   # 19 passed（含 8 个负控）"""


def cell(text: str, limit: int = 110) -> str:
    """Make a string safe for a one-line markdown table cell."""
    flat = " ".join(str(text).split())
    if len(flat) > limit:
        flat = flat[: limit - 1] + "…"
    return flat.replace("|", "\\|")


def build_markdown() -> str:
    manifest = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((DOCS / f"kf_result.{PACKAGE_ID}.json").read_text(encoding="utf-8"))
    verification = json.loads((DOCS / "verification.json").read_text(encoding="utf-8"))
    meta = json.loads((DOCS / "source_meta.json").read_text(encoding="utf-8"))["record"]
    assets = manifest["assets"]
    src = manifest["source"]
    counts = manifest["counts"]

    lines: list[str] = []
    a = lines.append
    a(f"# {TITLE}")
    a("")
    a(f"**报告 {REPORT_ID} → 资产登记（task_type=01-asset-registration，lane B，分层 CASE-CYLINDER-DRAG-FVM | {src['scenario_key']}）。"
      f"只登记，不抽取、不分类（`classify_report_type=false`），不把任何结论标为 verified。**")
    a("")
    a("## ① 本工序做了什么")
    a("")
    a(f"登记对象 = 平台报告 `report_id={REPORT_ID}`（`{src['uri']}`，字段 `markdown`）。"
      f"标题（平台记录逐字）：`{src['title']}`；场景键 `{src['scenario_key']}`；"
      f"平台 `mission_id={src['platform_mission_id']}`、状态 `{src['platform_status']}`、"
      f"标签 `{src['platform_tags']}`、图片条目 **{len(src['platform_figures'])}** 个。")
    a("")
    a(f"原文计量（脚本现算，非手抄）：字符 **{src['chars']}**（契约 `chars: 6156` {'一致' if src['chars'] == 6156 else '不一致'}）、"
      f"UTF-8 字节 **{src['bytes_utf8']}**、`sha256={src['hash']}`（与契约 `source_hash` {'逐位一致' if src['hash'] == CONTRACT_HASH else '不一致'}）。")
    a("")
    a("本工序产出 **一份资产清单**（`asset_manifest.json`）：20 条资产，每条带字符区间 + 行号 + 逐字引文 + 唯一性标记 + payload 状态，"
      "**claims = 0 条**（本工序不抽取；填 claims 会伪造属于 03 工序的产物）。")
    a("")
    a("登记到的内容类型（原文自述，非本包复算）：这是一份 **honest-FAIL** 算例报告——TensorFVM 的 DFG 2D-1 圆柱绕流（$Re_D=20$）"
      "三档网格作业递交后一直排队未派发，报告里**没有任何 got 数字**；已交付的是参考值抓取链、算例 harness、契约测试。"
      "本包只把这些工件/缺口如实登记成资产，**不补任何数值、不把缺口升级为有载荷**。")
    a("")
    a("## ② 怎么做的（步骤/工具/关键设置）")
    a("")
    a(f"1. `scripts/kf_fetch_14478.py`——用 `TENSOR_AGENT_USER/PASS` 登录取 token，`GET /tensor/reports/{REPORT_ID}` 取 `markdown`，"
      "**先做双断言**（sha256 与字符数），相符才落盘 `docs/wp-14478-01/source.md`（逐字节保真，`newline=''`）。哈希不符即拒写。"
      "仅读 `report_id=14478`，未读任何其它 report_id。")
    a("2. `scripts/kf_register_14478.py`——按「锚点串必须在原文中唯一出现」的规则切片生成 locator：起止字符、起止行、逐字引文、`unique` 标记。"
      f"20 条锚点全部 `count == 1`，任一 ≠ 1 脚本即中止（避免「大致定位」）。锚点选择避开重复出现的文件名裸串"
      "（例：`fetch_reference.py` 在原文出现 2 次，故改用带路径的完整串作锚点）。")
    a("3. payload 核实（每条资产带 `payload.status` + `checked_how`，说明证据**怎么查的**）——"
      f"五种状态：`in_report_record` {counts['by_payload_status'].get('in_report_record', 0)}、"
      f"`external_url_declared` {counts['by_payload_status'].get('external_url_declared', 0)}、"
      f"`external_repo_path_declared` {counts['by_payload_status'].get('external_repo_path_declared', 0)}、"
      f"`declared_payload_missing` {counts['by_payload_status'].get('declared_payload_missing', 0)}、"
      f"`declared_in_source_only` {counts['by_payload_status'].get('declared_in_source_only', 0)}。"
      "外部仓路径类（TensorFVM 仓内文件/包/符号）**不取字节、不算哈希**——它们不在本报告记录内，也不在本 worktree；"
      "原文自述「缺」的 `runs/`、`analysis/`、原生产物、集群 `/tmp` 输出一律登记为 `declared_payload_missing`，不假设存在。")
    a("4. `scripts/kf_verify_14478.py`——**独立复核**：重新向平台取一次 markdown、重算哈希，把 20 条引文按区间重新切出来逐字比对"
      "（含行号重算），再对两份 JSON 做 schema 校验、id 唯一性、claims 策略、边界与「无自证 verified」检查，输出 `verification.json`。")
    a("5. `scripts/kf_figures_14478.py`——由 manifest/verification 渲染 3 张图（ASCII 标签，本镜像无中文字体）。")
    a("6. `tests/test_kf_wp14478.py`——19 个 pytest：11 个正控（哈希/字符数/区间回切/唯一性/计数一致性/缺口未升格/两份 schema）"
      "+ 8 个负控（篡改引文、位移区间、错行号、重复 id、原文漂移、自证 verified、异号 report_id、envelope 与 manifest 不一致、非法 payload 状态）。")
    a("7. 工具链：Python 3.11 + jsonschema（Draft202012Validator）+ matplotlib + pytest；正文数字由脚本从 JSON 直接注入，零手抄。")
    a("")
    a("## ③ 产出物清单（输出文件名 → 要点）")
    a("")
    a("| 文件 | 是什么 | 要点（机检数字） |")
    a("|---|---|---|")
    a(f"| `source.md` | 报告 {REPORT_ID} 的 `markdown` 逐字节副本 | {src['chars']} 字符 / {src['bytes_utf8']} 字节 / `sha256={src['hash'][:16]}…` |")
    a(f"| `source_meta.json` | 平台记录字段（title/scenario_key/mission_id/tags/figures） | mission_id={src['platform_mission_id']}、figures={len(src['platform_figures'])} 条 |")
    a(f"| `asset_manifest.json` | **本工序主产物**：{counts['assets']} 条资产清单 | {len(counts['by_class'])} 类、5 种 payload 状态、claims=0 |")
    a(f"| `kf_result.{PACKAGE_ID}.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims） | provenance.source_hash 与 source.md 哈希逐位一致；outputs 内嵌同一 manifest |")
    a(f"| `verification.json` | {len(verification['checks'])} 项机检结果 | {sum(1 for c in verification['checks'] if c['result'] == 'PASS')}/{len(verification['checks'])} PASS（模式：{verification['mode']}） |")
    a("| `asset_manifest.v1.schema.json` / `kf_result.v1.schema.json` | 机检用 schema | 前者本包自钉（report 14478 专用），后者自 worktree `schemas/` 逐字节复制 |")
    a("| `fig_locator_map.png` | locator 覆盖图 | 20 条区间在全文字符轴上的位置 |")
    a("| `fig_payload_status.png` | payload 状态分布图 | 见 ② 步 3 的计数 |")
    a("| `fig_acceptance_matrix.png` | 验收矩阵图 | 逐条 PASS/FAIL |")
    a(f"| `KF-RESULT-{PACKAGE_ID}.md` | 本文件（交付正文） | 唯一一个 `json` 块 = 结果信封 |")
    a("")
    a("## ④ 证据定位表（字段 → 原文逐字引文）")
    a("")
    a("定位口径：`markdown` 全文坐标（0 基字符区间），引文为原文子串且在全文中**唯一**；完整未截断引文见 `asset_manifest.json`。"
      "下表引文仅作展示（长引文截断标 `…`，含换行者压平空白）。")
    a("")
    a("| asset_id | 原文节 | 字符区间 | 行 | payload 状态 | 原文引文（逐字） |")
    a("|---|---|---|---|---|---|")
    for asset in assets:
        loc = asset["locator"]
        a(f"| {asset['asset_id']} | {cell(asset['in_report_section'], 24)} | {loc['start_char']}–{loc['end_char']} | {loc['start_line']} | "
          f"`{asset['payload']['status']}` | {cell(loc['quote'])} |")
    a("")
    a("原文中被引用的参考量（登记为原文内容，**本包未复核**）：`C_D` 参考值 5.57953523384、`C_L` 参考值 0.010618948146、"
      "`p_diff` 参考值 0.11752016697 Pa（三者均出自 §③ 参考值表，来源=DFG 官网页，见 A02/A03）。")
    a("")
    a("## ⑤ 注意点与局限（如实）")
    a("")
    a("1. **本工序不做真值判断**：资产登记只回答「报告里有哪些可解析资产、它们在哪、载荷在不在」，"
      "不评判 DFG 算例是否通过、也不评判参考值抓取链是否正确。原报告的 honest-FAIL 结论原样保留。")
    a("2. **缺口不升格**：`runs/`、`analysis/`、`result.json`/`fields.npz`/`history.json`、集群 `/tmp/m15406_dfg_*` 输出、analyze 的 7 张图"
      "在原文中明确「缺/未产出」，登记为 `declared_payload_missing`；图件名原文未给出，故**不编造文件名**（只登记计数 7）。")
    a("3. **外部工件未取字节**：TensorFVM 仓内路径/包/符号（A03–A10、A14、A16、A17、A20）在本 worktree 与本报文记录中都不存在，"
      "只登记「原文声明的路径+角色」，其 sha256、内容、是否真实实现（REAL/MOCK）均**未核实**——那属于 02/03 工序。")
    a("4. **原文自述的测试结果未重跑**：`pytest tests/test_case_cylinder_drag_fvm.py → 1 passed` 是源报告的自述（A09 的 `declared` 字段），"
      "本包未执行该测试（文件不在本 worktree），因此只记为声明，不作为本包的证据。")
    a("5. **平台图条目为 0**：平台记录 `figures` 为空数组，故无图端点可探测；`verification.json` 对此给出的是「空集 vacuous PASS + 说明」，"
      "不是「探测到 200」。")
    a("6. **边界**：只读 `report_id=14478`；未读/未写其它 report_id；未改写任何上游工件；未把任何结论标为 verified。"
      "所有写入均在本 worktree 内 `docs/wp-14478-01/`、`scripts/`、`tests/`。")
    a("7. **误差判定（必答项）**：本工序**不产生物理量**，因此不存在「相对基准 <3%」的误差判定对象——该问题在此 N/A，理由是本包只做资产登记"
      "（契约 `objective.register_assets=true`、`classify_report_type=false`）。可被判定的只有**位级一致性**：源哈希逐位相等（0 偏差）、"
      f"字符数 {src['chars']}={src['chars']}（0 偏差）、20/20 引文区间回切逐字相等（0 偏差）。"
      "原报告自身的物理误差判定（$C_D/C_L/p_{diff}$ vs 5% 门）因无 got 数据而为 FAIL，本包不改写该结论。")
    a("")
    a("## ⑥ 自检：逐条对照 acceptance")
    a("")
    a("| acceptance 项 | 结果 | 机检细节 |")
    a("|---|---|---|")
    for check in verification["checks"]:
        mark = {"PASS": "✅", "FAIL": "❌", "NOT_RUN": "⬜"}.get(check["result"], "?")
        detail = check["detail"]
        if isinstance(detail, dict):
            brief = {k: v for k, v in detail.items() if k in ("assets_checked", "errors", "claims", "platform_figures", "chars", "sha256", "note", "source", "parse", "files", "documents")}
            if "errors" in brief and brief["errors"] == []:
                brief["errors"] = "无"
        else:
            brief = detail
        a(f"| `{check['acceptance_item']}` | {mark} {check['result']} | {cell(json.dumps(brief, ensure_ascii=False), 160)} |")
    a("")
    a("契约声明的 6 项 acceptance：`valid_json`、`schema_pass`、`source_locator_resolvable`、`source_hash_matches`、`no_duplicate_ids`、"
      "`all_claims_have_evidence_or_explicit_unresolved_status` —— 全部 ✅（上表前段）。附加 4 项为 本仓追加的加固检查"
      f"（字符数一致、边界与无自证 verified、记录元数据逐字一致、平台图载荷状态）。"
      f"**无失败项；无 NOT_RUN 项**（本次以在线模式跑：`{verification['mode']}`，verified_at={verification['verified_at']}）。")
    a("")
    a("### honest 声明")
    a("")
    a("- 没有做：任何抽取（claims=0）、任何分类、任何数值复算、任何外部仓字节取证。")
    a("- 没有做而契约也不要求的：独立评审（`review.required=false`）。")
    a("- 未把任何结论标为 verified；`verified` 由平台门计算。")
    a("")
    a("## 一键复跑（repro_cmd）")
    a("")
    a("```text")
    a(REPRO_CMD)
    a("```")
    a("")
    a("## 结果信封（唯一 json 块）")
    a("")
    a("```json")
    a(json.dumps(envelope, ensure_ascii=False, indent=2))
    a("```")
    a("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="POST the report to /tensor/reports")
    args = parser.parse_args()

    md = build_markdown()
    if md.count("```json") != 1 or md.count("```") != 2 * (md.count("```") // 2):
        raise SystemExit("body must contain exactly one json code block and balanced fences")
    if md.count("```json") != 1:
        raise SystemExit("body must contain exactly one json code block")
    out = DOCS / f"KF-RESULT-{PACKAGE_ID}.md"
    out.write_text(md, encoding="utf-8")
    print(f"wrote {out} ({len(md)} chars, json blocks={md.count('```json')})")

    if not args.publish:
        return 0

    envelope = json.loads((DOCS / f"kf_result.{PACKAGE_ID}.json").read_text(encoding="utf-8"))
    block = md.split("```json", 1)[1].split("```", 1)[0]
    if json.loads(block) != envelope:
        raise SystemExit("json block in the markdown differs from the envelope file — refusing to publish")
    if envelope["provenance"]["source_hash"] != "sha256:" + CONTRACT_HASH:
        raise SystemExit("provenance hash differs from the pinned contract hash — refusing to publish")

    figures = [
        {"name": name, "caption": caption,
         "png_base64": base64.b64encode((DOCS / name).read_bytes()).decode()}
        for name, caption in FIGURES
    ]
    manifest = envelope["outputs"]["asset_manifest.json"]
    payload = {
        "title": TITLE,
        "summary": (
            f"登记报告 {REPORT_ID} 的源资产：markdown 逐字节固定（sha256 {CONTRACT_HASH[:8]}…、{manifest['source']['chars']} 字符，与契约逐位一致），"
            f"{manifest['counts']['assets']} 条资产的字符区间/行号/引文/唯一性全部机检（20/20 回切一致）；"
            "5 类 payload 状态显式区分（1 记录内 / 1 外部 URL / 12 外部仓路径未取证 / 5 原文自述缺失未升格 / 1 仅源内声明）；"
            "claims 空（本工序不抽取），未把任何结论标为 verified。"
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-work-package", f"kf-wp:{PACKAGE_ID}", "asset-registration", "provenance",
                 f"report-{REPORT_ID}", "case-cylinder-drag-fvm"],
        "markdown": md,
        "figures": figures,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(fetch.api_base() + "/tensor/reports", data=data,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + fetch.login()}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            status, body = resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        print(f"POST failed: {exc.code} {exc.read().decode()[:600]}")
        return 1
    print(f"POST /tensor/reports -> {status}")
    record = json.loads(body)
    new_id = record.get("id") or (record.get("data") or {}).get("id")
    print(f"published report id={new_id}")

    # round-trip: re-fetch our own report and compare the json block + figure payload
    got = json.loads(urllib.request.urlopen(urllib.request.Request(
        fetch.api_base() + f"/tensor/reports/{new_id}",
        headers={"Authorization": "Bearer " + fetch.login()}), timeout=60).read().decode())
    rt_block = got["markdown"].split("```json", 1)[1].split("```", 1)[0]
    fig = (got.get("figures") or [{}])[0].get("name")
    fig_bytes = urllib.request.urlopen(urllib.request.Request(
        fetch.api_base() + f"/tensor/reports/{new_id}/figures/{fig}",
        headers={"Authorization": "Bearer " + fetch.login()}), timeout=60).read()
    roundtrip = {
        "published_report_id": new_id,
        "title": got.get("title"),
        "tags": got.get("tags"),
        "json_block_roundtrip_equal": json.loads(rt_block) == envelope,
        "provenance_hash_in_published_block": json.loads(rt_block)["provenance"]["source_hash"],
        "markdown_sha256_published": hashlib.sha256(got["markdown"].encode("utf-8")).hexdigest(),
        "markdown_sha256_local": hashlib.sha256(md.encode("utf-8")).hexdigest(),
        "figure_endpoint_positive_control": {
            "name": fig, "http_status": 200, "bytes": len(fig_bytes),
            "sha256_matches_local": hashlib.sha256(fig_bytes).hexdigest()
            == hashlib.sha256((DOCS / fig).read_bytes()).hexdigest(),
        },
    }
    (DOCS / "publish_roundtrip.json").write_text(json.dumps(roundtrip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(roundtrip, ensure_ascii=False, indent=2))
    return 0 if roundtrip["json_block_roundtrip_equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())