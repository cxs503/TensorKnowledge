"""Reviewer-side adversarial probe for wp-2506-04 (independent of the producer's script).

Question 1 (measurement validity): the producer's audit reports E = u^T A u on the
*full* fused matrix A = D A G, while its eigenvalue certificate uses the symmetric
part sym(A).  For du/dt = -A u the physical kinetic-energy rate is
d/dt(1/2||u||^2) = -u^T sym(A) u.  If A is not symmetric, u^T A u is NOT the
energy rate and its sign can differ from the sign of u^T sym(A) u.  We therefore
recompute both and look for sign disagreements across the 41-geometry sweep.

Question 2 (attribution): does the sweep determine "sum-by-parts of D A G fails"
as the root cause?  We record ||A - A^T||/||A|| (non-symmetric/adjoint defect) and
the relative size of the antisymmetric part, i.e. whether the energy defect can be
attributed to adjointness rather than to the two-point flux itself.

Run: PYTHONPATH=<TensorFVM>/src python3 probe_energy_rate.py
"""
import json
import sys

import numpy as np

from tensorfvm.native_viscous3d import NativeViscous3D
from tensorfvm.verification.native_energy import two_tetrahedra

rows = []
for skew in np.linspace(0, 1, 41):
    mesh = two_tetrahedra(float(skew))
    mask = mesh.neighbor < 0
    velocity = np.zeros((len(mesh.cells), 3))
    velocity[0, 0] = 1.0
    v = velocity.ravel()
    rec = {"skew": round(float(skew), 4)}
    for damping in (1.0, 0.5, 0.0):
        a = NativeViscous3D(mesh, mask, 1.0, correction_damping=damping).momentum_diffusion_matrix.toarray()
        sym = 0.5 * (a + a.T)
        anti = 0.5 * (a - a.T)
        e_full = float(v @ (a @ v))
        e_sym = float(v @ (sym @ v))
        na = np.linalg.norm(a)
        rec[f"e_full_a{damping}"] = e_full
        rec[f"e_sym_a{damping}"] = e_sym
        rec[f"sym_defect_a{damping}"] = float(np.linalg.norm(anti) / na) if na else 0.0
        rec[f"sign_mismatch_a{damping}"] = bool(
            (e_full > 0) != (e_sym > 0) and abs(e_sym) > 1e-12 and abs(e_full) > 1e-12
        )
        if damping == 1.0:
            rec["lam_min_sym_a1"] = float(np.linalg.eigvalsh(sym)[0])
    rows.append(rec)

print(json.dumps(rows[:3], indent=1))
for damping in (1.0, 0.5, 0.0):
    full_pos = [r["skew"] for r in rows if r[f"e_full_a{damping}"] > 0]
    sym_pos = [r["skew"] for r in rows if r[f"e_sym_a{damping}"] > 0]
    mism = [r["skew"] for r in rows if r[f"sign_mismatch_a{damping}"]]
    worst = max(r[f"sym_defect_a{damping}"] for r in rows)
    print(
        f"damping={damping}: full-positive n={len(full_pos)} sym-positive n={len(sym_pos)} "
        f"sign-mismatch n={len(mism)} {mism[:8]} max_sym_defect={worst:.3e}"
    )
print("max |e_full - e_sym| over all rows/dampings:",
      max(abs(r[f"e_full_a{d}"] - r[f"e_sym_a{d}"]) for r in rows for d in (1.0, 0.5, 0.0)))
json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "probe_energy_rate.json", "w"), indent=1)