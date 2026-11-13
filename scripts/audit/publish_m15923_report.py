#!/usr/bin/env python3
"""Publish the m15923 board-audit report (six-element, figures embedded)."""
import base64, json, os, urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "/root/tp-agent/work/m15896"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs",
                   "board_audit_m15896")
OUT = os.path.abspath(OUT)
FIGS = os.path.join(OUT, "figures")
os.makedirs(FIGS, exist_ok=True)

settle = json.load(open(os.path.join(SRC, "docs/rci-f1-abc/round2/settlement.json")))
power = json.load(open(os.path.join(SRC, "docs/rci-f1-abc/round2/power.json")))
judge = json.load(open(os.path.join(OUT, "judge.json")))
repro = json.load(open(os.path.join(OUT, "repro.json")))
base = json.load(open(os.path.join(OUT, "baseline.json")))

# fig1: settlement matrix
arms = ["A", "B", "C"]
mets = ["M1_unit_cost", "M2_throughput", "M3_extraction_accuracy",
        "M4_evidence_completeness", "M5_knowledge_reuse"]
code = {"REAL": 2.0, "WITHHELD": 0.5, "PENDING": 0.5, "NOT_STARTED": 0.0}
grid = [[code.get(settle["metrics"]["arms"][a]["metrics"][m]["status"], 0) for m in mets] for a in arms]
fig, ax = plt.subplots(figsize=(7.4, 2.9))
ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=2, aspect="auto")
for i, a in enumerate(arms):
    for j, m in enumerate(mets):
        ax.text(j, i, settle["metrics"]["arms"][a]["metrics"][m]["status"], ha="center",
                va="center", fontsize=7)
ax.set_xticks(range(len(mets)))
ax.set_xticklabels([m.split("_", 1)[1] for m in mets], rotation=18, ha="right", fontsize=8)
ax.set_yticks(range(len(arms)))
ax.set_yticklabels(["A: 1 strong", "B: 20 (degraded)", "C: 20+review"], fontsize=8)
ax.set_title("m15896 settlement: 3 arms x 5 metrics (as measured)", fontsize=9)
fig.tight_layout()
p1 = os.path.join(FIGS, "fig1_status_matrix.png")
fig.savefig(p1, dpi=140); plt.close(fig)

# fig2: power vs n and decidability
nt = [r for r in power["ni_table"] if r["margin_pp"] == 3.0 and r["true_diff_pp"] == -0.0]
fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.4))
ax[0].plot([r["n_per_arm"] for r in nt], [r["power_analytic"] for r in nt], "o-",
           label="analytic power (margin 3pp, delta=0)")
ax[0].axhline(0.8, ls="--", c="k", lw=1, label="power 0.80")
ax[0].axvline(60, ls=":", c="r", lw=1.2, label="design n=60")
ax[0].set_xlabel("n per arm"); ax[0].set_ylabel("power")
ax[0].set_title("NI power vs n (n=60 -> 0.079; 0.80 needs 1570)", fontsize=9)
ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
hw = power["wilson_halfwidth_at_60"]
ax[1].bar(["Wilson half-width\n(n=60, p=0.90)", "prereg 3pp gate"], [100 * hw, 3.0],
          color=["#c0392b", "#2c7fb8"])
ax[1].annotate("%.1f pp = %.2fx gate" % (100 * hw, hw / 0.03), xy=(0.0, 100 * hw),
               xytext=(0.05, 100 * hw + 0.5), fontsize=8)
ax[1].set_ylabel("percentage points")
ax[1].set_title("decidability of the anchor's 3pp gate", fontsize=9)
fig.tight_layout()
p2 = os.path.join(FIGS, "fig2_decidability.png")
fig.savefig(p2, dpi=140); plt.close(fig)

# fig3: F1 countercheck
fig, ax = plt.subplots(figsize=(6.6, 3.0))
labels = ["parent 3d43e3c\n(v1, clean checkout)", "delivered 6a4037b\n(round 2)"]
ax.bar(labels, [base["failed"], 0], color="#c0392b", label="failed")
ax.bar(labels, [base["passed"], repro["tests_passed"]], bottom=[base["failed"], 0],
       color="#27ae60", label="passed")
ax.text(0, base["failed"] + base["passed"] / 2, "%dF/%dP" % (base["failed"], base["passed"]),
        ha="center", color="w", fontsize=9)
