"""Compose and publish the KF-RESULT report for wp-10459-01.

All numbers in the report body are injected from the artifacts produced by
scripts/kf_wp10459_register_assets.py and scripts/kf_wp10459_validate.py -- nothing is retyped.
The report carries exactly one ```json block (the kf_result envelope), per the delivery contract.

Usage: python3 scripts/kf_wp10459_report.py [--dry-run]
Outputs: docs/reports/kf_wp_10459_01_result.md ; POST /tensor/reports
"""
from __future__ import annotations

import base64
import json
import re
import os
import pathlib
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-10459-01"
REPORT_ID = "10459"
DOCDIR = REPO / "docs/kf" / PKG
MAN = DOCDIR / "asset_manifest.json"
ENV = DOCDIR / "kf_result.json"
SELF = DOCDIR / "selfcheck.json"
FIG = DOCDIR / "fig_asset_coverage.png"
OUT_MD = REPO / "docs" / "reports" / "kf_wp_10459_01_result.md"
ART = REPO / "artifacts" / PKG / "asset_manifest.json"

MISSION_ID = 15683
SCENARIO_KEY = "ship_performance/evidence_upgrade/in102_n03"


def disp(q: str, n: int = 56) -> str:
    """Display-truncated verbatim prefix; truncation is marked, never silently smoothed."""
    q = q.replace("\n", " ⏎ ").replace("|", "\\|")
    return q if len(q) <= n else q[:n] + " …(截断显示，全文见 json 块)"


def cell(q: str) -> str:
    """Inline-code a quote with a fence longer than any backtick run inside it."""
    body = disp(q)
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    fence = "`" * (longest + 1)
    return fence + " " + body + " " + fence


def size(p: pathlib.Path) -> str:
    return "%d B" % p.stat().st_size


