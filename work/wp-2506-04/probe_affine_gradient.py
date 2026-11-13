"""Reviewer probe 2: is the cell-gradient template exact on affine fields?

The shipped module ``native_compatible_viscous3d.py`` states (module docstring):
"For affine velocity fields the cell gradients are exact, so the discrete energy
identity ... holds to round-off and the coefficient of the operator is certified".
Report 2506 section 5 instead states that the native cell-gradient template is not
volume-normalised and deviates from the analytic value (max 6.17), so the absolute
scale of K is *not* certified.  The two statements cannot both be true.  This probe
measures the affine reproduction error directly from ``NativeViscous3D.gradient_matrices``.

Run: PYTHONPATH=<TensorFVM>/src python3 probe_affine_gradient.py
"""
import json

import numpy as np

from tensorfvm.native_viscous3d import NativeViscous3D
from tensorfvm.verification.native_energy import two_tetrahedra

rng = np.random.default_rng(0)


def affine_error(mesh):
    mask = mesh.neighbor < 0
    op = NativeViscous3D(mesh, mask, 1.0)
    a = rng.standard_normal((3, 3))
    b = rng.standard_normal(3)
    x = np.asarray(mesh.cell_centers, dtype=float)
    u = x @ a.T + b                      # cell-centred affine field, u_i = a_ij x_j + b_i
    g = np.empty((len(x), 3, 3))         # g[c, i, j] = d u_i / d x_j
    for i in range(3):
        for j in range(3):
            g[:, i, j] = op.gradient_matrices[j] @ u[:, i]
    err = np.abs(g - a[None, :, :])
    return {
        "n_cells": int(len(x)),
        "max_abs_deviation": float(err.max()),
        "max_rel_deviation": float(err.max() / np.abs(a).max()),
        "analytic_scale_max": float(np.abs(a).max()),
        "is_exact_to_roundoff": bool(err.max() < 1e-12),
    }


out = {}
for skew in (0.0, 0.5, 1.0):
    out[f"two_tetrahedra_skew{skew}"] = affine_error(two_tetrahedra(skew))
try:
    from tensorfvm.verification.native_energy import distorted_cube  # noqa

    out["distorted_cube_2"] = affine_error(distorted_cube(2))
except Exception as exc:  # pragma: no cover - probe only
    out["distorted_cube_2"] = f"unavailable: {exc}"

for k, v in out.items():
    print(k, v)
json.dump(out, open("probe_affine_gradient.json", "w"), indent=1)