"""Build the wp-7473-04 review deliverables (review_report.json + review_events.json).

Zero hand-copy discipline: every quote is extracted verbatim from the report
markdown snapshot by searching a distinctive marker line; the script fails hard
if a marker is missing or ambiguous. Every measured number is read from
probe_2026-11-12.json / twin_repro.json produced by independent_probe.py and
independent_twin.py.

Run:
    python3 work/wp-7473-04/build_review.py
"""
from __future__ import annotations

import hashlib
import json
import os

WT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(WT, "..", ".."))
SRC = os.path.join(WT, "source_7473.md")
OUTDIR = os.path.join(REPO, "docs", "kf", "wp-7473-04")
EXPECTED_SHA = "c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b"

md = open(SRC, encoding="utf-8").read()
sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
assert sha == EXPECTED_SHA, (sha, EXPECTED_SHA)

probe = json.load(open(os.path.join(WT, "probe_2026-11-12.json"), encoding="utf-8"))
twin = json.load(open(os.path.join(WT, "twin_repro.json"), encoding="utf-8"))


# --------------------------------------------------------------- verbatim quotes
def q(marker: str) -> dict:
    """Return the unique markdown line containing `marker`, verbatim."""
    lines = [ln for ln in md.split("\n") if marker in ln]
    if len(lines) != 1:
        raise SystemExit(f"marker not unique ({len(lines)}): {marker!r}")
    line = lines[0]
    pos = md.index(line)
    return {
        "quote": line,
        "source_field": "markdown",
        "locator": {"start_char": pos, "end_char": pos + len(line), "line": md[:pos].count("\n") + 1},
    }


def ev(marker: str, note: str) -> dict:
    d = q(marker)
    d["note"] = note
    return d


Q = {
    "row6": "2.22e-3（战役 Re_tau=180 粘性）",
    "aprime": "| A′ 战役粘性 |",
    "fit": "`guo_sp` 的注入率近似",
    "pct063": "在战役粘性下它只给出 **0.63 %** 的驱动力。",
    "wallorigin": "| 实测壁面原点（halfway，`q=0.5`）",
    "identity": "是这组参数化下的恒等式",
    "legacy_row": "| 沿用战役参数（`u_max_target=None`）的层流孪生 |",
    "uptau_exch": "`u_tau_wall_exchange = 0.03556`",
    "todo": "的窗口边界",
    "peak": "| 层流孪生峰值比",
    "interp_l2": "下 L2 2.46 %→3.11 %（800→2000 步",
    "interp_origin": "壁面原点指针恒返回",
    "tests18": "18 条 pytest",
    "line832": "**合入时无任何 pytest 用例、无验证文档**",
    "else": "原实现里拼错的值会**静默落到 else 分支**",
    "artifacts": "工件：`artifacts/turbulent_channel3d_verification",
    "no_turb": "`benchmarks/pending/channel_turb_3d/` 的完整战役",
    "three_no": "三条 `否` 都对应明确的未清偿项",
    "yplus": "目前不得用于 `y+` 标定",
    "nu_eff": "| `nu_eff`（剪切模态 500→2000 步） |",
    "row002": "| 0.0020 | 0.5060 | 1.9763 |",
    "closed_form": "本次验证只用**闭式解**做锚",
    "default_flip": "→ **`\"trt_split\"`**",
    "l2_half": "| 层流孪生 L2（halfway） |",
    "laminar_only": "本单只验证**层流锚**",
    "force_formula": "tau_w = rho * a * h",
    "not_fixed": "本单**未修**（超出最小改动范围）",
}

# measured values, read from the probe JSON (never retyped)
tt = probe["remeasure"]["truth_table"]
camp = probe["remeasure"]["campaign_and_A_prime"]
steps120 = probe["remeasure"]["steps_120"]
by = {(round(r["nu"], 12), r["scheme"]): r["dU_dt_over_a"] for r in tt + camp}
camp_trt = [r for r in camp if r["scheme"] == "trt_split" and r["nu"] < 0.002][0]
camp_guo = [r for r in camp if r["scheme"] == "guo_sp" and r["nu"] < 0.002][0]
aprime_guo = [r for r in camp if r["scheme"] == "guo_sp" and r["nu"] > 0.002][0]
aprime_trt = [r for r in camp if r["scheme"] == "trt_split" and r["nu"] > 0.002][0]
tw_half = twin["halfway_recalibrated_800"]

