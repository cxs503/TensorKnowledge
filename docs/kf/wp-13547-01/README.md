# wp-13547-01 — 包索引（report 13547 · mission 20589）

**源报告**：`tensor://reports/13547` — TensorKnowledge 质量审计（A+B）：14 个 scope 的成熟度判定与 main 红态根因

**一句话**：把报告里可解析的工件（内嵌图 / 路径引用 / 表格 / 复现命令 / 接口字段）逐一定位并留哈希，
并对报告点名的 git 对象在本工作树做存在性探针；**claims=0**——登记不等于抽取，验证由平台门计算。

## 文件清单（sha256 逐文件重算）

| 文件 | 字节 | sha256 | 说明 |
|---|---:|---|---|
| `asset_manifest.json` | 66600 | `4af934893732bf713346bca16c467d3f7445160bf3a480c6773a4d6404e8df93` | 资产清单（定位器 + 哈希，claims=0） |
| `kf_result.json` | 888 | `f2d8ca054b8f715b0ef09b75e0861647443dea7c44901315ab6873d710788cd7` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `verification.json` | 2460 | `4e0f2b042aca8dec5a20ed77ec1120759c93c52b15fbc29cd0ef79f331dbfb4f` | 逐条 acceptance 自检 + 哈希重算 |
| `evidence_git_probe.json` | 2532 | `c747e07161907a1ef1eef64ba7861ad4230ed3588884bcc980ee23cf22d18f36` | git 证据探针（报告点名的 commit 在本工作树是否存在） |
| `report.md` | 13538 | `fdad5537bd35c955a76e7b96345e3d5e3817cfe0b44935e96c29dd8e64c5a7ff` | 本包报告（程序化渲染，六要素） |
| `report_payload.json` | 144593 | `a9c51fe96cfbd739a8f3848dbce877918d8bad7e56694fecc0b0a5af4c51a77e` | 上报载荷（title/summary/markdown/figure） |
| `published.json` | 450 | `b52d92d23ab90980463652c8f1d53ec57b1d72d4d9f501a6a91e43804b6b3275` | 发布台账（status=awaiting_pr_merge） |
| `figures/wp-13547-01_asset_locator_map.png` | 97553 | `ce73f46668f95a07be3888604fa7cfab2177d91479c1489dca6d6d20de5cca61` | 资产定位覆盖图（类别×解析状态 + 字符跨度） |

## 规模

- 资产 **22** 项；`by_class` = `{"report_markdown": 1, "embedded_figure": 3, "document_reference": 2, "source_code_reference": 9, "report_table": 5, "db_table": 1, "schema_field": 1}`
- 解析分布：`resolved_in_source`=12 / `referenced_unresolved`=10 / `declared_absent`=0；claims=**0**
- 源 markdown：6168 字符 / 8782 字节 utf-8；`sha256:2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42`
- git 探针：2 个 ref 中 2 个在本工作树历史中实存（`all_refs_present`=True）；范围探针 1 条

## 状态

- 发布：`awaiting_pr_merge`（记录于 `published.json`；合并后由平台门发布，本包不自称已发布）
- 验证：`verification.json` 的 `all_pass` 是**生产方自检**结论，权威判定在平台门。

## 复现

```bash
python3 scripts/kf/kf01_register.py --preset wp-13547-01 build gitprobe result verify figure report publish readme
```

（顺序即依赖：`gitprobe` 先于 `verify`（自检会重跑探针）；`publish`/`readme` 最后（读全部产物哈希）。）
