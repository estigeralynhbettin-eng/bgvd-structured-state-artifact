"""Regression for the separately labelled, post-audit retry sensitivity."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import protocol_sensitivity as sensitivity  # noqa: E402


class ProtocolSensitivityTests(unittest.TestCase):
    def test_frozen_source_results(self):
        result = sensitivity.analyze(ROOT)
        low = result['low_pressure']
        expected = {'matched_freeform_weak_memory': (1, 0, 12, 13),
                    'raw_running_log': (0, 0, 14, 14),
                    'rag_retrieval_memory': (0, 0, 14, 14)}
        for arm, counts in expected.items():
            self.assertEqual(tuple(low[arm][k] for k in ('wins', 'losses', 'ties', 'pairs')), counts)
        cross = result['cross_family_extended']
        for name, counts in [('exclude_retries', (4, 3, 15, 22)),
                             ('exclude_retries_and_handoff_fallback', (4, 3, 13, 20))]:
            self.assertEqual(tuple(cross[name][k] for k in ('wins', 'losses', 'ties', 'pairs')), counts)

    def test_exclusion_is_symmetric_and_preserves_input(self):
        rows = [{'provider': 'p', 'episode': str(i), 'arm': arm, 'score': score}
                for i, scores in enumerate([(True, False), (False, False)])
                for arm, score in zip(('a', 'b'), scores)]
        result = sensitivity.paired_counts(rows, 'a', 'b', {('p', '0')})
        self.assertEqual((result['wins'], result['losses'], result['ties']), (0, 0, 1))
        self.assertEqual(len(rows), 4)

    def test_incomplete_duplicate_or_empty_inventory_rejected(self):
        one = {'provider': 'p', 'episode': 'e', 'arm': 'a', 'score': True}
        other = {**one, 'arm': 'b'}
        for rows, excluded in [([], set()), ([one], set()), ([one, one, other], set()),
                               ([one, other], {('p', 'missing')}),
                               ([one, other], {('p', 'e')}),
                               ([one, {**other, 'score': None}], set())]:
            with self.subTest(rows=rows, excluded=excluded), self.assertRaises(ValueError):
                sensitivity.paired_counts(rows, 'a', 'b', excluded)


if __name__ == '__main__':
    unittest.main()