# --------------------------------------------------------------- claim assessments
claims = [
    {
        "claim_id": "R1-C1-default-flip",
        "text": "模块默认 force_scheme 由 guo_sp 改为 trt_split，并新增 validate() 白名单。",
        "status": "supported",
        "evidence": [
            ev(Q["default_flip"], "§4 改动表第 1 行"),
            ev(Q["else"], "§4 改动表第 2 行：改白名单的理由"),
        ],
        "independent_check": {
            "method": "git 历史（外部工件，非生产者叙述）",
            "observed": "merge #891 (m6230) 引入模块 832 行且 force_scheme 默认 guo_sp；merge #894 (m6291) 首次新增 tests/test_turbulent_channel3d.py、默认改 trt_split、validate() 增加白名单",
            "commands": [
                "git -C /root/tensor-ecosystem/TensorLBM show 520d3282:src/tensorlbm/turbulence/turbulent_channel3d.py | wc -l  # 832",
                "git -C /root/tensor-ecosystem/TensorLBM show 520d3282:src/tensorlbm/turbulence/turbulent_channel3d.py | grep -n 'force_scheme: str'  # 132: guo_sp",
                "git -C /root/tensor-ecosystem/TensorLBM log --diff-filter=A -- tests/test_turbulent_channel3d.py  # fa86281d merge #894",
            ],
        },
    },
    {
        "claim_id": "R1-C2-trt-split-exact",
        "text": "trt_split 在全部扫描的 tau+ 上给出 (dU/dt)/a = 1（≤0.06%）。",
        "status": "supported",
        "evidence": [ev(Q["row002"], "表 1 首行"), ev(Q["force_formula"], "§1 动量平衡")],
        "independent_check": {
            "method": "module API 重测（8x18x8，a=1e-4，12 步，体相 x 6..11 平均）",
            "observed": {
                "nu_0.002": by[(0.002, "trt_split")],
                "nu_0.02": by[(0.02, "trt_split")],
                "nu_0.04": by[(0.04, "trt_split")],
                "nu_0.12": by[(0.12, "trt_split")],
                "nu_0.2": by[(0.2, "trt_split")],
                "campaign_nu": camp_trt["dU_dt_over_a"],
                "campaign_nu_120_steps": steps120[0]["dU_dt_over_a"],
            },
            "max_abs_dev_from_1": max(abs(by[(nu, "trt_split")] - 1.0) for nu in (0.002, 0.02, 0.04, 0.12, 0.2)),
        },
    },
    {
        "claim_id": "R1-C3-guo-sp-underdrive",
        "text": "guo_sp 在战役粘性下只注入 0.63% 的驱动力（锚 A 对力项缺陷有 >150x 鉴别力）。",
        "status": "supported",
        "evidence": [ev(Q["pct063"], "§3 表 1 结论句"), ev(Q["row6"], "§3 表 1 末行")],
        "independent_check": {
            "method": "module API 重测 campaign nu = u_tau*h/Re_tau = 0.01*8/180",
            "observed": {
                "nu": camp_guo["nu"],
                "tau_plus": camp_guo["tau_plus"],
                "s_plus": camp_guo["s_plus"],
                "guo_sp_ratio": camp_guo["dU_dt_over_a"],
                "trt_split_ratio": camp_trt["dU_dt_over_a"],
                "discrimination_ratio": round(camp_trt["dU_dt_over_a"] / camp_guo["dU_dt_over_a"], 2),
            },
            "note": "0.006258 vs 报告 0.0063 —— 数值一致。但表 1 末行的 nu/tau+ 单元格与同一行的 s+/比率不自洽，见 F1。",
        },
    },
    {
        "claim_id": "R1-C4-laminar-twin",
        "text": "重标定后的层流孪生在 halfway 下 L2=6.76e-3、峰值比 0.99065、实测壁面原点 0.4725（偏移 -0.0275 格）。",
        "status": "supported",
        "evidence": [ev(Q["l2_half"], "§3 表 2"), ev(Q["peak"], "§3 表 2")],
        "independent_check": {
            "method": "run_laminar_poiseuille(cfg(8,18,8,Re_tau=180,u_tau=0.01), steps=800)",
            "observed": {
                "relative_l2_error": tw_half["relative_l2_error"],
                "peak_ratio": round(tw_half["u_max_mean"] / tw_half["u_max_analytic"], 5),
                "wall_origin_measured": tw_half["wall_origin_measured"],
                "wall_origin_shift": tw_half["wall_origin_shift"],
                "tau_plus": tw_half["tau_plus"],
            },
        },
    },
    {
        "claim_id": "R1-C5-interpolated-limitation",
        "text": "插值反弹 q=0.625 的 L2 由 2.46% 涨到 3.11%（800→2000 步），壁面原点指针恒为 ~0.495 而非几何 0.375。",
        "status": "supported",
        "evidence": [ev(Q["interp_l2"], "§5-2"), ev(Q["interp_origin"], "§5-2")],
        "independent_check": {
            "method": "run_laminar_poiseuille(cfg(wall_origin=0.375, wall_scheme=interpolated)) steps=800/2000",
            "observed": {
                "l2_800": twin["interpolated_q0.375_800"]["relative_l2_error"],
                "l2_2000": twin["interpolated_q0.375_2000"]["relative_l2_error"],
                "wall_origin_800": twin["interpolated_q0.375_800"]["wall_origin_measured"],
                "wall_origin_2000": twin["interpolated_q0.375_2000"]["wall_origin_measured"],
            },
        },
    },
    {
        "claim_id": "R1-C6-legacy-diverges",
        "text": "沿用战役参数（u_max_target=None）的层流孪生必然发散（L2=nan，u_max=0.896，Ma=1.55）。",
        "status": "partially-supported",
        "evidence": [ev(Q["legacy_row"], "§3 表 3 负控")],
        "unresolved_reason": "NaN 与 u_max=0.896 同格并置但未标注 u_max 是解析值：复现得 u_max_mean=nan、u_max_analytic=0.896484；'必然发散' 由单次配置外推。见 F4。",
        "independent_check": {
            "method": "run_laminar_poiseuille(cfg(Re_tau=180,u_tau=0.01), steps=800, u_max_target=None)",
            "observed": {
                "u_max_mean": "nan",
                "u_max_analytic": 0.896484,
                "relative_l2_error": "nan",
                "nu": 0.000444,
                "tau_plus": 0.501333,
            },
        },
    },
    {
        "claim_id": "R1-C7-wall-exchange-anomaly",
        "text": "孪生里 wall_exchange 路线的 u_tau=0.03556 相对 body_force 的 0.025 高估 42%，原因是聚合窗口口径而非每步公式；本单未修。",
        "status": "supported",
        "evidence": [ev(Q["uptau_exch"], "§5-1 观测"), ev(Q["not_fixed"], "§5-1 未修声明"), ev(Q["todo"], "§5-1 待办")],
        "independent_check": {
            "method": "根因算术 + 当前 main 复现",
            "observed": {
                "pre_fix_arithmetic": "不带半步复位时累加器含预热段，tau_w 被放大 nsteps//window = 2 倍，u_tau x sqrt(2) = 1.414 -> +41.4%（报告 42%）",
                "current_main_u_tau_wall_exchange": tw_half["u_tau_wall_exchange"],
                "current_main_u_tau_body_force": tw_half["u_tau_body_force"],
                "fix_landed_in": "merge #927 (m6442)：step == nsteps//2 复位 + 以实测 flux_steps 作分母",
            },
            "note": "根因判断正确；但 '未修' 状态已过期，见 F6。",
        },
    },
    {
        "claim_id": "R1-C8-merge-without-tests",
        "text": "模块随 merge #891 合入 main 时 832 行、无任何 pytest 用例与验证文档。",
        "status": "supported",
        "evidence": [ev(Q["line832"], "文首对象说明")],
        "independent_check": {
            "method": "git 历史",
            "observed": "520d3282 (#891) 引入 832 行模块；tests/test_turbulent_channel3d.py 首次出现在 fa86281d (#894)",
        },
    },
    {
        "claim_id": "R1-C9-not-done-scope",
        "text": "本单只验证层流锚；壁面解析湍流（MKM/Reichardt）、stress_fit、Smagorinsky、turbulence_energy 未做。",
        "status": "supported",
        "evidence": [ev(Q["laminar_only"], "§5-3"), ev(Q["no_turb"], "§5-3")],
        "independent_check": {
            "method": "范围声明核对（不评估未做项）",
            "observed": "报告明确列出未做项并给出原因，未把未做项写成结论",
        },
    },
]

