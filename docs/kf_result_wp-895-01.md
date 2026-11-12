# KF-RESULT wp-895-01

**tags**: kf-wp:wp-895-01, 01-asset-registration, report:895, lane:C, draft
**date**: 2026-11-12
**agent**: agent/m15521
**repo**: TensorKnowledge
**branch**: agent/m15521

---

## 1. 本工序做了什么

本工作包 `wp-895-01` 为 **01-asset-registration**（资产登记）工序，仅处理 `report_id=895` 一份报告（W7-N10 冰盖对破冰船冲击的动态响应，scenario_key=`ice_cover_bow_impact`）。目标：确认报告 ID 与其 markdown 字节哈希的对应关系，列出可解析的附件/工件，**不做内容抽取**（claims 为空数组，契约允许）。

## 2. 怎么做的（步骤/工具/关键设置）

1. **读取工作包契约**：从任务指令提取 YAML 契约，确认 `package_id=wp-895-01`、`report_id=895`、`source_hash=sha256:31f6794e…166b39`、`chars=9459`、`scenario_key=ice_cover_bow_impact`。
2. **获取源报告**：平台 API `GET $TENSOR_API_BASE/tensor/reports/895`（Bearer 认证，登录 eco_admin），取 `markdown` 字段；未读/写其它 report_id。
3. **独立验证哈希**：Python `hashlib.sha256(markdown.encode('utf-8'))` 重算，得 `31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39`，与契约 `source_hash` **完全一致**；`len(markdown)=9459` 与契约 `chars` 一致。
4. **登记附件**：报告 JSON `figures` 数组 6 张 PNG（name+caption 逐字取自元数据）。
5. **登记工件**：正文引用的 7 项工件（criteria.json / history_elastic.csv / history_fracture.csv / contact_patch_sensitivity.json / impact_animation.gif / src/tensorphysics/ice/ / tests/test_ice_*.py），每项 locator 为 markdown 逐字子串（脚本断言 `locator in md` 通过）；宿主为 TensorPhysics 仓分支 agent/m1138，本仓不可直接解析，标 `resolvable=referenced_only`。
6. **生成产物**：`artifacts/wp-895-01/asset_manifest.json` + 结果信封（按 `kf_result.v1.schema.json` 校验通过，jsonschema 4.26.0）。
7. **自检**：逐条对照 acceptance（见 §6）。

## 3. 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| asset_manifest.json | `artifacts/wp-895-01/asset_manifest.json` | 报告 895 资产登记：source_hash（已验证匹配）、title、chars=9459、attachments=6 项、artifacts=7 项（referenced_only）、claims=[] |
| 结果 JSON | 本报告内唯一的 json 代码块 | kf_result v1 信封：package_id/task_type/report_id/provenance/outputs/claims |
| 构建脚本 | `runs/wp-895-01/build_result.py` | 一键复跑：拉报告→验哈希→建 manifest→schema 校验→落盘 |
| 源报告快照 | `runs/wp-895-01/source_report_895.md` | API 取回的 markdown 原文（sha256 与契约一致） |

## 4. 证据定位表

| claim / 字段 | 原文引文片段（来源） | 定位 |
|---|---|---|
| package_id | `package_id: wp-895-01` | 任务契约 YAML |
| task_type | `task_type: 01-asset-registration` | 任务契约 YAML |
| report_id | `report_id: '895'` | 任务契约 YAML |
| source_uri | `source_uri: tensor://reports/895` | 任务契约 YAML |
| source_hash | `source_hash: sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39` | 任务契约 YAML |
| title | `title: W7-N10 冰盖对破冰船冲击的动态响应：弹性板-流体耦合 + 冲击时程 + 弯曲断裂判据 + 裂纹萌生位置` | 任务契约 YAML（与 API title 逐字一致） |
| scenario_key | `scenario_key: ice_cover_bow_impact` | 任务契约 YAML |
| chars | `chars: 9459` | 任务契约 YAML（API 重算 len=9459 一致） |
| source_hash verified | `sha256=31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39`（hashlib 独立重算） | API 取回 markdown 后计算 |
| attachments (6 figures) | `"name": "fig1_dispersion.png"` … `"name": "fig6_supersonic_waves.png"` | 报告 JSON `figures` 数组（caption 逐字） |
| artifact: criteria.json | `全部由 `artifacts/m1138/criteria.json` 程序化产出，零手抄` | 报告 §3 标题行 |
| artifact: history_*.csv | `` `history_elastic.csv`、`history_fracture.csv` `` | 报告 §6 产物行 |
| artifact: contact_patch_sensitivity.json | `静态敏感性（`contact_patch_sensitivity.json`，P=4.73 MN，dx=1.5 m）` | 报告 §5.4 |
| artifact: impact_animation.gif | `` `impact_animation.gif` | 冲击过程挠度/应力场动画（23 帧）`` | 报告 §3.7 图表 |
| artifact: 模块目录 | `**模块**: `src/tensorphysics/ice/`（新建领域目录，TensorPhysics 工作树）` | 报告头 |
| artifact: 测试面 | `PYTHONPATH=src python -m pytest tests/test_ice_*.py -q         # 36 用例` | 报告 §6 复现方式 |
| claims=[] | `claims 允许为空数组` | 任务契约 notes 字段 |

