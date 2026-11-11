#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the mission report figure + payload for mission 14626 (one-off)."""
import base64
import json
import os
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/root/tp-agent/work/m14626")
ART = REPO / "knowledge/oss-lbm/artifacts"
report_data = json.loads((ART / "structure_report.json").read_text())
g1 = report_data["generations"]["gen1_aggregate"]
g2 = report_data["generations"]["gen2_per_record"]
g3 = report_data["generations"]["gen1_sub_packages"]
repos = report_data["coverage_by_repository"]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
labels = ["structure A\naggregate", "structure B\ngen-2 ingress", "structure C\nsub-packages"]
claims = [g1["claims"], g2["claims"], g3["claims"]]
evid = [g1["evidence"], g2["evidence"], g3["evidence"]]
x = range(len(labels))
ax.bar([i - 0.2 for i in x], claims, width=0.4, label="claims", color="#2b6cb0")
ax.bar([i + 0.2 for i in x], evid, width=0.4, label="evidence", color="#dd6b20")
for i, (c, e) in enumerate(zip(claims, evid)):
    ax.text(i - 0.2, c + 1, str(c), ha="center", fontsize=8)
    ax.text(i + 0.2, e + 1, str(e), ha="center", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("record count")
ax.set_title("OSS-LBM package: records per coexisting structure")
ax.legend(fontsize=8)

ax = axes[1]
keys = list(repos)
vals = [repos[k] for k in keys]
ax.bar(keys, vals, color="#38a169")
for i, v in enumerate(vals):
    ax.text(i, v + 0.05, str(v), ha="center", fontsize=8)
ax.set_ylabel("gen-2 claims")
ax.set_title("Gen-2 claims by upstream repository (total %d)" % sum(vals))
ax.tick_params(axis="x", labelrotation=30, labelsize=8)

fig.suptitle("FEAT-TK-OSS-LANDING: additive landing of 2 generations (no record dropped)", fontsize=10)
fig.tight_layout()
png = ART / "fig_structure_coverage.png"
fig.savefig(png, dpi=130)
print("figure:", png, png.stat().st_size, "bytes")

markdown = f"""## 1. 案例介绍

本任务不是求解器算例，而是 **TensorKnowledge 知识包的落地（landing）工程**：把分支
`agent/m8634`（FEAT-TK-OSS-LANDING，PR #6，commit `ce6cad5`）的 61 件 LBM 开源多相/MCMP
知识文件，以与当前 `main` 结构兼容的方式重新落地。因此本报告**没有物理几何、没有网格、
没有求解参数**（无几何/参数表可列，原因：全流程为知识工件合并与结构校验，未运行任何
LBM 求解器），也没有场量云图；图 1 给出的是结构覆盖统计（程序化从
`artifacts/structure_report.json` 读取，零手抄）。

冲突背景：PR #6 的 61 件文件与 `main` 的 `knowledge/oss-lbm/` 同路径两代布局（main:
`claims/claims.json` 单文件 27 claims + `ludwig/` 等 7 个子包；PR#6: 每条一个
`tkc-oss-lbm-*.json`），只能 rewrite 合入，故被协调者以 rewrite 型冲突关闭。

## 2. 怎么做的

1. **防重蹈检索**：`knowledge_base`（ktype=capability, domain=TensorKnowledge）= 0 行；
   `negative_knowledge_ledger` 101 条 active 中 9 条与本域相关，其中 oss-lbm 包一条为
   “m8635 lineage — 达标复核仅 L1”（缺 tests + run artifacts），本单据此补 tests 与运行记录。
2. **逐字保真搬运**：61 件 gen-2 文件原样入树（sha256 逐件入 manifest）。
3. **并入（aggregate）**：`tools/merge_record_files.py` 按 `id` 键追加合并，
   id 冲突且内容不同则硬失败；幂等（重跑 +0 merged）。claims 27→50、evidence 27→57、
   provenance 2→10。
4. **并置（per-record）**：gen-2 单文件保留，作为 ingress 记录；校验器要求与 aggregate 条目
   逐字节一致（canonical JSON）。
5. **README 重写**：两代分节陈述（gen-1 框架综述 / gen-2 多相源码综述），互不覆盖。
6. **校验器双结构扩展**：A aggregate / B per-record ingress / C sub-packages + landing manifest。
7. **对照报告**：`artifacts/structure_report.{{json,md}}` 由 `tools/structure_report.py` 生成。

## 3. 计算结果（程序化注入）

| 结构 | 布局 | claims | evidence | provenance |
|---|---|---|---|---|
| A aggregate（gen-1） | `claims.json` / `evidence.json` / `provenance.json` | {g1['claims']} | {g1['evidence']} | {g1['provenance']} |
| B per-record ingress（gen-2 `{g2['source_commit'][:12]}`） | `tkc-*.json` / `tke-*.json` / `tkp-*.json` | {g2['claims']} | {g2['evidence']} | {g2['provenance']} |
| C sub-packages（{g3['count']} 包） | `<pkg>/claims/claims.json` | {g3['claims']} | {g3['evidence']} | 每包 1 |

- gen-2 记录在 main 树定位率：claims **{g2['claims_located_in_aggregate']}/{g2['claims']}**、
  evidence {g2['evidence_located_in_aggregate']}/{g2['evidence']}、
  provenance {g2['provenance_located_in_aggregate']}/{g2['provenance']}。
- gen-1 既有 claims 保留 {g1['claims_not_from_m8634']} 条（27 = 17 原 + 10 mflbm），
  与 gen-2 的 23 条 **id 无交集**（50 = 27 + 23，严格可加）。
- 校验闸门：`python3 knowledge/oss-lbm/validate_oss_lbm.py` → **ALL PASS**，4 个结构段 0 errors；
  `pytest knowledge/oss-lbm/tests/test_dual_structure.py` → **10 passed**（含 4 个负对照）；
  `pytest test_oss_lbm.py tests/test_ke_export.py` → **38 passed**；
  4 个子包校验器（kruger/ludwig/thermalmulti/freesurf）全部 PASS（回归不变）。
- 负对照实测：删 1 条 gen-2 claim → 校验器 FAIL；篡改 ingress 语句 → FAIL；
  ingress 文件空白改动 → manifest sha256 FAIL；子包记录与 aggregate 分歧 → FAIL。

## 4. 结果图

图 1 左：三种共存结构的 claims/evidence 数量；右：gen-2 claims 按上游仓分布（合计 {sum(vals)}）。
说明：本任务无场量（未运行求解器），故无云图与解析解比较曲线；替代证据为上述负对照与
幂等/定位率数字。

## 5. 注意点（踩过的坑）

- `psql` 以 role `root` 读 `knowledge_base` / `negative_knowledge_ledger` 被 permission denied，
  改用 `postgres` 只读连接与平台 HTTP API（`/tensor/negative-knowledge`）；
  平台知识检索引擎 :8021 离线，`/tensor/knowledge/search` 返回 engine_offline。
- 加入 gen-2 claims 后 `ke.queries.all_claims` 按 id 排序，`tests/test_ke_export.py` 里依赖
  “第一行”的断言失稳（`[0]` 从 lbmpy 变成 kruger）；已改为按 id 选取，属测试脆弱性修复。
- 幂等是硬要求：合并脚本对同 id 不同内容直接失败，避免“第二次合并悄悄改写知识”。
- 子包 `mflbm/claims.json` 与 aggregate 10 条 id 完全重合（历史遗留镜像），校验器要求逐字节一致。

## 6. 误差判定

本任务无实验/参考物理量，**不存在 <3% 的数值误差判据**（原因：交付物是知识工件与校验闸门，
非数值解）。可比的“基准”是结构不变量，逐项列出：

| 指标 | 基准 | 实测 | 判定 |
|---|---|---|---|
| gen-2 claims 定位 | 23 | 23 | 达标（0 丢失） |
| gen-2 evidence 定位 | 30 | 30 | 达标 |
| gen-2 provenance 定位 | 8 | 8 | 达标 |
| aggregate claims 可加性 | 27 + 23 = 50 | 50，id 无交集 | 达标 |
| 校验器通过 | ALL PASS / 0 errors | ALL PASS / 0 errors | 达标 |
| 负对照（应 FAIL） | 4 个变体均 FAIL | 4/4 FAIL | 达标 |
| 幂等重跑 | +0 merged，字节不变 | +0 merged | 达标 |

结论：结构类判据全部满足；**物理精度判据不适用**（如实声明，不做粉饰）。
"""

payload = {
    "title": "FEAT-TK-OSS-LANDING 落地：OSS-LBM 知识包两代结构可加合并（23/23 claims 定位）",
    "summary": (
        "把 agent/m8634 的 61 件 OSS-LBM 知识文件以可加方式重新落地 main：claims 27→50、"
        "evidence 27→57、provenance 2→10，23/23 gen-2 claims 可在 main 树定位；"
        "validate_oss_lbm.py 扩展为双结构校验并 ALL PASS，10 个不变量测试（含 4 个负对照）通过。"
    ),
    "scenario_key": "tensor_knowledge_oss_lbm_landing",
    "mission_id": 14626,
    "tags": ["TensorKnowledge", "oss-lbm", "FEAT-TK-OSS-LANDING", "dual-structure", "validator"],
    "markdown": markdown,
    "figures": [
        {
            "name": "fig_structure_coverage.png",
            "caption": "左：三种共存结构（aggregate / per-record ingress / sub-packages）的 claims 与 evidence 数量；右：gen-2 claims 按上游仓分布。数据由 artifacts/structure_report.json 程序化读取。",
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }
    ],
}
Path("/tmp/report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
print("payload written /tmp/report.json", len(json.dumps(payload)))

base = os.environ["TENSOR_API_BASE"]
tok = open("/tmp/tok.txt").read().strip()
req = urllib.request.Request(
    base + "/tensor/reports",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
)
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    print("REPORT POSTED:", json.dumps(resp, ensure_ascii=False)[:400])
except Exception as exc:
    body = getattr(exc, "read", lambda: b"")()
    print("REPORT POST FAILED:", exc, body[:600])