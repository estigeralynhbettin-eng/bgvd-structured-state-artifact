"""Independent scorer checks and negative controls for absent/tampered evidence."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import score_released_rows as scoring  # noqa: E402
import validate_structured_state_artifact as validator  # noqa: E402


class ReleasedScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = {
            "expected_decision": "finalize", "expected_candidate": "C1",
            "current_material_refs": ["M1"], "current_verifier_refs": ["V1"],
            "stale_refs": ["OLD"],
        }
        self.response = {
            "decision": "finalize", "selected_candidate": "C1",
            "material_refs": ["M1"], "verifier_refs": ["V1"],
            "parse_ok": True, "provider_failure_type": "ok", "correct": False,
        }

    def test_stored_verdict_and_auxiliary_flags_do_not_control_score(self) -> None:
        self.response.update(material_cited=False, verifier_cited=False)
        self.assertTrue(scoring.score_response(self.fixture, self.response)["correct"])
        self.response.pop("correct")
        self.assertTrue(scoring.score_response(self.fixture, self.response)["correct"])

    def test_missing_current_material_cannot_be_repaired_by_stored_true(self) -> None:
        self.response.update(correct=True, material_cited=True, material_refs=["OTHER"])
        self.assertFalse(scoring.score_response(self.fixture, self.response)["correct"])

    def test_missing_current_verifier_is_incorrect(self) -> None:
        self.response["verifier_refs"] = []
        self.assertFalse(scoring.score_response(self.fixture, self.response)["correct"])

    def test_stale_support_is_incorrect_even_with_current_refs(self) -> None:
        self.response["material_refs"].append("OLD")
        score = scoring.score_response(self.fixture, self.response)
        self.assertFalse(score["correct"])
        self.assertTrue(score["stale_or_superseded_misuse"])

    def test_merely_noting_rejected_stale_refs_is_not_misuse(self) -> None:
        self.response["stale_or_superseded_refs_used"] = ["OLD"]
        self.assertTrue(scoring.score_response(self.fixture, self.response)["correct"])

    def test_wrong_candidate_and_list_candidate_fail_historical_rule(self) -> None:
        for candidate in ("C2", ["C1", "C2"]):
            self.response["selected_candidate"] = candidate
            self.assertFalse(scoring.score_response(self.fixture, self.response)["correct"])

    def test_continue_and_reject_match_nonfinalizable_fixture(self) -> None:
        self.fixture.update(expected_decision="continue", expected_candidate=None)
        for decision in ("continue", "reject"):
            self.response["decision"] = decision
            self.assertTrue(scoring.score_response(self.fixture, self.response)["correct"])
        self.response["decision"] = "finalize"
        self.assertFalse(scoring.score_response(self.fixture, self.response)["correct"])

    def test_unknown_decision_is_incorrect(self) -> None:
        self.response["decision"] = "accept"
        score = scoring.score_response(self.fixture, self.response)
        self.assertFalse(score["correct"])
        self.assertTrue(score["unsupported_decision"])

    def test_missing_oracle_or_response_refs_are_unscorable(self) -> None:
        for obj, key in ((self.fixture, "current_material_refs"),
                         (self.response, "verifier_refs")):
            value = obj.pop(key)
            with self.assertRaises(scoring.UnscorableError):
                scoring.score_response(self.fixture, self.response)
            obj[key] = value

    def test_missing_parse_status_cannot_default_to_success(self) -> None:
        self.response.pop("parse_ok")
        with self.assertRaises(scoring.UnscorableError):
            scoring.score_released_row(self.fixture, self.response)

    def test_protocol_failure_has_no_semantic_verdict(self) -> None:
        row = {"parse_ok": False, "provider_failure_type": "schema_failure", "correct": True}
        score = scoring.score_released_row(self.fixture, row)
        self.assertIsNone(score["semantic_correct"])
        self.assertFalse(score["semantic_eligible"])
        self.assertFalse(score["historical_correct"])

    def test_row_oracle_disagreement_is_not_silently_used(self) -> None:
        self.response["expected_candidate"] = "C2"
        with self.assertRaises(scoring.UnscorableError):
            scoring.score_released_row(self.fixture, self.response)

    def test_duplicate_keys_do_not_overwrite(self) -> None:
        row = {"provider": "glm", "episode": "fixture", "arm": "arm"}
        for indexer in (scoring.index_rows, validator.row_index):
            with self.assertRaises(scoring.UnscorableError):
                indexer([row, copy.deepcopy(row)])

    def test_contrast_refuses_unmatched_rows(self) -> None:
        row = {"provider": "glm", "episode": "fixture", "arm": "A", "correct": True}
        with self.assertRaises(scoring.UnscorableError):
            scoring.contrast([row], "A", "B")

    def test_fixture_vote_counts_correct_providers_not_unanimity(self) -> None:
        rows = []
        for provider, a, b in (("p1", True, False), ("p2", True, False), ("p3", False, True)):
            for arm, correct in (("A", a), ("B", b)):
                rows.append({"provider": provider, "episode": "fixture", "arm": arm,
                             "correct": correct, "semantic_eligible": True})
        result = scoring.contrast(rows, "A", "B", fixture_level=True)
        self.assertEqual(result["a_better"], 1)


class ReleasedInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summaries, cls.report = scoring.rescore_release(ROOT)

    def test_all_archived_scores_reconstructed_independently(self) -> None:
        self.assertEqual(self.report["status"], "PASS")
        self.assertEqual(self.report["semantic_rows_recomputed"], 965)
        self.assertEqual(len(self.report["protocol_failure_rows"]), 5)
        self.assertFalse(self.report["stored_verdict_or_auxiliary_mismatches"])

    def test_table5_denominators_and_protocol_sensitivity_are_explicit(self) -> None:
        historical = self.report["table5"]["historical_replication"]
        semantic = self.report["table5"]["semantic_valid_only"]
        self.assertEqual((historical["high_pressure"]["comparable"],
                          historical["low_pressure"]["comparable"],
                          historical["information_equivalent"]["comparable"]), (30, 16, 60))
        self.assertEqual((semantic["high_pressure"]["comparable"],
                          semantic["high_pressure"]["a_better"],
                          semantic["high_pressure"]["p_one_sided_a_gt_b"]), (29, 6, .015625))
        self.assertTrue(self.report["scientific_review_required"])

    def test_empty_low_pressure_rows_are_rejected(self) -> None:
        name = "phase9o_summary_protocol_repaired.json"
        oracle = {ep["name"]: ep for ep in scoring.read_json(ROOT / scoring.SOURCES[name])}
        with self.assertRaises(scoring.UnscorableError):
            scoring.require_inventory(name, [], oracle)

    def test_absent_typed_arm_is_rejected(self) -> None:
        name = "v3e_summary.json"
        oracle = {ep["name"]: ep for ep in scoring.read_json(ROOT / scoring.SOURCES[name])}
        rows = [r for r in scoring.rows_from(self.summaries[name]) if r["arm"] != "typed_protocol_state"]
        with self.assertRaises(scoring.UnscorableError):
            scoring.require_inventory(name, rows, oracle)

    def test_missing_provider_is_rejected(self) -> None:
        name = "v3i_summary.json"
        oracle = {ep["name"]: ep for ep in scoring.read_json(ROOT / scoring.SOURCES[name])}
        rows = [r for r in scoring.rows_from(self.summaries[name]) if r["provider"] == "glm"]
        with self.assertRaises(scoring.UnscorableError):
            scoring.require_inventory(name, rows, oracle)

    def test_empty_leakage_inventory_is_not_a_pass(self) -> None:
        original = validator.read_json

        def altered(root: Path, name: str):
            obj = original(root, name)
            if name == "LEAKAGE_AUDIT_STRICT_COUNTS.json":
                obj["pattern_counts"] = []
            return obj

        with patch.object(validator, "read_json", side_effect=altered):
            self.assertFalse(validator.leakage_status(ROOT)["strict_zero"])

    def test_failure_counts_are_episodes_and_calls_separately(self) -> None:
        cost = self.report["token_proxy"]
        self.assertEqual(cost["weak_curated_state"]["recorded_strong_token_proxy"], 24391)
        strong = cost["strong_curated_state"]
        self.assertEqual(strong["recorded_strong_token_proxy"], 146855)
        self.assertEqual(strong["runs_with_failed_state_update"], 8)
        self.assertEqual(strong["failed_state_update_calls"], 14)

    def test_validator_uses_recomputed_rows_and_distinguishes_review_gate(self) -> None:
        report = validator.validate_artifact(ROOT)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["scientific_review_status"], "REVIEW_REQUIRED")
        self.assertTrue(report["checks"]["table5_complete_denominators"])

    def test_full_validator_rejects_empty_low_pressure_and_missing_typed_arm(self) -> None:
        original = scoring.read_json

        def altered(path: Path):
            obj = original(path)
            if path.name == "phase9o_summary_protocol_repaired.json":
                obj["rows"] = []
            if path.name == "v3e_summary.json":
                obj["rows"] = [r for r in obj["rows"] if r["arm"] != "typed_protocol_state"]
            return obj

        with patch.object(scoring, "read_json", side_effect=altered):
            with self.assertRaises(scoring.UnscorableError):
                validator.validate_artifact(ROOT)

    def test_tampered_stored_correct_cannot_be_passed_by_aggregation(self) -> None:
        original = scoring.read_json

        def altered(path: Path):
            obj = original(path)
            if path.name == "v3i_summary.json":
                obj["new_rows"][0]["correct"] = not obj["new_rows"][0]["correct"]
            return obj

        with patch.object(scoring, "read_json", side_effect=altered):
            report = validator.validate_artifact(ROOT)
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["checks"]["independent_response_scores_match_archived_verdicts"])

    def test_tampered_stored_aggregate_is_reported(self) -> None:
        original = scoring.read_json

        def altered(path: Path):
            obj = original(path)
            if path.name == "v3i_summary.json":
                obj["aggregate"]["glm::schema_guided_weak_memory"]["correct"] = 0
            return obj

        with patch.object(scoring, "read_json", side_effect=altered):
            report = validator.validate_artifact(ROOT)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(report["row_scoring"]["own_arm_aggregate_mismatches"])


if __name__ == "__main__":
    unittest.main()
