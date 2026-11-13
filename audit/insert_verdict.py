#!/usr/bin/env python3
"""Board-audit verdict for m15810 (KBM-RCI-S1-REGISTRY, TensorKnowledge).

Independence: every number below is either read from an artifact or produced by
a check this audit ran itself (audit/recompute_registry.py, audit/db_crosscheck.sql,
audit/rerun_pipeline.sh at N=8, audit/insert_verdict.py SQL reads).
Paths in the machine-checked evidence keys point at copies under audit/refs/
(this worktree), which are byte-identical to the audited mission's files
(sha256 both sides recorded in evidence.details).

Level: L2 (独立功能实现). L3 withheld: the loader/consumer is not in repo main
and no platform service reads the table yet; L4 refused: tensor_benchmark_cases
has no case for this anchor.

Idempotent: one row per (repo, scope, verdict_by) -> ON CONFLICT update.
Run: python3 audit/insert_verdict.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

DSN = ("host=127.0.0.1 port=5432 dbname=tensorplatform user=foundation "
       "password=uGTN-KwuQv_7l8Tw0MMWUx_kf-nF2Rzz")
SUBJ = Path("/root/tp-agent/work/m15810")          # audited worktree (read-only)
HERE = Path(__file__).resolve().parent            # /root/tp-agent/work/m15886/audit
ROOT = HERE.parent                                # audit worktree m15886
REF = HERE / "refs"
ART = HERE / "artifacts"
REPO = "TensorKnowledge"
SCOPE = "m15810 KBM-RCI-S1-REGISTRY"
MISSION = 15886
BY = "board-audit"
LEVEL = 2

OUT = SUBJ / "runs/rci-s1-registry/out"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rp(p: Path) -> str:            # relative to audit worktree (machine-checked roots)
    return str(p.relative_to(ROOT))


def subj_sha(rel: str) -> str:
    return sha(SUBJ / rel)


def rerun_diff() -> dict:
    a = json.loads((OUT / "summary.json").read_text())
    b = json.loads((HERE / "runs/repro/out/summary.json").read_text())
    return {k: {"shipped": a.get(k), "rerun_n8": b.get(k)}
            for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def sql_checks() -> dict:
    import psycopg
    q: dict = {}
    with psycopg.connect(DSN) as cx, cx.cursor() as cur:
        cur.execute("SELECT count(*), count(DISTINCT report_id), min(report_id), max(report_id) "
                    "FROM rci_asset_registry")
        q["registry_rows"], q["distinct_ids"], q["min_id"], q["max_id"] = cur.fetchone()
        cur.execute("SELECT count(*) FROM tensor_reports WHERE status='published' "
                    "AND created_at <= TIMESTAMPTZ '2026-11-11 20:00:31.841339+00'")
        q["published_at_pin_sql"] = cur.fetchone()[0]
        cur.execute("""
            SELECT
              (SELECT count(*) FROM rci_asset_registry r LEFT JOIN tensor_reports t ON t.id=r.report_id WHERE t.id IS NULL),
              (SELECT count(*) FROM rci_asset_registry r JOIN tensor_reports t ON t.id=r.report_id WHERE t.status<>'published'),
              (SELECT count(*) FROM rci_asset_registry r JOIN tensor_reports t ON t.id=r.report_id
                 WHERE t.created_at > TIMESTAMPTZ '2026-11-11 20:00:31.841339+00')
        """)
        q["not_in_reports"], q["not_published"], q["after_pin"] = cur.fetchone()
        cur.execute("""SELECT count(*) FROM tensor_reports t LEFT JOIN rci_asset_registry r
                         ON r.report_id=t.id
                       WHERE t.status='published'
                         AND t.created_at <= TIMESTAMPTZ '2026-11-11 20:00:31.841339+00'
                         AND r.report_id IS NULL""")
        q["missing_from_registry"] = cur.fetchone()[0]
        cur.execute("""SELECT count(*), count(DISTINCT r.mission_id) FROM rci_asset_registry r
                       LEFT JOIN tensor_dev_missions m ON m.id=r.mission_id
                       WHERE r.mission_id IS NOT NULL AND m.id IS NULL""")
        q["dangling_rows"], q["dangling_missions"] = cur.fetchone()
        cur.execute("SELECT count(*) FROM information_schema.table_constraints WHERE "
                    "table_name='rci_asset_registry' AND constraint_type='FOREIGN KEY'")
        q["fk_constraints"] = cur.fetchone()[0]
        cur.execute("""SELECT count(*), sum(n), sum(n)-count(*) FROM
                       (SELECT dup_cluster_id, count(*) n FROM rci_asset_registry
                        WHERE dup_cluster_id IS NOT NULL GROUP BY 1) s""")
        q["dup_clusters_sql"], q["dup_reports_sql"], q["dup_excess_sql"] = cur.fetchone()
        cur.execute("""SELECT (markdown LIKE '%① 问题设定%'), (markdown LIKE '%② 方法与实现%'),
                              (markdown LIKE '%③ 参数表%'), (markdown LIKE '%④ 对照表%'),
                              (markdown LIKE '%⑤ 敏感性%'), (markdown LIKE '%⑥ 失败模式%')
                       FROM tensor_reports WHERE mission_id=15810 ORDER BY id DESC LIMIT 1""")
        q["six_sections_all_true"] = all(cur.fetchone())
        cur.execute("SELECT count(*) FROM tensor_benchmark_cases "
                    "WHERE anchor_slug='KBM-RCI-S1-REGISTRY'")
        q["benchmark_cases_for_anchor"] = cur.fetchone()[0]
    return q


def db_md5() -> str:
    r = subprocess.run(
        ["psql", "-h", "127.0.0.1", "-U", "foundation", "-d", "tensorplatform", "-At",
         "-c", "SELECT md5(markdown)||'|'||length(markdown) FROM tensor_reports WHERE id=14942"],
        capture_output=True, text=True,
        env={"PGPASSWORD": "uGTN-KwuQv_7l8Tw0MMWUx_kf-nF2Rzz", "PATH": "/usr/bin:/bin"})
    return r.stdout.strip()


def build_evidence() -> dict:
    rec = json.loads((ART / "m15810_recompute.json").read_text())
    rerun = rerun_diff()
    sql = sql_checks()
    R = REF / "rci-s1-registry"
    impl = [R / "build_data.py", R / "rci_pipeline.py", R / "load_registry.py",
            R / "verify_db.py", R / "sensitivity.py", R / "gen_report.py",
            R / "post_report.py", REF / "tests/test_rci_registry.py"]
    arts = [R / "out/registry_rows.jsonl.gz", R / "out/summary.json",
            R / "out/sensitivity.json", R / "out/db_extras.json",
            R / "out/inputs_manifest.json", R / "out/deep_dive.json",
            R / "figures/fig1_typing_clean.png", R / "figures/fig2_real_exec.png",
            R / "figures/fig3_duplicates.png", R / "figures/fig4_traceability_length.png",
            REF / "docs/rci-s1-registry.md", R / "repro.sh",
            ART / "m15810_recompute.json", ART / "m15810_db_crosscheck.txt",
            ART / "rerun_n8.log"]
    return {
        "impl_files": [rp(p) for p in impl],
        "entry": rp(R / "repro.sh"),
        "entry_cmd": ("bash audit/refs/rci-s1-registry/repro.sh (5 steps) — or step-wise: "
                      "rci_pipeline.py shard --shard i --n N ; rci_pipeline.py merge --snapshot "
                      "m15810@2026-11-11T20:00:31Z ; rci_pipeline.py verify"),
        "run_artifacts": [rp(p) for p in arts],
        "tests": [
            "audit/refs/tests/test_rci_registry.py::test_snapshot_and_row_count",
            "audit/refs/tests/test_rci_registry.py::test_partitions_are_complete",
            "audit/refs/tests/test_rci_registry.py::test_aggregates_recomputable_from_rows",
            "audit/refs/tests/test_rci_registry.py::test_relations_are_typed",
            "audit/refs/tests/test_rci_registry.py::test_sensitivity_monotone_in_gate",
            "audit/refs/tests/test_rci_registry.py::test_db_matches_artifacts",
            "auditor ran: python3 -m pytest tests/test_rci_registry.py -q -> 6 passed in 0.60s (subject worktree)",
            "auditor ran: python3 audit/recompute_registry.py -> 27/27 aggregates equal from "
            "registry_rows.jsonl.gz alone, 0 mismatch",
            "auditor ran: audit/rerun_pipeline.sh N=8 (different partition count) -> REPRO_N8_OK, "
            "'VERIFY OK: all 27 aggregates recomputed equal'",
            "auditor ran: psql audit/db_crosscheck.sql -> 9446/9446 ids, 0 missing, 0 extra, "
            "0 after-pin, dedup 763/2174/1411 matched",
        ],
        "integration_callers": [
            # NOTE: exists only at the data layer (platform DB), NOT in repo main ->
            # machine grep cannot confirm -> L3 deliberately not claimed (see level_note)
            "tensorplatform.rci_asset_registry (9446 rows, PK report_id, 1 FK -> tensor_reports)",
            "audit/refs/rci-s1-registry/load_registry.py:110 INSERT ... ON CONFLICT (report_id) DO UPDATE",
            "audit/refs/rci-s1-registry/verify_db.py:51-64 read-back of 17 aggregates",
            "caveat: no service/API consumes the table yet; q_accuracy/q_reusability/q_freshness "
            "are NULL placeholders (S2 scope)",
        ],
        "benchmark": ("NOT adjudicable: SELECT count(*) FROM tensor_benchmark_cases "
                      "WHERE anchor_slug='KBM-RCI-S1-REGISTRY' -> 0 (25 cases exist, none for this "
                      "anchor). Closest machine checks actually run: source-of-truth SQL "
                      "count(published, created_at<=T_pin)=9446 vs registry=9446 (error 0.0%); "
                      "coverage both directions 0 missing / 0 extra; dedup gate sweep "
                      "0.4/0.5/0.7 -> 764/763/758 clusters (main run insensitive)."),
        "repro_cmd": ("bash audit/refs/rci-s1-registry/repro.sh (full 5 steps, ~2.5 min/128 cores). "
                      "Auditor executed steps 1-3+5 at N=8 into audit/runs/repro -> REPRO_N8_OK; "
                      "step 4 (load_registry) NOT re-executed to keep the audited table read-only; "
                      "verify_db.py was run read-only against the shipped summary -> "
                      "'checked 17 aggregates; mismatches=0'."),
        "external_anchor": ("KBM-RCI-S1 criterion A1 headline 9446 vs SQL count at "
                            "T_pin=2026-11-11T20:00:31.841339Z = 9446 (exact); "
                            "KBM-CLEAN-W1 ledger sha256=72a287560c0bf868... (9504 rows, consumed "
                            "not rebuilt); Broder 1997 / Indyk-Mowatni 1998 / W3C PROV-O 2013; "
                            "oss_inventory '%REGISTRY%' -> 0 hits."),
        "level_note": ("L2 granted (machine-checkable): real code input->compute->output "
                       "(pinned SQL snapshot -> shard MinHash/typing -> DSU merge -> 9446-row "
                       "artifact + DB load), independently reproduced at a different shard count. "
                       "L3 WITHHELD: the loader/consumer exists only on branch agent/m15810 "
                       "(commit e4c7222, not in repo main) and nothing but verify_db.py/tests reads "
                       "tensorplatform.rci_asset_registry -> no platform wiring a gate can grep; "
                       "claiming L3 here would be an overstatement. L4 REFUSED: no "
                       "tensor_benchmark_cases entry for the anchor, so no ref-vs-got numeric "
                       "benchmark exists (only exact inventory-count agreement + threshold sweep)."),
        "auditor_checks": {
            "independent_recompute": rec["integrity"] | {
                "aggregate_mismatch_count": rec["mismatch_count"],
                "metadata_not_recomputable": rec.get("metadata_not_recomputable", [])},
            "sql_crosscheck": sql,
            "rerun_n8_vs_shipped_diff": rerun,
            "report_row": {"tensor_reports.id": 14942,
                           "worktree_doc_sha256": subj_sha("docs/rci-s1-registry.md"),
                           "db_md5|len": db_md5(),
                           "db_md5_equals_worktree_doc": db_md5().split("|")[0] ==
                           hashlib.md5((SUBJ / "docs/rci-s1-registry.md").read_bytes()).hexdigest()},
        },
        "findings": [
            {"id": "F1", "severity": "non-blocking", "claim": "repro.sh is not fully deterministic",
             "evidence": ("N=8 rerun vs shipped: wt_exists 2240->%s, triple_ok 1881->%s, "
                          "failed_empty 1737->%s; 447 of the 2240 shipped wt_exists missions no "
                          "longer have a worktree dir (live filesystem probe in "
                          "build_data.py:probe_worktree)" %
                          (json.loads((HERE / "runs/repro/out/summary.json").read_text())["wt_exists"],
                           json.loads((HERE / "runs/repro/out/summary.json").read_text())["triple_ok"],
                           json.loads((HERE / "runs/repro/out/summary.json").read_text())["failed_empty"])),
             "impact": ("3 of 27 aggregates (live-probe family) drift on replay; the other 24, the "
                        "headline 9446, typing and dedup are bit-stable"),
             "fix": "snapshot worktree_triple.json as a pinned input instead of probing live"},
            {"id": "F2", "severity": "non-blocking", "claim": "drift sentence mixes two timestamps",
             "evidence": ("docs §1 'published = 9993（漂移 +523）': inputs_manifest live=9969 "
                          "(9969-9446=523) but db_extras live=9993 (9993-9446=547)"),
             "impact": "auxiliary number only; ledger 9446 is SQL-verified and unaffected",
             "fix": "derive both numbers from one read timestamp"},
            {"id": "F3", "severity": "info", "claim": "failed_empty presented as additive",
             "evidence": ("codes sum 1992 (1589+140+185+78) vs union 1737; 223 rows carry >=2 codes "
                          "(rci_pipeline.py:325-326 union over rows)"),
             "impact": "presentation; union is the correct semantics and what tests assert",
             "fix": "label 'union, multi-code rows counted once' in report §4"},
            {"id": "F4", "severity": "info", "claim": "A5 mission chain criterion fails",
             "evidence": "SQL: 10 registry rows / 2 distinct mission_id dangle; report marks A5 ❌ itself",
             "impact": "0.11% of corpus; 9365/9446 rows carry a resolvable mission_id",
             "fix": "document as residual, or add orphan ledger / ON DELETE SET NULL"},
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ev = build_evidence()
    (ART / "m15810_verdict_evidence.json").write_text(
        json.dumps(ev, indent=1, ensure_ascii=False, default=str))
    print(json.dumps({"level": LEVEL, "evidence_keys": sorted(ev),
                      "run_artifacts": len(ev["run_artifacts"]),
                      "findings": [f["id"] + ":" + f["severity"] for f in ev["findings"]]},
                     ensure_ascii=False))
    if a.dry_run:
        return 0
    import psycopg
    with psycopg.connect(DSN) as cx, cx.cursor() as cur:
        cur.execute("""
            INSERT INTO tensor_maturity_verdicts
                (repo, scope, mission_id, level, evidence, verdict_by)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (repo, scope, verdict_by) DO UPDATE
               SET mission_id=EXCLUDED.mission_id, level=EXCLUDED.level,
                   evidence=EXCLUDED.evidence, created_at=now(),
                   gate_state='pending', gate_level=NULL, gate_note=NULL
            RETURNING id, gate_state, gate_level
        """, (REPO, SCOPE, MISSION, LEVEL,
              json.dumps(ev, ensure_ascii=False, default=str), BY))
        row = cur.fetchone()
        cx.commit()
    print("verdict row:", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())