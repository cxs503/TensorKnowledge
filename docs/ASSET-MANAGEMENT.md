# TensorKnowledge — Knowledge Asset Management

Status: implemented in `ke/assets.py`, exposed as `ke assets …`, registered by
`scripts/register_assets.py`. Contract precedent: `docs/ke/backends.md`
(one contract, two backends — SQLite fixture + authoritative PostgreSQL).

The record contract (`ke/contract.py`) answers *what is claimed*. This layer
answers the life-cycle questions on top of it:

* which knowledge objects (KOs) exist, in which version, and what replaced what;
* who approved which version, under which review policy, with what findings;
* which data artefacts (SFT / eval / triples exports) are pinned by digest;
* how much evidence each KO actually has, and whether it has gone stale.

## 1. Data model

Four tables, created by `ke.store.connect()` on both backends
(`assets.ASSET_SCHEMA`), so no caller can ever get a store without them:

| table | grain | mutability |
|---|---|---|
| `ko_versions` | one row per `(ko_id, version)` | append-only; replacement only via `superseded_by` |
| `review_events` | one row per review decision | append-only, `supersedes_event` for corrections |
| `dataset_assets` | one row per dataset asset id | immutable once the `sha256` is pinned |
| `quality_ledger` | one row per `ko_id` | derived, recomputed on demand |

Columns are `TEXT`/`INTEGER` only, so SQLite and PostgreSQL return
byte-identical values (`docs/ke/backends.md` records that rule for the record
contract; the asset layer follows it).

### KO identity

A KO version id is `f"{ko_id}:v{version}"`, e.g.
`tko:oss-lbm:ludwig:v1.0.16492317`. `ko_id` namespaces the object
(`tko:<path parts joined by ':'>` for a knowledge package), `version` is any
dotted string ordered by `assets.version_key` (`1.10.0 > 1.9.2`).

## 2. Life-cycle state machine

```
draft ──► in_review ──► published ──► deprecated (terminal)
  ▲           │  ▲            │
  └───────────┘  └────────────┘   (request-changes / re-review)
```

`assets.STATE_TRANSITIONS` is the single definition; `assets.check_transition`
raises `ValueError` on anything else (`deprecated` is terminal, `draft` cannot
jump straight to `published`). A version cannot be *born* deprecated.

`review_events.decision` drives the transition (`assets.REVIEW_EFFECTS`):

| decision | effect on the reviewed version |
|---|---|
| `approve` | → `published` |
| `request-changes` | → `in_review` |
| `reject` | → `draft` |
| `revoke` | → `deprecated` |
| `deprecate` | → `deprecated` |

`published` is therefore reachable *only* through a recorded `approve` — the
review gate is the table, not a convention.

## 3. Lineage instead of deletion

`supersede_ko(conn, old_vid, new_vid)`:

* requires both versions to exist, in the same `ko_id`;
* requires `version_key(new) > version_key(old)` (no regressions, no forks);
* refuses to supersede an already superseded version (lineage cannot fork);
* writes `old.superseded_by = new_vid` and moves `old` to `deprecated`.

Physical deletes are not implemented anywhere in the module.

## 4. Review events (audit trail)

`record_review(...)` appends one event and applies its state effect. Each event
carries `reviewer {kind, id}`, `policy_version`, `rationale`, `findings`,
`conditions` and an optional `supersedes_event`. Event ids are derived
deterministically from `(object_ref, target version, reviewed_at, decision,
seq)`; `seq` counts prior events for the same `object_ref`, so two decisions in
the same second stay distinguishable and ordered. `object_ref` may be a version
id *or* a bare `ko_id` (then the latest version is reviewed) — and
`get_review_events(ko_id)` returns the events recorded against *its versions*
too, otherwise the ledger would report "published but never reviewed" for
every version reviewed by id.

## 5. Dataset assets

`register_dataset_asset(...)` pins `(asset_id, version, record_count, sha256,
status_dist, gen_params, upstream_commit)`. Re-registering the same
`asset_id`:

* same `sha256` → idempotent no-op (safe to replay an export step);
* different `sha256` → `ValueError` immutability violation: published bytes are
  immutable, a content change must bump the version.

`sha256` must be a 64-char hex digest — the validation lives in the module, so
the CLI and the script cannot bypass it.

## 6. Quality ledger

`compute_quality_ledger(conn, stale_days=30, now=None)` recomputes and
materializes one row per KO:

| metric | definition |
|---|---|
| `evidence_count` | `COUNT(DISTINCT evidence_id)` over `claim_evidence` joined to `claims` whose `domain` is in the KO's declared `content["domains"]` (falling back to `[ko_id]`) |
| `citation_count` | other KO versions whose `content_json` references this `ko_id` |
| `falsified_count` | review events with decision `reject` or `revoke` |
| `last_review_at/decision` | newest review event of the KO |
| `state`, `version` | newest version (semver order) |
| `is_stale` | `published` **and** (never reviewed **or** last review older than `stale_days`) |

