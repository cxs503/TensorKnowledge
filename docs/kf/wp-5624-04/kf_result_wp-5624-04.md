# KF-RESULT wp-5624-04

- package_id: `wp-5624-04` ｜ task_type: `04-independent-review` ｜ lane: C
- report_id: `5624`（本包唯一触碰的报告）｜ source: `tensor://reports/5624` · field=`markdown`
- source_hash: `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839`
  （独立重算；与契约值一致：true；快照 `tests/fixtures/kf/5624_markdown.md`，其 sha256 与正文同值）
- 审核对象: `wp-5624-01`（01-asset-registration）｜被审产物按内容哈希固定，见 C14
- 状态: draft（verification 由平台门计算，本包不标 verified）

## ① 案例介绍（背景/对象/参数）

本包是报告→知识产线（KBM-RCI-F1-FACTORY）的 04 独立审核工序。对象是上游 01 工序包
`wp-5624-01`：它把平台报告 `tensor://reports/5624`（IN15-O5 工件 sha256 索引器，
一条"工件目录完整性索引"的后端工具报告）登记为资产清单。

| 参数 | 值 |
|---|---|
| 报告正文规模 | 1833 字符 / 3255 UTF-8 字节（行数口径见 C04） |
| 正文 sha256（契约值） | `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839` |
| 被 pin 的上游产物 | 3 个（asset_manifest / kf_result / 渲染 md），逐个按 sha256 固定 |
| 登记小节 | 7 节 |
| locator | 9 条（9 命中）｜附图上界 3 张 |
| 物理量纲 | 无（本工序的"基准"是密码学哈希与逐字子串匹配，不涉及流体/结构量） |

## ② 怎么做的（方法/流程/工具链）

1. **固定输入**：把平台正文固化成语义无歧义的字节快照 `tests/fixtures/kf/5624_markdown.md`；
   离线复核只用该快照 + 上游已提交产物。`--fetch` 时先在线重取并对快照做**字节相等断言**（C02），
   不一致直接中止，不产出报告。
2. **独立重算**：sha256 / chars / utf8-bytes / 行数口径 / ATX 小节切分（7 节，逐节 chars+sha256
   与上游清单比对）。
3. **逐字 locator 核验**：9 条 quote 按所属空间（正文 / 图注）做逐字子串匹配，并检查 quote 两两互异。
4. **缺陷探测**：①重复 locator 引用；②行数口径（复算后判为无缺陷，显式关闭）；
   ③验收套件对 gitignored 路径的依赖——用 `git archive` 只取已跟踪文件构造"裸检出"，
   并在同一次运行内做 A/B：一臂用当前 fixture，另一臂把回退逻辑改回修复前写法，两臂都在无 `artifacts/` 的检出中重放（C13/C15）。
5. **schema/边界**：上游信封过 `schemas/kf_result.v1.schema.json`；边界=只读 report 5624；claims=[] 合法（01 工序）。
6. **可复现**：`emitted_at` 用固定复现戳而非墙钟；同一输入两次运行产物字节一致（测试 `test_generation_is_deterministic` 断言）。

## ③ 计算结果（程序化注入，零手抄）

| 量 | 值 |
|---|---|
| 复核项 | 16/17 通过 |
| 源哈希 | `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839` |
| 源规模 | chars=1833 ｜ utf8 bytes=3255 |
| 小节复算 | 7 节（逐节 chars+sha256 对齐） |
| locator | resolved 9/9 ｜ figure captions=3 |
| 缺陷 | 4 条（severity: info, medium, major, low） |
| A/B 裸检出重放 | 对照臂（把 `OUT` 一行改回修复前写法）11 个用例 ERROR / rc=1；修复臂 0 个 ERROR / rc=0（11 passed, 1 warning in 0.63s），两臂都在**没有** `artifacts/` 树的检出中运行 |
| 在线重取 | 一致（快照 == 平台当前记录） |
| disposition | **approve_with_notes** |

