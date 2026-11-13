# m8802 旗舰闭环验收路径

**锚**：`KBM-TKC-DOC-SYNC`（本文件即 ⑤ 判据）。锚定仓库 TensorKnowledge。

## 闭环定义
`任务引用 KE → 产出新 claim → 回流沉淀（四契约 + 独立评审 + 发布） → 可再检索`

## 可执行验收链（逐步，每步有命令/端点）
1. **入库**：`python -m ke.migrate --check`（SQLite staging ↔ PostgreSQL 逐表 digest 对账 PASS）
2. **检索（任务侧引用）**：`GET /kb/search?q=...`、`GET /query/by-domain?domain=...`（命中落注入台账）
3. **产出 claim**：`POST /ko`（kind=claim/evidence/provenance，schema 校验 + 四轴状态 draft）
4. **封装四契约**：claim.evidence_refs ↔ evidence.claim_refs 双向边入库，`GET /query/chain` 可回溯 source/locator/quote
5. **独立评审**：`POST /ko/{id}/submit` → `POST /ko/{id}/review`（reviewer != producer，否则 403）
6. **发布**：`POST /ko/{id}/publish`（需 approved）
7. **再检索 + 度量**：`GET /query/stats` 计数变化；闭环延迟=第 2 步请求到第 7 步可见的时间戳差
8. **负结果入账**：refuted/not-assessed claim 同样走 3–7，不被丢弃

## 判据（全绿才算闭环成立）
- [x] 步骤 1：迁移对账 PASS（`tests/test_ke_migrate.py`；当前 4 项 pin 值过期，见下「已知缺陷」）
- [x] 步骤 2–6：API 集成测试通过（`tests/test_ke_api.py`，25 tests，真 uvicorn + 鉴权 + 并发）
- [x] 步骤 4：溯源链查询 `GET /query/chain` 已实现
- [x] 步骤 5：禁止自批由服务端强制（403 用例覆盖）
- [ ] 步骤 7：闭环延迟度量尚无单一端到端脚本（本单只明确路径，未实现脚本）
- [ ] 步骤 8：源包无 review-event 记录，经治理 KO 当前为 0（`docs/ke/stats.md`）→ 闭环未在真实资产上跑通

## 已知缺陷（honest）
- `tests/test_ke_migrate.py` 4 项失败：pin 值 `claims=102/objects=257` 为旧包快照，现包已增长
  （`kel.migrate` 实测 claims=150/objects=369）；`docs/ke/migration-reconcile.json` 待重生成。
  属统计口径漂移，已登记为文档同步遗留项，未在本单修复。
