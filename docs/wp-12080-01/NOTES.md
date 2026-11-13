# wp-12080-01 · 交付说明与已知局限（非发布件）

发布件 = 平台报告 **id 14839**（`title=KF-RESULT wp-12080-01`，`tags` 含 `kf-wp:wp-12080-01`），
其 markdown 与本目录 `KF-RESULT-wp-12080-01.md` **逐字节一致**（32837 bytes）。

## 一键复跑

```bash
# 1) 重新生成（触网取源报告，重算 sha256 与全部定位器）
python3 scripts/kf_wp12080_01_register.py
# 2) 复核（schema/哈希/引文可解析/唯一 id/单一围栏块）
python3 scripts/kf_wp12080_01_verify.py
# 3) 离线回归（10 例，不触网）
python3 -m pytest tests/test_kf_wp12080_01.py -q
# 4) 平台侧复核已发布件（读回 14839，比对围栏内容与正文字节）
python3 scripts/kf_wp12080_01_verify.py --published 14839
```

仅重算哈希/定位、不触网：`python3 scripts/kf_wp12080_01_register.py --offline`。

## 已知局限 1：平台报告是 append-only

平台对 `/tensor/reports/{id}` 只允许 POST 创建：`PUT` / `PATCH` / `DELETE` 均返回 `405`，
`/revision` `/update` `/versions` `/edit` 均 `404`（2026-11-12 实测）。因此：

* 已发布的 14839 **不可修订**，它是本工作包的规范副本；
* 生成器支持 `KF_EMITTED_AT` 钉住 `provenance.emitted_at`，使重跑能复现**逐字节一致**的正文：
  `KF_EMITTED_AT=2026-11-12T02:23:11 python3 scripts/kf_wp12080_01_register.py`
* 不带该环境变量重跑，正文只在 `emitted_at` 一个字段上不同；此时 `verify.py --published 14839`
  的 `published_body_byte_identical` 会如实报 FAIL（结构等式 `published_json_equals_envelope` 仍 PASS）。

## 已知局限 2：④ 证据表里的"引文片段"列是截断显示

正文 ④ 表格为可读性把长引文截断到 96 字符（换行记作 `⏎`）。源文本自带的单反引号在表格单元内
会造成 markdown 渲染上的一个未闭合反引号（纯显示问题）。**规范引文不在表格里**，而在 JSON 围栏的
`outputs.asset_manifest.json.assets[].locator.quote`，是 `md[start_char:end_char]` 的原样切片并断言全文唯一。

## 已知局限 3：跨仓资产只能登记为 unresolved

`artifacts/dp_time_domain/*.json`、`modules.dp_time_domain.*`、`tests/*.py` 属 ship-performance-platform 仓，
本工作树（TensorKnowledge）内不存在 → `resolution=referenced_unresolved`（探测结果如实记 `unresolved`）。
三张图（`fig_envelopes.png` / `fig_drift.png` / `fig_attribution.png`）在平台 `figures` 元数据中存在
（`result=present`），但二进制不在 markdown 内，本工序不下载、不抽取像素。

## 本工作包没做的事（边界）

claims 抽取、报告类型分类、图件重绘、跨仓工件下载、把任何结论标成 `verified`。报告自述的
C2 honest FAIL、三扇区不收敛、载荷系数 DECLARED 均按原文登记（A11 / A24 / A25），未做"通过化"改写。