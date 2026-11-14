#!/usr/bin/env python3
"""Probe 4: independently execute the shipped 35-test suite (C-statistic check).

The suite needs the repository root on PYTHONPATH (its conftest imports the
installed package layout); probe2's stripped environment produced a collection
error, which is an environment artifact, not a test failure. This probe records
the real outcome and wall time.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
TENSORDEM = pathlib.Path("/root/tp-agent/work/m19513")

env = dict(os.environ)
env["PYTHONPATH"] = str(TENSORDEM / "src") + os.pathsep + str(TENSORDEM)
env["HOME"] = "/tmp"

t0 = time.time()
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_dem_ice.py", "-q", "--no-header",
     "-p", "no:cacheprovider"],
    cwd=str(TENSORDEM), capture_output=True, text=True, env=env)
wall = time.time() - t0

tail = (proc.stdout or "").strip().splitlines()[-3:]
m = re.search(r"(\d+) passed", proc.stdout or "")
out = {
    "command": "python3 -m pytest tests/test_dem_ice.py -q --no-header -p no:cacheprovider",
    "cwd": str(TENSORDEM),
    "commit": subprocess.run(["git", "-C", str(TENSORDEM), "log", "-1", "--format=%H"],
                             capture_output=True, text=True).stdout.strip(),
    "returncode": proc.returncode,
    "passed": int(m.group(1)) if m else None,
    "wall_seconds": round(wall, 2),
    "tail": tail,
    "report_claims_total_tests": 35,
    "matches_report_statistic": bool(m and int(m.group(1)) == 35),
}
(HERE / "probe4_results.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(out, ensure_ascii=False, indent=2))