### 检查明细

| id | result | detail |
|---|---|---|
| C01 | pass | recomputed=sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839 contract=sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839 manifest=sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839 |
| C02 | pass | live=sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839 snapshot=sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839 chars=1833 |
| C03 | pass | chars=1833 (declared 1833) bytes=3255 (declared 3255) |
| C04 | pass | manifest.lines=46 newline_count=46 splitlines=46 naive_split_newline_tokens=47 ends_with_newline=True |
| C05 | pass | recomputed sections=7 manifest=7 mismatch=[] |
| C06 | pass | locators=9 resolved=9 declared_total=9 |
| C07 | fail | duplicate_groups={"markdown|`artifacts/`（0 文件）与 `runs/`（0 文件），": ["referenced_artifacts:5624-ref-01", "referenced_artifacts:5624-ref-02"]} occurrences_in_markdown={"markdown|`artifacts/`（0 文件）与 `runs/`（0 文件），": 1} |
| C08 | pass | validated against schemas/kf_result.v1.schema.json |
| C09 | pass | claims=[] envelope_has_verification_status=False boundary.verification_status='none — 由平台门独立计算，本包不标 verified' |
| C10 | pass | read=['5624'] written=['5624'] |
| C11 | pass | observation=5624-obs-01 status=unresolved quotes_resolved=3/3 (markdown or figure-caption space) |
| C12 | pass | gitignored=True tracked_in_git=False docs_fallback_in_fixture=True fixture_line=['OUT = ARTIFACTS_OUT if (ARTIFACTS_OUT / "kf_result.json").is_file() else DOCS_OUT'] |
| C13 | pass | summary='11 passed, 1 warning in 0.63s' errors=0 failed=0 artifacts_tree_present=False |
| C14 | pass | {"asset_manifest.json": "db0f062ea5d6", "kf_result.json": "01c63fb3e63a", "kf_result_wp-5624-01.md": "03e9158c0a91"} |
| C15 | pass | as_is=rc0 ('11 passed, 1 warning in 0.63s') fallback_ablated=rc1 ('1 warning, 11 errors in 1.02s', errors=11) |
| C16 | pass | inputs=['tests/kf/test_wp_5624_04.py', 'scripts/kf/wp-5624-04/review_wp_5624_01.py', 'tests/fixtures/kf/5624_markdown.md'] missing=[] artifacts_read={"tests/kf/test_wp_5624_04.py": false, "scripts/kf/wp-5624-04/review_wp_5624_01.py": false} |
| C17 | pass | modules_reading_gitignored_trees={'test_wp_14445_01.py': ['runs'], 'test_wp_297_04.py': ['artifacts']} count=2 |

### 缺陷分级

| id | severity | title | status |
|---|---|---|---|
| F-C04 | info | 前一轮审核把 lines=46 记为 low 级歧义；本轮复算判定为无缺陷（口径=换行符数，与 splitlines 一致） | closed_no_defect |
| F-C07 | medium | distinct ref_ids share one locator quote, so 'existence not checked' is asserted twice for one occurrence | open |
| F-C13 | major | 上游验收套件在裸检出中曾全红（fixture 读 gitignored 的 artifacts/）；本包加 docs/ 镜像回退后重放转绿 | fixed_in_this_package |
| F-C17 | low | tests/kf 下另有 2 个测试模块直接读 gitignored 的 artifacts/ 或 runs/，同类缺陷不止 5624 一线 | open_out_of_scope |

## ④ 结果图

`fig_review_evidence.png`（`scripts/kf/wp-5624-04/make_figure.py` 程序化生成，数据全部读自本包
`review_report.json`，零手抄）：

- 左图 A：每条 locator 在所属空间中的出现次数直方图——9 条里 8 条各对应 1 处，重复引用的两条也落在**同一处**，
  这是 F-C07 的直接可视化；
