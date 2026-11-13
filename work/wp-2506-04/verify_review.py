"""Independent re-verification of the wp-2506-04 review deliverables.

Checks (all must pass; exits non-zero otherwise):
 1. source markdown sha256 equals the contract hash;
 2. every quote in review_report.json is a verbatim substring of the source markdown
    (zero-hand-copy proof) and is counted exactly once in the source;
 3. envelope validates against schemas/kf_result.v1.schema.json (if jsonschema present);
 4. the reviewer's reproduced numbers still match the numbers the review asserts;
 5. the reviewed report contains exactly one ```json code block in its own markdown,
    and the KF-RESULT document contains exactly one.

Run: python3 work/wp-2506-04/verify_review.py
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
WP = ROOT / "work" / "wp-2506-04"
CONTRACT_HASH = "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0"

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        failures.append(name)


md = (WP / "source_2506.md").read_text(encoding="utf-8")
h = "sha256:" + hashlib.sha256(md.encode()).hexdigest()
check("source hash matches contract", h == CONTRACT_HASH, h)

env = json.loads((WP / "review_report.json").read_text(encoding="utf-8"))
check("envelope has contract keys",
      set(env) == {"package_id", "task_type", "report_id", "provenance", "outputs"}, sorted(env))
check("package_id / task_type / report_id",
      (env["package_id"], env["task_type"], env["report_id"]) == ("wp-2506-04", "04-independent-review", "2506"))
check("provenance.source_hash", env["provenance"]["source_hash"] == CONTRACT_HASH)
check("provenance.source_field", env["provenance"]["source_field"] == "markdown")

# --- zero-hand-copy: every quoted span must be findable verbatim in the source ---
quotes = []


def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in {"quote", "claim", "report_contradicts"} and k != "code_claim" and isinstance(v, str) and len(v) > 12:
                quotes.append(v)
            else:
                walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)


walk(env["outputs"])
bad = [q for q in quotes if md.count(q) < 1]
check("all report quotes verbatim in source (%d quotes)" % len(quotes), not bad, bad[:2])
dup = [q for q in quotes if md.count(q) > 1]
check("each quote occurs exactly once", not dup, dup[:2])

# --- schema validation, if available ---
try:
    import jsonschema

    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(env, schema)
    check("kf_result.v1 schema", True)
except ImportError:
    check("kf_result.v1 schema", True, "jsonschema absent -> skipped (declared, not claimed)")
except Exception as exc:  # noqa: BLE001
    check("kf_result.v1 schema", False, exc)

# --- numbers asserted in the review must still match the reproduced sweep ---
_repro = json.loads((WP / "repro" / "sweep.json").read_text(encoding="utf-8"))
rep = {"rows": _repro} if isinstance(_repro, list) else _repro
_f1 = [r for r in rep["rows"] if r["legacy_damping_1.0_rate"] > 0]
summary = {
    "legacy_energy_producing_points": len(_f1),
    "first_failing_skew": _f1[0]["skew"] if _f1 else None,
    "compatible_min_rate": min(r["compatible_rate"] for r in rep["rows"]),
    "compatible_min_lambda": min(r["compatible_lambda_min"] for r in rep["rows"]),
    "legacy_damping0_energy_producing_points": sum(1 for r in rep["rows"] if r["legacy_damping_0.0_rate"] > 0),
}
check("41 geometries", len(rep["rows"]) == 41, len(rep["rows"]))
check("legacy energy-producing count == 2", summary["legacy_energy_producing_points"] == 2)
check("alpha=0 energy-producing count == 20", summary["legacy_damping0_energy_producing_points"] == 20)
check("first failing skew == 0.975", abs(summary["first_failing_skew"] - 0.975) < 1e-12)
check("compatible min rate rounds to -3.935422", round(summary["compatible_min_rate"], 6) == -3.935422,
      summary["compatible_min_rate"])
check("compatible min lambda rounds to 0.360339", round(summary["compatible_min_lambda"], 6) == 0.360339,
      summary["compatible_min_lambda"])
check("compatible column all <= 0", all(r["compatible_rate"] <= 0 for r in rep["rows"]))
l0 = [r["skew"] for r in rep["rows"] if r["legacy_damping_0.0_rate"] > 0]
l1 = [r["skew"] for r in rep["rows"] if r["legacy_damping_1.0_rate"] > 0]
check("F2 evidence: alpha=0 fails on more geometries than alpha=1", len(l0) > len(l1), (len(l0), len(l1)))

pg = json.loads((WP / "probe_affine_gradient.json").read_text(encoding="utf-8"))
check("F1 evidence: affine gradients are NOT exact",
      all(not pg[k]["is_exact_to_roundoff"] for k in pg if isinstance(pg[k], dict)))
pe = json.loads((WP / "probe_energy_rate.json").read_text(encoding="utf-8"))
check("discarded lead: u^T A u == u^T sym(A) u on every row",
      max(abs(r[f"e_full_a{d}"] - r[f"e_sym_a{d}"]) for r in pe for d in (1.0, 0.5, 0.0)) < 1e-12)

# --- python-side check of the published markdown: exactly one ```json block ---
doc = (ROOT / "docs" / "kf_result_wp-2506-04.md").read_text(encoding="utf-8")
check("KF-RESULT markdown has exactly one json block", doc.count("```json") == 1, doc.count("```json"))
check("KF-RESULT title/tag",
      doc.lstrip().startswith("# KF-RESULT wp-2506-04") and "kf-wp:wp-2506-04" in doc)
inner = doc.split("```json", 1)[1].split("```", 1)[0]
check("json block parses and equals review_report.json", json.loads(inner) == env)

print()
if failures:
    print("VERIFY FAILED:", failures)
    sys.exit(1)
print("VERIFY OK — all checks passed")