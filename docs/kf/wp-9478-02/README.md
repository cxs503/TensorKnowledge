# wp-9478-02 — 报告 9478 分类解析（工序 02）

工作包契约：`contract.yaml`（与派单 YAML 逐字一致）。源报告：`tensor://reports/9478`
（`markdown`，`sha256:133dbe58…c1599e28`，5748 字符）。lane B，delivery status=draft。

## 判定（可反驳假设，未标 verified）

| 项 | 值 |
|---|---|
| report_type | `scientific-computation`（confidence=medium） |
| selected_skill | `xsk-scientific-computation`（registry `extraction-skills/registry.json`，lifecycle=template-created） |
| 加权得分 | 12.0；次高 `algorithm-implementation` 4.5、`experimental-validation` 4.0 |
| 计分权重（先定后算） | registry 关键词 ×1.0、applies_to 章节命中 ×0.5、语义锚点 ×2.0（弱锚 ×1.0） |
| claims / evidence / unresolved | 13 / 30 / 8 |

主判依据：正文同时有数值格式方程（Aitken Δ² 更新式）、带单位参数表、时间步收敛研究、
误差对参照值逐项表、显式模型假设 —— 正是 `xsk-scientific-computation` 三步抽取的输入形态。
`experimental-validation` 保留为竞争假设：有基准校验场景与基线比较表，但无设施/测量不确定度/
重复试验。类型判定的正确率**无 ground truth**（`unres-9478-02-U7`），不作通过声明。

## 产出物

| 文件 | 内容 |
|---|---|
| `classification.json` | 主工件：类型判定 + 六类候选评分 + 结构切分 + 13 claims + 30 证据 locator + 8 unresolved |
| `checks.json` | 契约 acceptance 逐条自检（`schema_pass` 记 not_run，理由见文件） |
| `verify.json` | 独立复核：重登录取源、重算哈希、重解每个 locator、`schemas/kf_result.v1.schema.json` |
| `kf_result.json` | 交付载荷（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`） |
| `classification_table.md` | 30 条证据的 quote + 字符区间 + 字节区间 + sha256(quote) 定位表 |
| `figures/fig1_structure_map.png` | 7 个二级章节的字符区间（结构切分可核验） |
| `figures/fig2_candidate_scores.png` | 六类候选加权评分（判定可复核） |
| `source/report_9478.md`、`source/record.json` | 源 markdown 与平台记录元数据（哈希钉住） |
| `scripts/` | `generate_classification.py`（取源+分类+自检）、`verify_result.py`（独立复核）、`build_report.py`（出图+报告载荷） |
| `repro.sh` | 一键复跑（`--refresh` 重取源，`--post` 发布报告） |
| `KF-RESULT-wp-9478-02.md` | 提交用的报告正文（六段 + 唯一一个 JSON 块） |

## 零手抄做法

每条证据的 `quote` 都由源码**行切片**生成（`lines[a-1:b]`），字符/字节偏移与
`content_hash = sha256(quote)` 全部由脚本计算；写盘前断言 `text[start:end] == quote`，
落盘后 `verify_result.py` 再用**重新取回**的源字节重解一遍，不一致即非零退出。
报告正文里的每个数字都从 `classification.json` / `checks.json` / `verify.json` 注入。

## 本工序记录的原文缺陷（只记录，不代修）

* Figures 章节 4 条图注名称位为空，记录 metadata 却有 4 条具名图（`fsi2_*`），正文出现
  `fsi2` 0 次 → 图注↔图文件只能按位置猜（`unres-9478-02-U3`）。
* 记录 title/tags 带 `TensorFEM`，正文 0 次；`TensorLBM` 仅出现在 Future Work（`cls-9478-02-13`）。
* 验收表 C3 写 `tracked` 却标 PASS、C4/C5 只给不等式、C8（Honest FAIL 行）也标 PASS。
* C2 幅度误差记 6.13%，按报告自身数值复算 6.14%；C6 又写 6.07%。
* Flutter 项计算列与参考列同为 6.325 却标 `<2%`（自我比较）。
* Audit Chain 断言 38 / 162 tests 全过，但无命令/链接；Code 与 Figures 两行为空。

## 复跑

```bash
bash docs/kf/wp-9478-02/repro.sh            # 用缓存源（仍逐字节校验哈希）
bash docs/kf/wp-9478-02/repro.sh --refresh  # 重新从平台取源
bash docs/kf/wp-9478-02/repro.sh --post     # 额外发布平台报告
```

凭证只从 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读取，不写入任何文件。