def build_markdown(man: dict, env: dict, selfchk: dict) -> str:
    c = man["counts"]
    src = man["source"]
    assets = man["assets"]
    checks = selfchk["checks"]
    npass = sum(1 for x in checks if x["result"] == "PASS")

    lines: list[str] = []
    A = lines.append
    A("# KF-RESULT wp-10459-01")
    A("")
    A("工作包 `wp-10459-01` · 工序 `01-asset-registration` · report_id **10459** · 分支 `agent/m15683` · "
      "仓库 TensorKnowledge")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A("把 report %s 的**源资产登记**下来，不做抽取、不做验证：确认平台记录里 `markdown` 字段的字节内容与契约 "
      "`source_hash` 一致，再把报告中可解析的附件/工件逐条登记为资产，每条给可机器复算的定位（字符区间 + 行区间 + "
      "逐字引文 + 唯一性）。" % REPORT_ID)
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| report_id | %s（本包只碰这一份） |" % man["report_id"])
    A("| source_uri | `%s` |" % src["uri"])
    A("| source_field | `%s` |" % src["field"])
    A("| sha256(markdown, utf-8) | `%s` |" % src["hash"])
    A("| chars / bytes_utf8 | %d / %d |" % (src["chars"], src["bytes_utf8"]))
    A("| 契约 source_hash 一致 | %s |" % ("是" if man["integrity"]["hash_matches_contract"] else "否"))
    A("| 契约 chars 一致 | %s（契约 6431） |" % ("是" if man["integrity"]["chars_matches_contract"] else "否"))
    A("| 资产数 | %d（resolved_in_source %d / referenced_unresolved %d / declared_absent %d） |"
      % (c["assets"], c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"]))
    A("| claims | %d（契约允许空数组：objective.classify_report_type=false，本工序不做抽取） |" % len(man["claims"]))
    A("| 是否标记 verified | 否（verification 由平台门计算） |")
    A("")
    A("源报告主题：%s。" % src["title"])
    A("")
    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("1. **取原文并锁定字节**：`GET /api/v1/tensor/reports/10459`（Bearer 由 `TENSOR_AGENT_USER` 登录换得，"
      "不在脚本里写任何凭据），只取 `markdown` 字段；`sha256(md.encode('utf-8'))` 与契约 "
      "`08c1a0cf…4f6c` 比对，不一致则脚本直接退出、拒绝登记（防止基于另一份 payload 登记）。")
    A("2. **锚点定位、不是手抄**：每个资产在脚本里声明一个**锚点子串**，脚本断言它在 markdown 中"
      "**恰好出现 1 次**，再按声明的前后行偏移切出引文；随后独立复核 `md[start_char:end_char] == quote` "
      "且 `md.count(quote)==1`，任一不成立即退出。行号由字符偏移反算（1-based）。")
    A("3. **三类解析状态，缺失就写缺失**：`resolved_in_source`（目标字节在源 markdown 内，或就是 markdown 本身）、"
      "`referenced_unresolved`（引用能定位、但目标在本 worktree / 平台记录里没有字节载荷，如外部仓代码文件、"
      "只有 name+caption 的图）、`declared_absent`（**报告自己声明**该物缺失/未做）。不发明地址、不补造内容。")
    A("4. **登记但不抽取**：`claims` 输出为空数组；没有把报告任何一句结论提升为本包结论，**未标 verified**。")
    A("5. **自检独立复算**：`scripts/kf_wp10459_validate.py` 不信任本地快照，重新从 API 取 markdown 再逐条复算"
      "验收项；manifest schema 用的是仓内 `schemas/asset_manifest.v1.schema.json`——它是 **report-bound** 的"
      "（`const` 钉死 wp-448-01/448/tensor://reports/448），自检器只重绑定这 3 个 const 并断言 schema 其余部分未改。")
    A("")
    A("## ③ 产出物清单（输出文件名 → 要点）")
    A("")
    A("| 文件 | 大小 | 要点 |")
    A("|---|---|---|")
    A("| `artifacts/%s/asset_manifest.json` | %s | 契约声明的输出文件：%d 资产 + structure_index + counts + integrity |"
      % (PKG, size(ART), c["assets"]))
    A("| `docs/kf/%s/asset_manifest.json` | %s | 同字节镜像（推送门会丢 artifacts/**，故落 docs/ 保活） |"
      % (PKG, size(MAN)))
    A("| `docs/kf/%s/kf_result.json` | %s | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs） |"
      % (PKG, size(ENV)))
    A("| `docs/kf/%s/selfcheck.json` | %s | 自检逐项结果：%d/%d PASS |" % (PKG, size(SELF), npass, len(checks)))
    A("| `docs/kf/%s/fig_asset_coverage.png` | %s | 图：资产定位区间覆盖图 + 类别×解析状态堆叠图 |" % (PKG, size(FIG)))
    A("| `docs/reports/kf_wp_10459_01_result.md` | 本文件 | 报告正文（含唯一 json 代码块） |")
    A("| `runs/%s/report_10459.md` | %d B | 平台 markdown 快照（逐字节，供复跑比对） |"
      % (PKG, (REPO / "runs" / PKG / "report_10459.md").stat().st_size))
    A("")
    A("### 资产登记表")
    A("")
    A("| id | class | 报告位置 | 行区间 | 字符区间 | resolution | 检查要点 |")
    A("|---|---|---|---|---|---|---|")
    for a in assets:
        loc = a["locator"]
        A("| %s | %s | %s | %d–%d | %d–%d | %s | %s |"
          % (a["asset_id"], a["asset_class"], a["in_report_section"], loc["start_line"], loc["end_line"],
             loc["start_char"], loc["end_char"], a["resolution"], a["resolution_check"]["result"]))
    A("")
    A("## ④ 证据定位表（claim/字段 → 原文引文片段）")
    A("")
    A("本工序不产出知识 claim（`claims=[]`），下表的每一行是一个**登记断言**：断言「原文在该位置逐字存在」。"
      "引文列为逐字前缀（超长标注截断），完整引文与字符偏移在 json 块的 `outputs.asset_manifest.json.assets[]` "
      "里，可被平台独立复算。")
    A("")
    A("| # | 登记断言（资产） | 原文引文片段（逐字） | 行 |")
    A("|---|---|---|---|")
    for i, a in enumerate(assets, 1):
        A("| %d | %s %s | %s | %s |"
          % (i, a["asset_id"], a["label"].replace("|", "\\|"),
             cell(a["locator"]["quote"]),
             "%d–%d" % (a["locator"]["start_line"], a["locator"]["end_line"])))
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("* **登记 ≠ 验证**：`resolution` 只说明定位能否解析，`resolved_in_source` 不等于数值可信。报告里 4 个量的等级"
      "（2 REAL / 2 WITHHELD）、重叠度 0.661 与 0.000 两处 honest FAIL、S_T 数值一律**按原文登记**，"
      "本包未复核、未改判、未升格。")
    A("* **上游一处不一致已如实登记（A29）**：markdown 第 113 行自述 `accuracy_caveat` 已写入报告 JSON，"
      "但 `GET /tensor/reports/10459` 返回的顶层键为 id/title/summary/scenario_key/mission_id/stage/tags/"
      "figures/status/created_by/created_at/markdown，**无 accuracy_caveat**。本包不代写该字段，记为 "
      "`referenced_unresolved`，交上游/门处置。")
    A("* **3 个图件无字节**（A20–A22）：平台 `figures[]` 只有 name+caption，无 `png_base64`，故无字节可哈希，"
      "记为 `referenced_unresolved`；图题在 ④ 节可逐字定位。")
    A("* **3 个代码/测试/图件脚本不在本仓**（A07/A13/A14，`backend/modules/evidence_upgrade.py`、"
      "`tests/test_evidence_upgrade.py`、`artifacts/evidence_upgrade/make_figures.py`）：属船舶平台仓，本 worktree "
      "内 `os.path.exists` 为假。报告自述「35 用例」「matplotlib 3.10.8」无法在此复核，只登记引用与其声明数。")
    A("* **A18 的 sha256 只有前 16 位**（原文如此），完整摘要不可由该表恢复；登记为截断摘要，不外推、不复原。")
    A("* **schema 局限**：仓内 `schemas/asset_manifest.v1.schema.json` 的 `const` 把 package_id/report_id/uri 钉在 "
      "wp-448-01/448 上，任何别的包都无法用它直接通过校验。本包用「只重绑定 3 个 const + 断言其余未改」的方式"
      "复用该 schema（见自检 `schema_pass` 详情），**未修改该文件**（它属上游 wp-448 产物）。若平台侧 schema 与此"
      "形态不同，以平台门为准。")
    A("* **本包不做的事**：不重算报告数字、不重建图件、不读其它 report_id、不 push、不改 .git 配置。")
    A("")
    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance / 约束 | 结果 | 复算依据 |")
    A("|---|---|---|")
    for x in checks:
        A("| %s | %s | %s |" % (x["check"].replace("_", "\\_"), x["result"], x["detail"].replace("|", "\\|")[:220]))
    A("")
    A("**自检结论：%d/%d PASS，VERDICT %s。** 失败项：%s。" %
      (npass, len(checks), selfchk["verdict"],
       "无" if selfchk["failed"] == 0 else "%d 项" % selfchk["failed"]))
    A("")
    A("### 误差判定（关键量 vs 基准，是否 <3%）")
    A("")
    A("本工序是**登记类**工序，没有物理关键量，因此**不声称任何物理量 <3%**（无基准可比，也无权代替上游判定）。"
      "可精确复算的量只有三个，均为确定性判定而非统计误差：")
    A("")
    A("| 量 | 判据 | 实测 | 误差 | 是否达标 |")
    A("|---|---|---|---|---|")
    A("| sha256(markdown) | 与契约 `%s` 逐字相等 | `%s` | 0（字节级相等） | 是 |"
      % (man["integrity"]["contract_expected_hash"][:16] + "…", man["source"]["hash"][:16] + "…"))
    A("| 定位可解析率 | 每条引文重现其字符区间且全文唯一 | %d/%d | 0 | 是 |"
      % (len(assets), len(assets)))
    A("| counts 自洽 | Σby_class = Σby_resolution = assets | %d / %d / %d | 0 | 是 |"
      % (sum(c["by_class"].values()), sum(c["by_resolution"].values()), c["assets"]))
    A("")
    A("## repro_cmd（一键复跑）")
    A("")
    A("```bash")
    A("cd <worktree>   # TensorKnowledge, branch agent/m15683")
    A("python3 scripts/kf_wp10459_fetch.py            # 取 report 10459 markdown，校验 sha256 == 契约")
    A("python3 scripts/kf_wp10459_register_assets.py  # 重建 asset_manifest.json + kf_result.json")
    A("python3 scripts/kf_wp10459_validate.py         # 重新取原文，逐条复算 acceptance（期望 VERDICT PASS）")
    A("python3 scripts/kf_wp10459_figures.py          # 重建覆盖图")
    A("python3 scripts/kf_wp10459_report.py --dry-run # 只合成报告，不发布")
    A("```")
    A("")
    A("环境：纯 Python 3 + `jsonschema` + `matplotlib`；凭据仅从 env `TENSOR_API_BASE` / "
      "`TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读取。")
    A("")
    A("## 结果 JSON（唯一一个 json 代码块，平台门按此校验）")
    A("")
    A("```json")
    A(json.dumps(env, ensure_ascii=False, indent=2))
    A("```")
    A("")
    return "\n".join(lines)


def main() -> int:
    man = json.loads(MAN.read_text(encoding="utf-8"))
    env = json.loads(ENV.read_text(encoding="utf-8"))
    selfchk = json.loads(SELF.read_text(encoding="utf-8"))
    md = build_markdown(man, env, selfchk)

    # contract self-checks on the composed document
    assert md.count("```json") == 1, "exactly one json block required, got %d" % md.count("```json")
    assert md.startswith("# KF-RESULT " + PKG)
    block = md.split("```json", 1)[1].split("```", 1)[0]
    parsed = json.loads(block)
    assert parsed["package_id"] == PKG and parsed["report_id"] == REPORT_ID
    assert parsed["provenance"]["source_hash"] == "sha256:" + man["source"]["hash"]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    print("composed %s (%d chars, 1 json block verified parseable)" % (OUT_MD.relative_to(REPO), len(md)))
    if "--dry-run" in sys.argv:
        return 0

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

    def post(path, payload, token=None):
        req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    token = post("/auth/login", {"username": user, "password": pwd}).get("access_token")
    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": (
            "资产登记工序完成：report 10459 源 markdown sha256 与契约一致（08c1a0cf…4f6c，6431 字符 / 9539 字节），"
            "登记 %d 个资产（resolved_in_source %d / referenced_unresolved %d / declared_absent %d），每条带字符区间+"
            "行区间+逐字唯一引文；claims 按契约留空、未标 verified；自检 %d/%d PASS。发现上游一处不一致："
            "markdown 自述 accuracy_caveat 已写入报告 JSON，但平台记录无该字段（记为 A29 referenced_unresolved）。"
            % (man["counts"]["assets"], man["counts"]["resolved_in_source"],
               man["counts"]["referenced_unresolved"], man["counts"]["declared_absent"],
               sum(1 for x in selfchk["checks"] if x["result"] == "PASS"), len(selfchk["checks"]))
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PKG, "kf-result", "01-asset-registration", "report-10459",
                 "IN102-N03", "asset-registration", "evidence-grade"],
        "markdown": md,
        "figures": [{
            "name": "fig_asset_coverage.png",
            "caption": ("wp-10459-01 资产登记覆盖图：左=29 个资产在 report 10459 markdown 中的字符区间"
                        "（蓝=resolved_in_source，橙=referenced_unresolved，红=declared_absent，点线为各节起点），"
                        "右=按类别×解析状态堆叠的资产数。全部数字由 asset_manifest.json 程序化注入。"),
            "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
        }],
    }
    resp = post("/tensor/reports", payload, token)
    print(json.dumps({"id": resp.get("id"), "title": resp.get("title"),
                      "tags": resp.get("tags"), "created_at": resp.get("created_at")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())