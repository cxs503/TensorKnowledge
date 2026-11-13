#!/usr/bin/env python3
"""Build the KF-RESULT report markdown for wp-11557-01 (single ```json block = result envelope)."""
import json

env = json.load(open("docs/kf/wp-11557-01/kf_result.wp-11557-01.json"))
md_src = open("docs/kf/wp-11557-01/report_11557.md").read()

def q(quote):
    """Return verbatim quote (asserts it is a substring of the source)."""
    assert quote in md_src, quote[:40]
    return quote

Q = {
    "h1": q("# DEM多面体颗粒与冰-结构混合模式失效验证面"),
    "geo": q("- 多面体颗粒：正二十面体（12顶点），半径0.01m，密度1000 kg/m³"),
    "ice": q("- 冰参数：σ_c=3 MPa, σ_f=0.7 MPa, σ_t=0.7 MPa, h=1.0 m, E=5 GPa"),
    "gjk": q("- GJK/EPA算法（已有convex_contact模块）"),
    "crush": q("- 压溃：R_crush = 2.5·σ_c·h·D·f(V), f(V)=min(1+0.3V, 1.5)"),
    "c1": q("| C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） |"),
    "c4": q("| C4 | V_c vs Timco<30% | PASS | V_c_model=1.3 m/s, V_c_timco=2.76 m/s |"),
    "c5": q("| C5 | 阻力vs Lindqvist<20% | PASS | R_model=70.9 MN, R_lindqvist=1.1 MN |"),
    "tests": q("- 总测试数：35"),
    "vc": q("| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |"),
    "fig": q("（本任务为验证面实现，无数值场云图。相图和力链分布通过测试验证。）"),
    "lim": q("1. 简化DEM显式时间积分；精确量化预测需更高级积分器"),
    "scope": q("- 多面体颗粒：凸多面体，GJK/EPA接触检测"),
    "files": q("- `src/tensordem/polyhedron/__init__.py`: 多面体颗粒力学"),
}

# repro command (single-quoted JSON payload -> no backslashes anywhere)
REPRO = (
    'TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/auth/login" -H \'Content-Type: application/json\' '
    '-d "{\\"username\\":\\"$TENSOR_AGENT_USER\\",\\"password\\":\\"$TENSOR_AGENT_PASS\\"}" '
    "| python3 -c 'import sys,json;print(json.load(sys.stdin)[\"access_token\"])') "
    '&& curl -s "$TENSOR_API_BASE/tensor/reports/11557" -H "Authorization: Bearer $TOKEN" '
    '-o /tmp/r11557.json '
    '&& python3 scripts/kf_register_11557.py /tmp/r11557.json docs/kf/wp-11557-01'
)

json_block = "```json\n" + json.dumps(env, ensure_ascii=False, indent=2) + "\n```"

