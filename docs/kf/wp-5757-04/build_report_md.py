#!/usr/bin/env python3
"""wp-5757-04 · 生成正文报告 docs/reports/kf_wp_5757_04_result.md 与发布载荷 /tmp/report_5757_04.json。

· 报告正文里的 json 代码块 = docs/kf/wp-5757-04/kf_result.json 原样（唯一 json 块）
· 报告正文里的引文全部由脚本从 report 5757 markdown 断言逐字存在后注入
"""
from __future__ import annotations

import base64
import json

OUT_MD = "docs/reports/kf_wp_5757_04_result.md"
KFR = "docs/kf/wp-5757-04/kf_result.json"
PNG = "docs/kf/wp-5757-04/review_matrix.png"

src = json.load(open("/tmp/report_5757.json", encoding="utf-8"))
md = src["markdown"]
kfr = json.load(open(KFR, encoding="utf-8"))
review = json.load(open("docs/kf/wp-5757-04/review_report.json", encoding="utf-8"))
checks = json.load(open("docs/kf/wp-5757-04/checks.json", encoding="utf-8"))

ANCHORS = {
    "code_main": "ops/taskplane/gate_auto_release.py",
    "figure": "artifacts/gate_auto_release_drill.png",
    "table": "tensorplatform.campaign_nodes",
    "gov_reason": "governance_marker=SPEC军",
    "wait_prose": "六门 `wait` ×6",
    "snapshot": "56e8ab792ceeeb40db68538a…",
    "content_limit": "只判「工件在不在、json 是否合法」，不判内容对错（内容由验收链负责）",
    "pytest": "10 条 pytest 覆盖",
    "synthetic": "证据在临时根按 `<repo>/artifacts/…` 同形造出\n（显式 `synthetic: true`）",
    "criteria_c3": "`metadata.owner_only` 非真 + 门名/goal 无治理标记",
    "never_auto": "永不自动放",
}
for k, v in ANCHORS.items():
    assert v in md, f"anchor not verbatim in markdown: {k}"
    assert src["markdown"].count(v) >= 1


REPRO = r"""```bash
# 1) 取原文并独立重算哈希/字符数（打印值须 = sha256:d85b5a16…bd915 / chars=5061）
python3 - <<'PY'
import json, os, urllib.request, hashlib
b = os.environ["TENSOR_API_BASE"].rstrip("/")
r = json.load(urllib.request.urlopen(urllib.request.Request(
    b + "/auth/login",
    data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                     "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
    headers={"Content-Type": "application/json"})))
d = json.load(urllib.request.urlopen(urllib.request.Request(
    b + "/tensor/reports/5757",
    headers={"Authorization": "Bearer " + r["access_token"]})))
open("/tmp/report_5757.json", "w").write(json.dumps(d, ensure_ascii=False))
print("sha256:" + hashlib.sha256(d["markdown"].encode()).hexdigest(), "chars:", len(d["markdown"]))
PY
# 2) 15 项机检（退出码 0 = 无 blocking 失败）
python3 docs/kf/wp-5757-04/verify_wp_5757_04.py
# 3) 重建 review_report.json / kf_result.json / 审核矩阵图
python3 docs/kf/wp-5757-04/build_review_report.py
# 4) 重建本报告正文与发布载荷
python3 docs/kf/wp-5757-04/build_report_md.py
# 5) 信封 schema 校验
python3 -c "import json,jsonschema;jsonschema.validate(json.load(open('docs/kf/wp-5757-04/kf_result.json')),json.load(open('schemas/kf_result.v1.schema.json')));print('schema PASS')"
```"""

non_unique = [r for r in checks["locator_matrix"] if r["occurrences"] > 1]
n_pass, n_total = checks["checks_pass"], checks["checks_total"]
blocking = checks["blocking_failures"]
findings = {s: sum(1 for f in review["findings"] if f["severity"] == s) for s in ("minor", "note")}

