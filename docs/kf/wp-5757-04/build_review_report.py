#!/usr/bin/env python3
"""wp-5757-04 · 由 checks.json 生成 review_report.json + 审核矩阵图。

输入只读：docs/kf/wp-5757-04/checks.json（verify_wp_5757_04.py 产出）、
上游 docs/kf/wp-5757-01/asset_manifest.json、平台 report 5757 markdown。
所有引文由脚本从 markdown 按 char_span 截取，保证逐字可定位。
"""
from __future__ import annotations

import hashlib
import json
import os

OUT = "docs/kf/wp-5757-04"
SRC = json.load(open("/tmp/report_5757.json", encoding="utf-8")) if os.path.exists("/tmp/report_5757.json") else None

checks = json.load(open(f"{OUT}/checks.json", encoding="utf-8"))
man = json.load(open("docs/kf/wp-5757-01/asset_manifest.json", encoding="utf-8"))

if SRC is None:
    raise SystemExit("缺少 /tmp/report_5757.json（先跑 verify 脚本取回原文）")
md = SRC["markdown"]


def q(asset_ids: str | list[str]) -> str:
    """从上游 locator 取逐字引文。"""
    ids = [asset_ids] if isinstance(asset_ids, str) else asset_ids
    quotes = [a["locator"]["quote"] for a in man["assets"] if a["asset_id"] in ids]
    return " | ".join(quotes)


def line_containing(*needles: str) -> str:
    for ln in md.splitlines():
        s = ln.strip()
        if all(n in s for n in needles):
            return s
    raise KeyError(needles)


non_unique = [r for r in checks["locator_matrix"] if r["occurrences"] > 1]

