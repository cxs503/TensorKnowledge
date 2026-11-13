"""Render docs/kf/wp-7473-04/README.md (KF-RESULT report) from the built JSON."""
from __future__ import annotations

import json
import os

WT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(WT, "..", ".."))
OUT = os.path.join(REPO, "docs", "kf", "wp-7473-04")

rep = json.load(open(os.path.join(OUT, "review_report.json"), encoding="utf-8"))
env = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
probe = json.load(open(os.path.join(WT, "probe_2026-11-12.json"), encoding="utf-8"))
twin = json.load(open(os.path.join(WT, "twin_repro.json"), encoding="utf-8"))

camp = probe["remeasure"]["campaign_and_A_prime"]
guo_camp = [r for r in camp if r["scheme"] == "guo_sp" and r["nu"] < 0.002][0]
trt_camp = [r for r in camp if r["scheme"] == "trt_split" and r["nu"] < 0.002][0]
guo_ap = [r for r in camp if r["scheme"] == "guo_sp" and r["nu"] > 0.002][0]
tw = twin["halfway_recalibrated_800"]
tw2000 = twin["halfway_recalibrated_2000"]
ti = twin["interpolated_q0.375_800"]
ti2000 = twin["interpolated_q0.375_2000"]
lg = twin["legacy_u_max_target_None_800"]

