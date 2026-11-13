# TK agent-consumption cases (KBM-TKC-INDEX-API ④)

mission_id=15722 · consumer=agent-m15722

| case | dimensions | verdict | artifact | cites |
|---|---|---|---|---|
| TK-CASE-A | concept, method | PASS | `artifacts/tk-agent-cases/case-a-taylor-green.json` | 2 |
| TK-CASE-B | evidence | PASS | `artifacts/tk-agent-cases/case-b-provenance.json` | 1 |
| TK-CASE-C | problem | PASS | `artifacts/tk-agent-cases/case-c-exactness-scope.json` | 2 |

## KPI-KB-REUSE-RATE (from `GET /usage/stats`)

- injected objects: 3
- cited objects: 4
- object-level reuse rate: 0.6666666666666666
- event-level reuse rate: 1.25

All numbers above are produced by `scripts/tk_agent_cases.py` from the API responses; nothing is hand-copied.
