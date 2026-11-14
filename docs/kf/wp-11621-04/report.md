# KF-RESULT wp-11621-04

**工作包**: wp-11621-04 · 04-independent-review  
**报告ID**: 11621  
**审核对象**: wp-11621-01（资产登记工序产物）  
**审核者**: agent/m19822  
**完成日期**: 2026-11-13  

tags: `kf-wp:wp-11621-04` `FVM` `numerical-viscosity` `independent-review` `lane-C`

---

## ① 本工序做了什么

对 report_id=11621（TensorFVM 数值黏性/色散算子验证面）执行独立审核（adversarial-review）。审核范围限于报告 markdown 原文及其内部声明的自洽性，不访问生产者解释/上下文。逐项核查 6 项验收判据 (a)-(f) 的数值自洽性、理论公式正确性、产物引用可达性，产出 severity-ranked findings 列表与审核决策。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取原文**：通过平台 API `GET /api/v1/tensor/reports/11621` 拉取 markdown 字段，独立重算 sha256 与 contract source_hash 比对（一致 ✓）。
2. **读取上游产物**：读取 `docs/kf/wp-11621-01/` 下的 `kf_result.json`、`asset_manifest.json`、`verification.json`，确认上游工序已完成且验证通过。
3. **理论公式手算核对**：
   - Upwind ν_th = cΔx(1-C)/2 → 无量纲化后 (1-C)/2 = 0.4/0.25/0.1（C=0.2/0.5/0.8）✓
   - CD2 |G| = √(1+C²sin²θ) → C=0.5,θ=π/2: √1.25≈1.118 ✓；C=0.8,θ=π/2: √1.64≈1.281 ✓
   - 网格收敛比值：0.125/0.250=0.500, 0.0625/0.125=0.500, 0.0313/0.0625≈0.501 ✓
   - QUICK ν_th = cΔx(1-C)(1-C²)/8 为标准修正方程结果 ✓
4. **产物可达性检查**：遍历 asset_manifest.json 中所有资产的 resolution.status，发现 5 个 unresolved 引用。
5. **判定分类**：按 severity（medium/low/info）对发现排序，区分 blocking 与 non-blocking 问题。

**关键设置**：
- 审核者上下文 = 报告原文 + 上游 KO，排除生产者解释
- 不将任何声明标记为 verified（verification 由平台门计算）
- 所有引文逐字来自报告 markdown

## ③ 产出物清单

| 输出文件 | 要点 |
|----------|------|
| `docs/kf/wp-11621-04/review_report.json` | 审核决策（approve_with_notes）、5 项 severity-ranked findings、9 项已执行检查、5 项未执行检查、独立性局限声明 |
| `docs/kf/wp-11621-04/review_events.json` | 5 条审核事件账本（review_started → hash_verified → claim_analysis → artifact_probe → review_completed） |

## ④ 证据定位表

| Claim / 字段 | 原文引文片段（逐字） | 行号 | 审核结论 |
|--------------|---------------------|------|----------|
| Upwind ν_th 公式 | `Upwind: ν_th = cΔx(1-C)/2` | §2.2 | ✓ 标准修正方程结果 |
| Upwind ν_th 表格值 | `0.400 / 0.250 / 0.100` | §3.1 | ✓ 对应 (1-C)/2（已无量纲化） |
| CD2 |G| 公式 | `\|G\| = √(1 + C²sin²θ)` | §3.4 | ✓ 手算验证通过 |
| CD2 |G| 数值 | `C=0.5: \|G\| = 1.118` | §3.4 | ✓ √1.25≈1.118 |
| CD2 |G| 数值 | `C=0.8: \|G\| = 1.281` | §3.4 | ✓ √1.64≈1.281 |
| 网格收敛比值 | `0.500 / 0.500 / 0.501` | §3.5 | ✓ 手算验证通过 |
| L-W 阈值标注 | `阈值: 1e-2` | §3.3 | ⚠ F1：判据原文为 1e-2·cΔx |
| ν 量纲声明 | （无） | §3.1-3.5 | ⚠ F2：未声明已无量纲化 |
| 结果图引用 | `![Von Neumann Amplification Factor](fig1_von_neumann.png)` | §4.1 | ⚠ F3：文件未解析 |
| 测试声明 | `pytest tests/test_numerical_viscosity.py -v，57 passed` | §8 | ⚠ F4：测试文件未解析 |
| 自报结论 | `✅ 全部验收判据通过` | 标题 | ℹ F5：生产者自报，非独立验证 |

## ⑤ 注意点与局限