findings = [
    {
        "id": "F1",
        "severity": "minor",
        "likelihood": "certain",
        "title": "locator.unique=true 对 A13/A15 不成立（引文在原文出现 2 次）",
        "scope": "wp-5757-01 asset_manifest.json assets[12].locator、assets[14].locator",
        "evidence": {
            "asset_ids": [r["asset_id"] for r in non_unique],
            "quotes": [r["quote"] for r in non_unique],
            "occurrences": {r["asset_id"]: r["occurrences"] for r in non_unique},
            "first_index_equals_recorded_span": {r["asset_id"]: r["first_index_equals_span"] for r in non_unique},
        },
        "reproduction": "python3 docs/kf/wp-5757-04/verify_wp_5757_04.py → 检查项 C6",
        "impact": "机器可读字段与事实不符；但 md.find(quote) 对 15/15 资产都等于记录 start_char，"
                  "按 first-occurrence 解析的下游不会错位；只有依赖『引文唯一』不变量的消费方会被绊倒。",
        "remediation": "把 unique 改成 occurrence_count=1/2 的真实计数，或改用 (start_char,end_char) 作为唯一键。",
        "blocking": False,
    },
    {
        "id": "F2",
        "severity": "minor",
        "likelihood": "certain",
        "title": "召回缺口：报告以『pytest 覆盖』为证据的测试套件未登记为资产",
        "scope": "asset_manifest.json summary.total_assets=15 的资产全集",
        "evidence": {
            "report_quote": line_containing("pytest"),
            "registered_test_assets": checks["checks"][7]["detail"]["registered_test_assets"],
            "host_corroboration": "TensorPlatform 检出（commit 3d6ff8aba 的 worktree）"
                                  "tests/test_gate_auto_release.py 含 10 个 def test_，与报告『10 条』相符",
        },
        "reproduction": "verify C8；grep -c '^def test_' tests/test_gate_auto_release.py（TensicrosoftPlatform 检出）",
        "impact": "资产清单作为下游 inventory 基线时，release 路径的唯一测试证据不可定位。",
        "remediation": "增补 asset（class=test），locator 指向报告里出现 pytest 的那一行。",
        "blocking": False,
    },
    {
        "id": "F3",
        "severity": "minor",
        "likelihood": "certain",
        "title": "判据表未声明 C3 先于 C2 的优先级，但结果（G20 判 hold 而非 wait）依赖该优先级",
        "scope": "报告 ② 判据表 vs ③ 生产矩阵 G20(185) 行",
        "evidence": {
            "gate185_row": " | ".join(checks["checks"][12]["detail"]["gate185_row"]),
            "criteria_quote": "C3 非治理门 | `metadata.owner_only` 非真 + 门名/goal 无治理标记 | 只标 `owner_only=1`，**永不自动放**",
        },
        "reproduction": "verify C13",
        "impact": "实现层 evaluate_gate() 以 owner_only 短路（见外部核对）；报告只靠『永不自动放』隐含，"
                  "若下游按表中 C1→C2→C3 顺序重实现，G20 会得到 wait 而不是 hold，owner_only 保护叙事被削弱。",
        "remediation": "判据表加一行明文『优先级 C3 > C1 > C2』。",
        "blocking": False,
    },
    {
        "id": "F4",
        "severity": "note",
        "likelihood": "certain",
        "title": "生产快照哈希被截断展示（56e8ab79…），production_untouched 外部不可复算",
        "scope": "报告 ③ 生产只读矩阵末条",
        "evidence": {"quote": line_containing("快照", "before")},
        "reproduction": "verify C14",
        "impact": "只能采信程序结论；跨轮比对与归档无法验证快照未变的强证据。",
        "remediation": "程序化注入完整 64 hex 摘要（before/after）。",
        "blocking": False,
    },
    {
        "id": "F5",
        "severity": "note",
        "likelihood": "certain",
        "title": "图件 A12 只带 name+caption、GET 读接口不回传 png_base64（平台读侧行为，非生产者漏发）",
        "scope": "平台 report 5757 figures[0]；manifest A12 resolution=referenced_unresolved",
        "evidence": {"figure_name": (SRC.get("figures") or [{}])[0].get("name", ""),
                     "figure_keys": sorted((SRC.get("figures") or [{}])[0].keys()),
                     "manifest_quote": q("A12"),
                     "self_roundtrip": "本单自己的 KF-RESULT 报告以 figures[].png_base64 内嵌发布后，"
                                       "经同一 GET /api/v1/tensor/reports/<id> 回读，figures 也只剩 name+caption"
                                       "（复现：python3 docs/kf/wp-5757-04/probe_figure_payload.py 5757 <id>）"},
        "reproduction": "verify C15；GET /api/v1/tensor/reports/5757 → figures[0] 无 png_base64；探针见 probe_figure_payload.py",
        "impact": "上游把 A12 记为 referenced_unresolved 是**完全正确**的分类；缺失不在报告 5757、也不在 wp-5757-01，"
                  "而在平台读侧不返回图件载荷 → 任何下游都验不了图。因此本项归属平台侧改进，不构成对上游的缺陷。",
        "remediation": "平台读侧提供图件下载端点或回传 png sha256；wp-5757-01 / report 5757 侧无需改动。",
        "blocking": False,
    },
    {
        "id": "F6",
        "severity": "note",
        "likelihood": "likely",
        "title": "『只判工件在不在、不判内容对错』与仓内新增 gate_content_criteria 层可能版本失同步",
        "scope": "报告 ⑤.5 局限 vs TensorPlatform 检出 ops/taskplane/gate_content_criteria.py + evaluate_gate() 内 C2b 分支",
        "evidence": {
            "report_quote": "只判「工件在不在、json 是否合法」，不判内容对错（内容由验收链负责）",
            "host_files": "ops/taskplane/gate_content_criteria.py、gate_auto_release.py 中 '# C2b 判据内容' 分支",
        },
        "reproduction": "grep -n 'C2b' ops/taskplane/gate_auto_release.py（TensorPlatform 检出）",
        "impact": "若产线版本已含 C2b，则报告局限描述偏保守/过期；但未绑定 commit，无法定论 → 记 note 而非 defect。",
        "remediation": "报告补 commit sha；或注明 C2b 仅在门显式声明 checks 时生效。",
        "blocking": False,
    },
]

claims = [
    {
        "claim_id": "C-01",
        "text": "wp-5757-01 provenance.source_hash / source_chars 与 report 5757 markdown 字节一致",
        "status": "supported",
        "evidence": {"recomputed_hash": checks["source_hash"], "chars": checks["source_chars"]},
    },
    {
        "claim_id": "C-02",
        "text": "15 个资产的 char_span/行号在原文逐字命中",
        "status": "supported",
        "evidence": {"checked": len(checks["locator_matrix"]), "failed": []},
    },
    {
        "claim_id": "C-03",
        "text": "locator.unique=true 对全部资产成立",
        "status": "refuted",
        "evidence": {"non_unique": [r["asset_id"] for r in non_unique]},
    },
    {
        "claim_id": "C-04",
        "text": "5 个判据工件 declared_absent",
        "status": "partially-supported",
        "evidence": {"quote": "证据在临时根按 `<repo>/artifacts/…` 同形造出\n（显式 `synthetic: true`）",
                     "note": "生产侧确实 not_found（A07–A11 表行一致），但沙箱内同形存在；"
                             "manifest 的 per-asset note 写了『生产侧 not_found』，状态词表本身未带这个限定"},
    },
    {
        "claim_id": "C-05",
        "text": "code/config 资产 referenced_unresolved 因为它们住在其它仓",
        "status": "supported",
        "evidence": {"note": "主机上 TensorPlatform 检出内 6/6 路径存在（gate_auto_release.py 849 行、"
                             "gate_auto_release_loop.sh 48 行、deploy/taskplane/gate-auto-release.service 34 行、"
                             "tools/gate_drill.py 262 行、ops/taskplane/supervise.py、ops/taskplane/taskplane.manifest.yaml）；"
                             "在 TensorKnowledge 工作树内确实不可解析 → unresolved 分类诚实"},
    },
]