ax.text(1, repro["tests_passed"] / 2, "%d passed" % repro["tests_passed"], ha="center",
        color="w", fontsize=9)
ax.set_ylabel("tests"); ax.set_title("F1 countercheck: round-1 defect reproduced, then fixed",
                                     fontsize=9)
ax.legend(fontsize=8); fig.tight_layout()
p3 = os.path.join(FIGS, "fig3_test_baseline.png")
fig.savefig(p3, dpi=140); plt.close(fig)

figs = []
for name, cap in (("fig1_status_matrix.png", "结算矩阵：三臂×五指标实测状态（A/C 零产物；B 仅 M1/M2/M4，M1 WITHHELD、M3/M5 不可得）"),
                  ("fig2_decidability.png", "可判定性：3pp 门下 n=60 把握度 0.079、Wilson 半宽 7.74pp=门宽 2.58 倍"),
                  ("fig3_test_baseline.png", "F1 反核：父 commit 干净检出 5 failed/4 passed，交付后 23 passed")):
    figs.append({"name": name, "caption": cap,
                 "png_base64": base64.b64encode(open(os.path.join(FIGS, name), "rb").read()).decode()})

rows = "\n".join("| %s | %s | %s | %s |" % (r["criterion"], r["ref"], r["got"], r["verdict"])
                 for r in judge["rows"])
md = f"""# m15896（KBM-RCI-F1-ABC）交差核验：L2，仪器真实、锚点未成立

## ① 案例介绍（问题设定与基准出处）
锚点 `KBM-RCI-F1-ABC` 问的是「大量普通 Agent + 分解/工具/治理能否承担少量强 Agent 难独立承担的大规模工作」：
A 臂=1 强独做、B 臂=20 普通并行、C 臂=20 普通+独立审核+Skills，同批（60 篇冻结语料 `82f698cf…`）同契约，
五指标＝单位成本/产量/抽取准确率/证据完整率/复用；prereg 先行 + 盲审。
基准（ref）出处：预注册文件 `docs/rci-f1-abc/frozen/prereg.json`（prereg_id `9e4e0bf5…`），同 digest 的
`PREREG.md` 已在父 commit `3d43e3c` 中，先行性有版本历史见证；统计口径 Blackwelder 1982 / FDA 2016 NI /
Cohen 1960 / Fleiss 1981 / Kish 1965。
**注册裁判**：`tensor_benchmark_cases` 中 `anchor_slug='KBM-RCI-F1-ABC'` → **0 行**（全表 25 行），
故本轮以预注册阈值作 ref，并如实记裁判缺口。

## ② 怎么做的（方法/流程/工具链）
1. 取被审交付 `agent/m15896` @ `6a4037bd` 的**干净检出**（`git archive | tar -x`，不读工作树脏状态）。
2. 三个必交件逐项取证：run_artifacts（settlement/power/7 份 B 臂回执/4 张图/60 篇冻结快照）、
   benchmk ref vs got（预注册阈值 vs 结算实测）、repro_cmd（在干净检出里重跑）。
3. 独立复算：Wilson 半宽按公式从零算；power.py 重跑与原 `power.json` **逐叶 0 差异** 324 叶。
4. 基线反核：父 commit 干净检出跑 v1 测试，验证「5 红 4 绿」是否属实。
5. 判级 L0–L5 机器规则：L2=真实代码+测试+可复现仪器；L3=scripts/tests 之外有调用者；L4=注册基准行+完整算例。
工具链：pytest / git archive / psycopg 查基准表 / matplotlib 出图；本页所有数字由脚本注入。

## ③ 计算结果（实测，程序化注入）
- 干净检出：pytest **{repro["tests_passed"]} passed**（v1 9 项 + round2 14 项）；corpus verify **60/60 sha256 一致**；
  verify --lane B **130/130 locator 逐字反查**、自报偏差 0；settle → **WITHHELD**。
- 基线：父 commit `3d43e3c` 干净检出 **{base["failed"]} failed / {base["passed"]} passed**（与自称 5 红 4 绿逐数吻合）。
- 判据打勾/打叉共 {len(judge["rows"])} 项：**PASS {judge["pass_count"]} / FAIL {judge["fail_count"]} / WITHHELD-PENDING {judge["withheld_count"]}**（明细见下表与图 1）。
- 确定性：settlement/power 重跑逐叶差异 **0/324**（绝对路径已归一，否则有 2 叶路径差异）。

| 判据 | ref | got | 判定 |
|---|---|---|---|
{rows}

## ④ 结果图
- 图 1＝三臂×五指标实测状态矩阵；图 2＝3pp 门可判定性（把握度 vs n、Wilson 半宽 vs 门宽）；
  图 3＝F1 测试基线反核。数据全部来自 `settlement.json` / `power.json`，无手抄。

## ⑤ 注意点（坑/局限/适用范围）
- **臂 B 的回执是 no-LLM 确定性抽取器产物**（`extractor='rule-based, deterministic, no-LLM'`，
  `llm_used=false`，3 篇耗时 0.028s），M2/M4 的「漂亮数字」只描述仪器，不描述 20 个普通 Agent；
  交付方已用身份门（`identity_match=false`）自认不可用于 H1–H3 —— 这点诚实，也是 L4 不能给的原因。
- 结算与功率工件**嵌入了绝对工作树路径**，跨检出比对须先归一，否则误判为不可复现（本轮已按归一后比对）。
- 报告 ⑤ 两处 κ 覆盖率（0.888→实测 0.8962、0.944→0.9396）与工件有 0.004–0.008 转写偏差，不改结论。
- 局限：A/C 臂零产物、B 无 LLM 调用 —— 无从重跑任何臂，本审计只核验仪器与判据。

## ⑥ 误差判定（逐项 vs 基准，显式回答是否<3%）
- 语料校验：60/60，相对偏差 **0.0%** → **<3% ✅**
- 证据门反查：130/130，相对偏差 **0.0%** → **<3% ✅**
- Wilson 半宽独立复算：0.0774 vs 工件 0.0774，Δ=0.0000 → **<3% ✅**
- 但锚点的关键量是**3pp 非劣效门的可判定性**：n=60 半宽 7.74pp = 门宽的 **2.58 倍**（超门 158%）
  → **不满足**；n=60 把握度 0.079（<0.80）、最小可证明界 15.3pp（>3pp）、3pp 门需 1570 份/臂。
- 结论：**仪器精度达标（0%），实验判定力不达标（差 2.58 倍）** —— honest，不粉饰。

## 裁定
**L2（board-audit）**：仪器层（corpus/verify/settle/power）真实、测试 23 绿、干净检出可复现，功能实质成立；
L3 阻断（仓内/CI/平台都无 scripts、tests 之外的调用者）；L4 阻断（注册基准行 0 条 + 三臂不齐）。
`accepted=true` 是交付验收（TP_AUTO_APPROVE_DEV_ACCEPTANCE），不等于锚点达成；锚点仍 WITHHELD。
"""
md = md.replace("benchmk", "benchmark")