## 5. 注意点与局限

- **哈希已独立验证**：API 取回 markdown 后 Python hashlib 重算 sha256=`31f6794e…166b39`，与契约值完全一致；`len(markdown)=9459` 与契约 `chars` 一致。
- **附件仅登记元数据**：6 张 PNG 的 name/caption 逐字取自报告 JSON `figures` 数组；PNG 字节未下载校验（契约未提供工件 URI）。
- **工件为正文引用**：7 项工件（criteria.json、2×history CSV、contact_patch_sensitivity.json、impact_animation.gif、模块目录、测试面）宿主在 TensorPhysics 仓分支 agent/m1138，本仓不可直接解析，故标 `resolvable=referenced_only` 并附逐字 locator。
- **零抽取**：本工序为纯资产登记，claims=[]（契约允许），未做 claim 提取/分类/内容分析，未把任何结论标为 verified。
- **未越界**：仅读取 report_id=895，未读/写/覆盖其它 report_id 的产物。
- **标题差异**：API/契约标题为「冲击时程」，markdown H1 为「船首冲击时程」；manifest 采用 API 标题（权威源）。

## 6. 自检（acceptance 逐条对照）

| 条件 | 状态 | 说明 |
|---|---|---|
| valid_json | ✓ | 结果 JSON 经 `json.dumps`/`json.loads` 往返验证 |
| schema_pass | ✓ | jsonschema 4.26.0 对 kf_result.v1.schema.json 校验通过（additionalProperties=false 顶层无多余键） |
| source_locator_resolvable | ✓ | `tensor://reports/895` 经 API 实际取回；7 项工件 locator 均为 markdown 逐字子串（脚本断言） |
| source_hash_matches | ✓ | 独立重算 sha256=`31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39`，与契约一致 |
| no_duplicate_ids | ✓ | report_id 唯一；attachments/artifacts 名称无重复（脚本断言） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims 为空数组（契约允许），无未解决声明 |

**误差判定**：本工序唯一量化核对=源 markdown 字节哈希，独立重算与契约值**精确一致**（偏差 0，<3% 平凡成立）；无其它数值比较（零抽取、零计算，无基准需求）。

**无图说明**：本工序为纯资产登记（无计算/无场量），不产生云图或比较曲线，故 figures 为空——符合「纯文档任务无图须写明理由」要求。

---

## 结果 JSON