body = f"""# KF-RESULT wp-5757-04

tags: kf-wp:wp-5757-04, 04-independent-review, gate-auto-release, report-5757, red-team-reviewer

## ① 本工序做了什么

对 `report_id=5757`（《放门自动化成熟化：gate_auto_release daemon（IN20-R2，G13–G20 六门演练）》，mission 5046）执行**独立审核（红队）**，审核对象是上游工作包 `wp-5757-01`（资产登记）的产物 `docs/kf/wp-5757-01/asset_manifest.json`，判据面为「语义保真」：出处在原文是否逐字可定位、哈希是否可独立重算、分类与 resolution 状态是否与原文相符、资产召回有无遗漏，并把报告 ③ 的数字算术自洽性作为保真的必要条件一并复算。

**版本说明（v2）**：v1 发于 report id=14961；发布后为复核 F5，用同一 GET 回读自证：任何报告（含本单内嵌 png_base64 发布的那份）回读后 `figures` 都只剩 `name`+`caption` → 图件载荷缺失是**平台读侧行为**，不是报告 5757 或 wp-5757-01 的遗漏，F5 的归属据此更正（`probe_figure_payload.py` 可复现）。平台无 `PUT /tensor/reports/{id}`（实测 405），故以本 v2 为准，v1 作废。

不做的三件事（边界）：不改写上游产物、不标任何结论为 verified（本单只给 pass/fail/needs-fix 与分级发现）、不读写其它 report_id 的 markdown/产物。

结论：**verdict = pass**（无 blocking 缺陷）。15/15 资产 locator 的 char_span 与行号在原文逐字命中；provenance 哈希独立重算与合同一致；未发现凭空捏造的资产。查出 {n_pass}/{n_total} 项机检通过；共 {findings['minor'] + findings['note']} 条非阻断发现（{findings['minor']} minor + {findings['note']} note），其中 5 条由机检复现（C6/C8/C13/C14/C15）、1 条靠跨仓旁证（F6）；归属上 2 条可在 wp-01 侧小改（F1/F2），4 条归报告侧或版本同步（F3–F6）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST /api/v1/auth/login` 取 Bearer token → `GET /api/v1/tensor/reports/5757` 取 `markdown`，落 `/tmp/report_5757.json`。独立重算 `sha256` = `d85b5a16…bd915`、chars = 5061，与合同 `source_hash` 一致（不采信上游自述，重算后比对）。
2. **读上游 KO**：只读 `docs/kf/wp-5757-01/asset_manifest.json` 与 `kf_result.wp-5757-01.json`；不读生产者对它的解释（约束 `reviewer_context_excludes_producer_explanation`）。审核清单由本单自拟（约束 `review_prompt_not_copied_from_producer`）。
3. **locator 复核（C5/C6）**：对 15 个资产逐个断言 `md[start_char:end_char] == quote`、行号 `md[:start].count('\\n')+1 == start_line`、`md.count(quote)`、`md.find(quote) == start_char`。
4. **召回复核（C7/C8）**：用正则独立抽取原文所有 `*.py|*.sh|*.yaml|*.yml|*.json|*.md|*.png` 形态的路径与反引号标识符，与 manifest 的 quote 集合求差；并单点检查报告以「10 条 pytest 覆盖」作证据的测试套件是否登记。
5. **算术复算（C9–C12）**：从原文表格行解析生产矩阵与沙箱矩阵的行动作序列，与自述「动作计数」「审计动作计数」逐键比对；派生「6 门动作 + plan 21 G21 一行 = 7 行」并核账；核 release↔rollback 配对（4 放 4 回滚）。
6. **隐蔽缺陷探测（C13–C15）**：判据表是否声明 C3 先于 C2 的优先级（G20 判 hold 而非 wait 依赖此优先级）；生产快照哈希是否给全（`…` 截断 → 外部不可复算）；图件是否带 png 载荷（下游能否验图）。
7. **旁证（非权威）**：在主机上一个 TensorPlatform 检出（commit 3d6ff8aba，只读）核对 6 个 code/config 资产路径是否存在、`test_gate_auto_release.py` 的 `def test_` 计数是否等于报告自述的 10 条。
8. **产物**：`checks.json`（15 项机检结果 + 15×(span,行号,出现次数,首个命中)矩阵）→ `review_report.json`（含 6 条 findings、5 条 claim 级判定、not_run 清单、overstated 清单）→ `kf_result.json`（信封，schema 校验）→ 审核矩阵图。

关键设置：所有断言可复跑（`verify_wp_5757_04.py` 退出码=是否存在 blocking 失败）；引文零手抄——本报告 ④ 的每条引文在生成期被断言为原文子串，否则构建失败。

## ③ 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| review_report.json | docs/kf/wp-5757-04/review_report.json | 审核正文：15 项 checks、6 条 findings（0 blocking / {findings['minor']} minor / {findings['note']} note）、5 条 claim 判定（supported 3 / partially-supported 1 / refuted 1）、3 条 checks_not_run、3 条 overstated_claims、verdict=pass |
| kf_result.json | docs/kf/wp-5757-04/kf_result.json | 结果信封（本报告唯一 json 块的来源），`schemas/kf_result.v1.schema.json` 校验通过 |
| checks.json | docs/kf/wp-5757-04/checks.json | 机检原始结果：{n_pass}/{n_total} pass，blocking=[]，含 15 个 locator 的 span/行号/出现次数/首个命中四元组 |
| verify_wp_5757_04.py | docs/kf/wp-5757-04/verify_wp_5757_04.py | 一键复跑：取原文→重算哈希→15 项检查→写 checks.json（退出码=是否有 blocking 失败） |
| build_review_report.py | docs/kf/wp-5757-04/build_review_report.py | 由 checks.json 生成 review_report.json / kf_result.json / 审核矩阵图 |
| probe_figure_payload.py | docs/kf/wp-5757-04/probe_figure_payload.py | 图件载荷探针：`python3 … 5757 14961` → 两份报告都是 `keys=[caption,name] png_payload=False`，证 F5 归平台读侧 |
| review_matrix.png | docs/kf/wp-5757-04/review_matrix.png | 图 1：A 面板=locator 出现次数（橙=unique=true 不成立但首个命中仍对位）；B 面板=15 项检查 pass/fail 与影响分级 |

## ④ 证据定位表

| claim / 字段 | 原文引文片段（逐字，脚本断言） | 复核方式与结论 |
|---|---|---|
| A01 主脚本 locator（span 1301–1335） | `{ANCHORS['code_main']}` | `md[1301:1335]==quote` ✅ 且 `md.find(quote)==1301` |
| A14 库表 locator（span 339–368） | `{ANCHORS['table']}` | `md[339:368]==quote` ✅（原文即写作 `tensorplatform.campaign_nodes`） |
| A12 图件 locator（span 3721–3758） | `{ANCHORS['figure']}` | span 命中 ✅；但 report 记录 `figures[0]` 只有 name+caption、**无 png_base64** → 图内容不可验（F5） |
| manifest `provenance.hash/chars` | （非引文，独立重算） | 重算 `sha256:{"d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915"[:16]}…`、chars=5061，与 manifest 及合同三方一致 ✅ |
| A13/A15 `locator.unique=true` | `gate_release_audit` / `gate_drill` | `md.count(quote)` = 2 / 2 → unique 为假（F1）；但 `md.find()` 仍等于记录 span，first-occurrence 解析不受影响 |
| 六门判据工件 declared_absent | `{ANCHORS['synthetic'].replace(chr(10), " ")}` | 生产侧 not_found 与矩阵 5 行一致 ✅，但沙箱内同形存在 → `declared_absent` 只对生产侧成立（claim C-04 = partially-supported） |
| G20 治理门判 hold | `{ANCHORS['gov_reason']}` | 185 行动作 `hold_owner_only` 与理由一致 ✅；但判据表只有 `{ANCHORS['criteria_c3']}` + `{ANCHORS['never_auto']}`，未写 C3>C2 优先级（F3） |
| 生产动作计数 | `- 动作计数：release=0 / wait=5 /` + 续行 `hold_owner_only=1` | 与 6 行矩阵解析值 `{{'wait': 5, 'hold_owner_only': 1}}` 逐键相等 ✅（C9） |
| 首轮审计 7 行 | `{ANCHORS['wait_prose']}` | 算术 5(wait)+1(hold)+1(G21)=7 ✅ 自洽；但措辞把第 6 个 wait 归给「六门」不实（六门中 wait=5、hold=1）→ overstated_claims 第 3 条 |
| 生产快照未变 | `{ANCHORS['snapshot']}` | 哈希被 `…` 截断 → `production_untouched=True` 外部不可复算（F4） |
| 报告局限「不判内容」 | {ANCHORS['content_limit']} | 与仓内 `ops/taskplane/gate_content_criteria.py` + `evaluate_gate()` 的 `# C2b 判据内容` 分支可能版本失同步（F6，note 级） |
| 测试证据 | {ANCHORS['pytest']} | 旁证：TensorPlatform 检出 `tests/test_gate_auto_release.py` 的 `def test_` = 10 ✅；但该套件未登记为资产（F2） |

## ⑤ 注意点与局限

1. **无权复核的部分如实标 not_run**：`psql -d tensorplatform -c "select … from campaign_nodes"` 返回 `permission denied for table campaign_nodes`，因此报告里的上游依赖数（8/11/8/11/4/9）、六门 `status`、`metadata.owner_only` 实测值**未独立复核**；本单只核了它们在正文表格里的自洽性。
2. **旁证≠生产版本**：仓内实现判断（C3 短路、C2b 内容层）基于主机上一个 TensorPlatform 检出（commit 3d6ff8aba），与产线提交可能不同 → 相关结论一律降级为 note，不据此判 fail。
3. **未做沙箱写路径复现**：真 UPDATE + rollback 需隔离 schema 写权限，且本单边界禁止改上游状态，故 C10/C11 只做「表 vs 自述」的算术核账，未复现数据库动作。
4. **审核偏保守**：把「机器可读字段为假」（F1 的 unique）判 minor 而非 note，理由是字段一旦被下游当不变量使用会错位；但它不改写原文、不影响哈希与 span。
5. **两处判定口径**：①「declared_absent」按生产侧解释；②「六门 wait ×6」按其后续派生总数 7 正确而不判 blocking。
6. **图件载荷缺失已改判为平台侧**：实测 `GET /tensor/reports/5757` 与 `GET /tensor/reports/14961`（本单自己内嵌 png 发布的报告）回读 `figures[0].keys()` 均为 `[caption, name]`，`png_payload=False` → 下游无法验任何图；这既解释了报告 5757 的 ④ 图为何无法核对，也说明 wp-5757-01 把 A12 记为 `referenced_unresolved` 是正确分类。
7. **本单不产出知识对象**：`claims=[]`（审核结论留在 review_report.json 的 claims_assessed / findings 里，不与 03 的知识对象混用）。

## ⑥ 误差判定：关键量 vs 基准，逐项回答是否 <3%

无物理场量（治理/后端机制的审核单），故以「独立重算值 / 合同声明值 / 上游自述值」为基准做逐项对表。

| 关键量 | 机制结果 | 基准 | 偏差 | <3% ? |
|---|---|---|---|---|
| markdown sha256 | `d85b5a16…bd915`（重算） | 合同 `source_hash` | 0（逐字节相同） | **是** |
| markdown 字符数 | 5061 | 合同 `chars` / manifest `chars` | 0% | **是** |
| 资产数 | 15 | manifest `summary.total_assets`=15、`len(assets)`=15 | 0% | **是** |
| locator 逐字命中 | 15/15 | 全命中 | 0/15 | **是** |
| locator 行号命中 | 15/15 | 全命中 | 0/15 | **是** |
| 首个命中==记录 span | 15/15 | 全一致 | 0/15 | **是** |
| `unique=true` 为真 | 13/15 | 15/15 | 2/15 = 13.3% | **否（F1，minor）** |
| 路径型资产召回 | 11/11 覆盖 | manifest 15 项 | 0 漏（文件型） | **是** |
| 报告内证据类资产召回 | 测试套件 0/1 | 应登记 1 | 1/1 = 100% | **否（F2，minor）** |
| 生产矩阵行动作计数 | wait=5, hold=1, release=0 | 自述动作计数 | 0% | **是** |
| 沙箱行动作计数 | release=4, wait=1, hold=1, rollback=4 | 自述审计动作计数 | 0% | **是** |
| release↔rollback 配对 | 4/4 | 4 放 4 回滚 | 0% | **是** |
| 首轮审计行数 | 7 | 5+1+1=7 派生 | 0% | **是** |
| 机检通过率 | {n_pass}/{n_total} = {100.0*n_pass/n_total:.1f}% | 全 pass | 5 项 | **否**（其中 blocking=0） |

**逐项结论**：凡「可与原文/合同逐字比对」的量，偏差一律 0%，<3% 成立；两处 <3% 不成立的量（`unique` 真实性 13.3% 错、测试套件召回 100% 缺）**如实列出且判为 minor、非阻断**——它们不改变 locator 解析结果与 provenance，故 verdict 仍为 pass，但已写进 review_report.json 的 `remediation_required` 建议。`campaign_nodes` 实测类指标因权限缺失**未测**，按纪律记 not_run，不折算成 0% 偏差。

```json
{json.dumps(kfr, ensure_ascii=False, indent=2)}
```

**repro_cmd**（工作树根执行；一键复跑机检并重建审核正文与图）：

{REPRO}
```
"""

