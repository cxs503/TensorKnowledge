# Task-Kit 契约草案

> 智能体任务包装配规范。GET /task-kit?goal=&method=&domain= 返回分层任务包。

**版本**: 0.1.0-draft  
**状态**: draft  
**本文件**: `docs/ontology/task-kit.md`

---

## 1. 端点

```
GET /task-kit?goal=<string>&method=<enum>&domain=<enum>
```

### 1.1 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `goal` | string | 是 | 任务目标描述，用于匹配 DecisionCard.context.goal |
| `method` | enum | 否 | 方法轴过滤，值见 ontology/v1.md §1.1 |
| `domain` | enum | 否 | 领域轴过滤，值见 ontology/v1.md §1.2 |
| `trust_min` | enum | 否，默认 `reviewed` | 最低信任态：`draft` / `reviewed` / `published` |
| `token_budget` | integer | 否，默认 4096 | 返回包最大 token 数 |

### 1.2 响应结构

```json
{
  "task_kit_id": "tkit:<hash>",
  "query": { "goal": "...", "method": "...", "domain": "..." },
  "assembly": {
    "decision_cards": [...],
    "recipe_cards": [...],
    "pitfall_cards": [...],
    "anchor_cards": [...],
    "method_cards": [...],
    "gap_cards": [...]
  },
  "token_count": 3842,
  "token_budget": 4096,
  "trust_filter": "reviewed",
  "generated_at": "2026-11-10T..."
}
```

---

## 2. 分层装配规则

Task-Kit 按以下层次装配，每层按 `token_budget` 裁剪：

| 层级 | 内容 | 优先级 | 裁剪策略 |
|------|------|--------|---------|
| L0 | DecisionCard（决策卡） | 最高 | 按 goal 匹配度排序，取 top-N |
| L1 | AnchorCard（验证锚） | 高 | 关联到 L0 决策的验证锚 |
| L2 | PitfallCard（坑卡） | 中 | 关联到 L0/L1 的常见错误 |
| L3 | RecipeCard（配方卡） | 中 | 关联到 L0 决策的执行步骤 |
| L4 | MethodCard（方法卡） | 低 | 背景知识，按需加载 |
| L5 | GapCard（缺口卡） | 最低 | 仅当无完整方案时返回 |

### 2.1 装配算法

```
1. 匹配 DecisionCard:
   - 过滤 method_axis / domain_axis（若指定）
   - 过滤 status >= trust_min
   - 按 goal 文本相似度排序
   - 取 top-3（或直到 token 预算的 30%）

2. 关联 AnchorCard:
   - 查找 relations 中 verifies/precondition_of 指向 L0 的 AnchorCard
   - 过滤 status >= trust_min
   - 取 top-2（或直到 token 预算的 25%）

3. 关联 PitfallCard:
   - 查找 relations 中 fixes 指向 L0/L1 的 PitfallCard
   - 过滤 status >= trust_min
   - 取 top-3（或直到 token 预算的 20%）

4. 关联 RecipeCard:
   - 查找 relations 中 supports 指向 L0 的 RecipeCard
   - 过滤 status >= trust_min
   - 取 top-2（或直到 token 预算的 15%）

5. 关联 MethodCard:
   - 查找 relations 中 supports 指向 L0 的 MethodCard
   - 过滤 status >= trust_min
   - 取 top-2（或直到 token 预算的 7%）

6. 关联 GapCard:
   - 查找 method_axis + domain_axis 匹配的 GapCard
   - 仅当 L0-L4 总 token < budget * 0.8 时返回
   - 取 top-1（或直到 token 预算的 3%）

7. 若总 token > budget，从最低优先级层开始裁剪
```

---

## 3. Token 预算计算

每个知识件的 token 估算规则：

| 形态 | 估算公式 |
|------|---------|
| DecisionCard | `200 + 50 × len(options) + 30 × len(decision_criteria)` |
| RecipeCard | `150 + 100 × len(steps)` |
| PitfallCard | `150 + 80 × len(root_causes) + 60 × len(fixes)` |
| AnchorCard | `200 + 50 × len(expected_values)` |
| MethodCard | `200 + 30 × len(parameter_space.dimensions)` |
| GapCard | `150 + 50 × len(attempts)` |

---

## 4. 信任态过滤

默认 `trust_min = reviewed`，即只返回 `status ∈ {reviewed, published}` 的知识件。

| trust_min 值 | 返回的 status | 说明 |
|-------------|--------------|------|
| `draft` | draft, reviewed, published | 包含所有非废弃知识件 |
| `reviewed` | reviewed, published | 默认值，经过至少一次审查 |
| `published` | published | 仅正式发布版本 |

---

## 5. 响应示例

```json
{
  "task_kit_id": "tkit:a1b2c3d4",
  "query": {
    "goal": "Select collision model for high-Re LBM simulation",
    "method": "lbm",
    "domain": "turbulence"
  },
  "assembly": {
    "decision_cards": [
      {
        "id": "tkdc:lbm:collision-space-selection",
        "title": "LBM 碰撞空间选型决策",
        "kind": "decision-card",
        "method_axis": "lbm",
        "domain_axis": "turbulence",
        "status": "published",
        "context": { "goal": "Select collision model for high-Re LBM simulation" },
        "options": [
          { "label": "SRT", "description": "Single Relaxation Time" },
          { "label": "MRT", "description": "Multiple Relaxation Time" },
          { "label": "TRT", "description": "Two Relaxation Time" }
        ],
        "decision_criteria": [
          { "criterion": "stability", "rule": "if Re > 1e5 → MRT or TRT", "priority": 1 }
        ]
      }
    ],
    "anchor_cards": [
      {
        "id": "tkac:lbm:turbulent-channel",
        "title": "Turbulent Channel Flow LBM Benchmark",
        "kind": "anchor-card",
        "method_axis": "lbm",
        "domain_axis": "turbulence",
        "status": "published"
      }
    ],
    "pitfall_cards": [
      {
        "id": "tkpc:lbm:srt-high-re-instability",
        "title": "SRT 高雷诺数不稳定",
        "kind": "pitfall-card",
        "method_axis": "lbm",
        "domain_axis": "turbulence",
        "status": "published"
      }
    ],
    "recipe_cards": [],
    "method_cards": [],
    "gap_cards": []
  },
  "token_count": 1247,
  "token_budget": 4096,
  "trust_filter": "reviewed",
  "generated_at": "2026-11-10T05:30:00Z"
}
```

---

## 6. 与 KE 查询的映射

| Task-Kit 装配步骤 | KE 查询 |
|-------------------|---------|
| 匹配 DecisionCard | Q4 `claims_by_domain` + 文本相似度 |
| 关联 AnchorCard | Q5 `evidence_for_claim`（反向查 verifies 关系） |
| 关联 PitfallCard | Q2 `evidence_by_relation`（查 fixes 关系） |
| 关联 RecipeCard | Q2 `evidence_by_relation`（查 supports 关系） |
| 关联 MethodCard | Q4 `claims_by_domain` + Q5 关系遍历 |
| 关联 GapCard | Q4 `claims_by_domain`（查 gap-card kind） |
