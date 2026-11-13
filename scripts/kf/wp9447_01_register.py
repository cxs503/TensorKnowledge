#!/usr/bin/env python3
"""wp-9447-01 demo: register a matured mission's deliverables, prove the gates.

Runs the shipped :mod:`ke.mission_assets` path end to end on a scratch SQLite
store and writes ``artifacts/wp-9447-01/registration_report.json``.  Every number
in that file is produced by a call — nothing is typed by hand.

    python scripts/kf/wp9447_01_register.py [--out artifacts/wp-9447-01]

The mission package is synthetic and domain-neutral on purpose: TensorKnowledge
is the knowledge engine, so the demo must not carry any field-specific payload.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import assets, mission_assets, store  # noqa: E402

MISSION = "demo9447"

DOC = """# deliverable: reference-vs-baseline comparison

Three cases, error against the reference implementation:

| case | reference | candidate | rel. error |
|---|---|---|---|
| A | 1.000 | 0.997 | 0.30% |
| B | 2.500 | 2.512 | 0.48% |
| C | 4.000 | 3.982 | 0.45% |
"""

DATA = "case,reference,candidate\nA,1.000,0.997\nB,2.500,2.512\nC,4.000,3.982\n"


def build_package(root: Path) -> Path:
    pkg = root / "mission-package"
    (pkg / "docs").mkdir(parents=True)
    (pkg / "artifacts").mkdir()
    (pkg / "docs" / "result.md").write_text(DOC, encoding="utf-8")
    (pkg / "artifacts" / "comparison.csv").write_text(DATA, encoding="utf-8")
    # build junk that must be refused by the registration gate
    cache = pkg / "ke" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "store.cpython-311.pyc").write_bytes(b"\x00bytecode\x00")
    return pkg


def specs() -> list[dict]:
    return [
        {"deliverable_id": "result", "title": "reference-vs-baseline comparison",
         "path": "docs/result.md", "evidence_grade": "REAL",
         "acceptance": "three cases vs reference, all rel. error < 3%"},
        {"deliverable_id": "comparison", "title": "comparison table (csv)",
         "path": "artifacts/comparison.csv", "evidence_grade": "REAL",
         "acceptance": "row count 3, matches docs/result.md table verbatim"},
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "artifacts" / "wp-9447-01"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="wp9447-"))
    try:
        pkg = build_package(work)
        conn = store.connect(str(work / "ke.db"))

        first = mission_assets.register_matured_deliverables(
            conn, MISSION, specs(), base_dir=pkg, created_by="mkf-agent")
        conn.commit()
        second = mission_assets.register_matured_deliverables(
            conn, MISSION, specs(), base_dir=pkg, created_by="mkf-agent")
        conn.commit()

        # gate demonstrations (each expected to be refused)
        refusals: list[dict] = []
        mock_specs = [{**specs()[0], "evidence_grade": "MOCK"}]
        try:
            mission_assets.register_matured_deliverables(
                conn, MISSION, mock_specs, base_dir=pkg, version="9.9.9")
        except ValueError as exc:
            refusals.append({"attempt": "evidence_grade=MOCK",
                             "error_class": type(exc).__name__,
                             "reasons": getattr(exc, "problems", [str(exc)])})
        try:
            mission_assets.register_matured_deliverables(
                conn, MISSION,
                [{"deliverable_id": "pyc", "title": "bytecode",
                  "path": "ke/__pycache__/store.cpython-311.pyc",
                  "evidence_grade": "REAL", "acceptance": "n/a"}],
                base_dir=pkg, version="9.9.9")
        except ValueError as exc:
            refusals.append({"attempt": "path=__pycache__/*.pyc",
                             "error_class": type(exc).__name__,
                             "reasons": getattr(exc, "problems", [str(exc)])})
        try:
            mission_assets.register_matured_deliverables(
                conn, MISSION, specs(), base_dir=pkg, state="published")
        except ValueError as exc:
            refusals.append({"attempt": "state=published",
                             "error_class": type(exc).__name__,
                             "reasons": [str(exc)]})

        clean = mission_assets.verify_mission_deliverables(conn, MISSION, base_dir=pkg)
        (pkg / "docs" / "result.md").write_text(DOC + "\nedited after review\n",
                                                encoding="utf-8")
        drifted = mission_assets.verify_mission_deliverables(conn, MISSION, base_dir=pkg)
        index = mission_assets.mission_deliverable_report(conn, MISSION)
        versions = assets.list_ko_versions(conn)
        conn.close()

        payload = {
            "schema": "wp-9447-01-evidence.v1",
            "mission_id": MISSION,
            "first_run": first,
            "second_run": second,
            "refusals": refusals,
            "verify_clean": clean,
            "verify_after_edit": drifted,
            "mission_index": index,
            "ko_versions_in_store": len(versions),
            "checks": {
                "registered_first_run": first["counts"]["registered"] == 2,
                "idempotent_second_run": second["counts"]["registered"] == 0
                and second["counts"]["skipped_idempotent"] == 2,
                "batch_witness_stable": first["batch_sha256"] == second["batch_sha256"],
                "all_born_in_review": all(v["state"] == "in_review" for v in versions),
                "three_refusals": len(refusals) == 3,
                "drift_detected": drifted["counts"]["drift"] == 1,
                "clean_before_edit": clean["ok"] is True,
            },
        }
        (out / "registration_report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    checks = payload["checks"]
    print(json.dumps({"out": str(out), "checks": checks,
                      "all_ok": all(checks.values())}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())