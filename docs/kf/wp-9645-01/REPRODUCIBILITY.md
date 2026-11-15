# wp-9645-01 — 证据可复现层（源资产快照）

本文件说明工作包 `docs/kf/wp-9645-01/`（report_id=9645，工序 01 asset-registration）
在新补的快照层下**怎么离线复核**，以及哪些复核项仍然不在本包边界内。

## 1. 原有缺口

工序 01 的产物把源报告 9645 的 SHA-256（`a8bb8902…fb00`，11824 字符）钉进了
`asset_manifest.json`，但**被哈希的字节没有进工作树**：

* `source.md` 只有摘要（690 B），`report_body.md` 只有登记报告（1.7 KB）——
  两者都不是 11824 字符的源 markdown；
* 于是 8 个 section 哈希、`locator_check.json` 的 `all_pass`、`sha256.txt` 的两行
  都成了「不可再推导的常数」，只能靠再问一次平台 API 才能核对；
* 换言之，`hash self-证` 这一项当时是**靠信任过的，不是靠重算过的**（WITHHELD 级证据），
  离线 CI 无法证伪任何一处哈希漂移。

## 2. 补的东西（不新增论断，只补被哈希的字节 + 复核工具）

| 文件 | 作用 |
|---|---|
| `source/report_9645.md` | 源 markdown 逐字节快照，15967 B / 11824 字符 / 196 行，`sha256:a8bb8902…fb00` |
| `source/record_9645.json` | record 元数据（id/title/summary/scenario_key/tags/figures/status/created_at…），`markdown` 载荷以 `markdown_sha256`/`markdown_chars` 指针替代 |
| `source/snapshot.json` | 快照自身 provenance：抓取时间、快照哈希/长度、与 manifest 钉住值的逐项比对结果 |
| `scripts/kf/wp_9645_01_snapshot.py` | `--fetch`（抓取→**先校验后落盘**，漂移即拒写）/ `--verify`（纯离线复核） |
| `tests/test_kf_wp9645_01.py` | 17 项验收回归：全部从快照重算，不需要网络与凭据 |

抓取时脚本从 `asset_manifest.json` 读钉住值（零手抄），平台返回体一旦与钉住值不符，
`--fetch` 返回非零且**不覆盖**已提交快照——源头漂移必须由人显式处理，不允许被静默吸收。

## 3. 可重算矩阵（离线，`pytest tests/test_kf_wp9645_01.py`）

| 复核项 | 方式 | 结论 |
|---|---|---|
| 源哈希 / 字符数 / UTF-8 字节数 / 行数 | 对 `source/report_9645.md` 重算，与 manifest 钉住值比对 | 4/4 一致 |
| `asset_manifest.json` | `build_manifest(record)` 用快照重建，逐字段比对 | 除 `generated_at`（墙钟）外完全一致 |
| `asset_manifest.schema.json` | `build_schema(manifest)` | JSON 完全一致 |
| `locator_check.json` | `build_locator_check(manifest, snapshot)` | 完全一致，`all_pass=true`，8/8 |
| `report_body.md` / `source.md` / `sha256.txt` | 对应 builder 重建 | 逐字节一致 |
| `kf_result.json` 内嵌 manifest | 与磁盘 manifest 比对 | 完全一致 |
| 引用定位符（3 条：1 绝对路径 + 2 Python 模块） | 行号/整行引文/出现次数 | 3/3 在快照中逐字命中 |
| `asset_coverage.png` | PNG 魔数 + IHDR 尺寸 + 尾部 | 1782×881 / 61673 B，非 1×1 matplotlib 缺省占位 |

负控（证伪能力，防止「永远绿」的门）：

* 快照里翻转 1 个字符 → `verify_snapshot` 必须 `all_pass=false`（`sha256` 项失败）；
* 篡改 1 个 section 哈希 → `build_locator_check` 必须只在该项失败（计数恰为 1）；
* 给抓取工具喂漂移载荷 → `do_fetch` 返回 1 且已提交快照字节不变。

## 4. 边界（不做的事，如实登记）

* 快照是 **2026-11-15 抓取的字节**，不是「平台当前字节」的实时镜像；上游若编辑
  report 9645，需显式重跑 `--fetch`（脚本会先判断漂移）。
* `referenced_artifacts` 的 3 条引用（`/srv/tensor/agent/work/m8350/.../in101_n09_results.json`、
  `p_area_joint.py`、`target_reliability_inverse.py`）位于工作树之外，本包**不读取、不核验存在性**，
  `existence=not_checked` 保持不变——本次补的是「引文是否逐字在源里」这一层，不是工件内容一致性。
* `figures` 的 6 张图件载荷仍未下载（工序 01 只登记元数据）；`attachments.scan` 的
  6 次 markdown 图片语法命中已可从快照重算。
* 本包 `claims=[]`（工序 01 不抽取），因此**没有**任何数值断言需要 vs 基准比对；
  误差判定项为空是合同允许的完整结果，不是空完成。