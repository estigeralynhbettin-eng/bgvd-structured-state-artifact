from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
