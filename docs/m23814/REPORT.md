# PROD-RA R5 残差修复（R6-fix，m23814）

## 1. 案例介绍
TensorKnowledge 仓的 PROD-RA（research-audit）stage-3 评审包
（`docs/m22059/` + `docs/review_m22059_prod_ra/`）在 R5 独立复审
（m23157，verdict=changes_requested）中留下三项残差，m23257 独立重算确认其在
main@3fbd3b3 原样未修。本单按冻结判据（m23157 回执 + m23257
`verify_status.py`，未改动）修复：

| 残差 | 级别 | 内容 |
|---|---|---|
| R5-1 | blocking | 144 个纯路径 locator 字段冷启动仅 17 可解析；114 指向 legacy `runs/m22059/`；17 绝对外域；5 条前缀重写后仍不可解析 |
| R5-2 | major | SHA256SUMS 18 条中 6 条不符（4 缺 raw 文件 + 2 摘要不符，含 PR#511 引入的 recheck.py 62b31f54 vs 2cfa2454） |
| R5-3 | major | D6 证据 5 条中 ev-kb10k-incompatibility 无 input_sha256；3 条绝对外域 input_refs；source_ref 冷启动 0/5 |

## 2. 怎么做的
确定性脚本 `docs/m23814/repair_r6.py`（幂等，二次运行 0 变更），全程程序化、零手抄：
1. **R5-2**：4 个缺失 raw 文件从 m22508 工作树逐字节复原（复制前逐一对比提交版
   manifest 声明摘要，全部命中）；`raw/SHA256SUMS` 镜像截断为其声明的空状态
   （e3b0c442…）；SHA256SUMS 按主线现状实算重生成（18 条，原顺序）。
2. **R5-1**：字段级（JSON-aware）重写 19 个 JSON 中的纯路径字段——
   `runs/m22059/`→`docs/m22059/`（114）、绝对工作树路径→仓内相对路径（12）、
   5 个裸工作树根→显式 `platform-evidence://worktree/<mid>` 指针；
   2 个 m19455 语料引用→仓内 `work/wp-2506-04/kf_result_wp-2506-04.md`。
   引文性散文（如 R4 缺陷描述）不动。`#sha256:` 片段 8 处按新实际摘要刷新。
3. **R5-3**：bundle 5 条 item 的 sha256 按重写后源文件实算；
   ev-kb10k-incompatibility 补 input_sha256（目录摘要约定写入
   provenance.digest_convention：`sha256('name:file_sha256\n' 按名排序)`，
   并注明 m22760 原目录摘要约定不可从仓内复现、故不冒认）；
   绝对外域 input_refs 全部去除；bundle_sha256 按
   `tensorbench.criteria.canonical_sha256` 重算。
4. **复跑** m23257 `verify_status.py`（冷抽取 `git archive HEAD`，第三方视角）。

## 3. 计算结果（m23257 冻结口径，前后对比）
| 指标 | before | after |
|---|---|---|
| 纯路径字段数 | 144 | 137 |
| 冷启动可解析 | 17 | 137 |
| 前缀重写后仍不可解析 | 5 | 0 |
| legacy runs/ 前缀 | 114 | 0 |
| 绝对外域 | 17 | 0 |
| manifest sound | False | True |
| manifest missing / mismatch | 4 / 2 | 0 / 0 |
| D6 缺 input_sha256 | 1 | 0 |
| D6 绝对外域 input_refs | 3 | 0 |
| D6 source_ref 冷启动可解析 | 0/5 | 5/5 |
| D6 item sha256 与实际相符 | 0/5 | 5/5 |
| D6 bundle_sha256 相符 | True | True |
| 入口 recheck.py 冷跑 exit | 0 | 0 |
| 六项检查（R5 记录） | True | True |
| recheck.py = R5 评审修复版 | True | True |

纯路径字段 144→137 的差值：5 个裸工作树根转为 platform-evidence 指针（不再是
文件 locator），2 个 m19455 语料引用转为仓内 `work/...` 路径（不再匹配
locator 前缀定义）。137/137 冷启动可解析。

## 4. 结果图
见内嵌图：冻结验证器 10 项指标 before/after。

## 5. 注意点
- 修复对象是**证据文书**：重写 locator 会改变文件字节，因此 item sha256、
  items_sha256、`#sha256:` 片段、bundle_sha256 全部按新字节重算，未手抄任何摘要。
- m22760 的目录摘要约定无法从仓内复现（试了 10+ 种候选约定均不匹配），
  新补的 kb10k 目录摘要采用显式声明的新约定，不冒认旧约定。
- R5-4（info）未处理：recheck.py 的 failure_record 顶层 input_sha256 查找
  与嵌套 provenance 不一致，属 recheck.py 自身缺陷；改 recheck.py 会使
  m23257 的 fix_identity（sha 钉死 2cfa2454）翻红，故如实保留并在此说明。
- psql 台账探针仍 permission denied（角色限制，与 before 相同，已记录）。
- 全量 pytest 套件维持原记录 not_run（集群排队语义），相邻单测证据
  `raw/adjacent_unit_tests.log` 已复原入 manifest。

## 6. 误差判定
本单为证据链修复，无数值解算量；判据为冻结验证器的布尔/计数指标，
after 状态全部达标（137/137 可解析、manifest 18/18 sound、D6 5/5 全绿、
bundle 摘要相符、入口冷跑 exit 0）。无「<3%」类数值误差项；
唯一未闭合项为 R5-4（info 级，见 §5），不属本单判据。
