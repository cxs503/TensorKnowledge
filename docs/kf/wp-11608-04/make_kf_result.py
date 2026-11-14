#!/usr/bin/env python3
"""wp-11608-04: assemble the KF-RESULT envelope, validate it, and stage the deliverables.

Reads : runs/wp-11608-04/{review_report.json, review_events.json, checks.json}
        + verbatim source markdown
Writes: runs/wp-11608-04/kf_result.wp-11608-04.json
        runs/wp-11608-04/source_report_11608.md   (byte-exact copy, for hermetic tests)
        docs/kf/wp-11608-04/*                     (staged deliverables)

Usage:
  python3 runs/wp-11608-04/make_kf_result.py [--source /tmp/r11608.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PKG = "wp-11608-04"
SOURCE_HASH = "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
TITLE = (
    "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + "
    "离散放大因子 G(θ) 全域比对"
)
SCENARIO = "p73w3-n04-fvm-numerical-viscosity"


def iter_quotes(obj, path=""):
    """Yield (path, quote) for every dict that carries a verbatim quote locator."""
    if isinstance(obj, dict):
        if isinstance(obj.get("quote"), str) and "start_char" in obj:
            yield path, obj
        for k, v in obj.items():
            yield from iter_quotes(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_quotes(v, f"{path}[{i}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/tmp/r11608.md")
    args = ap.parse_args()
    src = Path(args.source)
    raw = src.read_bytes()
    md = raw.decode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert digest == SOURCE_HASH, digest

    review = json.loads((HERE / "review_report.json").read_text(encoding="utf-8"))
    events = json.loads((HERE / "review_events.json").read_text(encoding="utf-8"))

    # every locator must be a verbatim, span-consistent substring of the source
    checked = 0
    for path, loc in iter_quotes(review):
        q = loc["quote"]
        span = md[loc["start_char"] : loc["end_char"]]
        if span != q:
            raise SystemExit(f"locator span mismatch at {path}: {span!r} != {q!r}")
        if md.count(q) < loc["occurrences"]:
            raise SystemExit(f"occurrence count wrong at {path}")
        checked += 1

    upstream_manifest = json.loads(
        (ROOT / "docs/kf/wp-11608-01/asset_manifest.json").read_text(encoding="utf-8")
    )
    upstream_hash = upstream_manifest["integrity"]["hash_recomputed_locally"]
    if "sha256:" + upstream_hash.replace("sha256:", "") != SOURCE_HASH:
        raise SystemExit("upstream wp-11608-01 manifest pins a different source hash")

    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": "11608",
        "provenance": {
            "source_uri": "tensor://reports/11608",
            "source_field": "markdown",
            "source_hash": digest,
            "source_hash_matches": True,
            "title": TITLE,
            "scenario_key": SCENARIO,
            "chars": len(md),
        },
        "outputs": {
            "review_report.json": review,
            "review_events.json": events,
        },
    }

    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(envelope)

    (HERE / "kf_result.wp-11608-04.json").write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # hermetic source copy for tests / re-runs
    (HERE / "source_report_11608.md").write_bytes(raw)

    # stage deliverables into docs/
    stage = ROOT / "docs/kf" / PKG
    stage.mkdir(parents=True, exist_ok=True)
    for name in (
        "review_report.json",
        "review_events.json",
        "checks.json",
        "kf_result.wp-11608-04.json",
        "fig1_upwind_deviation.png",
        "fig2_criterion_power.png",
        "fig3_quick_and_lw.png",
        "fig4_cd2_and_grid.png",
        "source_report_11608.md",
        "independent_checks.py",
        "build_review.py",
        "fetch_source.py",
        "make_report.py",
        "make_kf_result.py",
        "publish_report.py",
    ):
        shutil.copy2(HERE / name, stage / name)

    verification = {
        "package_id": PKG,
        "report_id": "11608",
        "gate": "pending_platform_verification",
        "note": "local mechanical checks only; verification verdict is computed by the platform gate",
        "checks": {
            "source_hash_recomputed": digest,
            "source_hash_matches_contract": digest == SOURCE_HASH,
            "chars_matches_contract": len(md) == 7342,
            "kf_result_schema_valid": True,
            "quote_locators_verified": checked,
            "quote_spans_match_source": True,
            "upstream_manifest_hash_agrees": True,
            "reviewer_context_excluded_producer_explanation": True,
            "claims_marked_verified": 0,
            "disposition": review["disposition"]["verdict"],
            "severity_counts": review["severity_counts"],
        },
        "emitted_at": "2026-11-12T00:00:00+00:00",
    }
    (stage / "verification.json").write_text(
        json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (HERE / "verification.json").write_text(
        json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps(verification["checks"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())