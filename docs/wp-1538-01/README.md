# wp-1538-01 · 资产登记（report_id=1538）· 被跟踪副本

本目录是工作包 **wp-1538-01 / 01-asset-registration**（作用域：仅 `report_id=1538`）的**正式被跟踪副本**。
工作目录 `artifacts/wp-1538-01/` 内容与之逐字节相同，但本仓 `.gitignore` 丢弃 `artifacts/**`
（mission-push gate），故把交付面镜像到 `docs/` 以保证推仓后仍可复现、可审计。

平台侧交付：报告 `KF-RESULT wp-1538-01`（report id **14588**，tags 含 `kf-wp:wp-1538-01`），
其中的唯一 ```json 块即本目录 `kf_result_wp-1538-01.json` 的内容。

## 文件

| 文件 | 作用 |
|---|---|
| `asset_manifest.json` | **主产物**：资产清单（report 身份块 / attachments / artifacts / external_references / claims=[] / uncertainties / provenance） |
| `kf_result_wp-1538-01.json` | kf_result.v1 结果信封（平台门读取面） |
| `check_log.json` | 15 项核验记录（`all_ok=true`，含 schema 来源与指纹） |
| `build_asset_manifest.py` | 构建器：API 取数 → 哈希/长度核验 → §7 工件表程序化抽取 → 存在性探查 → 组 manifest → 结构门 → 写 check_log |
| `plot_manifest_checks.py` | 结果图（工件解析矩阵 + 身份核验条），数字全部从 manifest 读 |
| `build_report.py` | 由 manifest/check_log 生成六段报告 markdown 与平台 POST 载荷（零手抄） |
| `post_report.py` / `verify_posted_report.py` | 发布到平台 / 回读自检（标题、tags、json 块唯一、source_hash 指向 1538） |
| `wp1538_01_manifest_checks.png` | 结果图本体（150 dpi） |
| `../../../tests/test_wp1538_01_asset_manifest.py` | 8 项不变量测试（hash 绑定 / 引文逐字可定位 / id 唯一 / 信封结构） |

## 一键复跑

```bash
TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER \
TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS \
python3 docs/wp-1538-01/build_asset_manifest.py \
 && python3 docs/wp-1538-01/plot_manifest_checks.py \
 && python3 docs/wp-1538-01/build_report.py \
 && python3 -m pytest tests/test_wp1538_01_asset_manifest.py -q
```

（脚本按自身所在目录定位输出，故从 `docs/` 副本运行会就地刷新本目录文件；`generated_at` 时间戳会变，
其余字段不变。）

## 边界

- 只读取 `report_id=1538`；未读/写/覆盖任何其它 report_id，未改写上游产物。
- `claims=[]`：本工序 `task_type=01-asset-registration` 明确不做抽取（契约 notes）。
- 未把任何结论标成 `verified`；verification 由平台门计算。
- 附件 PNG 仅登记元数据（`binary_resolution=metadata_only`），未对二进制作断言。