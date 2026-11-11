# KE HTTP API — endpoint contract

Service: `ke/api.py` (FastAPI). Storage: `ke/apistore.py` (Postgres via
`psycopg`, SQLite for local tests — same portable SQL, real transactions in both).

```
export KE_API_TOKEN=...                       # required for every write
export KE_DSN='postgresql:///ke_service?user=ke_reader'
python -m uvicorn ke.api:app --host 127.0.0.1 --port 8021
```

`127.0.0.1:8021` deliberately avoids the platform control plane (`:8010`) and the
ship-performance API (`:8011`). Nothing is hard-coded: host, port, DSN and token
are environment variables (`KE_DSN`, `KE_API_TOKEN`, optional `KE_DB` for a
SQLite file, `KE_SCHEMA_STRICT=1` to validate every record against
`schemas/*.schema.json`).

Systemd/manual unit: [`ke/api.service`](../../ke/api.service).

## Knowledge objects

A knowledge object is one of the four contract records — `claim`,
`evidence`, `provenance`, `review` — stored verbatim (`doc`) plus a denormalised
status block. Id prefixes decide the kind: `tkc:` claim, `tke:` evidence,
`tkp:` provenance, `tkr:` review (a wrong prefix is a `422`).

### Four independent states

| axis | values | moved by |
|---|---|---|
| `production_status` | `draft`, `submitted`, `superseded` | `POST /ko/{id}/submit` |
| `evidence_status` | `claim.epistemic_status` / `evidence.assessment_status` (e.g. `established`, `well-supported`, `contested`, `unassessed`, `not-assessed`) | carried in the record |
| `review_status` | `unreviewed`, `in-review`, `approved`, `changes-requested`, `rejected`, `revoked`, `deprecated` | `POST /ko/{id}/review` |
| `publication_status` | `private`, `published`, `retracted` | `POST /ko/{id}/publish` |

They never imply one another: submitting for production does not assess
evidence, an approved review does not publish, and a revoke retracts a published
object without touching its evidence status.

Review decisions map to `review_status` as: `approve → approved`,
`request-changes → changes-requested`, `reject → rejected`, `revoke → revoked`,
`deprecate → deprecated`; `revoke`/`deprecate` also set
`publication_status=retracted` if the object was published. Re-approval out of
`rejected`/`revoked`, and any decision after `deprecated`, is a `409`.

**No self-audit:** the service refuses any review whose `reviewer.id` equals the
object's `producer` (`403`), and the rule lives in the storage layer so no entry
point can bypass it.

## Auth

`Authorization: Bearer $KE_API_TOKEN` on every mutating call.

* `KE_API_TOKEN` unset → `503` (write surface disabled; a bad deploy fails closed)
* header missing / wrong → `401` with `WWW-Authenticate: Bearer`

Reads (`GET`) are open on the loopback interface; put the service behind a
reverse proxy if the read surface must be protected.

Producer identity for producer-scoped writes (`submit`, `patch`, `delete`) comes
from the `X-KE-Agent` header (fallback: the `producer` body field, then
`created_by`/`captured_by` of the record). Missing identity → `422`.

## Endpoints

### Ops

| method | path | notes |
|---|---|---|
| GET | `/healthz` | `{status, driver, reachable, write_enabled, version, time}` — no auth |
| GET | `/` | service info + endpoint list |

### CRUD

| method | path | body | result |
|---|---|---|---|
| POST | `/ko` | `{kind, producer?, doc}` or a bare record | `201` object; `409` duplicate id; `422` bad record |
| GET | `/ko/{id}` | — | `200` object incl. exact `doc`; `404` |
| GET | `/ko` | query: `kind`, `axis`+`status`, `domain`, `limit`, `offset`, `include_doc` | `{total, items}` |
| PATCH | `/ko/{id}` | `{doc}` | `200` — drafts only, producer only (`409`/`403`) |
| DELETE | `/ko/{id}` | — | `204` — drafts only, producer only |

### Review / publication flow

| method | path | body | notes |
|---|---|---|---|
| POST | `/ko/{id}/submit` | — | `draft → submitted`, producer only |
| POST | `/ko/{id}/review` | `{decision, reviewer:{id,reviewer_type}, policy_version?, rationale?, findings?, id?}` | appends a `review-event`; `403` self-audit; `409` illegal transition |
| POST | `/ko/{id}/publish` | — | needs `review_status=approved`; `409` otherwise |
| GET | `/ko/{id}/reviews` | — | append-only review log |

Review events are immutable: the log is only ever appended to.

### Query surface (six classes)

| # | method | path | purpose |
|---|---|---|---|
| Q1 | GET | `/query/by-status?axis=&status=&kind=` | objects by any one of the four state axes |
| Q2 | GET | `/query/by-evidence-relation?relation=supports\|refutes\|qualifies\|contextualizes\|mentions\|derived-from` | evidence↔claim pairs by relation |
| Q3 | GET | `/query/chain?claim_id=` | claim → evidence → source, plus provenance records |
| Q4 | GET | `/query/by-domain?domain=&exact=&kind=` | claims by `scope.domain` (substring by default) |
| Q5 | GET | `/query/claim-evidence?claim_id=` | evidence attached to one claim + `dangling_evidence_refs` |
| Q6 | GET | `/query/stats` | per-kind counts, edge count, review-event count, four status distributions |
| — | GET | `/search?q=&kind=&domain=&axis=&status=&limit=` | case-insensitive text search over claim statements/notes/domain (and evidence citations, provenance activity), filterable |

