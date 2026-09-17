"""Verify per-call accounting and fail closed on missing/fabricated evidence."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import score_token_accounting as accounting  # noqa: E402


class TokenAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = accounting.read_json(ROOT / "token_accounting" / "calls.json")["records"]

    def modified(self) -> list[dict]:
        return copy.deepcopy(self.records)

    def test_original_per_call_usage_reconstructs_both_proxies(self) -> None:
        report = accounting.validate_accounting(ROOT)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual((report["total_call_records"], report["raw_usage_records"],
                          report["unknown_usage_records"]), (144, 130, 14))
        weak = report["arms"]["weak_curated_state"]
        strong = report["arms"]["strong_curated_state"]
        self.assertEqual((weak["runs"], weak["finalizer_tokens"], weak["recorded_token_proxy"]),
                         (30, 24391, 24391))
        self.assertEqual((strong["runs"], strong["state_update_calls"], strong["finalizer_tokens"],
                          strong["recorded_state_update_tokens"], strong["recorded_token_proxy"]),
                         (30, 84, 25565, 121290, 146855))
        self.assertEqual(strong["runs_with_failed_state_update"], 8)
        self.assertEqual(report["accounting_completeness"], "OBSERVED_USAGE_ONLY")

    def test_empty_input_is_not_zero_cost_success(self) -> None:
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, [])

    def test_missing_successful_call_fails(self) -> None:
        records = self.modified()
        records.pop(next(i for i, r in enumerate(records) if r["outcome"] == "success"))
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_missing_failed_call_fails_even_though_zero_proxy(self) -> None:
        records = self.modified()
        records.pop(next(i for i, r in enumerate(records) if r["outcome"] == "schema_failure"))
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_duplicate_call_fails(self) -> None:
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, self.modified() + [copy.deepcopy(self.records[0])])

    def test_failed_unknown_usage_cannot_be_changed_to_known_zero(self) -> None:
        records = self.modified()
        row = next(r for r in records if r["outcome"] == "schema_failure")
        row["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_fabricated_failed_usage_is_rejected(self) -> None:
        records = self.modified()
        row = next(r for r in records if r["outcome"] == "schema_failure")
        row.update(usage_status="reported", usage={"prompt_tokens": 10, "completion_tokens": 1,
                                                   "total_tokens": 11}, recorded_proxy_tokens=11)
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_raw_usage_total_must_match_components(self) -> None:
        records = self.modified()
        row = next(r for r in records if r["outcome"] == "success")
        row["usage"]["total_tokens"] += 1
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_consistent_tampered_usage_still_disagrees_with_summary(self) -> None:
        records = self.modified()
        row = next(r for r in records if r["stage"] == "finalizer")
        row["usage"]["total_tokens"] += 1
        row["usage"]["prompt_tokens"] += 1
        row["recorded_proxy_tokens"] += 1
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_boolean_is_not_a_token_count(self) -> None:
        records = self.modified()
        row = next(r for r in records if r["outcome"] == "success")
        row["usage"]["prompt_tokens"] = True
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_unexpected_free_text_field_is_rejected(self) -> None:
        records = self.modified()
        records[0]["prompt"] = "This field must never be exported."
        with self.assertRaises(accounting.AccountingError):
            accounting.validate_records(ROOT, records)

    def test_changed_data_checksum_cannot_pass(self) -> None:
        original = accounting.read_json

        def tamper(path: Path):
            obj = original(path)
            if path.name == "origin_manifest.json":
                obj["records_canonical_sha256"] = "0" * 64
            return obj

        with patch.object(accounting, "read_json", side_effect=tamper):
            with self.assertRaises(accounting.AccountingError):
                accounting.validate_accounting(ROOT)

    def test_duplicate_origins_cannot_replace_required_source_run(self) -> None:
        original = accounting.read_json

        def tamper(path: Path):
            obj = original(path)
            if path.name == "origin_manifest.json":
                obj["source_runs"][1] = copy.deepcopy(obj["source_runs"][0])
            return obj

        with patch.object(accounting, "read_json", side_effect=tamper):
            with self.assertRaises(accounting.AccountingError):
                accounting.validate_accounting(ROOT)

    def test_projection_contains_no_source_paths_prompts_or_urls(self) -> None:
        for name in ("calls.json", "origin_manifest.json"):
            text = (ROOT / "token_accounting" / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"[A-Za-z]:[\\/]|/mnt/|/home/|https?://", text))
            self.assertNotIn('"prompt":', text)
            self.assertNotIn('"content":', text)
        for row in self.records:
            self.assertEqual(set(row), accounting.RECORD_KEYS)

    def test_content_hash_is_stable_across_line_endings_and_key_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "lf.json"
            right = Path(directory) / "crlf.json"
            left.write_bytes(b'{\n  "a": 1,\n  "b": [2, 3]\n}\n')
            right.write_bytes(b'{\r\n "b": [2,3], "a": 1\r\n}\r\n')
            self.assertNotEqual(accounting.sha256(left), accounting.sha256(right))
            self.assertEqual(accounting.canonical_json_sha256(left),
                             accounting.canonical_json_sha256(right))

    def test_standalone_isolated_cli_works(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, "-I", "-s", "-X", "utf8", str(ROOT / "score_token_accounting.py"),
                 "--artifact", str(ROOT), "--out-dir", out],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(out) / "token_accounting_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["unknown_usage_records"], 14)


if __name__ == "__main__":
    unittest.main()