Two deliberate design notes:

1. **Exact linkage, not substring.** The closed prototype PR#22 counted
   evidence with `evidence.id LIKE '%<ko short name>%'`, which attributes an
   unrelated record to a KO whenever the substring happens to occur. The
   ledger now joins on the contract's own scope dimension
   (`claims.scope.domain → claims.domain`) and `claim_evidence`. No match ⇒ 0.
2. **Known granularity limit (honest).** `domain` is the only claim-level
   scope dimension in the record contract. All 118 claims of
   `knowledge/oss-lbm` share the single domain `lattice-Boltzmann-method`, so
   every sub-package KO that declares that domain reports the same
   domain-wide evidence total (158 evidence records in the current store).
   Per-package record counts are exact (`content["counts"]`, computed by
   `ke.contract.discover`); per-package *evidence* attribution needs a finer
   linkage dimension in the contract and is **not** claimed here.

`now` is injectable, which is what makes staleness testable.

## 7. Asset index export

`export_asset_index_obj(conn)` → `asset-index-v1`:

```json
{"format": "asset-index-v1",
 "generated_at": "2026-11-11T09:39:04Z",
 "total_entries": 9,
 "index_sha256": "<sha256 over the entries>",
 "entries": [{"asset_id": "...", "asset_type": "knowledge_object|dataset_sft|...",
              "version": "...", "state": "...", "sha256": "...",
              "created_at": "...", "lineage": ["<successor>"],
              "metadata": {"ko_id": "...", "content_keys": [...],
                           "content_sha256": "<pinned package digest>"}}]}
```

KO digests are a pure function of the stored row (`id`, `version`, `content`),
so an unchanged registry exports a byte-identical document on both backends.
`metadata.content_sha256` pins the *content* digest (for a knowledge package:
the digest of its record files), which is what makes drift detection possible.

## 8. Registration script

```bash
# register every KE package under knowledge/ (state: in_review — the registry
# records existence; publishing is a separate audited decision)
python scripts/register_assets.py --root knowledge --db /var/lib/ke/ke.db \
    --index artifacts/asset-index.json --report artifacts/health-report.json

# promote one asset through the gate
python -m ke.cli assets review tko:oss-lbm --decision approve \
    --reviewer ke-review --rationale "records + evidence complete" --db ke.db

# drift detection against the pinned index (exit 1 on any drift)
python scripts/register_assets.py --root knowledge --verify \
    --index artifacts/asset-index.json
```

The script derives the package digest as sha256 over
`[(relative path, file sha256), …]` sorted — machine independent, changes iff
record bytes change. Facts (record counts, claim domains) come from
`ke.contract.discover`, i.e. the *same* reader as the ingest path, so a
package can never be counted differently here than in the store.

## 9. CLI surface

```bash
ke assets list [--ko-id KO]              # registered versions
ke assets show KO [--lineage]            # latest version / full chain
ke assets register-ko KO --version V [--content JSON] [--state S]
ke assets review REF --decision D [--rationale R] [--reviewer R] [--finding F]
ke assets deprecate REF [--rationale R]
ke assets register-dataset --asset-id ID --type sft|eval|triples --version V \
                          --count N --sha256 HEX
ke assets datasets                       # dataset assets
ke assets report [--stale-days N]        # quality ledger + health summary
ke assets export-index [--output FILE]   # asset-index-v1 JSON
```

All subcommands take `--db` (SQLite path or PostgreSQL DSN) plus the shared
`--backend/--dsn/--schema` options; domain errors are reported as
`ERROR: …` on stderr with exit code 1 (no traceback).

## 10. Verification

`tests/test_assets.py` (51 cases, every store test run twice — SQLite and
PostgreSQL) covers: schema creation on connect, immutability of versions,
semver ordering, the full state machine, supersede fork/regression refusal,
the review gate (`published` only via approve), append-only review ordering,
dataset digest immutability, ledger evidence roll-up against a real ingested
pilot package, citation/falsification counters, staleness with injected `now`,
report summary, deterministic index export, the CLI round trip, and the
register/verify script (including tamper-triggered drift, exit 1).

```bash
python -m pytest tests/test_assets.py -q          # 51 passed (sqlite + pg)
python -m pytest tests/ -q                        # full suite
```

## 11. Non-goals

* No physical deletion, no in-place version rewriting (lineage only).
* No review *content* policy: the module records decisions, it does not judge
  evidence sufficiency (that is `ke/validate.py` + reviewer policy).
* Per-package evidence attribution (see §6 note 2) is out of scope until the
  record contract gains a finer claim-scope dimension.