```json
{
  "package_id": "wp-895-01",
  "task_type": "01-asset-registration",
  "report_id": "895",
  "provenance": {
    "source_uri": "tensor://reports/895",
    "source_field": "markdown",
    "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
    "producer": "agent/m15521",
    "emitted_at": "2026-11-12T01:10:23Z",
    "notes": "hash independently recomputed from API-fetched markdown; matches contract source_hash"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-895-01",
      "report_id": "895",
      "source_uri": "tensor://reports/895",
      "source_field": "markdown",
      "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
      "title": "W7-N10 冰盖对破冰船冲击的动态响应：弹性板-流体耦合 + 冲击时程 + 弯曲断裂判据 + 裂纹萌生位置",
      "scenario_key": "ice_cover_bow_impact",
      "chars": 9459,
      "mission_id": 1138,
      "report_status": "published",
      "registered_at": "2026-11-12T01:10:23Z",
      "registered_by": "agent/m15521",
      "attachments": [
        {
          "name": "fig1_dispersion.png",
          "caption": "Flexural-gravity dispersion of the ice plate on water: analytic $\\omega^2=(Dk^4+\\rho_w g)/(\\rho_i h+m_a(k))$ vs. the numerical wave (wavelength error 0.001%, group velocity error 0.00%).",
          "source": "report_figures_metadata"
        },
        {
          "name": "fig2_static_hetenyi.png",
          "caption": "Verification of the steady plate-on-fluid deflection against the Hetényi/Kelvin-function solution (independent Hankel quadrature); best centre-deflection error 0.22%, profile error 0.42%.",
          "source": "report_figures_metadata"
        },
        {
          "name": "fig3_impact_history.png",
          "caption": "Coupled impact time history: contact force, ship deceleration, penetration and peak bottom stress (peak load 4.73 MN, duration 3.23 s).",
          "source": "report_figures_metadata"
        },
        {
          "name": "fig4_fracture_fields.png",
          "caption": "Fields at the instant of flexural fracture: deflection, bottom-surface maximum principal stress with the predicted radial crack initiation point and the predicted ring-crack circle, and the radial bottom/top stress profiles.",
          "source": "report_figures_metadata"
        },
        {
          "name": "fig5_energy_ledger.png",
          "caption": "Energy ledger of the impact: ship kinetic energy released vs. plate strain+buoyancy+kinetic energy, fluid kinetic energy, crushing work and damping loss; residual and impulse-momentum error annotated.",
          "source": "report_figures_metadata"
        },
        {
          "name": "fig6_supersonic_waves.png",
          "caption": "Flexural wave radiation by a load moving faster than the minimum phase speed of the ice-coupled system: deflection field and the underwater potential-flow pressure field.",
          "source": "report_figures_metadata"
        }
      ],
      "artifacts": [
        {
          "name": "criteria.json",
          "referenced_path": "artifacts/m1138/criteria.json",
          "locator": "全部由 `artifacts/m1138/criteria.json` 程序化产出，零手抄",
          "locator_section": "§3",
          "resolvable": "referenced_only",
          "note": "判据数字 + 全部用例参数；宿主=TensorPhysics 仓分支 agent/m1138，本仓不可直接解析"
        },
        {
          "name": "history_elastic.csv",
          "referenced_path": "artifacts/m1138/history_elastic.csv",
          "locator": "`history_elastic.csv`、`history_fracture.csv`",
          "locator_section": "§6",
          "resolvable": "referenced_only",
          "note": "弹性算例冲击时程 CSV；宿主=TensorPhysics 仓分支 agent/m1138"
        },
        {
          "name": "history_fracture.csv",
          "referenced_path": "artifacts/m1138/history_fracture.csv",
          "locator": "`history_elastic.csv`、`history_fracture.csv`",
          "locator_section": "§6",
          "resolvable": "referenced_only",
          "note": "断裂算例冲击时程 CSV；宿主=TensorPhysics 仓分支 agent/m1138"
        },
        {
          "name": "contact_patch_sensitivity.json",
          "referenced_path": "artifacts/m1138/contact_patch_sensitivity.json",
          "locator": "静态敏感性（`contact_patch_sensitivity.json`，P=4.73 MN，dx=1.5 m）",
          "locator_section": "§5.4",
          "resolvable": "referenced_only",
          "note": "接触斑抹平敏感性数据；宿主=TensorPhysics 仓分支 agent/m1138"
        },
        {
          "name": "impact_animation.gif",
          "referenced_path": "artifacts/m1138/impact_animation.gif",
          "locator": "`impact_animation.gif` | 冲击过程挠度/应力场动画（23 帧）",
          "locator_section": "§3.7",
          "resolvable": "referenced_only",
          "note": "23 帧动画；未列入报告 figures 元数据，仅正文引用"
        },
        {
          "name": "src/tensorphysics/ice/",
          "referenced_path": "src/tensorphysics/ice/ (TensorPhysics 工作树, 分支 agent/m1138)",
          "locator": "**模块**: `src/tensorphysics/ice/`（新建领域目录，TensorPhysics 工作树）",
          "locator_section": "报告头",
          "resolvable": "referenced_only",
          "note": "领域模块目录；宿主=TensorPhysics 仓分支 agent/m1138"
        },
        {
          "name": "tests/test_ice_*.py",
          "referenced_path": "tests/test_ice_*.py (6 个测试文件, 36 个用例)",
          "locator": "PYTHONPATH=src python -m pytest tests/test_ice_*.py -q         # 36 用例",
          "locator_section": "§6",
          "resolvable": "referenced_only",
          "note": "测试面；宿主=TensorPhysics 仓分支 agent/m1138"
        }
      ],
      "claims": [],
      "notes": "Asset registration only — no claim extraction performed (contract: claims 允许为空数组). Source hash independently recomputed from API-fetched markdown (match confirmed). 6 figure attachments from report `figures` metadata; 7 further artifacts are referenced in the markdown body but hosted in the TensorPhysics repo (branch agent/m1138), hence resolvable=referenced_only with verbatim locators. API title matches contract title exactly; the markdown H1 adds 船首 before 冲击时程 (API/contract title used as authoritative)."
    }
  },
  "claims": []
}
```

---

**repro_cmd**（一键复跑：登录→取报告→验哈希→重建 manifest→schema 校验）:

```bash
cd <worktree> && python3 runs/wp-895-01/build_result.py
```