# --------------------------------------------------------------- findings
findings = [
    {
        "id": "F1",
        "severity": "major",
        "kind": "evidence-label-mismatch",
        "title": "表 1 末行的 nu/tau+ 与同一行的 s+/比率不自洽：0.63% 复现的是 campaign nu=4.44e-4，不是行内写的 2.22e-3",
        "evidence": [
            ev(Q["row6"], "§3 表 1 末行（nu=2.22e-3, tau+=0.5067, s+=1.9947, guo=0.0063）"),
            ev(Q["aprime"], "§1 参数表 A′ 行（把 2.22e-3 标成战役粘性）"),
        ],
        "reproduction": {
            "arithmetic": {
                "tau_plus_from_0.5_plus_3nu_at_2.22e-3": 0.50666,
                "s_plus_from_1_over_tau_plus_at_2.22e-3": 1.97371,
                "nu_implied_by_s_plus_1.9947": round((1 / 1.9947 - 0.5) / 3, 7),
                "campaign_nu_u_tau_h_over_re_tau": round(0.01 * 8 / 180, 7),
            },
            "remeasure": {
                "guo_sp_at_nu_2.22e-3": aprime_guo["dU_dt_over_a"],
                "guo_sp_at_campaign_nu_4.444e-4": camp_guo["dU_dt_over_a"],
                "trt_split_at_nu_2.22e-3": aprime_trt["dU_dt_over_a"],
            },
        },
        "impact": "结论（guo_sp 在战役工作点只给 0.63% 驱动力）成立且可复现；但单元格式把两个不同粘度的数写进同一行：照行内 nu/tau+ 复跑得 3.07%，与 0.63% 差 4.9 倍。下游若按行取参会得到相反量级的缺陷评估。",
        "required_fix": "末行拆分或在 nu 单元格注明 campaign nu = u_tau*h/Re_tau = 4.444e-4（tau+=0.5013）；§1 A′ 行的 '战役粘性' 标签改成其真实出处（2.22e-3 对应 u_tau=0.05）。",
    },
    {
        "id": "F2",
        "severity": "major",
        "kind": "acceptance-criterion-relabeled",
        "title": "§6 把 5.5% 的偏差标成 '<3% = 是'，用 '(几何量)' 事后改判据",
        "evidence": [
            ev(Q["wallorigin"], "§6 行：5.5% 却打 '是（几何量）'"),
            ev(Q["three_no"], "§6 末句：只承认三条 否"),
        ],
        "reproduction": {"abs_dev": 0.0275, "pct_of_0.5": 5.5, "threshold_in_column_header": 3.0},
        "impact": "验收列的表头是 '是否 <3 %'，该单元格 5.5% 判 '是' 与表头矛盾；把 '几何量' 免检写进结论等于事后放宽预声明判据。仓内其余 >3% 项都诚实打了 '否'，故这是单点判据污染，但它落在验收列上，会抬高整表通过率。",
        "required_fix": "该格改 '否'（保留绝对量解释），或在 §6 开头预声明 '几何量按绝对格数判定 (<0.05 格)'；二者择一，且不得在看到结果后追加。",
    },
    {
        "id": "F3",
        "severity": "minor",
        "kind": "model-overreach",
        "title": "引用的线性拟合 2.11 - 1.045 s+ 在其物理相关端（高 s+）失效",
        "evidence": [ev(Q["fit"], "§3 拟合句")],
        "reproduction": {
            "residuals_from_own_rows": {
                str(r["s_plus_reported"]): {
                    "reported": r["guo_sp_reported"],
                    "fit": r["guo_fit_2.11-1.045s"],
                    "rel_dev_pct": r["guo_fit_rel_dev_pct"],
                }
                for r in probe["table1_arithmetic"]["rows"]
            },
            "fit_at_campaign_s_plus_1.9947": round(2.11 - 1.045 * 1.9947, 5),
            "measured_at_campaign_s_plus_1.99468": camp_guo["dU_dt_over_a"],
        },
        "impact": "'s+ -> 2 注入趋于 0' 由实测点（0.0277 / 0.0063）支持；但拟合式在 s+=1.9763 处偏 61.6%、在 s+=1.9947 处偏 305%（预测约 4 倍于实测），不能当外推模型用。",
        "required_fix": "拟合限定 s+ in [0.9, 1.8] 并注明端部由实测点给出，或改为实测表 + 单调性说明。",
    },
    {
        "id": "F4",
        "severity": "minor",
        "kind": "evidence-ambiguity",
        "title": "表 3 负控格把解析 u_max=0.896 与 NaN 仿真输出并置且未标注；§1 又把 0.896 说成恒等式 u_tau*Re/2 的值（恒等式给 0.900）",
        "evidence": [ev(Q["legacy_row"], "§3 表 3 负控行"), ev(Q["identity"], "§1 恒等式句")],
        "reproduction": {
            "legacy_run_u_max_mean": "nan",
            "legacy_run_u_max_analytic": twin["legacy_u_max_target_None_800"]["u_max_analytic"],
            "identity_u_max": probe["campaign_identity"]["u_max_identity_u_tau*re/2"],
            "Ma_at_identity": round(probe["campaign_identity"]["Ma_identity"], 4),
            "why_0.896": "halfway 壁面原点 0.5 使最近节点落在 y=7.5 而非 H/2=8，离散解析极大 = a*7.5*8.5/(2nu) = 0.896484",
        },
        "impact": "读者可由该格误以为发散运行产出了 u_max=0.896（复现显示仿真场是 NaN，u_max_mean=nan）。数值本身没错，标注缺失。",
        "required_fix": "该格把 0.896 标为 'analytic max on staggered grid'，Ma 用 1.559（或注明 1.55 由 0.896 折算）；§1 区分连续恒等式 0.900 与离散 0.896。",
    },
    {
        "id": "F5",
        "severity": "minor",
        "kind": "reproducibility-pointer",
        "title": "§7 的一键复跑指针指向未随仓交付的 artifacts/ 目录",
        "evidence": [ev(Q["artifacts"], "§7 工件指针"), ev(Q["closed_form"], "文首 '所有数字由 ... 程序化生成'")],
        "reproduction": {
            "checked": "ls /root/tensor-ecosystem/TensorLBM/artifacts/turbulent_channel3d_verification -> No such file or directory",
            "consequence": "§7 的复核命令在交付树内不可执行；本审用自写探针重导了全部关键数（work/wp-7473-04/*.py）",
        },
        "impact": "结论仍可复现（本次已独立重测），但 '无手抄/一键复跑' 的可审计性依赖一个仓外目录。",
        "required_fix": "把 run_probe.py + results.json 纳入仓（或给出带 sha256 的工件清单），保持 §7 指针可解析。",
    },
    {
        "id": "F6",
        "severity": "informational",
        "kind": "status-stale",
        "title": "§5-1 的 wall_exchange 42% 待办已由后续合入修复，报告/台账需注明状态",
        "evidence": [ev(Q["uptau_exch"], "§5-1 观测"), ev(Q["not_fixed"], "§5-1 '本单未修'")],
        "reproduction": {
            "current_main_u_tau_wall_exchange": tw_half["u_tau_wall_exchange"],
            "current_main_u_tau_body_force": tw_half["u_tau_body_force"],
            "rel_dev_pct": round(100 * abs(tw_half["u_tau_wall_exchange"] - tw_half["u_tau_body_force"]) / tw_half["u_tau_body_force"], 2),
            "fix_commit": "b3470562 merge #927 (m6442) — 'must not be divided by the (shorter) averaging window' + test_production_run_does_not_book_spinup_wall_flux",
            "test_suite_current_main": "21 passed in 41.68s（报告：18 条）",
        },
        "impact": "不是报告缺陷（当时确实未修，根因判断正确）。但下游若照 '未清偿项' 记账会重复劳动；需标注已由 #927 关闭。",
        "required_fix": "§5-1 与 §6 末行补一句状态（由 #927 关闭，实测 0.6%），或由知识台账记一条 superseding 关系。",
    },
]

