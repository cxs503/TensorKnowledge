# wp-9632-02 · 02-classification-parse（report_id=9632）

工作包：给报告 `9632`（IN101-N07 冰脊固结热力学）打**类型标签 / 主题标签 / 结构切分**，并给出每条判定的原文定位。**不做抽取、不做资产登记、不下 verified 判定。**

判定结果：`report_type = scientific-computation`（score 0.80，次优 `experimental-validation` 0.50），选中 skill `xsk-scientific-computation` v0.1.0；状态 `classified_draft`。

## 一键复跑

```
python work/wp-9632-02/build_classification.py --source work/wp-9632-02/source_9632.md
python work/wp-9632-02/make_kf_result.py
python work/wp-9632-02/verify_classification.py
python work/wp-9632-02/make_figure.py
python work/wp-9632-02/make_report_md.py
bash   work/wp-9632-02/post_report.sh     # 需 $TENSOR_API_BASE/$TENSOR_AGENT_USER/$TENSOR_AGENT_PASS
```

`--source` 缺省时走 API 现取（`GET $TENSOR_API_BASE/tensor/reports/9632`），并在切片前校验
`sha256(markdown)` 与契约 `source_hash` / `chars`；不一致直接 fail-closed 退出。

## 文件

| 文件 | 说明 |
|---|---|
| `classification.json` | 主产物：类型判定 + 30 条 registry 信号判据 + 20 条逐字证据 + 结构切分 + 主题 + 局限 + 未决 |
| `kf_result_wp-9632-02.json` | KF-RESULT 包装体（报告里唯一 json 块，原样提交） |
| `source_9632.md` | 源报告 markdown 原样副本（离线复跑与哈希重算用，未改动） |
| `build_classification.py` | 构建器：取原文→验哈希→选择器机器切片→六分型打分→落产物 |
| `make_kf_result.py` | 包装体生成器 |
| `verify_classification.py` | 11 项自检（wp_gate 定位复解析 / jsonschema / 重复 id / 自证字段扫描 / 结构连续性） |
| `verify_report.json` | 自检机器记录 |
| `make_figure.py` + `figures/classification_overview.png` | 分类覆盖与结构切分图（数据注入） |
| `make_report_md.py` + `platform_report.json` | KF-RESULT 报告生成器与投递 payload |
| `post_report.sh` | 投递到平台 `POST /tensor/reports` |
| `package_contract.json` | 工作包契约留档（门禁按 YAML 校验） |
| `KF-RESULT-wp-9632-02.md` | 交付报告（六段 + 唯一 json 块） |

## 两条工程约束（对后续工作包可复用）

1. **零手抄**：证据 `quote` 一律由选择器（唯一子串所在整行）从源文本机器切片，脚本里不写源报告的
   数字/公式；切片后断言 `text.find(quote) == start_offset`，保证逐字且唯一。
2. **偏移量基准**：`start_offset/end_offset` 是 markdown 字段的 **Python str 字符偏移**（`ke.wp_gate.locator_matches` 语义），
   不是 UTF-8 字节偏移。证据同时带逐字 `quote` 与 `content_hash = sha256(quote)`，
   平台若按字节偏移复核，可用 quote 全文查找退化定位。
   （注：本仓工序 01 的 `asset_manifest.json` 用 `quote_sha256` 作字段名，工序 02/03 的
   `ke.wp_gate` 读 `content_hash`；本包按 `content_hash` 落，与门禁代码一致。）