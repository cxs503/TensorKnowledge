#!/usr/bin/env python3
"""wp-9447-01 gate-cost benchmark: registration time vs batch size.

Measures :func:`ke.mission_assets.register_matured_deliverables` on synthetic
packages of N deliverables (N = 1..64, 4 KiB files, median of 3 runs, fresh
in-memory store per run) and writes ``artifacts/wp-9447-01/bench.json`` plus the
figure ``docs/figures/wp-9447-01-registration.png``.

    python scripts/kf/wp9447_01_bench.py

Numbers land in the files; nothing is hand-copied into the report.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import mission_assets, store  # noqa: E402

SIZES = (1, 2, 4, 8, 16, 32, 64)
PAYLOAD = ("case,reference,candidate\n" + "A,1.000,0.997\n" * 250).encode()


def one_run(n: int, root: Path) -> float:
    pkg = root / f"pkg{n}"
    (pkg / "artifacts").mkdir(parents=True, exist_ok=True)
    specs = []
    for i in range(n):
        rel = f"artifacts/d{i:03d}.csv"
        (pkg / rel).write_bytes(PAYLOAD + f"#{i}\n".encode())
        specs.append({"deliverable_id": f"d{i:03d}", "title": f"deliverable {i}",
                      "path": rel, "evidence_grade": "REAL",
                      "acceptance": "row count 250, sha256 pinned"})
    conn = store.connect(":memory:")
    try:
        start = time.perf_counter()
        mission_assets.register_matured_deliverables(conn, "bench", specs, base_dir=pkg)
        conn.commit()
        elapsed = time.perf_counter() - start
    finally:
        conn.close()
    return elapsed


def main() -> int:
    out = REPO / "artifacts" / "wp-9447-01"
    out.mkdir(parents=True, exist_ok=True)
    fig_dir = REPO / "docs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="wp9447-bench-"))
    # Three independent sweeps; per point we keep the median of the sweep
    # medians, so a noisy shared box cannot move the reported number by luck.
    sweeps = [[[one_run(n, work) * 1000.0 for _ in range(3)] for n in SIZES]
              for _ in range(3)]
    rows = []
    per_sweep_slope = []
    for index, n in enumerate(SIZES):
        point = [statistics.median(sw[index]) for sw in sweeps]
        rows.append({"deliverables": n, "payload_bytes": len(PAYLOAD) * n,
                     "median_ms": round(statistics.median(point), 3),
                     "sweep_medians_ms": [round(v, 3) for v in point],
                     "us_per_deliverable": round(statistics.median(point) * 1000.0 / n, 2)})

    # least-squares slope through the origin: us per deliverable (marginal cost)
    for sw in sweeps:
        num = sum(statistics.median(sw[i]) * n for i, n in enumerate(SIZES))
        den = sum(n ** 2 for n in SIZES)
        per_sweep_slope.append(num / den)
    num = sum(r["median_ms"] * r["deliverables"] for r in rows)
    den = sum(r["deliverables"] ** 2 for r in rows)
    slope_ms = num / den
    resid = [r["median_ms"] - slope_ms * r["deliverables"] for r in rows]
    max_rel = max(abs(e) / r["median_ms"] for e, r in zip(resid, rows))

    payload = {
        "schema": "wp-9447-01-bench.v1",
        "environment": {"python": sys.version.split()[0], "platform": os.uname().machine},
        "rows": rows,
        "fit": {"slope_ms_per_deliverable": round(slope_ms, 4),
                "us_per_deliverable": round(slope_ms * 1000.0, 2),
                "max_rel_residual": round(max_rel, 4),
                "per_sweep_us_per_deliverable": [round(v * 1000.0, 2) for v in per_sweep_slope],
                "run_to_run_spread_us": [round(min(per_sweep_slope) * 1000.0, 2),
                                         round(max(per_sweep_slope) * 1000.0, 2)]},
        "notes": ("3 independent sweeps x 3 runs per point, median of sweep medians, "
                  "fresh in-memory store per run, 4 KiB csv payload; run-to-run spread "
                  "is reported because the host is shared"),
    }
    (out / "bench.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    ns = [r["deliverables"] for r in rows]
    ax.plot(ns, [r["median_ms"] for r in rows], "o-", label="measured (median of 3)")
    ax.plot(ns, [slope_ms * n for n in ns], "--",
            label=f"fit through origin: {slope_ms*1000:.0f} µs/deliverable")
    ax.set_xlabel("deliverables in batch")
    ax.set_ylabel("registration wall time (ms)")
    ax.set_title("wp-9447-01 registration gate cost\n(gate checks + sha256 + 1 INSERT per deliverable)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    png = fig_dir / "wp-9447-01-registration.png"
    fig.savefig(png)
    plt.close(fig)

    print(json.dumps({"bench": payload["fit"], "figure": str(png)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())