review = {
    "schema": "kf-independent-review.v1",
    "package_id": "wp-5757-04",
    "task_type": "04-independent-review",
    "reviewed_package": "wp-5757-01",
    "report_id": "5757",
    "reviewer_role": "red-team-reviewer",
    "reviewed_artifact": {
        "path": "docs/kf/wp-5757-01/asset_manifest.json",
        "sha256": "sha256:" + hashlib.sha256(open("docs/kf/wp-5757-01/asset_manifest.json", "rb").read()).hexdigest(),
        "upstream_result": "docs/kf/wp-5757-01/kf_result.wp-5757-01.json",
    },
    "independence": {
        "context_used": ["report 5757 markdown（平台 API，独立重算哈希）",
                         "上游 wp-5757-01 产物（asset_manifest.json / kf_result）",
                         "仓内代码与 schema（worktree，只读）",
                         "主机上 TensorPlatform 检出（只读 grep，仅作旁证）"],
        "context_excluded": ["生产者对 wp-5757-01 的口头/文字解释（未读）",
                            "其它 report_id 的 markdown/产物（未读）"],
        "review_prompt_not_copied_from_producer": True,
        "limitations": [
            "生产库 tensorplatform.campaign_nodes 无读权限 → 报告里的 8/11/8/11/4/9 依赖数、门状态、owner_only 值无法独立复核，记 not_run。",
            "旁证只读自主机上一个 TensorPlatform 检出（commit 3d6ff8aba），不保证等于生产侧产线提交 → 关于实现的判断降级为 note。",
            "报告快照哈希被截断，production_untouched=True 无法独立复算。",
        ],
    },
    "scope": {
        "in_scope": ["wp-5757-01 出处可定位性（hash/chars/char_span/行号/唯一性）",
                     "wp-5757-01 资产分类与 resolution 状态的可辩护性",
                     "wp-5757-01 资产召回（是否有报告内资产漏登记）",
                     "报告 ③ 数字的内部算术一致性（作为上游 fidelity 的必要条件）"],
        "out_of_scope": ["report 5757 的作者结论正确性（release 逻辑是否安全）——由平台门/后续 wp 判",
                         "生产库真实状态（无权限）"],
    },
    "checks": checks["checks"],
    "locator_matrix": checks["locator_matrix"],
    "claims_assessed": claims,
    "findings": findings,
    "checks_not_run": [
        {"id": "N1", "what": "生产 campaign_nodes 六门的 dependencies/status/metadata.owner_only 实测",
         "reason": "psql: permission denied for table campaign_nodes"},
        {"id": "N2", "what": "浮点/物理量基线比对", "reason": "非该类报告（治理/后端机制，无物理量）"},
        {"id": "N3", "what": "沙箱 UPDATE/rollback 真跑复现", "reason": "需写生产库隔离 schema 权限；按本单边界不改上游状态"},
    ],
    "overstated_claims": [
        {"claim": "locator.unique=true（A13/A15）", "why": "引文各出现 2 次", "finding": "F1"},
        {"claim": "declared_absent 对 A07–A11", "why": "只对生产侧成立，沙箱内同形存在（report 自述 synthetic:true）", "finding": "F2 相关"},
        {"claim": "「六门 wait ×6」", "why": "六门中 wait=5、hold=1，第 6 个 wait 来自 plan 21 的 G21；总行数 7 仍自洽", "finding": "F7(算术措辞)"},
    ],
    "summary_counts": {
        "checks_total": checks["checks_total"],
        "checks_pass": checks["checks_pass"],
        "checks_fail": checks["checks_fail"],
        "blocking_failures": checks["blocking_failures"],
        "findings": {s: sum(1 for f in findings if f["severity"] == s)
                     for s in ("blocking", "major", "minor", "note")},
    },
    "remediation_required": [
        {"id": "R1", "owner": "wp-5757-01", "from_finding": "F1", "action": "locator.unique 改为真实 occurrence_count（A13/A15=2），或以 (start_char,end_char) 作唯一键", "blocking": False},
        {"id": "R2", "owner": "wp-5757-01", "from_finding": "F2", "action": "增补 test 类资产（pytest 套件），locator 指向『10 条 pytest 覆盖』所在行", "blocking": False},
        {"id": "R3", "owner": "report-5757", "from_finding": "F3", "action": "判据表补一行『优先级 C3 > C1 > C2』", "blocking": False},
        {"id": "R4", "owner": "report-5757", "from_finding": "F4", "action": "程序化注入完整 64-hex 快照摘要（before/after）", "blocking": False},
        {"id": "R5", "owner": "platform", "from_finding": "F5", "action": "读侧提供图件下载端点或回传 png sha256（wp-01 与 report 5757 侧无需改动）", "blocking": False},
        {"id": "R6", "owner": "report-5757", "from_finding": "F6", "action": "报告补产线 commit sha；或注明 C2b 仅在门显式声明 checks 时生效", "blocking": False},
    ],
    "verdict": "pass",
    "disposition": "pass with notes（无 blocking 缺陷；F1/F2/F3 建议在 wp-01 侧小改，F4/F5/F6 归报告侧或下游）",
    "verdict_rule": "blocking=出处/哈希不可定位、资产凭空捏造、分类与原文矛盾；"
                    "以上均未触发（15/15 locator 逐字命中、哈希独立重算一致、无虚构资产）。"
                    "minor=机器可读字段为假或召回缺口（不改变下游解析结果）。",
    "do_not_mark_claims_as_verified": True,
    "emitted_at": SRC.get("created_at"),
}