sev = rep["severity_summary"]
body = f"""# KF-RESULT wp-7473-04

**独立性**：审核上下文 = report 7473 原文（sha256 逐字节校验）+ 上游 KO（`docs/kf/wp-7473-01/`）
+ 仓内公开代码与 git 历史。未读生产者的解释性叙述；产物不含生产者自评材料。

**结论（disposition）**：`request-changes`（needs-fix）。severity：blocking {sev['blocking']} ·
major {sev['major']} · minor {sev['minor']} · informational {sev['informational']}。
科学结论全部独立复现、无造假迹象；两处证据表标注/判据问题必须在入账前修。

---

## ① 本工序做了什么

对 report_id=7473（TensorLBM 湍流槽道求解器验证欠账清偿 R1）做**独立红队审核**，审核对象
= 上游包 `wp-7473-01`。三件事：
1. 逐条把报告的 9 组主张绑定到原文引文，并对每个可观测量做**外部复算/重测**（不引用生产者的
   `results.json`，因为它未随仓交付）；
2. 对报告自己的数值表做**算术审计**（tau+/s+/拟合残差/误差百分比/参数恒等式）；
3. 用 git 历史核对代码侧主张（默认值、白名单、合入时是否无测试）。

不改上游产物、不改 report 7473、不写 verified 之类字段（验证级别留给平台门）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具/设置 |
|---|---|---|
| 1 | 取原文 | `GET /api/v1/tensor/reports/7473`，重算 sha256 = `{rep['source']['sha256_hex']}`，与契约一致 |
| 2 | 读上游 KO | `docs/kf/wp-7473-01/{{asset_manifest.json,verification.json}}`（38 资产，结构化检查全过） |
| 3 | 算术审计 | `work/wp-7473-04/independent_probe.py`（纯算术层：tau+=0.5+3nu、s+=1/tau+、拟合残差、误差百分比） |
| 4 | 力项重测 | 同上脚本第二层：8×18×8、a=1e-4、12 步、体相 x∈[6,12) 平均、CPU float32 单线程；5 个 nu × 2 scheme + campaign nu + A′ nu + 120 步长 run |
| 5 | 孪生重测 | `work/wp-7473-04/independent_twin.py`：`run_laminar_poiseuille` halfway/interpolated × 800/2000 步 + `u_max_target=None` 负控 |
| 6 | 代码溯源 | `git -C /root/tensor-ecosystem/TensorLBM`：`show 520d3282:…`（#891）、`log --diff-filter=A -- tests/…`（#894）、`-S` 找 #927 |
| 7 | 引文落库 | `work/wp-7473-04/build_review.py`：每条 quote 按"唯一行"提取并断言是原文子串，失败即中止 |

环境：python 3.11 + torch 2.7.1；TensorLBM main `da452346`（含 #927 之后的状态，见局限）。
一键复跑：`bash work/wp-7473-04/repro.sh`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7473-04/review_report.json` | 审核报告：9 条主张裁定、6 条 finding（severity 分级）、复现命令、not_run 清单、局限 |
| `docs/kf/wp-7473-04/review_events.json` | 审核台账（`request-changes`，带 findings；过 `schemas/review-event.schema.json` 与 `scripts/ke_state_machine.py` 折叠 → `draft` / `OK_CHANGES_REQUESTED`） |
| `docs/kf/wp-7473-04/kf_result.json` | 结果信封（过 `schemas/kf_result.v1.schema.json`） |
| `work/wp-7473-04/independent_probe.py` + `probe_2026-11-12.json` | 力项重测原始数（可机读） |
| `work/wp-7473-04/independent_twin.py` + `twin_repro.json` | 孪生/负控重测原始数 |
| `work/wp-7473-04/fig_review_force_injection.png` | 图 1：guo_sp 注入率实测 vs 报告拟合式 |
| `work/wp-7473-04/source_7473.md` | 原文快照（8934 bytes，sha256 与契约一致） |

## ④ 证据定位表（claim → 原文引文）

| claim | 裁定 | 原文引文（逐字） |
|---|---|---|
| C1 默认值 guo_sp→trt_split + 白名单 | supported | `{rep['claim_assessments'][0]['evidence'][0]['quote']}` |
| C2 trt_split 力项精确 | supported | `{rep['claim_assessments'][1]['evidence'][0]['quote']}` |
| C3 guo_sp 战役下 0.63% | supported | `{rep['claim_assessments'][2]['evidence'][0]['quote']}` |
| C4 孪生 L2/峰值比/壁面原点 | supported | `{rep['claim_assessments'][3]['evidence'][1]['quote']}` |
| C5 插值反弹不收敛 | supported | `{rep['claim_assessments'][4]['evidence'][0]['quote']}` |
| C6 旧标定发散 | partially-supported | `{rep['claim_assessments'][5]['evidence'][0]['quote']}` |
| C7 wall_exchange 42% 根因 | supported | `{rep['claim_assessments'][6]['evidence'][0]['quote']}` |
| C8 合入时无测试 | supported | `{rep['claim_assessments'][7]['evidence'][0]['quote']}` |
| C9 未做项声明 | supported | `{rep['claim_assessments'][8]['evidence'][0]['quote']}` |

全部 17 条引文均由脚本断言为原文逐字子串，并记录字符偏移（`review_report.json.evidence.locator`）。

## ⑤ 注意点与局限

* **F1（major）** 表 1 末行把 `nu=2.22e-3 / tau+=0.5067` 与 `s+=1.9947 / guo=0.0063` 写在同一行。
  重测：campaign nu=4.444e-4（tau+=0.50133）下 guo_sp = {guo_camp['dU_dt_over_a']}（= 报告的 0.63% ✓）；
  而按行内 nu=2.22e-3（tau+=0.50666, s+=1.97371）实测 guo_sp = {guo_ap['dU_dt_over_a']}（3.07%）。
  结论对、标注错：照行取参会差 4.9 倍。
* **F2（major）** §6 表头是"是否 <3 %"，而"壁面原点（halfway）…5.5 %…**是**"用"(几何量)"事后改判据。
* **F3（minor）** 拟合式 `2.11 - 1.045 s+` 在 s+=1.9763 处偏 61.6%、在 s+=1.9947 处偏 305%（预测 0.0255 vs 实测 0.0063）。
* **F4（minor）** 表 3 把解析 u_max=0.896 与 `L2 = nan` 并置未标注：复现得 `u_max_mean=nan`、
  `u_max_analytic={lg['u_max_analytic']}`；恒等式 u_tau·Re/2 实为 0.900，0.896 是 y=7.5 上的离散解析极大。
* **F5（minor）** §7 复跑指针 `artifacts/turbulent_channel3d_verification/` 未随仓交付（树内不存在）。
* **F6（informational）** §5-1 的 42% 待办已由 merge #927 修复：现测
  `u_tau_wall_exchange={tw['u_tau_wall_exchange']}` vs `body_force={tw['u_tau_body_force']}`（0.6%）。
* 本审局限：重测走被审模块 API（重测非重实现，kernel 共模误差看不见）；复现跑在 main 的后续状态
  （测试 21 条 vs 报告 18 条）；§5-3 壁面湍流锚与 §5-4 的 LES/统计面报告声明未做，本审不评。
* 语义保真（M6）的强模型抽样不在本单执行，本审语义判定为单席位意见。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 三个 JSON 均 `json.load` 通过 |
| schema_pass | ✅ | envelope 过 `schemas/kf_result.v1.schema.json`；review_events 过 `schemas/review-event.schema.json` |
| reviewer_independent | ✅ | 上下文=原文+KO+公开代码/git；未读生产者解释；prompt 未复制生产 prompt |
| upstream_packages_completed | ✅ | `docs/kf/wp-7473-01/verification.json` 全检查 pass，source_hash 三方一致 |
| do_not_mark_claims_as_verified | ✅ | 无 any verified/verification_* 字段（脚本扫描）；disposition 仅 `request-changes` |

honest 说明：本单**未**通过（disposition=request-changes）。不通过的原因不是数据造假——所有关键
数字都独立复现——而是 F1/F2 两处证据面缺陷会让下游错误使用这份报告。

## 图 1

`fig_review_force_injection.png`：guo_sp 注入率实测点（含 campaign nu=4.444e-4 的
{guo_camp['dU_dt_over_a']} a）与报告拟合线的偏离——拟合在 s+>1.9 端明显高估，实测点按
1.9763 → 1.9947 单调降到 0.63%，支撑定性结论而不支撑拟合式。

---

```json
{json.dumps(env, ensure_ascii=False, indent=1)}
```
"""