1. **独立性局限**：审核者无法访问求解器源代码、测试代码、JSON 产物文件和结果图，所有验证基于报告内自洽性检查和已知理论公式的手算核对。
2. **未执行检查**：独立重跑数值实验、独立运行 pytest、独立生成 von Neumann 曲线、JSON 产物结构验证、2D 交叉导数项独立验证——均因文件未解析而无法执行。
3. **文档清晰度问题**：F1（L-W 阈值标注不一致）和 F2（ν 量纲未声明）不影响数值结论正确性，但降低报告可读性。
4. **交付物可达性**：F3/F4 指出 5 个引用资产在交付工作树中未解析，影响可复现性，但非报告内容错误。
5. **无 blocking 问题**：所有发现均为 medium/low/info 级别，无 correctness 或 security 级别的 blocking 问题。

## ⑥ 自检：逐条对照 acceptance

| Acceptance 项 | 状态 | 说明 |
|---------------|------|------|
| valid_json | ✅ | review_report.json 通过 JSON 解析，字段完整 |
| schema_pass | ✅ | 符合 kf_result.v1.schema.json 结构（package_id/task_type/report_id/provenance/outputs 齐全） |
| reviewer_independent | ✅ | 审核者上下文 = 报告原文 + 上游 KO，未访问生产者解释 |
| upstream_packages_completed | ✅ | wp-11621-01 verification.json 显示 all_ok=true |
| source_hash_matches | ✅ | 独立重算 sha256 与 contract source_hash 一致 |
| do_not_mark_claims_as_verified | ✅ | 审核决策为 approve_with_notes，未将任何声明标记为 verified |
| review_prompt_not_copied_from_producer | ✅ | 审核流程独立执行，未复制生产者提示 |

**结论**：全部 acceptance 项通过 ✅

---

