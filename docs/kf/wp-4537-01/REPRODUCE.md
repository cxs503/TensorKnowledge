# wp-4537-01 离线复现说明（取源快照入库）

本包（report 4537 资产登记，task_type `01-asset-registration`）的所有不变量的前提是
**同一份源字节**：manifest 里每个 `span` / `quote` / `snippet_sha256` 都是对
`tensor_reports.markdown`（report 4537）那 12973 字节的切片。原方案把这份快照只落在
`runs/m15537_wp4537_01/`（`.gitignore` 忽略），后果是：

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 干净检出跑 `pytest tests/test_kf_wp4537_01.py` | 9 passed / **1 skipped**（`test_builder_is_deterministic` 无缓存即 skip）；`test_source_hash_matches_contract` 等依赖现场取源（无网络/无 `TENSOR_*` 时连哈希都验不了） | **12 passed / 0 skipped**，全程离线 |
| `python3 scripts/kf/register_4537_assets.py --from-cache` | 干净检出下 `FileNotFoundError` | 走入库快照，重算并校验钉住的 sha256 |
| `python3 scripts/kf/publish_4537_report.py --dry-run` | 干净检出下 `FileNotFoundError`（`SOURCE_MD` 指向上行缓存） | 走入库快照，报告可重生成 |

## 入库的两份快照

| 文件 | 内容 | 钉住值 |
|---|---|---|
| `docs/kf/wp-4537-01/source_report_4537.md` | `GET /api/v1/tensor/reports/4537` 的 `markdown` 字段原文（UTF-8） | `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08`，7931 字符 / 12973 字节 |
| `docs/kf/wp-4537-01/report_record_4537.json` | 同一记录的元数据（去掉 `markdown` 字段） | 构建器确定性复算的输入 |

快照**不是第二份真相**：`asset_manifest.json` 只登记 span/sha256，权威正文仍回平台取；
快照只用于复算。读入路径统一收敛到 `scripts/kf/kf4537_source.py`
（入库快照优先 → `runs/` 缓存兜底），`load_markdown()` 读入即校验 sha256 与字符数，
**漂移直接抛错，绝不静默刷新**（`test_snapshot_resolver_rejects_drifted_bytes`）。

## 一键复现（工作树根执行，无需网络、无需运行缓存）

```bash
python3 scripts/kf/kf4537_source.py                       # 打印实际取源路径 + sha256
python3 -m pytest tests/test_kf_wp4537_01.py -q           # 12 passed
python3 scripts/kf/register_4537_assets.py --from-cache \
        --out-dir /tmp/kf4537_rebuild                      # 复算到临时目录
python3 scripts/kf/publish_4537_report.py --dry-run        # 重生成 report.md
```

`--out-dir` 的意义：复算不该改动入库交付物。实跑结果（`generated_at` 除外逐字段相等）：

```
manifest equal modulo generated_at: True
rebuilt generated_at: 2026-11-15T01:26:07Z | committed: 2026-11-12T00:58:09Z
```

## 刷新快照（仅在平台侧报告正文真的更新时）

```bash
python3 scripts/kf/fetch_4537.py --out docs/kf/wp-4537-01   # 覆盖快照 + 记录
python3 -m pytest tests/test_kf_wp4537_01.py -q             # 期望先红：哈希/span 漂移
```

先红是设计意图：源一变，manifest、span、`kf_result.json`、结论都必须重做，
而不是让 gate 拿旧定位去比对新正文。刷新后须走 `register_4537_assets.py`（在线取源）
重建 manifest 与信封，再本文件末尾记录新的钉住值。

## 局限与注意点

1. `asset_manifest.json` 里 `source.retrieval` 仍只记 `endpoint`/`field`，资产级的
   `retrieval.cache` 仍写历史的 `runs/m15537_wp4537_01/source_report_4537.md` ——
   那是 m15537 当时的取源出处，作为**历史溯源**保留，不随快照入库而改写（改写会让
   已交付清单与历史不符）。入库副本的字节与该历史路径逐字节相同，由 sha256 保证。
2. `kf_result.json` 是信封的**去时间戳压缩投影**（无 `producer`/`emitted_at`/`notes`），
   以便重建字节稳定；`report.md` 内嵌的是发布当时的完整信封，故由
   `publication_envelope()` 从 manifest 现场重建，而不是读压缩件 —— 否则
   `--dry-run` 会静默把报告里的溯源字段抹掉（这是修复前的一个真实缺陷）。
3. 图 `asset_status.png` 由 `scripts/kf/make_4537_figure.py` 从 manifest 现场计数渲染；
   不同 matplotlib 版本像素可能不同，故本包只钉 manifest/信封/报告文本，**不钉 png 字节**。
4. 本包 objective 不含抽取，`claims` 恒为空数组；`unresolved` 25 项是诚实计负，不是缺陷。