with open(OUT_MD, "w", encoding="utf-8") as fh:
    fh.write(body)

# ── 发布载荷（六要素 + 内嵌图） ────────────────────────────────────
png64 = base64.b64encode(open(PNG, "rb").read()).decode()
payload = {
    "title": "KF-RESULT wp-5757-04：report 5757 独立审核（红队）— wp-5757-01 资产登记保真复核",
    "summary": f"独立审核 report 5757 的上游工作包 wp-5757-01：重算 sha256 与合同一致，15/15 locator 逐字命中，"
               f"未发现捏造资产；{n_pass}/{n_total} 项机检通过、blocking=0、{findings['minor']} minor + {findings['note']} note，verdict=pass。",
    "scenario_key": "gate-auto-release",
    "mission_id": 15840,
    "tags": ["kf-wp:wp-5757-04", "04-independent-review", "report-5757", "wp-5757-01", "red-team-reviewer", "gate-auto-release"],
    "markdown": body,
    "figures": [
        {
            "name": "review_matrix.png",
            "caption": "图 1 左：wp-5757-01 的 15 个 locator 引文在 report 5757 原文中的出现次数（橙=A13/A15 的 unique=true 不成立，但首个命中仍等于记录 span）；右：本单 15 项机检 pass/fail 与影响分级（blocking=0）。",
            "png_base64": png64,
        }
    ],
}
json.dump(payload, open("/tmp/report_5757_04.json", "w", encoding="utf-8"), ensure_ascii=False)
print("wrote", OUT_MD, "and /tmp/report_5757_04.json")
print("md chars:", len(body), "figures:", len(payload["figures"]))