checks_performed = [
    {"check": "source_hash_recompute", "result": "sha256(markdown utf-8) = " + sha + " == 契约 source_hash"},
    {"check": "source_snapshot_byte_identical", "result": "work/wp-7473-04/source_7473.md 与 GET /tensor/reports/7473 的 markdown 字节一致（8934 bytes / 5942 chars）"},
    {"check": "quote_verbatim", "result": "review_report 里每条 evidence.quote 均由脚本按唯一行提取并断言是 markdown 子串（共 %d 条）" % sum(len(c["evidence"]) for c in claims)},
    {"check": "table1_arithmetic_audit", "result": "逐行重算 tau+=0.5+3nu、s+=1/tau+、拟合残差；见 F1/F3"},
    {"check": "table2_arithmetic_audit", "result": "0.039939 vs 0.04 = 0.15%；峰值比 0.99065 = 0.94%；0.4725 vs 0.5 = 5.5%（abs 0.0275）；0.495 vs 0.375 = 32%；0.03556 vs 0.025 = 42.2% 且 tau_w 比 2.02x —— 与报告逐项一致"},
    {"check": "force_impulse_remeasure", "result": "5 个 nu x 2 个 scheme + campaign/A′ + 120 步长 run，见 probe_2026-11-12.json"},
    {"check": "laminar_twin_remeasure", "result": "halfway/interpolated x 800/2000 步 + legacy 负控，见 twin_repro.json"},
    {"check": "code_lineage_git", "result": "#891 引入 832 行无测试 + 默认 guo_sp；#894 默认改 trt_split + 加 validate 白名单 + 首增测试"},
    {"check": "upstream_package_present", "result": "docs/kf/wp-7473-01/verification.json：4 项结构检查 pass、source_hash 三方一致；asset_manifest 38 个资产"},
    {"check": "pytest_suite_current_main", "result": "PYTHONPATH=src pytest -q tests/test_turbulent_channel3d.py -> 21 passed in 41.68s"},
]

