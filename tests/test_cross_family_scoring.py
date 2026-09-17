"""Cross-family score reconstruction, exclusion and provenance negative controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import score_cross_family as scoring  # noqa: E402


class CrossFamilyScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = scoring.read_json(ROOT / "cross_family/source_audit_evidence.json")
        cls.result = scoring.score_bundle(cls.bundle)

    def test_primary_negative_results_recompute_without_stored_labels(self) -> None:
        result = self.result
        self.assertEqual(result["status"], "PASS")
        self.assertEqual((result["selected_attempts"], result["retained_attempts"]), (96, 98))
        aggregates = result["aggregates"]
        for arm, expected in zip(scoring.ARMS, ((10, 24), (12, 24), (6, 21), (12, 24))):
            value = aggregates[arm]["final_response_eligible"]
            self.assertEqual((value["accepted"], value["denominator"]), expected)
        schema = result["comparisons"]["final_response_eligible"]["schema_vs_matched"]
        extended = result["comparisons"]["final_response_eligible"]["extended_vs_matched"]
        self.assertEqual((schema["a_better"], schema["b_better"], schema["ties"]), (2, 4, 18))
        self.assertEqual((extended["a_better"], extended["b_better"], extended["ties"]), (4, 4, 16))

    def test_archived_true_cannot_override_missing_anchor(self) -> None:
        row = copy.deepcopy(next(r for r in self.bundle["attempts"] if r["archived_accepted"]))
        row["response"] = {key: [] for key in self.bundle["oracle"]["required_final_keys"]}
        row["response"]["finding_present"] = True
        self.assertFalse(scoring.score_attempt(row, self.bundle["oracle"])["accepted"])

    def test_stored_false_does_not_override_successful_response(self) -> None:
        row = copy.deepcopy(next(r for r in self.bundle["attempts"] if r["archived_accepted"]))
        row["archived_accepted"] = False
        self.assertTrue(scoring.score_attempt(row, self.bundle["oracle"])["accepted"])

    def test_finding_present_string_is_not_true(self) -> None:
        row = copy.deepcopy(next(r for r in self.bundle["attempts"] if r["archived_accepted"]))
        row["response"]["finding_present"] = "true"
        self.assertFalse(scoring.score_attempt(row, self.bundle["oracle"])["accepted"])

    def test_protocol_failures_have_no_semantic_acceptance(self) -> None:
        failures = [r for r in self.bundle["attempts"] if r["failure_type"] != "ok"]
        self.assertEqual(len(failures), 5)
        for row in failures:
            result = scoring.score_attempt(row, self.bundle["oracle"])
            self.assertIsNone(result["accepted"])
            self.assertFalse(result["final_response_eligible"])

    def test_upstream_failure_sensitivity_removes_two_tied_pairs(self) -> None:
        self.assertEqual(len(self.result["upstream_handoff_failure_selected_attempts"]), 2)
        result = self.result["comparisons"]["end_to_end_eligible"]["extended_vs_matched"]
        self.assertEqual((result["comparable"], result["a_better"], result["b_better"], result["ties"]),
                         (22, 4, 4, 14))
        self.assertEqual(result["p_one_sided_a_gt_b"], .63671875)
        self.assertEqual((result["a_accepted"], result["b_accepted"]), (10, 10))

    def test_missing_response_or_schema_cannot_be_success(self) -> None:
        row = copy.deepcopy(next(r for r in self.bundle["attempts"] if r["archived_accepted"]))
        row["response"].pop("evidence_chain")
        with self.assertRaises(scoring.EvidenceError):
            scoring.score_attempt(row, self.bundle["oracle"])
        row["response"] = None
        with self.assertRaises(scoring.EvidenceError):
            scoring.score_attempt(row, self.bundle["oracle"])

    def test_missing_or_unknown_status_is_not_silently_eligible(self) -> None:
        for field, value in (("parse_status", "unknown"), ("failure_type", None),
                             ("weak_parse_status", "failed")):
            row = copy.deepcopy(next(r for r in self.bundle["attempts"] if r["archived_accepted"]))
            row[field] = value
            with self.assertRaises(scoring.EvidenceError):
                scoring.score_attempt(row, self.bundle["oracle"])

    def test_missing_or_duplicate_analysis_unit_is_rejected(self) -> None:
        for mode in ("remove", "duplicate"):
            bundle = copy.deepcopy(self.bundle)
            if mode == "remove":
                bundle["attempts"].pop(0)
            else:
                duplicate = copy.deepcopy(bundle["attempts"][0])
                duplicate["attempt_id"] += "-duplicate"
                bundle["attempts"].append(duplicate)
            with self.assertRaises(scoring.EvidenceError):
                scoring.score_bundle(bundle)

    def test_retry_requires_retained_original_and_identical_prompt(self) -> None:
        for mode in ("missing_original", "different_prompt", "successful_original"):
            bundle = copy.deepcopy(self.bundle)
            retry = next(r for r in bundle["attempts"] if r["retry_of"])
            original = next(r for r in bundle["attempts"] if r["attempt_id"] == retry["retry_of"])
            if mode == "missing_original":
                bundle["attempts"].remove(original)
            elif mode == "different_prompt":
                retry["prompt_sha256"] = "0" * 64
            else:
                original.update(parse_status="ok", failure_type="ok")
            with self.assertRaises(scoring.EvidenceError):
                scoring.score_bundle(bundle)

    def test_missing_oracle_or_unknown_rule_fails_closed(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["oracle"]["tasks"].pop("WP-H-001")
        with self.assertRaises(scoring.EvidenceError):
            scoring.score_bundle(bundle)
        with self.assertRaises(scoring.EvidenceError):
            scoring.evaluate_condition({"arbitrary_execution": "anything"}, "text", ["missing"])

    def test_incomplete_pair_is_not_dropped_silently(self) -> None:
        rows = self.result["scored_selected_rows"][1:]
        with self.assertRaises(scoring.EvidenceError):
            scoring.paired(rows, scoring.ARMS[0], scoring.ARMS[1])

    def test_release_manifest_and_redaction_boundary(self) -> None:
        path = ROOT / "cross_family/source_audit_evidence.json"
        manifest = scoring.read_json(ROOT / "cross_family/source_provenance.json")
        self.assertEqual(scoring.canonical_json_sha256(scoring.read_json(path)),
                         manifest["released_evidence_canonical_sha256"])
        self.assertFalse(manifest["historical_raw_vs_released_check_mismatches"])
        text = path.read_text(encoding="utf-8")
        for pattern in (r"https?://", r"/root/", r"/mnt/", r"[A-Z]:\\\\",
                        r"\bCVE-\d{4}-\d+", r"\.\./", r"\bcurl\s", r"\bwget\s",
                        r"Bearer\s+[A-Za-z0-9]", r"sk-[A-Za-z0-9]{16,}"):
            self.assertIsNone(re.search(pattern, text, flags=re.I), pattern)
        self.assertEqual(manifest["redaction_counts"]["traversal_example"], 6)

    def test_public_json_hash_ignores_transport_newlines_and_spacing(self) -> None:
        text = json.dumps(self.bundle, ensure_ascii=False, indent=2)
        decoded = json.loads(text.replace("\n", "\r\n"))
        self.assertEqual(scoring.canonical_json_sha256(self.bundle),
                         scoring.canonical_json_sha256(decoded))

    def test_release_entrypoint_checks_integrity_before_scoring(self) -> None:
        report = scoring.validate_release(ROOT)
        self.assertEqual(report["public_data_integrity"], {"status": "PASS", "parsed_response_count": 95})
        manifest = scoring.read_json(ROOT / "cross_family/source_provenance.json")
        altered = copy.deepcopy(self.bundle)
        altered["attempts"][0]["response"]["finding_present"] = False
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "cross_family"
            directory.mkdir()
            (directory / "source_audit_evidence.json").write_text(json.dumps(altered), encoding="utf-8")
            (directory / "source_provenance.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(scoring.EvidenceError, "canonical provenance"):
                scoring.validate_release(root)

    def test_release_entrypoint_refuses_missing_response_provenance(self) -> None:
        manifest = scoring.read_json(ROOT / "cross_family/source_provenance.json")
        manifest["response_sources"].pop()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "cross_family"
            directory.mkdir()
            (directory / "source_audit_evidence.json").write_text(json.dumps(self.bundle), encoding="utf-8")
            (directory / "source_provenance.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(scoring.EvidenceError, "provenance does not cover"):
                scoring.validate_release(root)


if __name__ == "__main__":
    unittest.main()
