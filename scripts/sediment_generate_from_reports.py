#!/usr/bin/env python3
"""Generate sediment packages for specific missions from extraction reports.

Creates knowledge/sediment/m{id}/ directories with four-contract JSON files
based on the extraction reports in docs/.

Missions covered:
- m8381: KVLCC2 MMG model (from docs/m8838_sediment_extraction_report.md)
- m2591: Wigley wave resistance pressure path (from docs/sediment-m2591-report.md)
- m7485: KP505 open water BEM (from scripts/sediment_spec_m7485.py)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

SEDIMENT_DIR = REPO_ROOT / "knowledge" / "sediment"
NOW = datetime.now(timezone.utc).isoformat()


def create_m8381():
    """KVLCC2 MMG model knowledge extraction (from docs/m8838_sediment_extraction_report.md)."""
    d = SEDIMENT_DIR / "m8381"
    d.mkdir(parents=True, exist_ok=True)

    claims = [
        {
            "id": "tkc:ship-m8381:turning-circle-deviation",
            "statement": "D/L=0.354 at delta=35 degrees for KVLCC2 MMG model, baseline 3.05, deviation -88.4%. Far exceeds the <=10% target.",
            "claim_type": "predictive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-manoeuvrability",
                "system": "KVLCC2 MMG model",
                "conditions": ["delta=35 degrees", "SIMMAN Workshop baseline"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m8381:turning-circle-sim"],
            "created_at": NOW,
            "created_by": "agent/m8838",
            "version": "0.1.0",
            "notes": ["HONEST-FAIL: turning circle accuracy not achieved"]
        },
        {
            "id": "tkc:ship-m8381:hydrodynamic-derivative-calibration",
            "statement": "Hydrodynamic derivative calibration insufficiency is the primary cause of turning circle deviation for KVLCC2 MMG model.",
            "claim_type": "causal",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-manoeuvrability",
                "system": "KVLCC2 MMG model"
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m8381:calibration-analysis"],
            "created_at": NOW,
            "created_by": "agent/m8838",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m8381:test-suite-validation",
            "statement": "pytest suite of 15 tests, 13 passed (86.7% pass rate) for KVLCC2 MMG model implementation.",
            "claim_type": "descriptive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-manoeuvrability",
                "system": "KVLCC2 MMG model",
                "conditions": ["pytest 15 items"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m8381:pytest-output"],
            "created_at": NOW,
            "created_by": "agent/m8838",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m8381:geometry-params",
            "statement": "KVLCC2 geometry: Lpp=320.0m, B=58.0m, T=20.8m, Cb=0.8098, displacement=312622t, Dp=9.86m, AR=112.0m2.",
            "claim_type": "descriptive",
            "epistemic_status": "draft",
            "scope": {"domain": "ship-geometry", "system": "KVLCC2"},
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m8381:geometry-source"],
            "created_at": NOW,
            "created_by": "agent/m8838",
            "version": "0.1.0"
        }
    ]

    evidence = [
        {
            "id": "tke:ship-m8381:turning-circle-sim",
            "claim_refs": ["tkc:ship-m8381:turning-circle-deviation"],
            "source": {"source_type": "simulation", "citation": "ship-performance-platform agent/m8381"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "ship-performance-platform@575ecc21 benchmarks/turning_circle"},
            "extraction_method": "simulation",
            "captured_at": NOW,
            "captured_by": "agent/m8838",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m8381:calibration-analysis",
            "claim_refs": ["tkc:ship-m8381:hydrodynamic-derivative-calibration"],
            "source": {"source_type": "internal-artifact", "citation": "docs/m8838_sediment_extraction_report.md"},
            "relation": "supports",
            "locator": {"locator_type": "section", "value": "Section 3: Calibration Analysis"},
            "extraction_method": "direct-quotation",
            "captured_at": NOW,
            "captured_by": "agent/m8838",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m8381:pytest-output",
            "claim_refs": ["tkc:ship-m8381:test-suite-validation"],
            "source": {"source_type": "simulation", "citation": "pytest output agent/m8381"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "tests/ 15 items, 13 passed"},
            "extraction_method": "simulation",
            "captured_at": NOW,
            "captured_by": "agent/m8838",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m8381:geometry-source",
            "claim_refs": ["tkc:ship-m8381:geometry-params"],
            "source": {"source_type": "internal-artifact", "citation": "ship-performance-platform agent/m8381 source"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "ship-performance-platform@575ecc21 hull geometry"},
            "extraction_method": "direct-quotation",
            "captured_at": NOW,
            "captured_by": "agent/m8838",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        }
    ]

    provenance = [
        {
            "id": "tkp:ship-m8381:extraction",
            "generated_entity": {"id": "knowledge/sediment/m8381", "entity_type": "knowledge-object"},
            "activity": {
                "id": "activity-m8381-extraction",
                "activity_type": "extraction",
                "description": "Knowledge extraction from KVLCC2 MMG model mission m8381",
                "started_at": NOW,
                "ended_at": NOW
            },
            "agents": [{"id": "agent-m8838", "agent_type": "software-agent", "name": "TensorKnowledge extractor", "role": "knowledge extractor"}],
            "derived_from": ["ship-performance-platform@575ecc21"],
            "recorded_at": NOW,
            "version": "0.1.0"
        }
    ]

    _write_package(d, claims, evidence, provenance, "m8381", "KVLCC2 MMG model")


def create_m2591():
    """Wigley wave resistance pressure path (from docs/sediment-m2591-report.md)."""
    d = SEDIMENT_DIR / "m2591"
    d.mkdir(parents=True, exist_ok=True)

    claims = [
        {
            "id": "tkc:ship-m2591:pressure-path-negative",
            "statement": "Wave resistance pressure path gives consistently negative values for Wigley hull (B/L=0.10), diverging 103-284% from Kochin far-field reference.",
            "claim_type": "predictive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-wave-resistance",
                "system": "Wigley hull BEM",
                "conditions": ["B/L=0.10", "Fr=0.20-0.40", "thin-ship approximation"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m2591:pressure-audit"],
            "created_at": NOW,
            "created_by": "agent/m8830",
            "version": "0.1.0",
            "notes": ["HONEST-FAIL: pressure path does not converge to correct answer"]
        },
        {
            "id": "tkc:ship-m2591:convergence-not-correct",
            "statement": "Quadrature converges to 7-digit precision at 128 nodes but maintains 120.6% offset from Kochin reference - convergence does not imply correctness.",
            "claim_type": "methodological",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-wave-resistance",
                "system": "Wigley hull BEM",
                "conditions": ["Fr=0.30", "pressure path"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m2591:quadrature-convergence"],
            "created_at": NOW,
            "created_by": "agent/m8830",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m2591:geometry-verified",
            "statement": "Wigley hull geometry verified: B/L=0.10, T/L=0.0625, Cb=4/9=0.4444, matching analytic formula y=(B/2)(1-(2x/L)^2)(1-(z/T)^2).",
            "claim_type": "mathematical",
            "epistemic_status": "draft",
            "scope": {"domain": "ship-geometry", "system": "Wigley hull"},
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m2591:geometry-check"],
            "created_at": NOW,
            "created_by": "agent/m8830",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m2591:mesh-convergence-direction",
            "statement": "Mesh refinement 128->8192 panels shows relative diff to Kochin trending from 1.472 to 1.028, converging toward zero not reference value.",
            "claim_type": "predictive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-wave-resistance",
                "system": "Wigley hull BEM",
                "conditions": ["Fr=0.30", "pressure path"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m2591:mesh-study"],
            "created_at": NOW,
            "created_by": "agent/m8830",
            "version": "0.1.0"
        }
    ]

    evidence = [
        {
            "id": "tke:ship-m2591:pressure-audit",
            "claim_refs": ["tkc:ship-m2591:pressure-path-negative"],
            "source": {"source_type": "simulation", "citation": "TensorBEM agent/m2591 wave_resistance_pressure audit"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "TensorBEM@a9f77b1 benchmarks/wigley_pressure_audit"},
            "extraction_method": "simulation",
            "captured_at": NOW,
            "captured_by": "agent/m8830",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m2591:quadrature-convergence",
            "claim_refs": ["tkc:ship-m2591:convergence-not-correct"],
            "source": {"source_type": "simulation", "citation": "TensorBEM agent/m2591 quadrature study"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "results.json: quadrature 32-512 nodes"},
            "extraction_method": "calculation",
            "captured_at": NOW,
            "captured_by": "agent/m8830",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m2591:geometry-check",
            "claim_refs": ["tkc:ship-m2591:geometry-verified"],
            "source": {"source_type": "simulation", "citation": "TensorBEM agent/m2591 case dictionary"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "TensorBEM@a9f77b1 wigley case params"},
            "extraction_method": "direct-quotation",
            "captured_at": NOW,
            "captured_by": "agent/m8830",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m2591:mesh-study",
            "claim_refs": ["tkc:ship-m2591:mesh-convergence-direction"],
            "source": {"source_type": "simulation", "citation": "TensorBEM agent/m2591 mesh refinement study"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "results.json: mesh 128-8192 panels"},
            "extraction_method": "calculation",
            "captured_at": NOW,
            "captured_by": "agent/m8830",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        }
    ]

    provenance = [
        {
            "id": "tkp:ship-m2591:extraction",
            "generated_entity": {"id": "knowledge/sediment/m2591", "entity_type": "knowledge-object"},
            "activity": {
                "id": "activity-m2591-extraction",
                "activity_type": "extraction",
                "description": "Knowledge extraction from Wigley wave resistance pressure path honest-FAIL mission m2591",
                "started_at": NOW,
                "ended_at": NOW
            },
            "agents": [{"id": "agent-m8830", "agent_type": "software-agent", "name": "TensorKnowledge extractor", "role": "knowledge extractor"}],
            "derived_from": ["TensorBEM@a9f77b14d4d835ab5ecff3ba093dc504a1c04e6c"],
            "recorded_at": NOW,
            "version": "0.1.0"
        }
    ]

    _write_package(d, claims, evidence, provenance, "m2591", "Wigley wave resistance pressure path")


def create_m7485():
    """KP505 open water BEM (from scripts/sediment_spec_m7485.py)."""
    d = SEDIMENT_DIR / "m7485"
    d.mkdir(parents=True, exist_ok=True)

    claims = [
        {
            "id": "tkc:ship-m7485:openwater-bem-kt",
            "statement": "KP505 open water BEM computes K_T at J=0.0-1.2 with propeller BEM solver; convergence verified against points.csv benchmark data.",
            "claim_type": "predictive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-propulsion",
                "system": "KP505 propeller BEM",
                "conditions": ["J=0.0-1.2", "open water characteristics"]
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m7485:convergence-data"],
            "created_at": "2026-11-10T00:00:00+00:00",
            "created_by": "agent/m8823",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m7485:propeller-solver",
            "statement": "TensorBEM propeller.py implements lifting-line BEM for open water propeller characteristics with wake fraction and thrust deduction.",
            "claim_type": "descriptive",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-propulsion",
                "system": "TensorBEM propeller solver"
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m7485:solver-source"],
            "created_at": "2026-11-10T00:00:00+00:00",
            "created_by": "agent/m8823",
            "version": "0.1.0"
        },
        {
            "id": "tkc:ship-m7485:test-coverage",
            "statement": "test_propeller_open_water.py validates BEM open water predictions against benchmark points with tolerance checks.",
            "claim_type": "methodological",
            "epistemic_status": "draft",
            "scope": {
                "domain": "ship-propulsion",
                "system": "TensorBEM propeller tests"
            },
            "modality": "asserted",
            "evidence_refs": ["tke:ship-m7485:test-source"],
            "created_at": "2026-11-10T00:00:00+00:00",
            "created_by": "agent/m8823",
            "version": "0.1.0"
        }
    ]

    evidence = [
        {
            "id": "tke:ship-m7485:convergence-data",
            "claim_refs": ["tkc:ship-m7485:openwater-bem-kt"],
            "source": {"source_type": "simulation", "citation": "TensorBEM agent/m7485 benchmarks/kp505_openwater_bem"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "TensorBEM@80ad52a benchmarks/kp505_openwater_bem/convergence.csv"},
            "extraction_method": "calculation",
            "captured_at": "2026-11-10T00:00:00+00:00",
            "captured_by": "agent/m8823",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m7485:solver-source",
            "claim_refs": ["tkc:ship-m7485:propeller-solver"],
            "source": {"source_type": "internal-artifact", "citation": "TensorBEM src/tensorbem/propeller.py"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "TensorBEM@80ad52a src/tensorbem/propeller.py"},
            "extraction_method": "direct-quotation",
            "captured_at": "2026-11-10T00:00:00+00:00",
            "captured_by": "agent/m8823",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        },
        {
            "id": "tke:ship-m7485:test-source",
            "claim_refs": ["tkc:ship-m7485:test-coverage"],
            "source": {"source_type": "internal-artifact", "citation": "TensorBEM tests/test_propeller_open_water.py"},
            "relation": "supports",
            "locator": {"locator_type": "code-location", "value": "TensorBEM@80ad52a tests/test_propeller_open_water.py"},
            "extraction_method": "direct-quotation",
            "captured_at": "2026-11-10T00:00:00+00:00",
            "captured_by": "agent/m8823",
            "assessment_status": "unassessed",
            "version": "0.1.0"
        }
    ]

    provenance = [
        {
            "id": "tkp:ship-m7485:extraction",
            "generated_entity": {"id": "knowledge/sediment/m7485", "entity_type": "knowledge-object"},
            "activity": {
                "id": "activity-m7485-extraction",
                "activity_type": "extraction",
                "description": "Knowledge extraction from KP505 open water BEM mission m7485",
                "started_at": "2026-11-10T00:00:00+00:00",
                "ended_at": "2026-11-10T00:00:00+00:00"
            },
            "agents": [{"id": "agent-m8823", "agent_type": "software-agent", "name": "TensorKnowledge extractor", "role": "knowledge extractor"}],
            "derived_from": ["TensorBEM@80ad52a8236030e2343d5a88131bea3190088c09"],
            "recorded_at": "2026-11-10T00:00:00+00:00",
            "version": "0.1.0"
        }
    ]

    _write_package(d, claims, evidence, provenance, "m7485", "KP505 open water BEM")


def _write_package(d: Path, claims: list, evidence: list, provenance: list,
                   mission_id: str, description: str):
    """Write four-contract files to sediment directory."""
    for i, c in enumerate(claims, 1):
        (d / f"claim-{i:02d}.json").write_text(
            json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    for i, e in enumerate(evidence, 1):
        (d / f"evidence-{i:02d}.json").write_text(
            json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    for i, p in enumerate(provenance, 1):
        (d / f"provenance-{i:02d}.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # INDEX.md
    lines = [
        f"# Sediment Package: {mission_id}",
        f"",
        f"**Description**: {description}",
        f"**Generated**: {NOW}",
        f"**Status**: succeeded",
        f"",
        f"| Kind | Count |",
        f"|------|-------|",
        f"| claims | {len(claims)} |",
        f"| evidence | {len(evidence)} |",
        f"| provenance | {len(provenance)} |",
        f"",
        f"## Claims",
        f"",
    ]
    for c in claims:
        stmt = c.get("statement", "")[:80]
        lines.append(f"- `{c['id']}`: {stmt}")
    (d / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")

    # review-status.json
    (d / "review-status.json").write_text(
        json.dumps({
            "mission_id": mission_id,
            "review_status": "pending",
            "producer_self_review": False,
        }, indent=2), encoding="utf-8"
    )

    print(f"  {mission_id}: {len(claims)} claims, {len(evidence)} evidence, {len(provenance)} provenance")


def main():
    SEDIMENT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating sediment packages from extraction reports...")
    create_m8381()
    create_m2591()
    create_m7485()
    print(f"\nDone. Sediment dir: {SEDIMENT_DIR}")


if __name__ == "__main__":
    main()