report = f"""# KF-RESULT wp-11557-01

## ① 本工序做了什么

本单是报告→知识产线的 **01-asset-registration** 工序，锚点 KBM-RCI-F1-FACTORY，只处理 report_id=11557（{Q['h1'][2:]}，scenario_key=P180W2-N05，1953 字符）。做了且只做了三件事：

1. 从平台接口取回 report_id=11557 的 `markdown` 字段，本地重算 sha256 并与契约哈希比对——**一致**（`sha256:471f8b21…ae78b1cb3`，1953 字符与契约一致）。
2. 登记源资产清单 `asset_manifest.json`：11 项资产（9 项 resolved_in_source、1 项 referenced_unresolved、1 项 declared_absent），每项带可解析定位器（char_span/行号/逐字引文）。
3. 按契约 notes **不做抽取**：claims 为空数组；未把任何结论标成 verified（verification 由平台门计算）。

## ② 怎么做的

步骤（全部程序化，零手抄）：

1. `POST $TENSOR_API_BASE/auth/login`（$TENSOR_AGENT_USER）拿 Bearer token；`GET $TENSOR_API_BASE/tensor/reports/11557` 取 `markdown` 字段（1953 字符）。
2. 本地重算 `sha256(markdown)` = `471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3`，与契约 `source_hash` **逐位一致**；字符数 1953 与契约一致。
3. `scripts/kf_register_11557.py` 构建 `asset_manifest.json`（11 项资产，每项带 char_span/行号/逐字引文定位器）与结果信封 `kf_result.wp-11557-01.json`；脚本内断言每条引文是源 markdown 的唯一子串。
4. 用 `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验信封：0 错误；manifest 结构按 `schemas/asset_manifest.v1.schema.json` 形状核对。
5. 产物落 worktree `docs/kf/wp-11557-01/`，源 markdown 本地副本 `report_11557.md` 重算哈希与平台一致。

关键设置：定位器 method=char_span（A01 文档本体用 document）；resolution 三态 resolved_in_source / referenced_unresolved / declared_absent；不指定节点、不跑重计算（本工序纯登记）。

## ③ 产出物清单

| 文件（worktree 内） | 要点 |
|---|---|
| `docs/kf/wp-11557-01/asset_manifest.json` | 11 项资产：9 resolved_in_source、1 referenced_unresolved（TensorDEM 仓内 5 个产出文件路径）、1 declared_absent（图，报告自述无图且平台 figures=[]）；claims=[] |
| `docs/kf/wp-11557-01/kf_result.wp-11557-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），过 kf_result.v1 schema |
| `docs/kf/wp-11557-01/report_11557.md` | 源 markdown 本地副本（sha256 与平台一致） |
| `docs/kf/wp-11557-01/verification.json` | 8 项自检结果（全 true） |
| `scripts/kf_register_11557.py` | 一键复跑脚本（取数→建 manifest→自检） |

## ④ 证据定位表（claim/字段 → 原文引文片段，均逐字）

| 字段/claim | 原文引文（report_id=11557 markdown） |
|---|---|
| provenance.source_hash | 本地重算 sha256 = `471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3`（与契约一致；源文档首行：{Q['h1']}） |
| source.title | 平台 title 字段：`DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)` |
| A02 参数集 | {Q['geo']}；{Q['ice']} |
| A03 方法声明 | {Q['gjk']} |
| A04 失效公式 | {Q['crush']} |
| A05 判据表 | {Q['c1']} … {Q['c4']} … {Q['c5']} |
| A06 测试统计 | {Q['tests']}（同节：通过 35、失败 0） |
| A07 误差判定 | {Q['vc']} |
| A08 局限 | {Q['lim']} |
| A09 适用范围 | {Q['scope']} |
| A10 产出文件 | {Q['files']}（共 5 项，TensorDEM 仓内路径，本工作树不可解析→referenced_unresolved） |
| A11 图 | {Q['fig']}（平台 figures=[]） |

## ⑤ 注意点与局限

- **无图理由**：纯登记工序，无数值计算/场量，不生成图（源报告本身亦声明无图）。
- A10 的 5 个产出文件属 TensorDEM 源仓（P180W2-N05 节点），本 TensorKnowledge 工作树内不存在，如实登记为 referenced_unresolved，未伪造解析；如需 resolved 需后续工序在 TensorDEM 检出内核验。
- 源报告自述误差较大（V_c 53%、R_total 63%，均 <3% 判否），本工序只登记不评判，不覆盖其结论，也不把任何结论标成 verified。
- 未读/未写其它 report_id；未改写上游产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 信封与 manifest 均 `json.load` 通过；jsonschema(Draft 2020-12) 校验 kf_result.v1：0 错误 |
| schema_pass | ✅ | 同上（schemas/kf_result.v1.schema.json） |
| source_locator_resolvable | ✅ | 11 条引文全部为源 markdown 唯一子串，char_span 与引文逐字一致（脚本断言） |
| source_hash_matches | ✅ | 本地重算 sha256 = 契约哈希（verification.json） |
| no_duplicate_ids | ✅ | A01–A11 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（契约允许空数组；无强制造 claim） |

honest-FAIL 项：无。

**repro_cmd**（一键复跑）：
```bash
{REPRO}
```

## 结果（唯一 json 块，结构=schemas/kf_result.v1.schema.json）

{json_block}
"""

open("docs/kf/wp-11557-01/KF-RESULT-wp-11557-01.md", "w").write(report)
print("report written:", len(report), "chars")
print("json blocks:", report.count("```json"))
