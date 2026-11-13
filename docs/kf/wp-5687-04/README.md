# wp-5687-04 — 独立审核（04-independent-review / red-team）

**审核对象**：`wp-5687-01`（01-asset-registration），输入报告 `report_id=5687`
（IN18-T2 战史官编年史与指标计算器成熟化，`scenario_key=chronicle-metrics-in18-t2`）。
**结论**：`pass`（advisory，非 verified 标记）——门判据 13/13 绿，blocking 0，非阻塞缺陷 6 条（medium 1 / low 5）。
平台报告：`KF-RESULT wp-5687-04`（report id 见 `publish_receipt.json`）。

## 独立性怎么保证

- 上下文只有两样东西：报告 5687 的 markdown **原始字节**（sha256 锚定），以及上游**机器产物**
  （`kf_result.json` / `asset_manifest.json` / `verification.json` 逐字节快照）。
- 生产者叙述、`report_body.md`、生产者工作树笔记一律不读（`review_report.json → independence` 机器可核）。
- 每个断言都**从报告字节重算**，不复述上游结论；`verify_wp5687_01.py --offline` 无网可重放。
- 局限：与生产者同模型族，独立性是程序性的而非组织性的（已写入 `checks_not_run` / 报告⑤）。

## 判据（动手前预声明，事后不改）

`verdict=pass` 需 ①13 条门判据（C1–C13）全绿 且 ②零 blocking 缺陷。blocking 仅限五类：

| 类 | 定义 |
|---|---|
| B1 | 源哈希不可复算或分歧 |
| B2 | locator 引文非「声明行内的连续逐字子串」 |
| B3 | 伪造分辨率状态（说 resolved 但字节不存在/不可哈希） |
| B4 | 把 claim 说成 verified，或用空 claims 掩盖已抽取的 claim |
| B5 | 交付信封 JSON / schema 非法 |

覆盖度与命名类缺陷记为非阻塞项，不改变门判据结论。

## 文件

| 文件 | 内容 |
|---|---|
| `review_report.json` | 本轮审核唯一结果对象（decision / 18 条 checks / locator 逐字复核 / findings / provenance） |
| `kf_result.json` | 工序结果信封（`provenance.source_hash` 锚定报告 5687 markdown） |
| `checks.json` | 机器检查明细 + 覆盖枚举（可由复核器重新生成） |
| `verify_wp5687_01.py` | 复核器：18 条独立重算（`--offline` 只用快照；`--write-dir` 可写入临时目录） |
| `test_verify_wp5687_01.py` | 8 条不变量测试（离线复跑一致 / schema / 哈希锚定 / 无 verified 断言等） |
| `make_figure.py` → `fig1_review_evidence.png` | 检查矩阵 / locator 逐字复核 / 缺陷分级三视图（数字全部从 JSON 读） |
| `make_report.py` → `report_body.md` | 六段报告生成器；引用前用 `locate()` 强制逐字校验（零手抄护栏） |
| `publish_report.py` → `publish_receipt.json` | 发布到平台并回执 |
| `upstream_snapshot/` | 被审字节的逐字节快照 + `SHA256SUMS.txt`（审核只对这些字节负责） |

## 复跑（一键）

```bash
python3 docs/kf/wp-5687-04/verify_wp5687_01.py \
  && python3 -m pytest docs/kf/wp-5687-04/test_verify_wp5687_01.py -q \
  && python3 docs/kf/wp-5687-04/make_figure.py \
  && python3 docs/kf/wp-5687-04/make_report.py
# 无网重放（仅快照字节，不覆盖已提交产物）：
python3 docs/kf/wp-5687-04/verify_wp5687_01.py --offline --write-dir /tmp/wp5687-04-offline
```

## 结论摘要（wp-5687-01）

成立的核心契约：源哈希三方一致（契约/信封/manifest）、11 个 asset id 唯一、7 条 locator 引文在声明行逐字命中、
只有 1 个 `resolved` 且可重新哈希、3 个 `metadata_only` 明确声明无字节、`claims: []` 且全文无 verified 断言、
声明的输出哈希与交付字节相等、上游 6 条 verification 断言本机全量重放一致、两个 artifact 端点独立复核仍 404。

非阻塞缺陷（详见 `review_report.json → findings`）：F1 `schema_note` 对 HEAD 已过期（`schemas/kf_result.v1.schema.json`
已入库）；F2 报告声明的 `artifacts/chronicle/` 目录级工件未登记也未声明越界；F3 `ref:05` 丢了所在目录；
F4 `distinct_referenced_paths=5` 按 basename 归一是 4；F5（medium）`verification.json` 的
`source_locator_resolvable: pass (unresolvable=[])` 易被下游读成「7 条未解析引用已解析」；F6 报告的 4 张表/6 行参数
数据资产既未登记也未声明不在 kind 词表内。

## 边界

本单只读写 `report_id=5687` 相关内容；未改写上游或其它工作包产物（上游仅做逐字节只读快照）；
未给任何 claim 打 verified（verification 由平台门计算）。