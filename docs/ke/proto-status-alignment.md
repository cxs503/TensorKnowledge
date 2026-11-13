# proto.md 状态校准（2026-11-11，m15956）

`docs/ke/proto.md` §0 已声明 PostgreSQL 为权威、SQLite 仅单测夹具，与
`docs/ke/backends.md` 一致。补充校准：

- 原型已从"仅 SQLite + 15 tests"演进为：SQLite/PostgreSQL 双后端同契约
  （`ke/store.py` / `ke/apistore.py`），API 层 `ke/api.py` 经 25 项 HTTP 集成测试。
- `ke/cli.py demo` 的示例路径 `pilots/m8554` 是历史单号段路径，夹具已迁到
  `tests/fixtures/ke-pilot/`（见其 `PROVENANCE.md`），以夹具路径为准。
- 源包规模以 `docs/ke/stats.md` 为准（机器生成，勿手抄）。