```json
{
  "package_id": "wp-11621-04",
  "task_type": "04-independent-review",
  "report_id": "11621",
  "provenance": {
    "source_uri": "tensor://reports/11621",
    "source_field": "markdown",
    "source_hash": "sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb",
    "source_hash_matches": true,
    "title": "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + 离散放大因子 G(θ) 全域比对",
    "scenario_key": "p73w3-n04-fvm-numerical-viscosity",
    "chars": 7198
  },
  "outputs": {
    "review_report.json": {
      "reviewer": "agent/m19822",
      "reviewed_at": "2026-11-13T00:00:00+00:00",
      "upstream_package": "wp-11621-01",
      "upstream_status": "completed",
      "disposition": "approve_with_notes",
      "severity_ranked_findings": [
        {
          "id": "F1",
          "severity": "medium",
          "likelihood": "high",
          "category": "documentation_clarity",
          "claim": "验收判据 (c) Lax–Wendroff 阈值列标注为 '1e-2'，但判据原文为 '|ν| < 1e-2·cΔx'",
          "evidence": "报告 §3.3 表格中 '阈值' 列统一写为 '1e-2'，而 §2.2 判据定义为 '|ν| < 1e-2·cΔx'。若 cΔx ≠ 1，则表格阈值与实际判据阈值不一致。",
          "affected_scope": "§3.3 表格可读性；不影响数值结论（ν_meas 量级 1e-4~7e-4 远小于 1e-2·cΔx 对任何合理 cΔx）",
          "remediation": "表格阈值列应标注为 '1e-2·cΔx' 或将 ν_meas 明确标注为已归一化（除以 cΔx）"
        },
        {
          "id": "F2",
          "severity": "medium",
          "likelihood": "high",
          "category": "dimensional_ambiguity",
          "claim": "数值黏性表格中 ν_meas 和 ν_th 的量纲/归一化方式未显式声明",
          "evidence": "§3.1 表格中 Upwind ν_th 列值为 0.400/0.250/0.100，对应 (1-C)/2 而非 cΔx(1-C)/2。说明表格中的 ν 值已除以 cΔx 做了无量纲化，但表格标题和表头未声明这一点。",
          "affected_scope": "§3.1, §3.3, §3.4, §3.5 所有数值表格",
          "remediation": "在表格标题或表头注明 'ν 值为无量纲形式（已除以 cΔx）' 或改为显示有量纲值"
        },
        {
          "id": "F3",
          "severity": "low",
          "likelihood": "medium",
          "category": "unresolved_artifacts",
          "claim": "报告引用的 3 张结果图和核心代码/产物文件在交付工作树中未解析",
          "evidence": "上游 wp-11621-01 asset_manifest.json 中 r11621:ref:02~04 (figures) 和 r11621:ref:05~07 (code/artifacts) 的 resolution.status 均为 'unresolved'",
          "affected_scope": "可复现性；审核者无法独立查验图像和代码",
          "remediation": "将图像和代码产物纳入交付工作树，或在报告中提供可访问的外部链接"
        },
        {
          "id": "F4",
          "severity": "low",
          "likelihood": "low",
          "category": "verification_gap",
          "claim": "报告声称 'pytest 57 passed'，但测试文件在交付工作树中不可达",
          "evidence": "asset_manifest.json 中 r11621:ref:06 resolution.status = 'unresolved'",
          "affected_scope": "测试声明的可验证性",
          "remediation": "将测试文件纳入交付物，或提供测试输出日志作为附件"
        },
        {
          "id": "F5",
          "severity": "info",
          "likelihood": "high",
          "category": "self_reported_verification",
          "claim": "报告标题声明 '✅ 全部验收判据通过'，但此为生产者自报",
          "evidence": "报告正文 §6.1 误差判定表中所有判据均标 '✅ 是'，但审核者未独立重算",
          "affected_scope": "声明的权威性；不影响报告内部一致性",
          "remediation": "无（此为产线设计：verification 由平台门计算）"
        }
      ],
      "checks_performed": [
        "sha256 哈希独立重算：与 contract source_hash 一致",
        "报告内部数值自洽性检查：Upwind ν_th 表格值与 (1-C)/2 一致",
        "von Neumann 放大因子公式验证：CD2 的 |G| 手算与报告值一致",
        "网格收敛比值验证：0.500/0.500/0.501 手算通过",
        "QUICK 修正方程公式核查：标准结果",
        "验收判据阈值一致性检查：发现 F1/F2",
        "产物引用可达性检查：发现 F3/F4",
        "报告结构完整性：9 章节完整，六要素齐全",
        "上游 wp-11621-01 验证状态确认：all_ok=true"
      ],
      "checks_not_run": [
        "独立重跑数值实验（无求解器代码访问权限）",
        "独立运行 pytest 测试套件（测试文件未解析）",
        "独立生成 von Neumann 曲线图（代码未解析）",
        "JSON 产物结构验证（artifacts/fvm_modified_equation.json 未解析）",
        "2D 交叉导数项 ν_xy 的独立验证（仅报告描述，无数据）"
      ],
      "overstated_claims": [
        {
          "claim": "✅ 全部验收判据通过",
          "issue": "此为生产者自报结论，非独立验证结果。数值在报告内自洽，但未经第三方重算确认。",
          "severity": "info"
        }
      ],
      "independence_limitations": [
        "审核者未访问生产者解释/上下文（符合 adversarial-review 要求）",
        "审核者无法访问求解器源代码",
        "审核者无法访问测试代码和测试输出日志",
        "审核者无法访问 JSON 产物文件进行结构验证",
        "审核者无法访问结果图进行视觉验证",
        "所有数值验证基于报告内自洽性检查和已知理论公式的手算核对"
      ],
      "scope": "仅审核 report_id=11621 的 markdown 内容及其内部声明的自洽性",
      "decision_rationale": "报告在数值自洽性、理论公式正确性、验收判据逻辑上无实质性错误。发现的 5 项问题中：F1/F2 为文档清晰度问题，F3/F4 为交付物可达性问题，F5 为产线设计固有特性。无 blocking correctness 问题。建议 approve with notes。"
    },
    "review_events.json": [
      {"event_id": "re-001", "timestamp": "2026-11-13T00:00:00+00:00", "event_type": "review_started", "detail": "开始独立审核 report_id=11621"},
      {"event_id": "re-002", "timestamp": "2026-11-13T00:00:00+00:00", "event_type": "hash_verified", "detail": "sha256 独立重算确认与 contract 一致"},
      {"event_id": "re-003", "timestamp": "2026-11-13T00:00:00+00:00", "event_type": "claim_analysis", "detail": "完成 6 项验收判据逐一核查，发现 F1/F2"},
      {"event_id": "re-004", "timestamp": "2026-11-13T00:00:00+00:00", "event_type": "artifact_probe", "detail": "检查上游 asset_manifest，发现 5 个引用资产未解析"},
      {"event_id": "re-005", "timestamp": "2026-11-13T00:00:00+00:00", "event_type": "review_completed", "detail": "disposition=approve_with_notes，5 项发现，无 blocking 问题"}
    ]
  }
}
```

---

**repro_cmd**: `cd /root/tp-agent/work/m19822 && python3 -c "import json; d=json.load(open('docs/kf/wp-11621-04/review_report.json')); print('disposition:', d['outputs']['review_report.json']['disposition']); print('findings:', len(d['outputs']['review_report.json']['severity_ranked_findings']))"`
