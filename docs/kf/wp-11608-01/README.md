# wp-11608-01 — asset registration for report 11608

工序：`01-asset-registration`（lane C）｜报告：report_id=11608｜scenario：`p73w3-n04-fvm-numerical-viscosity`
源哈希：`sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62`（7342 字符 / 10392 字节 UTF-8）

## 一键复跑

```bash
python3 scripts/kf_fetch_11608.py            # 取源 + 校验 sha256/字符数（需 TENSOR_AGENT_USER/PASS/TENSOR_API_BASE）
python3 scripts/kf_wp11608_01_register.py    # -> asset_manifest.json / kf_result / verification / locator_map
python3 scripts/kf_wp11608_01_report.py      # -> 三张图 + KF-RESULT-wp-11608-01.md（加 --publish 则发平台）
python3 -m pytest tests/test_kf_wp11608_01.py -q   # 16 项验收不变量
```

## 目录内容

| 文件 | 说明 |
|---|---|
| `asset_manifest.json` | 主产出：25 个资产、char-span locator、resolution、counts、integrity、limitations |
| `kf_result.wp-11608-01.json` | 平台结果信封（`claims=[]`，契约要求；`provenance.source_hash` = sha256:…） |
| `KF-RESULT-wp-11608-01.md` | 论文级报告（六段 + 唯一 json 代码块） |
| `asset_manifest.v1.schema.json` | 本包固定 schema（仓库通用版把 package_id 钉死 wp-448-01，不可复用） |
| `verification.json` | 本地机械校验清单，`gate=pending_platform_verification`（不含任何 verified 标记） |
| `fig1_asset_inventory.png` | 资产类别 × resolution |
| `fig2_locator_coverage.png` | 25 条 locator 在 7342 字符上的覆盖 |
| `fig3_resolution_audit.png` | resolution 普查 + 主体一致性拆分 |
| `publish.json` | 发布回执（`--publish` 后生成） |

取源字节级副本与 locator 中间件在 `runs/wp-11608-01/`（`report_11608.md|json`、`locator_map.json`）。

## 登记结论速览

- 25 资产 = `resolved_in_source` 5 + `referenced_unresolved` 14 + `declared_absent` 6；`off_topic` 10。
- 全部 locator 引文均为 markdown 逐字唯一子串（`integrity.quote_uniqueness=true`）；A16–A21 为
  `record.figures` 声明但正文缺席，locator 用逐字锚点 `## 4. 结果图`（`locator_semantics=anchor_where_expected`），
  缺席事实由 `record_name` + `resolution_check.result=absent` 承载——不为缺席资产编造引文。
- 两处上游主体不一致（只记录、不改上游）：6/6 `record.figures` 图注属水弹性主题且正文未引用；
  正文末行 *报告工件路径* 指向 4 个 hydroelasticity 工件（A12–A15）。
- 不做抽取：正文数字（如 §3.1 的 0.3999/0.400/0.03%）未复算；§8 的 “57 passed” 与 commit 号记 `not_run`。
- 边界：仅读 report_id=11608（测试 `test_only_report_11608_is_touched` 断言）。