"""New evidence is mandatory in the combined offline reviewer workflow."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import validate_structured_state_artifact as validator  # noqa: E402


class RevisionEvidenceIntegrationTests(unittest.TestCase):
    def test_validator_includes_independent_cross_family_and_token_results(self):
        report = validator.validate_artifact(ROOT)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["token_accounting"]["total_call_records"], 144)
        self.assertEqual(report["cross_family"]["selected_attempts"], 96)
        self.assertEqual(report["cross_family"]["comparisons"]["end_to_end_eligible"]
                         ["extended_vs_matched"]["comparable"], 22)

    def test_combined_pass_cannot_hide_token_failure(self):
        with patch.object(validator, "validate_accounting", return_value={"status": "FAIL"}):
            report = validator.validate_artifact(ROOT)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["per_call_token_accounting"])

    def test_combined_pass_cannot_hide_cross_family_failure(self):
        with patch.object(validator, "validate_cross_family", return_value={"status": "FAIL"}):
            report = validator.validate_artifact(ROOT)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["cross_family_independent_scoring"])

    def test_missing_new_dataset_does_not_fall_back_to_legacy_pass(self):
        with patch.object(validator, "validate_cross_family", side_effect=FileNotFoundError("missing data")):
            with self.assertRaises(FileNotFoundError):
                validator.validate_artifact(ROOT)


if __name__ == "__main__":
    unittest.main()
