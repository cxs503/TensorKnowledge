import json, sqlite3

evidence = {
    "impl_files": [
        "ke/kbm_extract.py:534 (main, 576 lines)",
        "ke/kbm_validate.py:1 (89 lines)",
        "schemas/method-card.schema.json",
        "schemas/parameter-card.schema.json",
        "schemas/failure-card.schema.json",
        "schemas/benchmark-card.schema.json",
        "schemas/code-pointer-card.schema.json",
        "docs/kbm-schema-v1.md"
    ],
    "entry": "ke/kbm_extract.py:575 (__main__); python3 -m ke.kbm_extract",
    "run_artifacts": [
        "runs/kbm/demo-sample/run_manifest.json (6/6 verified, verification_rate=1.0)",
        "knowledge/kbm/demo-sample/extract/claims/ (6 cards)",
        "knowledge/kbm/demo-sample/extract/evidence/ (6 records)",
        "knowledge/kbm/demo-sample/extract/provenance/tkp_demo_kbm-extract.json",
        "knowledge/kbm/demo-sample/extract/INDEX.md"
    ],
    "tests": "tests/test_kbm_extract.py: 30/30 passed (independently re-run 2026-11-11 by board-audit)",
    "integration_callers": "none: KE API alignment (POST /ko) is design-only, no platform caller invokes kbm_extract",
    "benchmark": "no registered case in tensor_benchmark_cases for anchor_slug=KBM-SCHEMA-W1 (table absent from local DBs, no API endpoint); mission judge = its own goal criteria (schema doc + repro_cmd + sampling>=80%); demo benchmark card: knowledge/kbm/demo-sample/extract/claims/tkc_demo_benchmark-benchmark-case-wigley-fr025.json",
    "repro_cmd": "python3 -m ke.kbm_extract --source-report knowledge/kbm/demo-sample/report.md --llm-output knowledge/kbm/demo-sample/llm_output.json --out <out> --run-dir <run> --namespace demo (re-run 2026-11-11: 6/6 verified, card set identical to committed)",
    "external_anchor": "PR#50 merged, commit 98b78e0 (m15180: matured mission deliverables, 27 files, 2544 insertions)"
}

sql = ("INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by) "
       "VALUES ('TensorKnowledge', 'm15180 KBM-SCHEMA-W1', '15246', 2, ?, 'board-audit')")
for db in ("/root/tp-agent/tensor.db", "/root/tp-agent/tools/tensor_platform.db"):
    c = __import__("sqlite3").connect(db)
    c.execute(sql, (json.dumps(evidence, ensure_ascii=False),))
    c.commit()
    n = c.execute("select count(*) from tensor_maturity_verdicts where scope='m15180 KBM-SCHEMA-W1'").fetchone()[0]
    print(db, "rows_for_scope:", n)
    c.close()
print("INSERTED level=2")
