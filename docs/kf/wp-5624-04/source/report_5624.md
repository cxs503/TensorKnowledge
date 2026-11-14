# IN15-O5 · 工件 sha256 索引器（自回归燃料⑤：可复算）

## ① 案例介绍（背景/对象/参数）
自回归战役的"可复算"燃料：跨仓工件目录的完整性索引，把每个工件映射为
`路径 → sha256 → 大小 → mtime` 并落索引表，配套随机抽查复算命令。
对象=本 worktree（TensorPlatform, 分支 agent/m4963）两个工件根：
`artifacts/`（0 文件）与 `runs/`（0 文件），
共 **102 文件 / 6.45 MB**。判据（任务书）：索引建立后抽查 20 文件全中 +
增量更新（mtime 未变跳过）幂等 + pytest≥5。纪律=只增不改：新工具独立目录
`tools/artifact_indexer/`，纯标准库，不触碰任何既有 API/schema/表。

## ② 怎么做的（方法/流程/工具链）
- 索引表=版本化 JSON（v1，原子写 tmp+os.replace），条目含 root/rel/sha256/size/mtime(ns)。
- 增量规则：size 与 mtime(ns) 双匹配才复用缓存哈希（mtime 未变跳过），否则重算；消失文件剪枝。
- 幂等：无变化时**不重写**索引文件 → 字节级一致（sha256 前后一致，见 §③）。
- 抽查：`check --n 20 --seed 42`，固定种子可复现审计；`verify` 全量复算。
- 工具链：python3.11 标准库（hashlib/json/os/random），CLI `python3 -m tools.artifact_indexer {build|check|verify|show}`，
  每子命令带 `--dry-run`（build）/JSON 输出；pytest 10 用例。

## ③ 计算结果（程序化注入，零手抄）
| 量 | 值 |
|---|---|
| 冷构建 scanned/hashed/skipped/added | 102/102/0/102 |
| 二次构建 scanned/hashed/skipped/changed | 102/0/102/False |
| 索引文件 sha256（前后一致） | `7223cab4b4edf2f1dbad8cba148bf4c56b7cbc938dd9a2620ba146dd6ed20bb7` |
| 抽查 n=20 seed=42 | sampled=20 passed=20 failed=0 |
| 全量 verify | total=102 passed=102 failed=0 |
| pytest | 10 passed（≥5 达标） |
| 最终提交索引表 | 116 条（含本单 14 个工件），最终抽查 20/20 全中，末次构建 0 重算/116 跳过（幂等） |

## ④ 结果图
本单为后端完整性工具，无物理场量，故无云图；图=索引清单/尺寸分布/验收证据三张（见 figures）。

## ⑤ 注意点（坑/局限/适用范围）
- mtime 信任模型与 make 同构：size+mtime 双匹配才跳过；仅 mtime 变化（touch）会触发重算且哈希不变（有测试覆盖）。
- 并发写竞态：首轮演示中 tee 边写边被哈希导致 1 条 mismatch——工具行为正确（哈希了半截文件），
  已改为"产物先落 /tmp、终态再入库+重建"，最终 verify 102/102。
- 符号链接跳过；索引文件自身按名排除；mtime 回拨/时钟漂移场景不在保证范围。
- 适用：任意工件目录（多根=跨仓）；不适用：需要内容级去重（同哈希多路径）的场景（当前按路径键控）。

## ⑥ 误差判定
基准=独立 hashlib 复算（后端工具无外部物理基准，原因：完整性校验的 ground truth 即哈希函数本身）。
- 抽查 20 文件：mismatch 0/20 = **0.0% < 3% ✓**
- 全量 verify：mismatch 0/102 = **0.0% < 3% ✓**
- 幂等：二次构建索引 sha256 前后一致（`7223cab4b4edf2f1…`），**通过 ✓**
- pytest：10/10 通过（判据 ≥5）✓
