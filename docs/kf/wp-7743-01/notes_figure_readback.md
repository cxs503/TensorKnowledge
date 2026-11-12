# wp-7743-01 附注：report 平台图件读回行为（实测，非推测）

本包发布 KF-RESULT 报告后（`POST /tensor/reports` → **id 14703**，title `KF-RESULT wp-7743-01`），
对该报告做了一次读回核对，发现一个与“图件字节”有关的平台行为，记录在此以免下一单重复踩：

| 观察 | 证据 |
|---|---|
| 提交时 `figures[0]` 带 `name` / `caption` / `png_base64`（真 PNG，235521 bytes） | `scripts/kf_wp774301_publish_report.py::publish` 中 `base64.b64encode(FIG.read_bytes())` |
| 读回 `GET /tensor/reports/14703` 的 `figures[0]` **只有 `name`、`caption` 两个键**，无 `png_base64` | 实测 `dict_keys(['name','caption'])` |
| 因此“按 report id 取回图件字节”在当前平台不可用 | 旁证：report 7743 自身的 8 个图件字节端点（`/artifacts/<name>`、`/figures/<name>`）全 404 |

结论（诚实口径）：**报告里的图在平台上只保留“名字+说明”元数据，字节不在平台上**。
本包因此把 PNG 作为仓内资产提交（`docs/kf/wp-7743-01/figures/wp774301_source_locator_map.png`），
并在 `report.md` §三产出物清单里给出它的 sha256；复跑 `render` 会重新生成同一张图。

不影响本工序的 6 条 acceptance：它们只涉及 `asset_manifest.json` / `kf_result.json` 与源 markdown
哈希，不含图件字节。此处不做“已嵌入平台”的声明。