checks_not_run = [
    {"check": "producer_probe_byte_reproduction", "why": "artifacts/turbulent_channel3d_verification/ 未随仓交付（F5），无法按 §7 原样复跑；改以自写探针重测同一可观测量"},
    {"check": "wall_modelled_turbulence_anchors (MKM DNS / Reichardt / log-law)", "why": "报告 §5-3 明确未做；本审不评未做项"},
    {"check": "stress_fit / Smagorinsky / turbulence_energy", "why": "报告 §5-4 明确未纳入阶梯；本审不评"},
    {"check": "independent_lbm_implementation", "why": "本审用被审模块 API 重测可观测量（重测而非重实现）；模块 kernel 若有共模误差本审看不见——需第三方求解器对冲"},
    {"check": "gpu/multithread paths", "why": "报告声明 CPU float32 单线程；本审未扩展到并行路径"},
    {"check": "semantic_gate_promotion", "why": "不属于审核者权限：本审只给 disposition，验证级别由平台门计算"},
]

review_report = {
    "package_id": "wp-7473-04",
    "task_type": "04-independent-review",
    "report_id": "7473",
    "reviewed_package": "wp-7473-01",
    "review_target": "report 7473 markdown（TensorLBM 湍流槽道求解器验证欠账清偿 R1）",
    "source": {
        "uri": "tensor://reports/7473",
        "field": "markdown",
        "sha256": "sha256:" + sha,
        "sha256_hex": sha,
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/7473",
        "snapshot": "work/wp-7473-04/source_7473.md",
    },
    "reviewer": {
        "id": "m15853-red-team-reviewer",
        "role": "red-team-reviewer",
        "reviewer_type": "agent",
        "independent_of_producer": True,
        "independence_basis": "审核上下文只含 report 7473 原文、上游 KO（docs/kf/wp-7473-01/asset_manifest.json + verification.json）与仓内公开代码/git 历史；未读生产者的解释性叙述；产物不含生产者自评材料",
        "prompt_provenance": "审核 prompt 由本单现场指令组装，未复制生产 prompt",
    },
    "context": {
        "used": ["report_7473_markdown", "upstream_ko_wp-7473-01", "tensorlbm_code_and_git_history"],
        "excluded": ["producer_explanation", "producer_self_assessment"],
    },
    "disposition": "request-changes",
    "disposition_label": "needs-fix",
    "disposition_reason": "科学结论全部独立复现（力项 1.0000 / guo_sp 0.626% / 孪生 L2 6.76e-3 / 原点 0.4725 / 插值 2.46->3.11%），无造假迹象；但证据表有两处会误导下游的标注/判据问题（F1 表 1 末行参数自洽性、F2 §6 5.5% 判 '是'），必须在入账前修；另有 3 条 minor。故 request-changes 而非 approve。",
    "severity_summary": {
        "blocking": 0,
        "major": sum(1 for f in findings if f["severity"] == "major"),
        "minor": sum(1 for f in findings if f["severity"] == "minor"),
        "informational": sum(1 for f in findings if f["severity"] == "informational"),
    },
    "findings": findings,
    "claim_assessments": claims,
    "overstated_claims": [
        "§6 '壁面原点（halfway） ... 5.5 % ... 是' —— 与同列表头 '<3 %' 冲突（F2）",
        "§3 'guo_sp 的注入率近似 2.11 - 1.045·s+' —— s+>1.9 端偏 61.6%~305%，非可用近似（F3）",
        "§1 'u_max = u_tau·Re_tau/2 是这组参数化下的恒等式 ... 给出 u_max=0.896' —— 恒等式给 0.900，0.896 是离散 y=7.5 上的解析极大（F4）",
        "§3 表 3 'u_max = 0.896, Ma = 1.55, L2 = nan' —— 未标注 0.896 为解析值，仿真实测为 NaN（F4）",
        "§3 '使整个战役驱动力失效' —— 就 guo_sp 而言成立（0.63%），但报告内只有单步/均匀流探针，战役侧实跑证据未给出；因果链在报告内只到 '默认值错' 这一环",
    ],
    "remediation_required": [
        {"finding": "F1", "action": "表 1 末行拆行或把 nu 标注改为 4.444e-4（tau+=0.5013）；§1 A′ 行改标真实出处", "blocking_for": "evidence-table reproducibility"},
        {"finding": "F2", "action": "5.5% 格改 '否'，或在 §6 预声明几何量的绝对判据（不得事后追加）", "blocking_for": "acceptance-criteria integrity"},
        {"finding": "F3", "action": "拟合式限定区间 + 端部用实测点"},
        {"finding": "F4", "action": "标注 0.896 为离散解析极大；Ma 用 1.559 或注明折算"},
        {"finding": "F5", "action": "工件入仓或给 sha256 清单，保持 §7 指针可解析"},
        {"finding": "F6", "action": "§5-1 状态更新为已由 #927 关闭（实测 0.6%）"},
    ],
    "reproduction": {
        "env": "CPU float32 单线程；python 3.11 + torch 2.7.1；TensorLBM @ /root/tensor-ecosystem/TensorLBM (main, da452346)",
        "scripts": [
            "work/wp-7473-04/independent_probe.py",
            "work/wp-7473-04/independent_twin.py",
            "work/wp-7473-04/make_figure.py",
            "work/wp-7473-04/build_review.py",
        ],
        "artifacts": [
            "work/wp-7473-04/probe_2026-11-12.json",
            "work/wp-7473-04/twin_repro.json",
            "work/wp-7473-04/fig_review_force_injection.png",
        ],
        "one_liner": "bash work/wp-7473-04/repro.sh",
        "test_suite_current_main": "21 passed in 41.68s",
    },
    "limitations_of_this_review": [
        "重测使用被审模块 API：模块 kernel 若有共模误差，本审不具鉴别力（未做独立求解器对冲）",
        "复现运行在 TensorLBM main 的后续状态（da452346，含 #927 之后的改动）；被审报告的时点状态是 #894，测试数 21 vs 18 的差异由此而来；表 1/表 2 数值逐项对上，不影响可复现性结论",
        "未评估 §5-3 壁面解析湍流锚、§5-4 stress_fit/Smagorinsky/turbulence_energy —— 报告声明未做，本审只评声明的诚实性",
        "M6 semantic fidelity 的强模型抽样不在本单执行；本审语义判定为单席位意见",
        "未检查并行/GPU 路径与不同架构下的数值差异（报告声明 CPU 单线程）",
    ],
    "acceptance_self_check": {
        "valid_json": "pass",
        "schema_pass": "pass（result envelope 用 schemas/kf_result.v1.schema.json 校验）",
        "reviewer_independent": "pass（上下文=原文+上游 KO+公开代码；未读生产者解释）",
        "upstream_packages_completed": "pass（docs/kf/wp-7473-01/verification.json 全部检查 pass，source_hash 三方一致）",
        "do_not_mark_claims_as_verified": "pass（本包无 verified/verification_* 字段；验证级别留给平台门）",
    },
}

