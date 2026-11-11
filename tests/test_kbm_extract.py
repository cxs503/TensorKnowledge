"""Tests for KBM extraction pipeline and card schemas."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke.kbm_extract import (
    CARD_TYPES,
    locate_quote,
    verify_quotes,
    verify_numbers,
    validate_card,
    make_card_id,
    build_claim_record,
    run_pipeline,
    REQUIRED_BY_CARD,
)
from ke.kbm_validate import validate_card as schema_validate, validate_package, CARD_SCHEMAS


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_report():
    """A synthetic report with extractable content."""
    return """# Synthetic Ship Resistance Report

## 1. Hull Geometry
The test case uses a Wigley hull with the following parameters:
- Length L = 2.0 m
- Beam B = 0.3 m
- Draft T = 0.125 m
- Block coefficient Cb = 0.467

## 2. Method
The resistance is computed using the Holtrop-Mennen method (Holtrop & Mennen, 1982).
The total resistance coefficient is Ct = 3.25e-3 at Fr = 0.25.

## 3. Results
At Froude number Fr = 0.25, the computed resistance coefficient is Ct = 3.28e-3.
The reference value from the original paper is Ct_ref = 3.25e-3.
The relative error is 0.92%.

## 4. Known Issues
When the Froude number exceeds 0.45, the Holtrop-Mennen method tends to
overpredict resistance by 5-10%. This is a known limitation of the empirical
formulation for high-speed displacement hulls.