- 中图 B：行数口径四种算法（清单声明 / 换行符数 / `splitlines` / 朴素 `split('
')`）——前两者一致，
  只有朴素切分因末尾换行多出 1，属解析器伪影而非清单缺陷；
- 右图 C：裸检出 A/B 重放的上游用例结局（修复前 11 个 ERROR，修复后 0 个）。

无物理云图的原因：本工序审核的是元数据与哈希一致性，不存在空间场量（本包非物理仿真任务）。

## ⑤ 注意点（坑/局限/适用范围）

**本轮明确未核项（不得计为通过）：**

- 被登记工件的存在性/内容一致性：工件根位于 m4963 的 TensorPlatform worktree，跨 worktree 取证越界
- content_digests 的 sha256 值重算：被摘要工件不在本 worktree
- 报告附图（fig1/fig2/fig3）的图像内容核验：平台记录中 figures 未携带 png_base64 载荷
- m4963 的 artifact_indexer 源码复核：工具不在本仓

**局限：**

- 独立性局限：审核者与生产者同为 LLM 代理，可能共享推理模式；本包靠"只读字节 + 不采信生产者解释"保证独立性，
  但同族偏差无法在包内消除。
- 上游"pytest 11 passed"是**有条件**结论：只在手动补齐 `artifacts/` 后成立。本包给该 fixture 加了 `docs/` 镜像回退（R3），
  并用裸检出 A/B 重放验证了修复前后差异——修复臂通过、对照臂 11 个 ERROR。
- 适用范围：04 工序只做审核与最小可复现性修复，不修改 01 工序产物内容；R1（重复 locator 引用）与
  R2（行数口径写明）保持 open，交上游 01 工序处置。
- 与前一轮（已关闭的 PR#321）的差异：本轮不再把 `.pyc` 字节码入库、不再只有文字结论——每条结论都有可执行重放，
  且新增 17 个回归用例把"结论 ↔ 证据"钉住。

## ⑥ 误差判定

基准=独立重算（哈希 / 逐字子串 / 小节切分）。本工序无物理量，因此误差面是"复算与声明之差"，
逐项列出并显式回答是否 < 3%：

| 关键量 | 基准 | 实测 | 误差 | <3%? |
|---|---|---|---|---|
| 源 sha256 | 契约值 | 重算值 | 0 bit | **是（0%）** |
| 源 chars | manifest 声明 1833 | 重算 1833 | 0 | **是（0%）** |
| 源 utf8 bytes | manifest 声明 3255 | 重算 3255 | 0 | **是（0%）** |
| 小节切分 | 7 节 ranges+chars+sha256 | 重算同 7 节 | 0 节不符 | **是（0%）** |
| locator 命中 | 9 条 | 9 条 | 0 条不命中 | **是（0%）** |

复核项通过率 16/17 = 94.1%，其中 1 项 fail（C07）指向**上游真实缺陷 F-C07**
（重复 locator 引用），不是本包的复算误差——因此该行不作为误差率、也不声称 < 3%。
若把它当质量指标读：本包自身复算误差 0%，上游缺陷 1 项如实登记、未粉饰。

## 附：复跑命令

```bash
python3 scripts/kf/wp-5624-04/review_wp_5624_01.py                 # 离线，快照固定
python3 scripts/kf/wp-5624-04/review_wp_5624_01.py --fetch --fresh-clone   # 联网复取 + 裸检出 A/B
python3 scripts/kf/wp-5624-04/make_figure.py                       # 图（数据来自 review_report.json）
python3 -m pytest tests/kf/test_wp_5624_04.py tests/kf/test_wp_5624_01.py -q
```

## 附：kf_result 信封

与 `docs/kf/wp-5624-04/kf_result.json` 同内容（字段=package_id/task_type/report_id/provenance/outputs/claims，
过 `schemas/kf_result.v1.schema.json`）。
