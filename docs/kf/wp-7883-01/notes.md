# wp-7883-01 · 平台信道实测与记账（可复用知识）

本文件记录本工序中**实测得到**的平台行为，供后续知识产线工序复用；每条都注明观测方式与对象 id，
不写推测。

## 1. `tensor_reports` 表不可直连读（凭证层）

`psql -d tensorplatform -c "select markdown from tensor_reports where id=7883"` → `ERROR: permission denied for table tensor_reports`。
因此契约给的两条取文信道里，**只有 REST 可用**：`GET /api/v1/tensor/reports/{id}`（Bearer = `/auth/login` 的 `access_token`）。
本包所有数字都来自该信道的同一份响应字节。

## 2. 报告发布后 `figures[].png_base64` 被平台剥掉（观测：id=14692，源报告 id=7883）

* 发布 payload：`figures:[{name, caption, png_base64}]`（PNG 149,666 B）。
* 回读 `GET /tensor/reports/14692`：`figures[0]` 只剩 `name` + `caption`，**无 `png_base64`**。
* 源报告 7883 的 `figures[0]` 同样是 name+caption（无载荷）——不是生产方没传，而是平台 ingest 时丢弃。
* 推论（对本产线的意义）：**图不可能靠平台接口做字节级复核**。要可哈希的图，必须把 PNG 随仓库交付
  （本包：`docs/kf/wp-7883-01/fig1_asset_coverage_map.png`，sha256 `5934ff98fb6a3b81243867a413785df6bce6de15374b8b59f89a6610b0e8c4ca`）。
  任何"内嵌图已哈希"的声明都不可复核，应登记为 `metadata_only`。

## 3. 已发布报告不可原地更正（观测：id=14684）

`PATCH` / `PUT` / `DELETE /api/v1/tensor/reports/{id}` → 一律 `405 Method Not Allowed`；`/openapi.json` → `404`（无自描述）。
所以"发布后才发现散文口径有误"只能靠**新报告 + 取代声明**记账。本包因此产生三份同名报告：

| id | 状态 | 差异 |
|---|---|---|
| 14684 | 已被取代 | 散文 summary 把路径/路由类引用写成 5 条（实为 6；清单 `summary.by_kind_and_status` 本身正确） |
| 14687 | 已被取代 | 未实测图载荷是否保留，缺"平台丢弃 png_base64"的局限条目 |
| 14692 | **最终** | 上述两处已更正，取代链写在 ⑤ |

**纪律建议**：发布前先跑 `audit_published_7883.py`（回读自检），把"散文里的数字"也从工件生成，避免为一句散文再发一版。

## 4. 引文可复算的最小充分集

复核任一条引文只需三样：`source_hash`（绑定整份 markdown）、`locator.line/line_start/line_end`、`locator.quote`。
本包 `verify` 用 `lines[n-1] == quote` + `quote in markdown` 双条件；区间型用
`"\n".join(lines[s-1:e]) == quote`。多行表格引文因此是**跨行原样切片**，不做行内规范化。