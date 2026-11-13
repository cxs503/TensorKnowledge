# docs/wp-9761-01 — 工作包 wp-9761-01（report 9761 源资产登记）

本目录是 `artifacts/` 与 `runs/` 的**耐久镜像**与说明：本仓 push 门会滤掉那两个目录，
所以审计需要的字节都放在这里。

## 一句话结论

report `9761` 的 markdown 与契约 `source_hash` **逐字节一致**（sha256 `4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a`，
8931 字符），已登记 29 条资产、29 条唯一可解析定位；
`claims = []`（契约允许，本工序不做抽取）；未标 verified（`verification_status = not_verified`）。

## 文件

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 主产物（= `artifacts/wp-9761-01/asset_manifest.json` 逐字节镜像），schema=`asset_manifest.v1` |
| `kf_result_block.json` | 交付用的 kf_result.v1 信封（= `runs/wp-9761-01/kf_result.wp-9761-01.json`） |
| `verification.json` | 9 项校验（6 项契约 acceptance + 3 项附加），overall=`PASS` |
| `report_9761_meta.json` | 源报告平台元数据镜像 |
| `coverage.json` | 定位覆盖率 8636/8931 = 96.70%，未登记正文行 0 |
| `KF-RESULT.wp-9761-01.md` | 交付报告正文（六段 + 唯一 json 代码块），与平台已发布报告同文字 |
| `figures/fig1_asset_coverage.png` | 资产定位覆盖图 |
| `figures/fig2_resolution_checks.png` | 解析状态分布 + 校验矩阵 |
| `schema` 钉定 | `schemas/asset_manifest.v1.wp-9761-01.schema.json` |

## 复跑

`python3 scripts/kf_fetch_9761.py && python3 scripts/kf_register_9761.py && python3 scripts/kf_verify_9761.py && python3 scripts/kf_figures_9761.py && python3 -m pytest tests/test_kf_wp9761.py -q && python3 scripts/kf_report_9761.py && python3 scripts/kf_check_published_9761.py`

## 已知与诚实的边界

* 3 条 `referenced_unresolved`（A10/A19/A25）指向 TensorDEM 仓的代码/图件/工件，本工作树内不可解析 —— 不是缺失。
* 上游报告的结论（`all_passed = True`、五项判据 PASS、六项 <3%）**未复核**，登记的是「原文如此」。
* 发布记录：`14741、14750` 是同一信封的首次发布（内容为早期文字稿），
  最终发布见 `runs/wp-9761-01/publish.json`；两个报告的 json 块内容相同。
