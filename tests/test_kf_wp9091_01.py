"""Acceptance invariants for work package wp-9091-01 (mission m18172 deliverables).

Offline checks: JSON validity, schema compliance, cross-file consistency,
file existence. No platform API dependency.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WP_DIR = REPO / "docs" / "wp-9091-01"
MANIFEST = WP_DIR / "asset_manifest.json"
KF_RESULT = WP_DIR / "kf_result.wp-9091-01.json"
VERIFICATION = WP_DIR / "verification.json"
PACKAGE_ID = "wp-9091-01"
REPORT_ID = "9091"
EXPECTED_FILES = [
    "KF-RESULT-wp9091-01.md",
    "README.md",
    "asset_manifest.json",
    "kf_result.wp-9091-01.json",
    "report_9091.md",
    "verification.json",
    "checks_baseline.md",
]


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf_result():
    return json.loads(KF_RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verification():
    return json.loads(VERIFICATION.read_text(encoding="utf-8"))


class TestFilesExist:
    """All expected files must be present in the work package directory."""

    def test_wp_directory_exists(self):
        assert WP_DIR.is_dir(), f"Work package directory missing: {WP_DIR}"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_exists(self, filename):
        path = WP_DIR / filename
        assert path.is_file(), f"Expected file missing: {path}"


class TestJsonValidity:
    """All JSON files must be valid and parseable."""

    def test_manifest_valid_json(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_kf_result_valid_json(self):
        data = json.loads(KF_RESULT.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_verification_valid_json(self):
        data = json.loads(VERIFICATION.read_text(encoding="utf-8"))
        assert isinstance(data, dict)


class TestPackageIdConsistency:
    """package_id must be consistent across all artefacts."""

    def test_manifest_package_id(self, manifest):
        assert manifest["package_id"] == PACKAGE_ID

    def test_kf_result_package_id(self, kf_result):
        assert kf_result["package_id"] == PACKAGE_ID

    def test_verification_package_id(self, verification):
        assert verification["package_id"] == PACKAGE_ID


class TestReportIdConsistency:
    """report_id must be consistent across all artefacts."""

    def test_manifest_report_id(self, manifest):
        assert manifest["report_id"] == REPORT_ID

    def test_kf_result_report_id(self, kf_result):
        assert kf_result["report_id"] == REPORT_ID

    def test_verification_report_id(self, verification):
        assert verification["report_id"] == REPORT_ID


class TestTaskType:
    """task_type must be a valid enum value."""

    ALLOWED = {
        "01-asset-registration",
        "02-classification-parse",
        "03-knowledge-extraction",
        "04-independent-review",
        "05-synthesis-research",
    }

    def test_manifest_task_type(self, manifest):
        assert manifest["task_type"] in self.ALLOWED

    def test_kf_result_task_type(self, kf_result):
        assert kf_result["task_type"] in self.ALLOWED

    def test_task_type_is_asset_registration(self, manifest, kf_result):
        assert manifest["task_type"] == "01-asset-registration"
        assert kf_result["task_type"] == "01-asset-registration"


class TestManifestStructure:
    """Asset manifest must have required fields and well-formed assets."""

    def test_required_fields(self, manifest):
        for key in (
            "schema",
            "package_id",
            "task_type",
            "report_id",
            "source_uri",
            "source_field",
            "source_hash",
            "assets",
            "claims",
        ):
            assert key in manifest, f"Missing required field: {key}"

    def test_source_uri(self, manifest):
        assert manifest["source_uri"] == f"tensor://reports/{REPORT_ID}"

    def test_source_field(self, manifest):
        assert manifest["source_field"] == "markdown"

    def test_source_hash_format(self, manifest):
        assert manifest["source_hash"].startswith("sha256:")

    def test_asset_ids_unique(self, manifest):
        ids = [a["asset_id"] for a in manifest["assets"]]
        assert len(ids) == len(set(ids)), "Duplicate asset_ids found"

    def test_assets_have_required_fields(self, manifest):
        for asset in manifest["assets"]:
            for key in ("asset_id", "asset_class", "name", "resolution"):
                assert key in asset, f"Asset {asset.get('asset_id')} missing {key}"

    def test_no_verified_claims(self, manifest):
        for claim in manifest["claims"]:
            assert claim.get("status") != "verified"


class TestKfResultStructure:
    """KF result envelope must have required fields."""

    def test_required_fields(self, kf_result):
        for key in ("package_id", "task_type", "report_id", "provenance", "outputs"):
            assert key in kf_result, f"Missing required field: {key}"

    def test_provenance_fields(self, kf_result):
        prov = kf_result["provenance"]
        for key in ("source_uri", "source_field", "source_hash"):
            assert key in prov, f"Missing provenance field: {key}"

    def test_provenance_source_uri(self, kf_result):
        assert kf_result["provenance"]["source_uri"] == f"tensor://reports/{REPORT_ID}"


class TestVerificationChecks:
    """Verification.json must report all checks passed."""

    def test_all_checks_passed(self, verification):
        summary = verification["summary"]
        assert summary["failed"] == 0
        assert summary["passed"] == summary["total_checks"]

    def test_individual_checks(self, verification):
        """Check that all top-level checks pass. Handles nested structures."""
        for name, check in verification["checks"].items():
            if "pass" in check:
                assert check["pass"] is True, f"Check {name} failed"
            else:
                # Nested checks (e.g., schema_pass has sub-checks)
                for sub_name, sub_check in check.items():
                    if isinstance(sub_check, dict) and "pass" in sub_check:
                        assert sub_check["pass"] is True, f"Sub-check {name}.{sub_name} failed"


class TestScopeIsSingleReport:
    """This work package must not register or reference any other report id."""

    def test_manifest_source_uri(self, manifest):
        assert manifest["source_uri"] == f"tensor://reports/{REPORT_ID}"

    def test_no_other_report_references(self, manifest):
        """Ensure no asset references a different report."""
        for asset in manifest["assets"]:
            if "locator" in asset:
                loc = asset["locator"]
                if "field" in loc:
                    assert loc.get("report_id", REPORT_ID) == REPORT_ID
