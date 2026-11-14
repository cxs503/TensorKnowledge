#!/usr/bin/env python3
"""Probe 2: phase-diagram mode census + shipped test suite execution.

Read-only against the sibling TensorDEM checkout; nothing is written outside
this work package.
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TENSORDEM = pathlib.Path("/root/tp-agent/work/m19513")
sys.path.insert(0, str(TENSORDEM / "src"))

out = {}
from tensordem import ice_mixed_mode as mm  # noqa: E402

cfg = mm.IceMixedModeConfig()
pd = mm.compute_phase_diagram(base_config=cfg)
cells = pd.mode_map
names={0:"crushing",1:"bending",2:"splitting",3:"mixed"}
out["phase_diagram_fields"] = [f for f in dir(pd) if not f.startswith("_")]
census = {}
flat = cells if not hasattr(cells, "ravel") else cells.ravel()
for c in flat:
    c = str(c)
    c = names.get(int(c), c)
    census[c] = census.get(c, 0) + 1
out["phase_diagram_mode_census"] = census
out["phase_diagram_cells"] = int(len(flat))
out["splitting_present_in_phase_diagram"] = any("split" in k for k in census)
out["mixed_present_in_phase_diagram"] = any("mixed" in k for k in census)

# mode census over the full reported phase-diagram box, sampled densely
modes = {}
for V in (0.05, 0.2, 0.5, 1.0, 1.4, 2.0, 3.0, 5.0, 8.0):
    for L in (1.0, 10.0, 50.0):
        c = mm.IceMixedModeConfig(**{**cfg.__dict__, "D": L})
        m = mm.determine_dominant_mode(c, V)
        modes.setdefault(m, 0)
        modes[m] += 1
out["dominant_mode_census_9x3"] = modes

# shipped test suite
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_dem_ice.py", "-q",
     "--no-header", "-p", "no:cacheprovider"],
    cwd=str(TENSORDEM), capture_output=True, text=True,
    env={"PATH": "/usr/local/bin:/usr/bin:/bin",
         "PYTHONPATH": str(TENSORDEM / "src"), "HOME": "/tmp"})
out["pytest_tail"] = (proc.stdout or "").strip().splitlines()[-6:]
out["pytest_returncode"] = proc.returncode
out["pytest_stderr_tail"] = (proc.stderr or "").strip().splitlines()[-4:]

(HERE / "probe2_results.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(out, ensure_ascii=False, indent=2))