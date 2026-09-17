"""The no-install review must neither hard-code 18 tests nor accept partial runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "reviewer_offline_check.py"
if not CHECKER.is_file():
    CHECKER = ROOT / "reviewer" / "reviewer_offline_check.py"
SPEC = importlib.util.spec_from_file_location("reviewer_check_under_test", CHECKER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReviewerReportingTests(unittest.TestCase):
    def test_scientific_status_is_not_hidden_by_execution_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.object(MODULE, "OUTPUT", output):
                MODULE._write_summaries({"status": "PASS", "generated_at": "test",
                    "scientific_review_status": "REVIEW_REQUIRED", "checks": []})
            for filename in ("REVIEWER_CHECK_SUMMARY.md", "REVIEWER_CHECK_SUMMARY.html"):
                self.assertIn("REVIEW_REQUIRED", (output / filename).read_text(encoding="utf-8"))
            payload = json.loads((output / "REVIEWER_CHECK_SUMMARY.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["scientific_review_status"], "REVIEW_REQUIRED")

    def test_updated_suite_count_is_not_hardcoded(self):
        self.assertEqual(MODULE._verified_test_count("Ran 37 tests in 0.5s\n\nOK\n", 37), 37)

    def test_partial_suite_is_rejected(self):
        with self.assertRaises(MODULE.CheckFailure):
            MODULE._verified_test_count("Ran 18 tests in 0.5s\n\nOK\n", 37)

    def test_zero_tests_and_invalid_metadata_are_rejected(self):
        for expected in (0, None, True, "37", -1):
            with self.subTest(expected=expected), self.assertRaises(MODULE.CheckFailure):
                MODULE._verified_test_count("Ran 0 tests in 0.0s\n\nOK\n", expected)

    def test_skip_failure_and_missing_summary_are_rejected(self):
        for output in (
            "Ran 37 tests in 0.5s\n\nOK (skipped=1)\n",
            "Ran 37 tests in 0.5s\n\nFAILED (failures=1)\n",
            "unrelated output\nOK\n",
            "Ran 37 tests in 0.5s\nOK\nRan 37 tests in 0.5s\nOK\n",
        ):
            with self.subTest(output=output), self.assertRaises(MODULE.CheckFailure):
                MODULE._verified_test_count(output, 37)
