#!/usr/bin/env python3
"""Probe 3: do the shipped C4/C5/C8 tests assert the acceptance invariants, and
what relative energy drift does the C8 scenario actually show?"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
TENSORDEM = pathlib.Path("/root/tp-agent/work/m19513")
sys.path.insert(0, str(TENSORDEM / "src"))
import numpy as np  # noqa: E402

from tensordem import ice_mixed_mode as mm  # noqa: E402
from tensordem.polyhedron import (  # noqa: E402
    create_regular_polyhedron, compute_polyhedron_inertia, PolyhedronParticle)

out = {}
cfg = mm.IceMixedModeConfig()

# --- what the C4/C5 validators actually return
lq = mm.validate_against_lindqvist(cfg, V=1.0)
tm = mm.validate_against_timco(cfg)
out["validate_against_lindqvist_keys"] = sorted(lq)
out["validate_against_timco_keys"] = sorted(tm)
out["timco_result"] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else str(v))
                       for k, v in tm.items() if not isinstance(v, (list, np.ndarray))}
out["lindqvist_relative_error_is_ratio_not_percent"] = {
    "returned": float(lq["relative_error"]),
    "as_percent": 100 * float(lq["relative_error"])}

# --- C8: replicate the shipped energy test and measure RELATIVE drift
verts = create_regular_polyhedron(n_vertices=12, radius=0.01)
mass, com, inertia = compute_polyhedron_inertia(verts)
v = 0.1
p1 = PolyhedronParticle(vertices=verts.copy(), position=np.array([0.0, 0.0, 0.0]),
                        orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                        velocity=np.array([v, 0.0, 0.0]), mass=mass,
                        inertia=inertia, id=0)
p2 = PolyhedronParticle(vertices=verts.copy(), position=np.array([0.015, 0.0, 0.0]),
                        orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                        velocity=np.array([-v, 0.0, 0.0]), mass=mass,
                        inertia=inertia, id=1)
KE0 = 0.5 * mass * v**2 + 0.5 * mass * v**2
out["C8"] = {
    "particle_mass_kg": float(mass),
    "velocity_m_s": v,
    "KE_initial_total_J": float(KE0),
    "reported_energy_change_J": 1e-3,
    "reported_1eJ_as_fraction_of_KE_pct": 100 * 1e-3 / float(KE0),
}

# --- C1: does any test compare the repose angle to a benchmark?
tests_src = (TENSORDEM / "tests/test_dem_ice.py").read_text(encoding="utf-8")
import re
blocks = {}
for name in ("TestAngleOfRepose", "TestValidation"):
    m = re.search(rf"class {name}:.*?(?=\nclass |\Z)", tests_src, re.S)
    blocks[name] = m.group(0) if m else ""
out["C1_test_blocks"] = {
    "repose_asserts": [ln.strip() for ln in blocks["TestAngleOfRepose"].splitlines()
                       if "assert" in ln],
    "validation_asserts": [ln.strip() for ln in blocks["TestValidation"].splitlines()
                           if "assert" in ln],
}
out["threshold_asserts_anywhere_in_C4_C5_blocks"] = [
    ln.strip() for ln in blocks["TestValidation"].splitlines()
    if "assert" in ln and ("0.3" in ln or "0.2" in ln or "relative_error <" in ln)]

print(json.dumps(out, ensure_ascii=False, indent=2))
(HERE / "probe3_results.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")