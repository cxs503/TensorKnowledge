# 发布记录 — KF-RESULT wp-6939-01

| 平台 report id | 角色 | markdown 长度 | 说明 |
|---|---|---|---|
| 14672 | 首版（已被取代） | 22682 chars | `kf_result` 块与现版同源、同样通过哈希与子串校验，但正文与 manifest 缺少 `artifact_probe`（附件探测证据），叙述为早期版本 |
| **14681** | **定稿（以此为准）** | 25439 chars | 与仓库内 `docs/kf/wp-6939-01/{report.md,kf_result.json,asset_manifest.json}` **逐字节一致**；含 `artifact_probe.json` 证据与三次附件探测结论 |

两条报告的 `provenance.source_hash` 均等于 `sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246`（= report_id=6939 markdown 的 utf-8 字节哈希），且两条正文均**只有 1 个 ```json 代码块**、块内每个 `locator.quote` 均是源 markdown 的子串（已用平台侧重算独立复核）。

平台 `/tensor/reports/{id}` 无 PATCH/PUT 接口，首版无法就地更新，故以重新发布取代；两条并存不构成冲突（本包 `no_foreign_report_ids` 只约束 report_id 维度，同名报告在平台上并非唯一，已有其它工作包存在 2–4 条同名记录）。

复跑发布：`python3 scripts/kf/wp6939_report.py publish`（会写入新的 `publish_response.json`）。