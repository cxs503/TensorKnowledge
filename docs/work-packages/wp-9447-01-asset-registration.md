# wp-9447-01 — 01-asset-registration（report 9447）

**工作包**：`wp-9447-01`（lane B，repo=TensorKnowledge，status=draft）
**源**：`tensor://reports/9447`，field=`markdown`，
`sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666`（chars=7241，bytes=10955）
**契约口径**：`register_assets: true`、`classify_report_type: false`、不做抽取（`claims = []`）

## 一句话结论

report 9447 的源身份已锁定（字节哈希与契约逐字符一致），16 条可解析资产全部登记并带
「逐字引文 + 行号 + 字符偏移」定位；原 mission 683 的 5 个工件按其自述标为
`declared_unrecoverable`，补报 runs 产物 9 条标为 `declared_only`（仅声明、未验证字节），
record 级 3 张图无 `png_base64` 载荷故图字节不可得。本工序不产出任何知识 claim。

## 资产状态口径

| status | 含义 | 本单条数 |
|---|---|---|
| `present_hash_verified` | 源文档字节本次实读并重算比对（sha256/chars） | 1 |
| `declared_unrecoverable` | 报告自述工件已灭失，不可恢复 | 5 |
| `declared_only` | 报告声明了路径，但本次未校验字节 | 9 |
| `reference_only` | 复现命令，作为字符串引用，未执行 | 1 |

> `present_hash_verified` **不表示**平台语义的 verified；verification 由平台门计算。

## 产物

| 路径 | 内容 |
|---|---|
| `runs/wp-9447-01/asset_manifest.json` | 资产清单 + 结构图 + 源注释 + 验证块（**canonical**，随仓推送） |
| `runs/wp-9447-01/kf_result.json` | KF 结果信封（唯一 json 块来源，canonical） |
| `runs/wp-9447-01/report.md` | 交付报告正文渲染件 |
| `artifacts/wp-9447-01/{asset_manifest,kf_result}.json` | 与 canonical 字节一致的镜像（`artifacts/` 被推送门滤除，仅本地便利） |
| `runs/wp-9447-01/register_assets.py` | 生成器（取源→重算哈希→逐字定位→自检→落盘） |
| `runs/wp-9447-01/emit_report.py` | 报告渲染/发布器 |
| `tests/test_wp_9447_01_asset_registration.py` | 回归测试（10 项，含 live locator 重解） |

## 复跑

```bash
python3 runs/wp-9447-01/register_assets.py
python3 -m pytest -q tests/test_wp_9447_01_asset_registration.py
python3 runs/wp-9447-01/emit_report.py          # 加 --no-post 只渲染
```

## 已发布报告

平台报告 **id=14711**（title=`KF-RESULT wp-9447-01`，tags 含 `kf-wp:wp-9447-01`，
mission_id=15641，scenario_key=ice_drag_cd_reissue）。发布后本地重跑仅 `provenance.emitted_at`
漂移（差异 1 处），16 条资产与验证块完全一致。

## 已知局限

1. `declared_only` 资产的**存在性与内容未校验**；本工作树对这些路径的
   `present_in_current_worktree` 全为 `false`（逐条记录在清单中）。
2. `record.figures` 仅 `name`/`caption`，无内嵌 PNG → 图字节不可从记录取得。
3. §⑤ 条目编号缺 7（1,2,3,4,5,6,8,9）；标题三种写法（合同/记录 title vs H1 多 `plan 1 / `）
   原样登记未归一，均以 `source_annotations` 记录，供下游抽取工序避坑。
4. 本单不做抽取、不做类型分类、不改写或重建任何上游产物。