## 5. Code Reference
The implementation is in TensorFVM, module resistance/holtrop_mennen.py,
function compute_ct().
"""


@pytest.fixture
def sample_llm_output():
    """Synthetic LLM output with five card types.
    Quotes must match the sample_report exactly.
    """
    return {
        "cards": [
            {
                "card_type": "method",
                "fields": {
                    "problem": {"description": "Ship resistance prediction for displacement hulls"},
                    "method": {"name": "Holtrop-Mennen", "description": "Empirical resistance prediction method", "family": "other"},
                    "equations": [{"formula": "Ct = f(L, B, T, Cb, Fr)", "source": "Holtrop & Mennen (1982)", "source_type": "paper"}],
                    "applicable_domain": {"domain": "ship-resistance", "limitations": ["valid for Fr < 0.45"]}
                },
                "source_quotes": [
                    {"quote": "The resistance is computed using the Holtrop-Mennen method", "path": "report.md"}
                ],
                "numbers": [
                    {"value": 0.00325, "needle": "Ct = 3.25e-3"}
                ]
            },
            {
                "card_type": "parameter",
                "fields": {
                    "parameter": {
                        "symbol": "Cb",
                        "name": "Block coefficient",
                        "definition": "Ratio of displaced volume to L*B*T",
                        "formula": "Cb = V / (L * B * T)",
                        "typical_value": 0.467
                    }
                },
                "source_quotes": [
                    {"quote": "Block coefficient Cb = 0.467", "path": "report.md"}
                ],
                "numbers": [
                    {"value": 0.467, "needle": "Cb = 0.467"}
                ]
            },
            {
                "card_type": "failure",
                "fields": {
                    "failure_mode": {
                        "description": "Overprediction at high Froude numbers",
                        "symptom": "Resistance 5-10% above measured values",
                        "severity": "major",
                        "trigger_conditions": ["Fr > 0.45"]
                    },
                    "root_cause": {
                        "description": "Empirical formulation not calibrated for high-speed regime",
                        "category": "model"
                    },
                    "workaround": {
                        "description": "Use CFD for Fr > 0.45",
                        "effectiveness": "full"
                    }
                },
                "source_quotes": [
                    {"quote": "overpredict resistance by 5-10%", "path": "report.md"}
                ],
                "numbers": []
            },
            {
                "card_type": "benchmark",
                "fields": {
                    "benchmark_case": {"case_id": "wigley-Fr025", "description": "Wigley hull at Fr=0.25"},
                    "reference": {"value": 0.00325, "source": "Holtrop & Mennen (1982)", "tolerance_pct": 3.0}
                },
                "source_quotes": [
                    {"quote": "The reference value from the original paper is Ct_ref = 3.25e-3", "path": "report.md"}
                ],
                "numbers": [
                    {"value": 0.00325, "needle": "Ct_ref = 3.25e-3"}
                ]
            },
            {
                "card_type": "code-pointer",
                "fields": {
                    "code_location": {"repo": "TensorFVM", "path": "resistance/holtrop_mennen.py", "symbol": "compute_ct", "symbol_type": "function"},
                    "implements": {"description": "Holtrop-Mennen resistance coefficient computation"}
                },
                "source_quotes": [
                    {"quote": "module resistance/holtrop_mennen.py", "path": "report.md"}
                ],
                "numbers": []
            }
        ]
    }


# --------------------------------------------------------------------------- #
# Quote verification tests
# --------------------------------------------------------------------------- #
class TestQuoteVerification:
    def test_locate_quote_found(self, sample_report):
        start, end = locate_quote(sample_report, "Block coefficient Cb = 0.467")
        assert start >= 0
        assert sample_report[start:end] == "Block coefficient Cb = 0.467"

    def test_locate_quote_not_found(self, sample_report):
        assert locate_quote(sample_report, "this quote does not exist anywhere") is None

    def test_locate_quote_not_unique(self):
        text = "foo bar foo"
        assert locate_quote(text, "foo") is None  # occurs twice

    def test_locate_quote_too_short(self):
        assert locate_quote("hello world", "ab") is None  # < 4 chars

    def test_verify_quotes_all_pass(self, sample_report):
        quotes = [
            {"quote": "Block coefficient Cb = 0.467", "path": "report.md"},
            {"quote": "The resistance is computed using the Holtrop-Mennen method", "path": "report.md"},
        ]
        results = verify_quotes(sample_report, quotes)
        assert all(r["ok"] for r in results)

    def test_verify_quotes_partial_fail(self, sample_report):
        quotes = [
            {"quote": "Block coefficient Cb = 0.467", "path": "report.md"},
            {"quote": "nonexistent quote", "path": "report.md"},
        ]
        results = verify_quotes(sample_report, quotes)
        assert results[0]["ok"]
        assert not results[1]["ok"]


# --------------------------------------------------------------------------- #
# Number verification tests
# --------------------------------------------------------------------------- #
class TestNumberVerification:
    def test_number_found(self, sample_report):
        results = verify_numbers(sample_report, [{"value": 0.467, "needle": "Cb = 0.467"}])
        assert results[0]["ok"]

    def test_number_not_found(self, sample_report):
        results = verify_numbers(sample_report, [{"value": 999, "needle": "nonexistent needle"}])
        assert not results[0]["ok"]

    def test_number_mismatch(self, sample_report):
        results = verify_numbers(sample_report, [{"value": 0.999, "needle": "Cb = 0.467"}])
        assert not results[0]["ok"]

    def test_number_tolerance(self, sample_report):
        # 0.00325 vs 0.00328 should pass with 1% tolerance
        results = verify_numbers(sample_report, [{"value": 0.00328, "needle": "Ct = 3.25e-3"}], tolerance=0.01)
        assert results[0]["ok"]


# --------------------------------------------------------------------------- #
# Card validation tests
# --------------------------------------------------------------------------- #
class TestCardValidation:
    def test_method_card_required(self):
        card = {
            "card_type": "method",
            "fields": {
                "problem": {"description": "test"},
                "method": {"name": "test", "description": "test"},
                "equations": [{"formula": "E=mc2", "source": "Einstein"}],
                "applicable_domain": {"domain": "physics"}
            }
        }
        assert validate_card(card, "method") == []

    def test_method_card_missing_field(self):
        card = {
            "card_type": "method",
            "fields": {"problem": {"description": "test"}}
        }
        errors = validate_card(card, "method")
        assert any("method" in e for e in errors)

    def test_parameter_card_required(self):
        card = {
            "card_type": "parameter",
            "fields": {
                "parameter": {"symbol": "Re", "name": "Reynolds number", "definition": "UL/nu"}
            }
        }
        assert validate_card(card, "parameter") == []

    def test_failure_card_required(self):
        card = {
            "card_type": "failure",
            "fields": {
                "failure_mode": {"description": "crash", "symptom": "segfault"},
                "root_cause": {"description": "null pointer"}
            }
        }
        assert validate_card(card, "failure") == []

    def test_benchmark_card_required(self):
        card = {
            "card_type": "benchmark",
            "fields": {
                "benchmark_case": {"case_id": "test-01", "description": "test"},
                "reference": {"value": 1.0, "source": "ref"}
            }
        }
        assert validate_card(card, "benchmark") == []

    def test_code_pointer_card_required(self):
        card = {
            "card_type": "code-pointer",
            "fields": {
                "code_location": {"repo": "TensorFVM", "path": "src/main.py"},
                "implements": {"description": "main entry point"}
            }
        }
        assert validate_card(card, "code-pointer") == []


# --------------------------------------------------------------------------- #
# ID generation tests
# --------------------------------------------------------------------------- #
class TestIdGeneration:
    def test_valid_id(self):
        cid = make_card_id("test", "method", "holtrop-mennen")
        assert cid.startswith("tkc:test:method-")

    def test_slug_sanitization(self):
        cid = make_card_id("test", "method", "Holtrop-Mennen (1982)!")
        assert cid == "tkc:test:method-holtrop-mennen-1982"

    def test_empty_slug(self):
        cid = make_card_id("test", "method", "")
        assert cid == "tkc:test:method-unnamed"


# --------------------------------------------------------------------------- #
# Schema validation tests
# --------------------------------------------------------------------------- #
class TestSchemaValidation:
    def _skip_if_no_jsonschema(self):
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

    def test_method_card_schema(self):
        self._skip_if_no_jsonschema()
        card = {
            "id": "tkc:test:method-01",
            "card_type": "method",
            "problem": {"description": "test"},
            "method": {"name": "test", "description": "test"},
            "equations": [{"formula": "E=mc2", "source": "test"}],
            "applicable_domain": {"domain": "test"},
            "created_at": "2026-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        errors = schema_validate(card, "method")
        assert errors == [], f"schema errors: {errors}"

    def test_parameter_card_schema(self):
        self._skip_if_no_jsonschema()
        card = {
            "id": "tkc:test:parameter-01",
            "card_type": "parameter",
            "parameter": {"symbol": "Re", "name": "Reynolds", "definition": "UL/nu"},
            "created_at": "2026-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        errors = schema_validate(card, "parameter")
        assert errors == [], f"schema errors: {errors}"

    def test_failure_card_schema(self):
        self._skip_if_no_jsonschema()
        card = {
            "id": "tkc:test:failure-01",
            "card_type": "failure",
            "failure_mode": {"description": "crash", "symptom": "segfault"},
            "root_cause": {"description": "null ptr"},
            "created_at": "2026-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        errors = schema_validate(card, "failure")
        assert errors == [], f"schema errors: {errors}"

    def test_benchmark_card_schema(self):
        self._skip_if_no_jsonschema()
        card = {
            "id": "tkc:test:benchmark-01",
            "card_type": "benchmark",
            "benchmark_case": {"case_id": "c1", "description": "test"},
            "reference": {"value": 1.0, "source": "ref"},
            "created_at": "2026-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        errors = schema_validate(card, "benchmark")
        assert errors == [], f"schema errors: {errors}"

    def test_code_pointer_card_schema(self):
        self._skip_if_no_jsonschema()
        card = {
            "id": "tkc:test:code-pointer-01",
            "card_type": "code-pointer",
            "code_location": {"repo": "TensorFVM", "path": "src/main.py"},
            "implements": {"description": "main"},
            "created_at": "2026-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        errors = schema_validate(card, "code-pointer")
        assert errors == [], f"schema errors: {errors}"


# --------------------------------------------------------------------------- #
# Full pipeline test
# --------------------------------------------------------------------------- #
class TestFullPipeline:
    def test_run_pipeline(self, sample_report, sample_llm_output):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            report_path = tmp / "report.md"
            report_path.write_text(sample_report)
            llm_path = tmp / "llm.json"
            llm_path.write_text(json.dumps(sample_llm_output))
            out_dir = tmp / "out"
            run_dir = tmp / "runs"

            manifest = run_pipeline(
                source_report=report_path,
                llm_output=llm_path,
                out_dir=out_dir,
                run_dir=run_dir,
                namespace="test",
                created_by="test-agent",
            )

            m = manifest["metrics"]
            assert m["cards_extracted"] == 5
            assert m["cards_verified"] == 5
            assert m["cards_discarded"] == 0
            assert m["verification_rate"] == 1.0
            assert m["evidence_records"] > 0

            # Check output files exist
            assert (out_dir / "INDEX.md").is_file()
            assert (out_dir / "claims").is_dir()
            assert (out_dir / "evidence").is_dir()
            assert (out_dir / "provenance").is_dir()
            assert (run_dir / "run_manifest.json").is_file()

            # Check claims are valid JSON
            claim_files = list((out_dir / "claims").glob("*.json"))
            assert len(claim_files) == 5
            for cf in claim_files:
                card = json.loads(cf.read_text())
                assert "id" in card
                assert card["id"].startswith("tkc:test:")

    def test_run_pipeline_with_bad_card(self, sample_report):
        """Test that a card with bad quotes gets discarded."""
        llm_data = {
            "cards": [
                {
                    "card_type": "method",
                    "fields": {
                        "problem": {"description": "test"},
                        "method": {"name": "test", "description": "test"},
                        "equations": [{"formula": "E=mc2", "source": "test"}],
                        "applicable_domain": {"domain": "test"}
                    },
                    "source_quotes": [
                        {"quote": "this quote does not exist in the report at all", "path": "report.md"}
                    ],
                    "numbers": []
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            report_path = tmp / "report.md"
            report_path.write_text(sample_report)
            llm_path = tmp / "llm.json"
            llm_path.write_text(json.dumps(llm_data))
            out_dir = tmp / "out"
            run_dir = tmp / "runs"

            manifest = run_pipeline(
                source_report=report_path,
                llm_output=llm_path,
                out_dir=out_dir,
                run_dir=run_dir,
                namespace="test",
                created_by="test-agent",
            )

            m = manifest["metrics"]
            assert m["cards_extracted"] == 1
            assert m["cards_verified"] == 0
            assert m["cards_discarded"] == 1

    def test_package_validation(self, sample_report, sample_llm_output):
        """Test validate_package on a generated package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            report_path = tmp / "report.md"
            report_path.write_text(sample_report)
            llm_path = tmp / "llm.json"
            llm_path.write_text(json.dumps(sample_llm_output))
            out_dir = tmp / "out"
            run_dir = tmp / "runs"

            run_pipeline(
                source_report=report_path,
                llm_output=llm_path,
                out_dir=out_dir,
                run_dir=run_dir,
                namespace="test",
                created_by="test-agent",
            )

            result = validate_package(out_dir)
            assert result["total"] == 5
            assert result["valid"] == 5
            assert result["invalid"] == 0


# --------------------------------------------------------------------------- #
# Card type constants
# --------------------------------------------------------------------------- #
class TestConstants:
    def test_card_types(self):
        assert CARD_TYPES == {"method", "parameter", "failure", "benchmark", "code-pointer"}

    def test_required_by_card(self):
        assert "method" in REQUIRED_BY_CARD
        assert "parameter" in REQUIRED_BY_CARD
        assert "failure" in REQUIRED_BY_CARD
        assert "benchmark" in REQUIRED_BY_CARD
        assert "code-pointer" in REQUIRED_BY_CARD

    def test_card_schemas_exist(self):
        for card_type, schema_file in CARD_SCHEMAS.items():
            schema_path = ROOT / "schemas" / schema_file
            assert schema_path.is_file(), f"schema missing: {schema_path}"
