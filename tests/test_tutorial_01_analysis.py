"""Arithmetic and provenance regression checks for Tutorial 01's invented dataset.

Passing these tests cannot certify scientific accuracy, measurement quality,
subject-matter review, pedagogical validity, or a real learner pilot.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUTORIAL = ROOT / "flagship-tutorials" / "01-scientific-thinking"
DATA = TUTORIAL / "illustrative-pendulum.csv"
SCRIPT = TUTORIAL / "analyze_illustrative_pendulum.py"


def test_illustrative_values_cannot_be_mistaken_for_measurements() -> None:
    with DATA.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert all(row["origin"] == "invented_illustrative" for row in rows)
    assert len({row["length_m"] for row in rows}) == len(rows)
    assert sorted(rows[0]) == sorted((
        "length_m", "trial_1_10_cycles_s", "trial_2_10_cycles_s",
        "trial_3_10_cycles_s", "origin",
    ))


def test_cli_reproduces_only_illustrative_regression() -> None:
    run = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "ILLUSTRATIVE INVENTED DATA" in run.stdout
    assert "NOT PHYSICAL MEASUREMENTS" in run.stdout
    assert "4.075722 s^2/m" in run.stdout
    assert "0.000526 s^2" in run.stdout
    assert "9.686239 m/s^2" in run.stdout
    assert "NOT a measured g" in run.stdout


def test_companion_explicitly_discloses_origin_and_review_status() -> None:
    text = (TUTORIAL / "ILLUSTRATIVE_ANALYSIS.md").read_text(encoding="utf-8")
    assert "invented" in text.lower()
    assert "not" in text.lower() and "measurements" in text.lower()
    assert "pending" in text.lower()
    assert "analyze_illustrative_pendulum.py" in text