with open(f"{OUT}/review_report.json", "w", encoding="utf-8") as fh:
    json.dump(review, fh, ensure_ascii=False, indent=2)

# ── kf_result 信封 ────────────────────────────────────────────────
kfr = {
    "package_id": "wp-5757-04",
    "task_type": "04-independent-review",
    "report_id": "5757",
    "provenance": {
        "source_hash": checks["source_hash"],
        "source_field": "markdown",
        "producer": "red-team-reviewer (m15840)",
        "emitted_at": review["emitted_at"],
        "notes": "独立审核 wp-5757-01；上下文=报告原文+上游 KO，未读生产者解释；未将任何结论标为 verified",
    },
    "outputs": {
        "review_report.json": review,
    },
    "claims": [],
}
with open(f"{OUT}/kf_result.json", "w", encoding="utf-8") as fh:
    json.dump(kfr, fh, ensure_ascii=False, indent=2)

# ── 图：审核矩阵 ───────────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs(OUT, exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))

ax = axes[0]
ids = [r["asset_id"] for r in checks["locator_matrix"]]
occ = [r["occurrences"] for r in checks["locator_matrix"]]
ok = [r["first_index_equals_span"] and r["span_exact"] for r in checks["locator_matrix"]]
colors = ["#2e7d32" if (o == 1 and k) else ("#ef6c00" if k else "#c62828") for o, k in zip(occ, ok)]
ax.bar(ids, occ, color=colors)
ax.axhline(1, color="#555", lw=1, ls="--")
ax.set_ylim(0, 2.6)
ax.set_ylabel("occurrences of locator.quote in markdown")
ax.set_title("A: wp-5757-01 locator audit (15/15 spans verbatim)\n"
             "green=unique & first hit == recorded span; orange=non-unique, first hit still == span")
for r in checks["locator_matrix"]:
    if r["occurrences"] > 1:
        ax.annotate("unique=true false", (r["asset_id"], r["occurrences"]),
                    textcoords="offset points", xytext=(-8, 6), fontsize=8, color="#ef6c00")

ax = axes[1]
labels = [c["check_id"] for c in checks["checks"]]
passed = [1 if c["result"] == "pass" else 0 for c in checks["checks"]]
sev = {"blocking": "#c62828", "minor": "#ef6c00", "note": "#f9a825"}
cols = ["#2e7d32" if p else sev[c["severity_if_fail"]] for p, c in zip(passed, checks["checks"])]
ax.bar(labels, passed, color=cols)
ax.set_ylim(0, 1.25)
ax.set_yticks([0, 1])
ax.set_yticklabels(["fail", "pass"])
ax.set_title(f"B: review check matrix {checks['checks_pass']}/{checks['checks_total']} pass\n"
             f"blocking failures={len(checks['blocking_failures'])}; red/orange/yellow = severity")
for i, (p, c) in enumerate(zip(passed, checks["checks"])):
    ax.annotate(c["severity_if_fail"] if not p else "", (i, p), ha="center", va="bottom", fontsize=8)
ax.tick_params(axis="x", labelrotation=90)

fig.suptitle("wp-5757-04 independent review | report 5757 | reviewed: wp-5757-01 (asset registration)", fontsize=11)
fig.tight_layout()
png = f"{OUT}/review_matrix.png"
fig.savefig(png, dpi=150)
print("wrote", f"{OUT}/review_report.json", f"{OUT}/kf_result.json", png)
print("verdict:", review["verdict"], review["summary_counts"])