Q3 details: `links[]` are per-claim evidence records with `source` + `locator`;
`provenance[]` holds records bound to the claim/evidence ids
(`generated_entity.id` or `derived_from`); `package_provenance[]` holds records
recorded at *package* level (`knowledge/<namespace>/...`) and is reported
separately so a missing per-claim provenance record stays visible. `complete` is
true only when every link carries a source.

Q5 details: `dangling_evidence_refs` lists ids referenced by the claim's
`evidence_refs` that were never ingested — the cross-reference invariant stays
observable instead of being silently enforced away.

## curl examples

```bash
TOKEN=$KE_API_TOKEN
BASE=http://127.0.0.1:8021
AUTH="Authorization: Bearer $TOKEN"

# health (no auth)
curl -s $BASE/healthz

# create a claim
curl -s -X POST $BASE/ko -H "$AUTH" -H 'Content-Type: application/json' \
  -H 'X-KE-Agent: agent-m8801' -d @- <<'JSON'
{"kind":"claim","doc":{
  "id":"tkc:smoke:lbm-limit",
  "statement":"D2Q9 LBM reproduces the Navier-Stokes limit at second order.",
  "claim_type":"mathematical","epistemic_status":"established",
  "scope":{"domain":"lattice-Boltzmann-method"},
  "evidence_refs":["tke:smoke:lbm-src"],
  "created_at":"2026-11-10T00:00:00Z","created_by":"agent-m8801","version":"1.0.0"}}
JSON

# read it back (exact ingested document)
curl -s $BASE/ko/tkc:smoke:lbm-limit

# submit for production, then review with a *different* identity
curl -s -X POST $BASE/ko/tkc:smoke:lbm-limit/submit -H "$AUTH" -H 'X-KE-Agent: agent-m8801'
curl -s -X POST $BASE/ko/tkc:smoke:lbm-limit/review -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"decision":"approve","reviewer":{"id":"agent-reviewer-1","reviewer_type":"agent"},"rationale":"source inspected"}'

# self-audit is refused (403)
curl -s -X POST $BASE/ko/tkc:smoke:lbm-limit/review -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"decision":"approve","reviewer":{"id":"agent-m8801","reviewer_type":"agent"}}'

# publication requires the approval above
curl -s -X POST $BASE/ko/tkc:smoke:lbm-limit/publish -H "$AUTH"

# six query classes
curl -s "$BASE/query/by-status?axis=evidence&status=established"
curl -s "$BASE/query/by-evidence-relation?relation=supports"
curl -s "$BASE/query/chain?claim_id=tkc:smoke:lbm-limit"
curl -s "$BASE/query/by-domain?domain=lattice-Boltzmann-method"
curl -s "$BASE/query/claim-evidence?claim_id=tkc:smoke:lbm-limit"
curl -s "$BASE/query/stats"

# search: text + domain + status
curl -s "$BASE/search?q=relaxation&domain=lbm&axis=evidence&status=established"
```

## Bulk ingest of an existing package

```bash
KE_API_TOKEN=$TOKEN python3 -m ke.ingest_client \
  --base-url http://127.0.0.1:8021 --package knowledge/oss-lbm --producer agent-m8801
```

Reads `<pkg>/{claims,evidence,provenance}/*.json` (list- or per-record form) and
recurses into sub-packages. Duplicate ids are counted as `exists` (HTTP 409), so
re-running an import is safe.

Real-data smoke (all six queries + review flow, raw responses written to
`artifacts/ke_smoke/`):

```bash
KE_API_TOKEN=$TOKEN python3 scripts/ke_smoke_oss_lbm.py --base-url http://127.0.0.1:8021
KE_API_TOKEN=$TOKEN python3 scripts/ke_smoke_verify.py   --base-url http://127.0.0.1:8021  # recount vs API
python3 scripts/ke_smoke_figure.py                                                    # figure from artifacts
```

`scripts/ke_smoke_verify.py` recomputes object/edge counts straight from the
package JSON with an independent loader and diffs them against `/query/stats`
(exit 1 on any mismatch), so the smoke numbers have a baseline rather than a
self-reference. Last run: 251 objects, 300 edges, 0 differences, 0 duplicate ids.

## Errors

| code | meaning |
|---|---|
| 401 | missing/invalid bearer token |
| 403 | four-state policy violation (self-audit, non-producer edit/delete) |
| 404 | unknown id |
| 409 | duplicate id, illegal state transition, editing a non-draft |
| 422 | malformed record / unknown kind / missing producer identity |
| 503 | write surface disabled (`KE_API_TOKEN` unset) |

## Tests

```bash
pytest tests/test_ke_api.py -q                                        # SQLite backend
KE_TEST_DSN='postgresql:///ke_m8801?user=postgres' pytest tests/test_ke_api.py -q   # Postgres backend
```

25 tests: auth (401/503), contract validation, CRUD, four-state machine,
self-audit refusal, publish gating, all six query classes, search filters,
concurrent distinct writes, concurrent same-id race (exactly one 201), plus a
smoke test that ingests the real `knowledge/oss-lbm` package.