open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(body)

repro = f"""#!/usr/bin/env bash
# One-key reproduction of wp-7473-04 (independent review of report 7473).
# Prereqs: python3 + torch; TensorLBM checkout at /root/tensor-ecosystem/TensorLBM,
# or set TLBM=<your checkout>. CUDA-free, CPU float32 single thread, < 2 min.
set -euo pipefail
cd "$(dirname "$0")/../.."
TLBM="${{TLBM:-/root/tensor-ecosystem/TensorLBM}}"
export OMP_NUM_THREADS=1 PYTHONPATH="$TLBM/src:${{PYTHONPATH:-}}"

# 1) force-impulse re-measurement (Table 1 / Table 3 anchors)
python3 work/wp-7473-04/independent_probe.py work/wp-7473-04/probe_2026-11-12.json

# 2) laminar twin / negative control re-measurement (Table 2 / Table 3)
python3 work/wp-7473-04/independent_twin.py

# 3) reviewed module's own suite at the checkout under test
( cd "$TLBM" && python3 -m pytest -q tests/test_turbulent_channel3d.py )

# 4) figure + deliverables (quotes re-extracted verbatim; schema validated)
python3 work/wp-7473-04/make_figure.py
python3 work/wp-7473-04/build_review.py
python3 work/wp-7473-04/gen_report_md.py
echo "OK: docs/kf/wp-7473-04/{{review_report.json,review_events.json,kf_result.json,README.md}}"
"""
open(os.path.join(WT, "repro.sh"), "w", encoding="utf-8").write(repro)
os.chmod(os.path.join(WT, "repro.sh"), 0o755)
print("README.md bytes:", len(body.encode("utf-8")))
print("repro.sh written")