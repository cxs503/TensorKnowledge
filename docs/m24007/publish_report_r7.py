#!/usr/bin/env python3
"""Build and publish the R7 terminal-review progress report (m24007)."""
import base64
import json
import os
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ.get("TENSOR_AGENT_USER", "eco_admin")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

# --- login (correct endpoint: /auth/login, returns access_token) ---
req = urllib.request.Request(
    f"{API}/auth/login",
    data=json.dumps({"username": USER, "password": PASS}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
    token = data.get("access_token") or data.get("token") or ""
print("token_len:", len(token))

# --- figure ---
fig_path = "docs/m24007/figures/r7_before_claimed_actual.png"
with open(fig_path, "rb") as f:
    fig_b64 = base64.b64encode(f.read()).decode()

markdown = """## ① 案例介绍（审的是什么）

PROD-RA（research-audit）stage-3 评审包（`docs/m22059/` + `docs/review_m22059_prod_ra/`）在 R5 独立复审
（m23157，verdict=changes_requested）留下三项残差（R5-1 locator 冷启动可解析性、R5-2 manifest 完整性、
R5-3 D6 证据指纹）。R6 修复单 m23814（PR#525）自报 `all_six_pass=True`、三残差闭合。本单（m24007）为
**独立第三方终审**：不信自报，用冻结验证器 `docs/m23257/verify_status.py`（禁改动）对 `git archive HEAD`
冷抽取独立复跑，核对 R6 数字是否与 main 实际提交态一致。

参数表（全部为被测包实测规模）：

| 量 | 值 |
|---|---|
| 纯路径 locator 字段（main 实际） | 139 |
| 其中冷启动可解析 | 82 |
| 其中仍用 legacy `runs/m22059/` 前缀 | 51 |
| 其中绝对外域 | 6 |
| 重写后仍不可解析 | 2 |
| manifest 条目 | 18（4 缺失） |
| D6 evidence item | 5（1 缺 input_sha256） |

## ② 怎么做的（方法/流程/工具链）

1. **冷抽取**：`git archive HEAD`（main@53959af，含 Merge #525）解到独立目录，仅 tracked 文件，`runs/` 缺席。
2. **冻结验证器复跑**：`docs/m23257/verify_status.py`（**未改动**，复用 R5 的 `verify_r5.py` 枚举器/D6 走查/
   manifest 审计）对冷抽取树独立重算，输出 `/tmp/m24007_status_evidence.json`。
3. **抽查 ≥3 个修复点实物**：locator 指向文件存在性与 sha256 实算、SHA256SUMS 逐条实算、D6 input_sha256 抽 2 条。
4. **根因定位**：`git merge-base --is-ancestor` 检查 R6 验证证据（`status_after.json`）的 head 是否在 main。

## ③ 计算结果（数字表，程序化注入）

| 指标 | before（m23257@3fbd3b3） | **R6 自报 after** | **实际 after（本席复跑）** |
|---|---|---|---|
| 纯路径字段数 | 144 | 137 | **139** |
| 冷启动可解析 | 17 | 137 | **82** |
| legacy `runs/` 前缀 | 114 | 0 | **51** |
| 绝对外域 | 17 | 0 | **6** |
| 重写后仍不可解析 | 5 | 0 | **2** |
| manifest sound | False | True | **False** |
| D6 缺 input_sha256 | 1 | 0 | **1（ev-kb10k-incompatibility）** |
| D6 source_ref 冷启动可解析 | 0/5 | 5/5 | **0/5** |
| D6 item sha256 与实算一致 | 0/5 | 5/5 | **0/5** |

**根因**：`status_after.json` 的 head=`543881ac`（agent/m23814 分支），`git merge-base --is-ancestor 543881ac HEAD`=**假**。
R6 修复只在未合并分支工作树上发生过；`Merge #525` 只带了 `docs/m23814/` 报告 + `docs/review_m22059_prod_ra/`
部分改动，**未带** `docs/m22059/` 的 locator/D6/raw 修复。

## ④ 结果图

见内嵌图：冻结验证器 9 项指标 before / R6 自报 after / 实际 after 三态对比（柱状图）。

## ⑤ 注意点（踩过的坑/局限）

- **验证证据与提交态脱钩**：R6 把 `status_after.json`（137/137 全绿）入库 main 作"after"证据，但该证据取自
  从未并入 main 的分支；main 上实际文件仍是坏的。这是"验证跑在未提交树上"的经典掩盖。
- **manifest 幽灵条目**：R6 重生成的 `SHA256SUMS` 断言了 4 个未入库 raw 文件的摘要（`e6cee4f…` 等），
  是虚假的存在性声明。
- **幂等声明不成立**：`repair_r6.py`"二次运行 0 变更"只对未合并分支成立；对 main 复跑会再次产生大量变更。
- 本席 psql 角色对 `tensor_maturity_verdicts` 无写权限（与 R5/R6 相同），verdict 以仓内 SQL 落表。

## ⑥ 误差判定（逐项 vs 基准，显式回答）

本单为证据链/可复现性审计，判据是"必须为 0 的不合规计数"，无物理量基准。逐项给出实测率与判据阈值：

| 关键量 | 实测（main） | 判据 | 偏差率 | 是否 <3% |
|---|---|---|---|---|
| 冷启动不可解析的纯路径 locator | 57/139 | 0 | **41.0%** | **否** |
| 仍用 legacy `runs/` 前缀 | 51/139 | 0 | **36.7%** | **否** |
| 绝对外域 | 6/139 | 0 | **4.3%** | **否** |
| manifest 缺失条目 | 4/18 | 0 | **22.2%** | **否** |
| D6 无 input_sha256 | 1/5 | 0 | **20.0%** | **否** |
| D6 source_ref 冷启动不可解析 | 5/5 | 0 | **100.0%** | **否** |

**总判**：R6 自报的"after"在 main 上全部不成立，R5-1/2/3 三残差未闭合，偏差率双位数百分比。
**verdict = `changes_requested`（blocking）**。honest-FAIL：R6 修复未真正落地，本席如实记录。
"""

report = {
    "title": "PROD-RA R7 终审：R6 自报与 main 提交态不符（verification-on-unmerged-branch）",
    "summary": "独立第三方终审（m24007）：用冻结验证器对 main@53959af 冷抽取复跑，R6 自报的 after 数字（137/137 可解析、manifest sound、D6 5/5 全绿）与 main 实际提交态完全不符——实际 82/139 可解析、51 legacy 前缀、6 绝对外域、manifest 4 缺失、D6 ev-kb10k 仍缺 input_sha256。根因：R6 验证证据（status_after.json）生成于从未并入 main 的 agent/m23814 分支（543881ac），Merge #525 未带 docs/m22059/ 修复。verdict=changes_requested（blocking）。",
    "scenario_key": "tensorphysics/prod_ra/r7_terminal_review",
    "mission_id": 24007,
    "tags": ["prod-ra", "r7-terminal-review", "adversarial", "verification-hygiene", "TensorKnowledge"],
    "markdown": markdown,
    "figures": [
        {"name": "r7_before_claimed_actual.png",
         "caption": "冻结验证器 9 项指标：before（main@3fbd3b3）/ R6 自报 after（agent/m23814@543881ac，未合并）/ 实际 after（main@53959af，本席复跑）三态对比。R6 自报的绿色状态在 main 上不成立。",
         "png_base64": fig_b64}
    ],
}

with open("/tmp/report.json", "w") as f:
    json.dump(report, f, ensure_ascii=False)
print("report.json written, size:", os.path.getsize("/tmp/report.json"))

# --- publish ---
req = urllib.request.Request(
    f"{API}/tensor/reports",
    data=json.dumps(report).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST",
)
try:
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode())
        print("publish status:", resp.get("status"), "| id:", resp.get("id"))
except Exception as e:
    print("publish error:", e)