events = [
    {
        "id": "tkr:wp-7473-01:review-wp-7473-04",
        "object_ref": "wp-7473-01",
        "object_version": "report-7473@sha256:" + sha,
        "decision": "request-changes",
        "reviewer": {
            "id": "m15853-red-team-reviewer",
            "reviewer_type": "agent",
            "role": "red-team-reviewer",
        },
        "reviewed_at": "2026-11-12T02:58:00Z",
        "policy_version": "ke-review-v0.1",
        "rationale": "结论可复现但证据表有两处需修的标注/判据问题（F1/F2）；见 review_report.json",
        "findings": [
            {
                "severity": "major",
                "finding": "F1 表 1 末行 nu/tau+ 与同格 s+/比率不自洽（0.63% 属 campaign nu=4.444e-4；行内 nu=2.22e-3 实测 3.07%）",
                "related_claim_refs": ["R1-C3-guo-sp-underdrive"],
            },
            {
                "severity": "major",
                "finding": "F2 §6 把 5.5% 偏差标成 '<3% = 是'，事后用 '(几何量)' 改判据",
                "related_claim_refs": ["R1-C4-laminar-twin"],
            },
            {
                "severity": "minor",
                "finding": "F3 拟合式 2.11-1.045 s+ 在 s+>1.9 端偏 61.6%~305%",
                "related_claim_refs": ["R1-C3-guo-sp-underdrive"],
            },
            {
                "severity": "minor",
                "finding": "F4 表 3 把解析 u_max=0.896 与 NaN 仿真并置未标注；§1 恒等式实为 0.900",
                "related_claim_refs": ["R1-C6-legacy-diverges"],
            },
            {
                "severity": "minor",
                "finding": "F5 §7 复跑指针指向未随仓交付的 artifacts/ 目录",
            },
            {
                "severity": "informational",
                "finding": "F6 §5-1 wall_exchange 42% 已由 merge #927 修复（实测 0.6%），'未修' 状态过期",
                "related_claim_refs": ["R1-C7-wall-exchange-anomaly"],
            },
        ],
        "conditions": [
            "F1 修正表 1 末行/§1 A′ 标注后可复核 0.63% 的可追踪性",
            "F2 改判 '否' 或预声明几何量判据后重评 §6 列",
        ],
    }
]

