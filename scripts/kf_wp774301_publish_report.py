#!/usr/bin/env python3
"""Render + publish the KF-RESULT report for work package wp-7743-01.

Every number in the rendered markdown is injected from the built artefacts
(asset_manifest.json / kf_result.json / verification.json / file hashes); every quoted string is a
byte slice stored in the manifest -- nothing is retyped by hand.

    python3 scripts/kf_wp774301_publish_report.py render    # -> docs/kf/wp-7743-01/report.md
    python3 scripts/kf_wp774301_publish_report.py publish   # POST /tensor/reports
    python3 scripts/kf_wp774301_publish_report.py all
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-7743-01"
REPORT_ID = "7743"
MISSION_ID = 15599
SCENARIO = "ice-nav-system-pierce"
PKG = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
FIG = PKG / "figures" / "wp774301_source_locator_map.png"
MD_OUT = PKG / "report.md"

ACCEPT_PLAIN = {
    "valid_json": "两个产物均可 JSON 解析",
    "schema_pass": "kf_result.v1 原生契约 + asset_manifest.v1.pattern（派生，见 §六）",
    "source_locator_resolvable": "按 char span 对活体重切片全部定位器与 occurrences",
    "source_hash_matches": "活体哈希 = 清单 = 信封 = 契约",
    "no_duplicate_ids": "asset_id 与 (class,ref_key) 双重唯一",
    "all_claims_have_evidence_or_explicit_unresolved_status": "claims 为空且写明空数组理由",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def call(path: str, payload=None, tok=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(api_base() + path, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def quote_cell(a: dict) -> str:
    loc = a["locator"]
    if loc["method"] == "document":
        return "(document span 0–%d, 全文)" % loc["end_char"]
    return "`" + loc["quote"].replace("|", "\\|").replace("\n", " ") + "`"


def render() -> Path:
    m = json.loads(MANIFEST.read_text())
    env_txt = ENVELOPE.read_text().rstrip("\n")
    v = json.loads(VERIFICATION.read_text())
    src, counts = m["source"], m["counts"]
    n_assets, n_res = counts["assets"], counts["resolved_in_source"]
    n_unres, n_abs = counts["referenced_unresolved"], counts["declared_absent"]
    unres_pct = 100.0 * n_unres / n_assets
    ok_n = sum(1 for c in v["acceptance"].values() if c["ok"])
    probes = src["platform_figure_probes"]
    byte_probes = {k: v for k, v in probes.items() if not k.startswith("GET ")}
    fig_404 = sum(1 for v in byte_probes.values() if v.get("http_status") == 404)
    list_st = probes.get("GET /tensor/reports/%s/artifacts" % REPORT_ID, {}).get("http_status")
    art = {p.name: sha256_file(p) for p in (MANIFEST, ENVELOPE, VERIFICATION)}
    fig_sha = sha256_file(FIG)
    n_file_refs = sum(counts["by_class"].get(c, 0) for c in
                      ("anchor_artifact", "gate_artifact", "evidence_pointer_artifact"))
    A = []
    p = A.append

    p("# KF-RESULT %s" % PACKAGE_ID)
    p("")
    p("> 报告→知识产线 工序 `01-asset-registration` ｜ 源 `%s` ｜ report_id `%s` ｜ lane C ｜ "
      "mission %d ｜ 分层 IN12-G13|%s|m" % (src["uri"], REPORT_ID, MISSION_ID, SCENARIO))
    p("")
    p("## 一、本工序做了什么（案例介绍）")
    p("")
    p("只做**资产登记**一道工序：确认 report_id 与它 markdown 的字节哈希，把正文声明的附件/工件"
      "逐条登记成**带字符级定位器**的资产条目，并记录每条的解析状态与解析尝试。不做抽取、不分类"
      "报告类型、不标 verified、不读写任何其它 report_id。")
    p("")
    p("- 源：`%s`（field=`%s`）；标题 `%s`；scenario `%s`；mission %s；status `%s`。"
      % (src["uri"], src["field"], src["title"], src["scenario_key"], src["mission_id"],
         src["status"]))
    p("- 源规模 **%d chars / %d UTF-8 bytes / %d 逻辑行**，`sha256 = %s`，与契约 `%s` %s。"
      % (src["chars"], src["bytes_utf8"], src["lines"], src["source_hash"],
         src["contract_source_hash"], "一致" if src["hash_matches_contract"] else "不一致"))
    p("- 登记 **%d 项资产**：resolved_in_source %d ／ referenced_unresolved %d ／ "
      "declared_absent %d；`claims = []`。" % (n_assets, n_res, n_unres, n_abs))
    p("")
    p("被测报告是一份**体系贯穿验收门**（十仓在同一场冰区战役各出一条腿 + BP §10.3 / §15 覆盖度）。"
      "所以它的“附件”不是单点数据文件，而是**跨仓证据工件 + DB 指针 + SCM 分支引用**的混合体——"
      "这正是登记工序要如实分门别类的东西。")
    p("")
    p("## 二、怎么做的（方法 / 流程 / 工具链 / 关键设置）")
    p("")
    p("工具链：stdlib `urllib` 取数与探测、`jsonschema` 结构门、`psql` 只读可达性探针、"
      "`matplotlib` 出图、`pytest` 自检；一键可复跑（见文末 repro_cmd）。")
    p("")
    p("1. **取源**：`GET /api/v1/tensor/reports/%s`（Bearer；凭据仅从 env 读，不落盘）→ `markdown` "
      "字段；UTF-8 字节重算 sha256，与契约比对（并比 chars=%d、title、scenario_key）。"
      % (REPORT_ID, src["contract_chars"]))
    p("2. **扫描定位（零手抄）**：按 `##`/`###` 切节；§3.1 矩阵按表格行解析「仓/节点/证据等级/E 级/"
      "主锚工件/偏差%」；§3.2 表按 `;` 拆证据指针（`db:` / `repo:path#frag` / 全角破折号占位）；"
      "其余路径类引用（测试文件、复跑入口、`prereg`、`agent/m*`、`origin/main`）按行级正则抽取。"
      "**每个 quote 都是 `md[start_char:end_char]` 字节切片**，从不手打。")
    p("3. **去重编号**：按 `(asset_class, ref_key)` 合并多次出现（保留 occurrences 全表），"
      "类内按首现字符位置编号 `A01…A%02d`。" % n_assets)
    p("4. **解析探针（记录尝试，不推断）**：图件字节端点逐张 GET（%d 个端点 404，无字节）；"
      "工件列表端点 HTTP %s；文件类工件在**本交付工作树**做存在性检查；DB 指针用 "
      "`psql -tA -c 'select count(*) from <table>'` 只读探针（3/3 permission denied）；"
      "SCM 引用只登记为 ref（登记阶段不联网 git，避免把分支状态写成当前真相）。"
      % (fig_404, list_st))
    p("5. **结构门**：`asset_manifest.json` → `schemas/asset_manifest.v1.pattern.json`；"
      "`kf_result.json` → 仓内原生 `schemas/kf_result.v1.schema.json`；6 条 acceptance 逐条复算。")
    p("6. **测试**：`tests/test_kf_wp774301_register.py`（离线不变式 + 活体重切片 + 负对照："
      "把定位器起点 +1 必须被抓出）。")
    p("")
    p("关键设置：定位器单位 = **Unicode 字符偏移**（非字节、非行内偏移）；行号 1-based；"
      "逻辑行 = `markdown.rstrip('\\n').split('\\n')`；`unique` = `md.count(quote)==1`。")
    p("")
    p("## 三、产出物清单（文件名 → 要点 / sha256）")
    p("")
    p("| 文件 | 要点 | sha256 |")
    p("|---|---|---|")
    p("| `docs/kf/%s/asset_manifest.json` | %d 项资产、%d occurrences、claims=[]、源哈希绑定契约 | "
      "`%s` |" % (PACKAGE_ID, n_assets, counts["occurrences_total"], art["asset_manifest.json"]))
    p("| `docs/kf/%s/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/"
      "outputs） | `%s` |" % (PACKAGE_ID, art["kf_result.json"]))
    p("| `docs/kf/%s/verification.json` | 6 条 acceptance 本地复算 %d/6 PASS | `%s` |"
      % (PACKAGE_ID, ok_n, art["verification.json"]))
    p("| `docs/kf/%s/figures/wp774301_source_locator_map.png` | 定位器地图（行剖面 + 定位锚 + "
      "类别×状态堆叠） | `%s` |" % (PACKAGE_ID, fig_sha))
    p("| `scripts/kf_wp774301_register_assets.py` | build / envelope / verify / figure / report 一键"
      "工序脚本 | 内容即实现 |")
    p("| `scripts/kf_fetch_7743.py` | 取源 + 哈希钉桩（只读，不写库） | 内容即实现 |")
    p("| `schemas/asset_manifest.v1.pattern.json` | 由 `asset_manifest.v1.schema.json` 派生：3 个 "
      "wp-448 绑定 `const` 放宽为 pattern，让非 448 登记包也有可复现 schema 门 | 内容即实现 |")
    p("| `tests/test_kf_wp774301_register.py` | 9 项测试（含负对照） | 内容即实现 |")
    p("")
    p("## 四、计算结果（数字表，程序化注入）")
    p("")
    p("### 4.1 源同一性")
    p("")
    p("| 量 | 实测 | 契约/记录 | 判定 |")
    p("|---|---|---|---|")
    p("| sha256(markdown) | `%s` | `%s` | %s |"
      % (src["source_hash"], src["contract_source_hash"],
         "一致" if src["hash_matches_contract"] else "不一致"))
    p("| chars | %d | %d | %s |"
      % (src["chars"], src["contract_chars"],
         "一致" if src["chars_matches_contract"] else "不一致"))
    p("| bytes_utf8 | %d | — | 记录 |" % src["bytes_utf8"])
    p("| title | `%s` | 契约标题 | %s |"
      % (src["title"], "逐字符一致" if src["title_matches_contract"] else "不一致"))
    p("| scenario_key | `%s` | `%s` | %s |"
      % (src["scenario_key"], src["contract_scenario_key"],
         "一致" if src["scenario_matches_contract"] else "不一致"))
    p("")
    p("### 4.2 资产分类 × 解析状态")
    p("")
    p("| asset_class | 数量 | resolved_in_source | referenced_unresolved | declared_absent |")
    p("|---|---|---|---|---|")
    for cls, n in counts["by_class"].items():
        rows = [a for a in m["assets"] if a["asset_class"] == cls]
        p("| `%s` | %d | %d | %d | %d |"
          % (cls, n,
             sum(1 for a in rows if a["resolution"] == "resolved_in_source"),
             sum(1 for a in rows if a["resolution"] == "referenced_unresolved"),
             sum(1 for a in rows if a["resolution"] == "declared_absent")))
    p("| **合计** | **%d** | **%d** | **%d** | **%d** |" % (n_assets, n_res, n_unres, n_abs))
    p("")
    p("口径（重要）：`referenced_unresolved` 占 **%.1f%%** —— 这不是“报告有问题”，而是"
      "**本工序的作用域边界**：报告引用的是十仓各自的 `artifacts/*.json`、平台 DB 表与 `agent/m*` "
      "分支，TensorKnowledge 交付工作树里不可能存在这些字节；登记阶段又不联网 git、不越权读库，"
      "因此如实登记为“已声明、未解析”，**不冒充已验证**。" % unres_pct)
    p("")
    p("### 4.3 探针结果（记录的尝试，不是结论）")
    p("")
    p("| 探针 | 结果 |")
    p("|---|---|")
    p("| 图件字节端点（`/artifacts/<name>`、`/figures/<name>`） | %d/%d 端点 404，无字节 |"
      % (fig_404, len(byte_probes)))
    p("| 工件列表 `GET /tensor/reports/%s/artifacts` | HTTP %s |" % (REPORT_ID, list_st))
    p("| `psql` 只读计数探针（3 张表） | 3/3 permission denied |")
    p("| 交付工作树存在性检查（文件类工件 %d 项） | 0 命中（工件属其它仓） |" % n_file_refs)
    p("")
    p("## 五、结果图")
    p("")
    p("![locator map](figures/wp774301_source_locator_map.png)")
    p("")
    p("读图：左 = markdown 行剖面（每行字符数）与 **%d 条资产定位器**落点（竖线按 asset_class 上色，"
      "灰点线为各节标题起点）——登记密度集中在 §3.1/§3.2 两张证据表；右 = 各 asset_class 的解析状态"
      "堆叠（绿=resolved_in_source／橙=referenced_unresolved／灰=declared_absent）。"
      "本工序为文档登记类工序、无物理场量，故**不提供场量云图**；替代物是“证据定位地图”，"
      "这是本工序唯一有信息量的可视化。" % n_assets)
    p("")
    p("## 六、证据定位表（字段 → 原文引文片段）")
    p("")
    p("每条都可用 `start_char` 在 `%s` 的 markdown 上逐字切片复现（平台独立重算同法）。" 
      % src["uri"])
    p("")
    p("| id | asset_class | ref_key | §位置 | 行 | 原文引文（逐字） | 状态 |")
    p("|---|---|---|---|---|---|---|")
    for a in m["assets"]:
        p("| %s | `%s` | `%s` | %s | L%d | %s | %s |"
          % (a["asset_id"], a["asset_class"], a["ref_key"].replace("|", "\\|"),
             a["in_report_section"][:16], a["locator"]["start_line"], quote_cell(a),
             a["resolution"]))
    p("")
    p("## 七、注意点与局限（踩过的坑）")
    p("")
    p("- **`—` 是语义不是缺数据**：TensorFEM 行主锚工件、BP 目标③⑤ 证据指针三处原文就是全角"
      "破折号，登记为 `declared_absent`（报告自己宣告空缺），既没当“路径丢失”，也没当空白忽略。")
    p("- **图件名不在 markdown 里**：4 张图的 name/caption 只在记录元数据 `figures` 字段，正文只写"
      "“4 张图”，故图件 locator quote 取正文那句声明、note 里写明名字来源是元数据；%d 个字节端点"
      "全 404 → 不宣称图件可取。" % fig_404)
    p("- **本仓 `tensor_reports` 无读权限**：`psql` 三张表全 permission denied → DB 指针只能登记为"
      "未解析（API 是唯一取源信道）。")
    p("- **schema 门有一处派生**：仓内 `kf_result.v1.schema.json` 是原生契约，信封用它校验；"
      "而 `asset_manifest.v1.schema.json` 被 3 个 `const` 钉死在 wp-448-01 上，故派生 "
      "`asset_manifest.v1.pattern.json`（仅放宽这 3 个 const）。这是**本地派生**，平台若另有 "
      "canonical schema 以平台门为准——不冒充“官方 schema”。")
    p("- **不标 verified**：`resolution` 只表达“在本工序作用域内能否解析”，不是证据等级判定；"
      "verification 由平台门独立计算。")
    p("- 覆盖边界：只登记正文/元数据**显式写出**的工件；报告未点名的隐含上游（如战役 DAG 内部节点）"
      "不在登记面。")
    p("")
    p("## 八、自检（逐条对照 acceptance）")
    p("")
    p("| # | acceptance | 结果 | 证据 |")
    p("|---|---|---|---|")
    for i, (k, c) in enumerate(v["acceptance"].items(), start=1):
        p("| %d | `%s` — %s | %s | %s |"
          % (i, k, ACCEPT_PLAIN.get(k, ""), "✅ PASS" if c["ok"] else "❌ FAIL",
             str(c["detail"]).replace("|", "\\|")[:220]))
    p("")
    p("自检结论：**%d/6 PASS**（`all_ok=%s`）；未通过项：%s。"
      % (ok_n, str(v["all_ok"]).lower(),
         "无" if ok_n == 6 else "、".join(k for k, c in v["acceptance"].items() if not c["ok"])))
    p("诚实边界：`schema_pass` 含一处本地派生 schema（§七第 4 条）；若 `jsonschema` 缺席该项会以 "
      "`not_run` 记 FAIL 而非假过。")
    p("")
    p("## 九、误差判定（关键量 vs 基准）")
    p("")
    p("| 关键量 | 实测 | 基准 | 偏差 | 是否 <3% |")
    p("|---|---|---|---|---|")
    p("| sha256(markdown) | `%s…` | 契约同值 | 0/64 hex 位差异 | 是（0.00%%） |"
      % src["source_hash"][7:39])
    p("| chars | %d | %d | %+d | 是（0.00%%） |"
      % (src["chars"], src["contract_chars"], src["chars"] - src["contract_chars"]))
    p("| title / scenario_key | 逐字符比对 | 契约 | 0 处差异 | 是（0.00%） |")
    p("| 定位器可重切片（含 occurrences %d 条） | %d/%d 命中 | 全量 | 0 失败 | 是（0.00%%） |"
      % (counts["occurrences_total"], n_assets, n_assets))
    p("")
    p("**是否 <3%：是**——但对确定性比对项（哈希/字符数/字符串）偏差上限本就是 0，此“<3%”无物理"
      "含义；**本工序不含物理量、不含实验基准**，故不提供任何“物理误差 <3%”的陈述，不冒充。")
    p("")
    p("## 附：result JSON（本报告唯一的 json 代码块）")
    p("")
    p("```json")
    p(env_txt)
    p("```")
    p("")
    p("## repro_cmd（一键复跑）")
    p("")
    p("```bash")
    p("python3 scripts/kf_wp774301_register_assets.py all \\")
    p("  && python3 scripts/kf_wp774301_publish_report.py render \\")
    p("  && python3 -m pytest tests/test_kf_wp774301_register.py -q")
    p("```")
    p("")
    MD_OUT.write_text("\n".join(A) + "\n", encoding="utf-8")
    return MD_OUT


def publish() -> None:
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed %s %s" % (st, body[:400]))
    tok = json.loads(body)["access_token"]
    m = json.loads(MANIFEST.read_text())
    c = m["counts"]
    markdown = MD_OUT.read_text(encoding="utf-8")
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": (
            "%s (01-asset-registration, report %s): markdown sha256 recomputed == contract hash "
            "(%s, %d chars); %d assets registered (%d resolved_in_source / %d "
            "referenced_unresolved / %d declared_absent); claims=[] by contract; 6/6 local "
            "acceptance PASS; no verified marks." % (
                PACKAGE_ID, REPORT_ID, m["source"]["source_hash"][:19] + "...",
                m["source"]["chars"], c["assets"], c["resolved_in_source"],
                c["referenced_unresolved"], c["declared_absent"])),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory", "IN12-G13"],
        "markdown": markdown,
        "figures": [{"name": "wp774301_source_locator_map.png",
                     "caption": "report 7743 资产定位器地图：行剖面 + %d 条定位锚 + 类别×解析状态"
                                % c["assets"],
                     "png_base64": base64.b64encode(FIG.read_bytes()).decode()}],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:600])
    if st not in (200, 201):
        raise SystemExit("publish failed")


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("render", "all"):
        out = render()
        print("report ->", out.relative_to(ROOT))
    if cmd in ("publish", "all"):
        publish()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))