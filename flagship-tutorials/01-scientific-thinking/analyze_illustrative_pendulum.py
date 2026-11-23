#!/usr/bin/env python3
"""Reproduce the explicitly invented numbers in ILLUSTRATIVE_ANALYSIS.md.

No experimental observations or stochastic physical simulation are included.
The calculations are ordinary least squares with a free intercept; a numerical
self-check checks arithmetic only, not scientific validity.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

DATA = Path(__file__).with_name("illustrative-pendulum.csv")
TRIAL_COLUMNS = ("trial_1_10_cycles_s", "trial_2_10_cycles_s", "trial_3_10_cycles_s")


def analyze(path: Path = DATA):
    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        for item in csv.DictReader(f):
            if item["origin"] != "invented_illustrative":
                raise ValueError("Each row must explicitly identify invented illustrative values")
            length = float(item["length_m"])
            trial_times = [float(item[k]) for k in TRIAL_COLUMNS]
            if length <= 0 or any(t <= 0 or not math.isfinite(t) for t in trial_times):
                raise ValueError("Lengths and trial times must be positive finite quantities")
            mean_period = sum(trial_times) / (10.0 * len(trial_times))
            rows.append({"length_m": length, "mean_period_s": mean_period, "period_squared_s2": mean_period ** 2})
    if len(rows) < 3 or len({r["length_m"] for r in rows}) != len(rows):
        raise ValueError("Use >=3 distinct pendulum lengths")
    x = [r["length_m"] for r in rows]
    y = [r["period_squared_s2"] for r in rows]
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    sxx = sum((v - xm) ** 2 for v in x)
    slope = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y)) / sxx
    intercept = ym - slope * xm
    if slope <= 0:
        raise ValueError("Cannot calculate a positive gravity proxy from a nonpositive slope")
    for row in rows:
        row["fitted_s2"] = slope * row["length_m"] + intercept
        row["residual_s2"] = row["period_squared_s2"] - row["fitted_s2"]
    return rows, slope, intercept, 4 * math.pi ** 2 / slope


def main():
    rows, slope, intercept, gravity_proxy = analyze()
    print("ILLUSTRATIVE INVENTED DATA — NOT PHYSICAL MEASUREMENTS")
    print("length_m  mean_T_s  mean_T2_s2  residual_s2")
    for r in rows:
        print(f'{r["length_m"]:8.2f}  {r["mean_period_s"]:8.6f}  {r["period_squared_s2"]:10.6f}  {r["residual_s2"]:+12.6f}')
    print(f"OLS free-intercept slope = {slope:.6f} s^2/m")
    print(f"OLS intercept = {intercept:.6f} s^2")
    print(f"Gravity proxy from fitted slope = {gravity_proxy:.6f} m/s^2 (NOT a measured g)")
    # Only an arithmetic regression check. Do not interpret as independent validation.
    assert len(rows) == 4
    assert abs(slope - 4.075722) < 1e-9
    assert abs(intercept - 0.000526133333333) < 1e-9
    assert abs(gravity_proxy - 9.686239052702186) < 1e-9
    assert abs(sum(r["residual_s2"] for r in rows)) < 1e-10


if __name__ == "__main__":
    main()