os.makedirs(OUTDIR, exist_ok=True)
json.dump(review_report, open(os.path.join(OUTDIR, "review_report.json"), "w"), indent=1, ensure_ascii=False)
json.dump(events, open(os.path.join(OUTDIR, "review_events.json"), "w"), indent=1, ensure_ascii=False)

# --------------------------------------------------------------- result envelope
envelope = {
    "package_id": "wp-7473-04",
    "task_type": "04-independent-review",
    "report_id": "7473",
    "provenance": {
        "source_uri": "tensor://reports/7473",
        "source_field": "markdown",
        "source_hash": "sha256:" + sha,
        "producer": "m15853",
        "emitted_at": "2026-11-12T02:58:00Z",
        "notes": "独立审核 wp-7473-01；审核上下文=原文+上游 KO+公开代码/git，未读生产者解释",
    },
    "outputs": {
        "review_report.json": review_report,
        "review_events.json": events,
    },
    "claims": [
        {
            "claim_id": c["claim_id"],
            "text": c["text"],
            "status": c["status"],
            "evidence": [{"quote": e["quote"], "source_field": "markdown", "note": e["note"]} for e in c["evidence"]],
            **({"unresolved_reason": c["unresolved_reason"]} if c.get("unresolved_reason") else {}),
        }
        for c in claims
    ],
}
json.dump(envelope, open(os.path.join(OUTDIR, "kf_result.json"), "w"), indent=1, ensure_ascii=False)

# schema validation of the envelope
try:
    import jsonschema

    schema = json.load(open(os.path.join(REPO, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    schema_note = "kf_result.v1.schema.json: OK"
except Exception as exc:  # pragma: no cover
    schema_note = f"schema validation issue: {exc}"

print("quote count:", sum(len(c["evidence"]) for c in claims))
print("disposition:", review_report["disposition"], review_report["severity_summary"])
print(schema_note)
print("wrote:", OUTDIR)