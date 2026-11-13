# wp-7216-01 · 交付审计记录（自审 / adversarial-review）

**对象**：工作包 `wp-7216-01`（01-asset-registration，report 7216）的全部交付物，以及已发布结果报告
`id=14696`（标题 `KF-RESULT wp-7216-01`，tag `kf-wp:wp-7216-01`）。
**独立性限制**：本审计由产出入的作者执行，**不是**独立复核（契约 `review.required: false`）。结论只能当作
"作者已自查并公开自己的弱点"，不能当作第三方保证。平台门仍会独立重算 hash / 定位点 / taxonomy。

## 1. 审了哪些东西、怎么审的

| 检查 | 手段 | 结果 |
|---|---|---|
| 已发布报告是否只有一个 json 块、能否解析 | 从平台 **读回** `GET /tensor/reports/14696`（不是本地缓冲）提取块并 `json.loads` | 1 块，可解析 |
| 块是否符合 `schemas/kf_result.v1.schema.json` + 本包 manifest 结构 pin | `jsonschema` Draft2020-12 / Draft-07 | 0 错误 |
| `provenance.source_hash` 是否等于 report 7216 的**实时** markdown 字节哈希 | 重新拉 `GET /tensor/reports/7216` 重算 | 一致（`sha256:34538b9b…1b9e0b`） |
| 40 个定位点能否在实时 markdown 上重解析 | `md[char_start:char_end] == quote` 且 `sha256(quote)` 匹配 | 40/40 |
| id / key 是否重复 | 集合计数 | 无重复 |
| claims 是否为空且给出理由 | 读 `claims_empty_reason` | 空 + 理由在 |
| 已发布块的文本是否与仓内 `kf_result.json` 逐字节一致 | 字符串比较 | 一致（仅尾空白差异） |
| 图是否真的落库 | `GET /tensor/reports/14696/figures/wp721601_source_locator_map.png` | HTTP 200，249117 B |

复跑：`python3 scripts/kf_wp721601_gate_sim.py 14696` → `docs/kf/wp-7216-01/gate_sim.json`（`all_ok=true`）。

## 2. 按严重度排序的发现

| # | 严重度 | 发现 | 证据 | 处置 |
|---|---|---|---|---|
| F1 | 非阻断（记录） | **定位粒度=整行**：同一行上多个 token 的资产共享同一 `char_start/char_end`（例：A27 `artifacts/in31_n12/rb_lattice_nyN.json` 与 A28 `benchmarks/…/run_bench.py` 同为 §6 表行 L198）。区分靠 `token` 字段，不靠区间。 | `asset_manifest.json` 中 A27/A28、A30/A31/A32、A33/A34、A38/A39 的 `locator` | 保留。验收项 `source_locator_resolvable` 要求"可解析"，整行区间满足；若下游需要 token 级区间，按 `line_start` + `token` 求 `md.find(token, line_start)` 即可，属增量改进。**未在本版实现**——发布后再改会让已发布块与仓内清单分叉，故冻结本版并在此登记。 |
| F2 | 非阻断（记录） | `locator.unique` 统计的是**整行引文**是否在源内唯一（40/40 为真），不是 token 唯一性。 | 同上；`integrity.quote_uniqueness` | 在 ⑤ 与本节明写，不当作 token 唯一性使用。 |
| F3 | 非阻断 | 旁证探针 `ecosystem_presence_probe.json` 依赖本机 `/root/tp-agent/work` 的文件系统快照，**不可跨环境复现**。 | 探针文件 `probe_root` 字段 | 明确标 `status: non_contract_probe`，且**不参与** `resolution` 判定；复跑到别的机器只会得到不同的存在性统计，不影响 acceptance。 |
| F4 | 非阻断 | manifest 的 `schema_pass` 用的是本包**重新参数化**的结构 pin（`asset_manifest.schema.json`），因为仓内 wp-448 先例 schema 把 `package_id/report_id` 写死。平台若另有权威 schema，结论可能不同。 | `docs/kf/wp-7216-01/asset_manifest.schema.json` 文件头说明 | 以平台门为准；未声称"平台级 schema 通过"。 |
| F5 | 已修复（开发期缺陷） | 渲染器的 `call()` 把 HTTP 响应截断到 400 字符再 `json.loads`，登录响应更长时抛 `JSONDecodeError`——首批投稿会因此失败而不是产出错误数据。 | 失败栈 `Unterminated string starting at … char 244` | 改为返回完整响应体、仅在打印时截断；此修复先于最终发布（id 14696）。 |
| F6 | 已修复（开发期假阳性） | 首版把含空格公式切出 `1/2` 登记为目录引用；`agent/m5628`（分支）被误分类为目录；`Jv≈(F(x0+εv)−F(x0))/ε` 被误判为路径。 | 首版清单 41 项 vs 终版 40 项 | 三条规则收紧（路径字符集、命令切分须带工件后缀、`agent/` → `git_branch_reference`）；终版逐项人工过一遍，未再见假阳性。 |
| F7 | 事实（不是缺陷） | 39/40 资产 `referenced_unresolved`：源属 TensorLBM 仓（分支 `agent/m5628`），交付仓是 TensorKnowledge，契约未授权跨仓取字节。 | 报告 ⑤-1；`resolution_check.reason` | 如实标注，不翻转、不猜测。 |
| F8 | 事实（不是缺陷） | 5 张图的字节平台不提供（`GET /tensor/reports/7216/figures/<name>` 全 404）。 | `resolution_check.http_status = 404` | 只登记"名字 + 声明 + 探测结果"，不伪造哈希。 |

## 3. 没跑的检查（如实标 unknown，不标 pass）

- 平台侧 artifact / attachment 端点未探测（只探了 figure 端点），因此**不声称**它们的可用性。
- `psql` 直读通道被判 `permission denied for table tensor_reports` → 双通道校验记 `not_run`，API 是唯一取源通道。
- 未做跨仓（TensorLBM）字节级解析：不在契约范围，且旁证探针显示同一路径在不同检出中存在**多种内容**（`rb_continuum_stability.py` 2 种），无法定位到产出修订。

## 4. 是否夸大

逐条核对后**未发现**夸大陈述：没有任何资产被标 `resolved` 除非字节在手；`verified_marks_emitted=0`；`claims=[]` 且给出理由；
"是否 <3%" 只对可判定量（哈希 / 字符数 / 定位点重解析）回答"是"，资产解析率明确写"无基线、不可判定"。

## 5. 处置

**approve with notes**（作者视角）：交付物满足 acceptance 六项且已在**已发布件**上复算通过；F1/F2/F3/F4 为记录级改进项，
不影响本工序结论；F5/F6 已在发布前修复。是否 verified 由平台门独立判定，本文件不代行。