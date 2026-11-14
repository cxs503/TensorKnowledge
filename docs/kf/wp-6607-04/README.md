# wp-6607-04 — 报告 6607 的独立复核（pass-with-notes）

任务要点：对报告 6607（IN32-N02，2D 无热颗粒 jamming 体积分数重锁）做一次**可复算**的独立复核 —— 复核方只用报告自己印出的表与阈值重算每一个数，并把「判据是否按写出的口径执行」与「结论是否对口径敏感」分开判。

## 结论

- 判定 **pass-with-notes**，disposition **approve with notes**；blocking 0 条，severity high/medium/low = 0/3/3。
- 复算台账 42 条：pass 26 / fail 6 / derived 3 / not_recomputable 5 / withheld 2。
- 报告没有捏造数字：φ_J(∞) 两个准静态臂可由第 3 节的 5 点表重算到 1e-4 相对量级，FIRE 的 (eps0, eps, fmax0, fmax, fmax_reduction) 互相闭合到逐位，误差栏 6 行全部对得上复算。
- 6 条发现全部不改变任何 PASS/FAIL：F1 三处「两臂一致/稳定」低估 1.3–3.2 倍、F2 淬火臂 nu=2.51 是扫描上界、F3 判据 c 写出≠执行、F4/F5 措辞、F6 外推敏感度未传播。

## 交付物

| 文件 | sha256(前 16) | 字节 | 作用 |
|---|---|---|---|
| `source_6607.md` | b228e4f68599218d | 11166 | 钉扎的快照（逐字节等于取回的 markdown，用于离线重建与哈希复核） |
| `recompute.json` | 866a41ccedcff2a9 | 33814 | 复算台账：每条含公式/引文(带 1-based 行号)/复算值/报告值/相对差/状态 |
| `review_report.json` | 18a9b004276c6150 | 24142 | 复核结论：判定/发现（含复现路径）/被证成主张/未执行检查/独立性限制 |
| `report_markdown.md` | d3c3b17cc53f592d | 18882 | 复核报告正文（全部数字由 recompute.json 渲染，零手抄） |
| `figures/wp-6607-04.png` | 558d1f82885e022e | 143825 | 图 1：四协议 phi_J(N) + FSS 拟合 + 文献锚带；复算台账相对差与状态矩阵 |
| `kf_result.json` | (见文件) | - | KF-RESULT v1 信封（04-independent-review，status=awaiting_pr_merge） |

## 复现

```bash
python3 scripts/kf/review_wp_6607_04.py --offline   # 由已提交快照重建全部工件
pytest -q tests/test_wp_6607_04_review.py          # 不变量 + 负对照
```

来源钉扎：`sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1`（7642 字符 / 136 行）。改快照一个字符，`--offline` 重建立刻 `PIN MISMATCH`。

## 边界（不做的事）

- 只审 markdown 字节。TensorDEM 的执行工件（`artifacts/jamming_protocol/`、`benchmarks/jamming_*.py`、`src/tensordem/granular2d/minimizer.py`）、29 个 pytest 用例、报告图的 PNG 字节都不在本仓库 → 一律 `NOT_RUN`/`WITHHELD` 登记，不按「没发现问题」算通过。
- 不发布、不自称已验证：`published.json` 由平台门在合并时写入，本包状态为 `awaiting_pr_merge`。
- 与报告的关系：本包不修改上游任何文件，只改述与登记。

## 与初版 PR#332 的差异（重开轮的成熟化决定）

- **去掉 `ke/__pycache__/*.pyc`**：缓存字节不是交付物，且已被 `.gitignore` 覆盖；带进 PR 只会让 diff 噪声化。
- **去掉自写的 `published.json`**：发布态是平台门的记账（pr-gate），生产方自证发布与「不自称已验证」纪律冲突；本包改为在 `kf_result.json` 的 `validation.publication_state` 写 `awaiting_pr_merge`，并保证 testing 断言它不出现 `published`/`verified`。
- **补 `tests/test_wp_6607_04_review.py`**：初版只有工件没有不变量测试；本版把「引文逐字、行号自洽、零手抄、判定与台账一致、检测器有牙」变成可执行断言。

## 热文件声明（与其他在开 PR 的重叠面）

- 本 PR 只新增 `docs/kf/wp-6607-04/`、`scripts/kf/review_wp_6607_04.py`、`tests/test_wp_6607_04_review.py`。
- 唯一会被改写的既有文件是生成物 `docs/kf/wp-459-01/envelope_conformance.json`（`scripts/kf/audit_envelope_conformance.py --write`）：新增一个信封后`test_census_regenerates_byte_for_byte` 会要求台账按当前检出逐字节重算。这是共享热文件，与任何同样新增 KF 信封的 PR 都会在这里相遇；本包的重算只增加 1 个 envelope / 1 个 conforming 计数，不改 schema、不改残留允许表。

