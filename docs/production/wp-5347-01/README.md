# wp-5347-01 — 工序 01 资产登记（report 5347）

本目录只承载 **一份报告（report_id=5347）** 的资产登记产物；不读取、不覆盖其它 report_id。

## 文件与用途

| 文件 | 用途 | 关键字段（不在本文件复述数字，见文件自身） |
|---|---|---|
| `report_5347.md` | 源字节快照（`tensor://reports/5347` 的 `markdown` 字段，UTF-8 原样） | 其 sha256 即 `provenance.source_hash` |
| `report_5347.md.meta.json` | 报告记录元数据（title/tags/figures/…），不含 `markdown` | `figures[].name/caption` 只有文本，无图像字节 |
| `asset_manifest.json` | **工序 01 声明输出**：源身份 + 资产清单 + 可达性 + `unresolved` | `counts`、`assets[].reachability`、`registration.extraction_rule` |
| `kf_result.json` | kf_result 信封（`package_id/task_type/report_id/provenance/outputs`，`claims: []`） | `outputs.asset_manifest.json` 与上一行文件同构 |
| `KF-RESULT-wp-5347-01.md` | 交付正文：六段 + **唯一一个** JSON 代码块（= `kf_result.json`） | 已原样发布于平台 report 14642 |
| `checks.json` | 本地 acceptance A1–A10 逐项结果 | `counts`：passed / vacuous / failed / not_run |
| `platform_gate.json` | 复用平台 `kf/ops/knowledge_factory/gates.py` 重放的结构门+证据门 | `structure`/`evidence`/`evidence_stats` |
| `live_gate.json` | 独立复检：从**已发布**报告榨取 payload、重取 5347 明文、重算哈希再跑门 | `checks` L1–L6 |
| `figures/*.png` | 台账图（资产分布 / 门禁逐项状态），由 `scripts/wp_5347_01_figures.py` 投影生成 | — |

## 边界与已知局限

- **不抽取、不分类、不生成 claim**：`claims` 为空数组，是契约允许的完整结果；
  `A6`（claims 均有证据或显式未解析）因此为**空真**，记 `vacuous`，不得读作“已验证”。
- **所有资产 `resolved=false`**：跨仓工件（TensorDEM 的 `docs/`/`scripts/`/`artifacts/`/`src/`/`tests/`）
  不在本包 `source_uri` 字节范围内；`/tmp/...` 复现目录属临时；runner 布局、环境依赖不是资产；
  两张图只有图注元数据。
- **图像字节不可回读**：不仅源报告 5347，本包自己上传的图在 `GET /tensor/reports/<id>`
  也只返回 `name`/`caption`（无 base64 字段），故下游不可依赖 API 取回图像。
- **未标 verified**：本包不写任何 `verified`/`verification_status` 类字段；
  verification 由平台门计算（`live_gate.json` 只是本地独立复检证据）。

## 一键复跑

```bash
python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md \
 && python3 scripts/wp_5347_01_register_assets.py \
 && python3 scripts/verify_wp_5347_01.py \
 && python3 scripts/check_wp_5347_01_platform_gates.py \
 && python3 scripts/wp_5347_01_register_assets.py --render-only \
 && python3 scripts/wp_5347_01_figures.py \
 && python3 -m pytest -q tests/test_wp_5347_01.py
```

发布复检（需平台凭据）：`python3 scripts/verify_wp_5347_01_live.py --report-id 14642`
## 本目录与运行区的关系

`artifacts/` 被 `.gitignore` 丢弃（本仓 run-area 约定），因此本目录是同一套产物的**入库快照**；
脚本优先读 `artifacts/wp-5347-01/`，不存在时回落到本目录（`scripts/*_wp_5347_01*.py` 顶部解析）。
快照已用 `python3 scripts/verify_wp_5347_01.py --dir docs/production/wp-5347-01` 独立复核通过。
