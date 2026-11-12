# wp-1204-01 · 01-asset-registration · report_id=1204

本目录是 work package `wp-1204-01` 的**已提交**产物（`artifacts/**` 被 `.gitignore` 丢弃，
见 `.gitignore` 第 5 行注释「mission-push gate drops artifacts/**」，故规范副本落 `docs/`，
运行期副本仍写 `artifacts/wp-1204-01/`，两份逐字节相等）。

## 产物

| 文件 | 说明 |
|---|---|
| `asset_manifest.json` | 主交付：report 1204 的资产清单（15 项，含定位符/解析状态/原因）。sha256 见下 |
| `kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs/claims`）；`outputs["asset_manifest.json"]` 与上面清单**深度相等** |
| `self_check.json` | worker 自检（从活取字节重算哈希与定位符），`all_pass=true`。**不是**平台验证 |
| `KF-RESULT-wp-1204-01.md` | 提交到平台的报告正文副本，与平台报告 14601 的 markdown **逐字节相同** |
| `fig_asset_inventory.png` | 图1：资产按 kind×解析状态分布（数字读自清单） |
| `report_published.json` | 平台发布记录（report_id=14601 + 回环校验结果） |

## 关键恒等式（可复算）

- 源 markdown：5853 字符 / 9016 字节 UTF-8，`sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef`（= 契约 `source_hash`）
- `asset_manifest.json` 字节 sha256：`28045e526d60e0c6f2f9b37afe9b50efc3fbe6238a911827d0fe5bf68fdd93f2`
- 提交的 `kf_result.json` ≡ 平台报告 14601 内嵌 JSON 块（deep equal，已回取比对）
- 提交的 `KF-RESULT-wp-1204-01.md` ≡ 平台报告 14601 `markdown` 字段（逐字节）

## 复跑

```bash
cd "$(git rev-parse --show-toplevel)"
python3 scripts/kf/build_asset_manifest_wp1204_01.py      # 活取 API + 硬哈希闸门 + 生成清单/信封
python3 scripts/kf/fig_asset_inventory_wp1204_01.py       # 图1
python3 scripts/kf/validate_kf_result.py                  # 自检（重取字节重算）
python3 -m pytest tests/test_kf_wp1204_01.py -q            # 10 条不变量测试
python3 scripts/kf/render_report_wp1204_01.py             # 报告正文 + /tmp/report_wp1204_01.json
```

注：`build_asset_manifest_wp1204_01.py --generated-at <ISO> --emitted-at <ISO>` 可冻结时间戳，
用于证明「重生成 == 已发布信封」（本包即以发布信封的戳复算得到 deep equal）。