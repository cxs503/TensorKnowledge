# P266W1-N10 补记：能力台账路由接线缺陷修复

## 发现的缺陷（可复现）

`backend/api/capability_audit.py`（21 能力证据等级矩阵端点，`GET /tensor/capabilities/audit`
与 `/audit/summary`）在仓内完整存在，但 `backend/main.py` **从未 include 该 router** →
线上该路径恒 404。

复现探针（带 JWT 打 :8010，2026-11-10）：

| 请求 | 结果 |
|---|---|
| `GET /api/v1/tensor/capabilities/audit`（无 token） | 401（auth 中间件先于路由） |
| `GET /api/v1/tensor/capabilities/audit`（带 token） | **404 Not Found** |
| `GET /api/v1/tensor/capabilities/semantics`（带 token） | 404（新端点，分支未部署，符合预期） |

无 token 时返回 401 而非 404，说明鉴权中间件先于路由匹配——所以**只看 401 会漏掉这个缺陷**，
必须带 token 探针才能区分「路由存在但需鉴权」与「路由根本不存在」。这是本单踩到的第二个坑。

## 修复

`backend/main.py` 按既有模式（try/except + 失败不拖垮主应用）挂载
`api.capability_audit.router`，与本次新建的 `api.capability_semantics.router` 并列在
`/api/v1/tensor/capabilities/*` 下。

接线回归（源码级，防止再次静默丢失）：`backend/tests/test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes`
断言 main.py 含两处 include，且两个 router 的路径形状正确（10 项测试全绿）。

## 局限

修复只在**本分支生效**；线上 :8010 需合并 + 重启后才会出现该端点（本次未重启服务、未 push）。
补记不改变主报告（id=11344）的任何判据数字。
