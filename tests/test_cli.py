from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
import tempfile
import unittest
from pathlib import Path

from bgvd_state.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_replay_and_gate_candidate_replacement(self) -> None:
        events = ROOT / "examples" / "candidate_replacement" / "events.json"
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            handoff = Path(tmp) / "handoff.json"
            gate = Path(tmp) / "gate.json"
            self.assertEqual(
                main(
                    [
                        "replay",
                        "--events",
                        str(events),
                        "--state-out",
                        str(state),
                        "--handoff-out",
                        str(handoff),
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    ["gate", "--state", str(state), "--candidate", "C_CURRENT", "--out", str(gate)]
                ),
                0,
            )
            packet = json.loads(handoff.read_text(encoding="utf-8"))
            decision = json.loads(gate.read_text(encoding="utf-8"))
        self.assertEqual(packet["finalization_allowed_for"], ["C_CURRENT"])
        self.assertTrue(decision["allowed"])

    def test_stale_verifier_returns_rejected_status(self) -> None:
        events = ROOT / "examples" / "stale_verifier" / "events.json"
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            self.assertEqual(
                main(["replay", "--events", str(events), "--state-out", str(state)]), 0
            )
            self.assertEqual(main(["gate", "--state", str(state), "--candidate", "C_STALE"]), 2)

    def test_discovery_runtime_case_summary_and_gate(self) -> None:
        events = ROOT / "examples" / "discovery_runtime_case" / "events.json"
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            handoff = Path(tmp) / "handoff.json"
            gate = Path(tmp) / "gate.json"
            self.assertEqual(
                main(
                    [
                        "replay",
                        "--events",
                        str(events),
                        "--state-out",
                        str(state),
                        "--handoff-out",
                        str(handoff),
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "gate",
                        "--state",
                        str(state),
                        "--candidate",
                        "CASE-C06",
                        "--out",
                        str(gate),
                    ]
                ),
                2,
            )
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["summary", "--state", str(state)]), 0)
            packet = json.loads(handoff.read_text(encoding="utf-8"))
            decision = json.loads(gate.read_text(encoding="utf-8"))

        self.assertEqual(len(packet["rejected_candidates"]), 5)
        self.assertEqual(len(packet["failed_paths"]), 5)
        self.assertEqual(packet["finalization_allowed_for"], [])
        self.assertFalse(decision["allowed"])
        self.assertIn("current_verifier_not_positive", decision["reasons"])
        self.assertIn("Events loaded: 23", output.getvalue())
        self.assertIn("Candidates: 6", output.getvalue())
        self.assertIn("Finalization allowed: none", output.getvalue())


if __name__ == "__main__":
    unittest.main()