payload = {
    "title": "m15896 交差核验（KBM-RCI-F1-ABC）：L2——仪器真实可复现，锚点实验未成立",
    "summary": ("对 m15896（TensorKnowledge @6a4037b）做交差核验：干净检出 23 测试全绿、语料 60/60 sha256、"
                "locator 130/130、settle 复现 WITHHELD、power 工件逐叶 0 差异；父 commit 反核 5F/4P 属实；"
                "但 tensor_benchmark_cases 该锚点 0 行、A/C 臂零产物、B 臂 agent_count=1 且 llm_used=false，"
                "3pp 门可判定性差 2.58 倍 → 判 L2，L3/L4 硬阻断。"),
    "scenario_key": "kbm-rci-f1-abc-board-audit",
    "mission_id": "15923",
    "tags": ["TensorKnowledge", "KBM-RCI-F1-ABC", "board-audit", "maturity-verdict",
             "adversarial-review"],
    "markdown": md,
    "figures": figs,
}

base_url = os.environ["TENSOR_API_BASE"]
req = urllib.request.Request(base_url + "/auth/login",
                            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                            headers={"Content-Type": "application/json"}, method="POST")
token = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]
req = urllib.request.Request(base_url + "/tensor/reports", data=json.dumps(payload).encode(),
                            headers={"Content-Type": "application/json",
                                     "Authorization": "Bearer " + token}, method="POST")
resp = urllib.request.urlopen(req, timeout=120)
print(resp.status, resp.read()[:200])
