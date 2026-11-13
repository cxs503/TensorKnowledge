# wp-13547-01 — asset registration for report 13547

KF 工序 `01-asset-registration`（lane C）的交付目录。**只登记，不抽取**：`claims=[]`，无 `verified` 标注。

| 项目 | 值 |
|---|---|
| report_id | `13547`（《TensorKnowledge 质量审计（A+B）：14 个 scope 的成熟度判定与 main 红态根因》） |
| source_uri / field | `tensor://reports/13547` / `markdown` |
| source_hash（sha256 over utf-8 bytes） | `sha256:2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42`（= 契约；chars 6168 / bytes 8782） |
| 资产 | 29 项，`by_resolution` = `{"resolved_in_source": 20, "referenced_unresolved": 8, "declared_absent": 1}` |
| claims | 0（契约允许空数组） |
| asset_manifest.json sha256 | `92b30eb07cc6d6e9ec9a08db29b2e83b3e97d748b0cc4b359a612662a39cb8ff` |
| kf_result.json sha256 | `2c1a7fb6de823bcd4f80b63285c617e30edac3ad24f01baf6a1cc8421bc5bf8b` |
| 平台报告 | `KF-RESULT wp-13547-01` → report_id **14887**（重发是同名 no-op，见 `published.json`） |

## 文件

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 资产清单（29 项，每项含绝对字符跨度 + 1-based 行号 + 逐字 quote + 解析状态） |
| `kf_result.json` | 结果信封（`schemas/kf_result.v1.schema.json` 通过） |
| `verification.json` | 9 项 acceptance 自检 + 哈希重算（`all_pass=true`） |
| `report.md` / `report_payload.json` | 已发布的报告正文 / 提交载荷 |
| `figures/wp-13547-01_asset_locator_map.png` | A) 类别×解析状态 B) 资产字符跨度覆盖图 |
| `evidence_git_probe.json` | 证据目录的 git 探针原始结果（HEAD 树 / 未合并分支） |
| `published.json` | 已发布报告 id |

## 一键复跑

```bash
python3 scripts/kf/kf01_register.py --preset wp-13547-01 build result verify figure
python3 scripts/kf/wp-13547-01/make_report.py            # 渲染；--publish 发布（幂等）
python3 scripts/kf/wp-13547-01/check_delivery.py         # 独立复核（--published 14887 复核已发布报告）
python3 -m pytest tests/test_kf_wp13547_01.py tests/test_kf01_register_probes.py -q
```

## 本次对共享工具的增量（`scripts/kf/kf01_register.py`）

1. **探针扫描** `scan_probes` + `run_probe`：把 glob / 目录 / commit / commit-range / 仓库 slug / 注册表名 / 工作树外路径这类"不是文件"的引用
   实测解析（文件系统、git 对象库、git 历史、psql），配置驱动（`PRESETS[...]["extra_probes"]`），无领域词硬编码。
   glob 未命中时再查 git 历史，从而区分「不存在」与「只在未合并分支」。
2. **bare filename 解析**（`basename_resolution`，默认关闭，仅本 preset 打开）：报告用 `cd <dir> && python x.py` 点名脚本时按唯一同名解析；歧义与省略号路径不解析。
3. **`resolve_local` 两处只增不改的判定**：绝对路径越界、省略号路径。修掉 `str.lstrip('./')` 按字符集剥离导致 `...m7437.py` 被误当成另一文件名的问题。

## 本报告的关键登记发现（都可在 `asset_manifest.json` 逐条复算）

- 证据目录 `artifacts/audit/*.log` 与 `artifacts/audit/figures/` **不在 HEAD 树**（`git ls-tree -r HEAD` → 0 条），
  字节存在于 commit `14fc40d`，只被 `refs/heads/agent/m14492` 包含 → 记 `referenced_unresolved` 并写明去处。
- `tensor_maturity_verdicts` 注册表在本 worker 上不可读（`permission denied`）→ 只登记引用，不复核 14 行判级。
- 三张图在平台记录里只有 name/caption（无 `png_base64`）→ `metadata_only`，不宣称拿到图字节。
