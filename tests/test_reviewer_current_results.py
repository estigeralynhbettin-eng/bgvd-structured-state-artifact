"""Lock the reviewer-visible results and durable relative report links."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import validate_structured_state_artifact as validator  # noqa: E402

CHECKER = ROOT / "reviewer_offline_check.py"
if not CHECKER.is_file():
    CHECKER = ROOT / "reviewer" / "reviewer_offline_check.py"
SPEC = importlib.util.spec_from_file_location("reviewer_current_results_under_test", CHECKER)
REVIEWER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEWER)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value is not None)


class CurrentResultsReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.validate_artifact(ROOT)

    def render(self, report: dict | None = None) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            validator.write_markdown(self.report if report is None else report, path)
            return path.read_text(encoding="utf-8")

    def test_current_counts_precede_separate_historical_results(self) -> None:
        text = self.render()
        current, historical = text.split("## Historical contrasts:", 1)
        self.assertIn("fixtures; correct-provider counts | 29 | 6 | 0 | 23 | 0.015625", current)
        self.assertIn("provider-episode pairs | 59 | 11 | 0 | 48 | 0.00048828125", current)
        self.assertIn("provider-episode pairs | 16 | 1 | 0 | 15 | 0.5", current)
        self.assertIn("provider-episode pairs | 60 | 0 | 0 | 60 | 1", current)
        self.assertNotIn("| 30 | 7 | 0 | 23 |", current)
        self.assertIn("| 30 | 7 | 0 | 23 | 0.0078125", historical)
        self.assertIn("| 60 | 12 | 0 | 48 | 0.000244140625", historical)

    def test_cross_family_units_eligibility_and_fallback_sensitivity_are_visible(self) -> None:
        text = self.render()
        self.assertIn("provider-task pair | 24 | 10/24 | 12/24 | 2 | 4 | 18", text)
        self.assertIn("provider-task pair | 24 | 12/24 | 12/24 | 4 | 4 | 16", text)
        self.assertIn("provider-task pair | 22 | 10/22 | 10/22 | 4 | 4 | 14", text)
        self.assertIn("Valid final response and upstream handoff", text)
        self.assertIn("not independent task replications", text)
        self.assertIn("separate source-audit lexical scorer", text)

    def test_unknown_updater_usage_is_not_mislabeled_as_finalizer_failure(self) -> None:
        text = self.render()
        self.assertIn("Finalizer parse failures", text)
        self.assertIn("Updater calls with unrecorded usage", text)
        self.assertIn("| Strong-curated handoff | 30/30 | 0 | 25565 | 121290 | 146855 | 14 | 8 |", text)
        self.assertIn("14 failed updater calls with unrecorded usage across 8 runs", text)
        self.assertIn("finalizer parse failures are 0; these are different stages and counts", text)
        self.assertIn("Unrecorded updater usage remains null", text)

    def test_report_displays_json_values_instead_of_repeating_constants(self) -> None:
        changed = copy.deepcopy(self.report)
        changed["row_scoring"]["table5"]["semantic_valid_only"]["high_pressure"].update(
            comparable=31, a_better=8, b_better=1, ties=22, p_one_sided_a_gt_b=0.03125)
        changed["token_accounting"]["arms"]["strong_curated_state"]["unknown_usage_calls"] = 5
        changed["token_accounting"]["arms"]["strong_curated_state"]["runs_with_failed_state_update"] = 3
        text = self.render(changed)
        self.assertIn("fixtures; correct-provider counts | 31 | 8 | 1 | 22 | 0.03125", text)
        self.assertIn("5 failed updater calls with unrecorded usage across 3 runs", text)

    def test_rendering_does_not_change_machine_results(self) -> None:
        before = copy.deepcopy(self.report)
        self.render()
        self.assertEqual(before, self.report)

    def test_missing_current_results_cannot_fall_back_to_historical_table(self) -> None:
        changed = copy.deepcopy(self.report)
        del changed["row_scoring"]["table5"]["semantic_valid_only"]
        with self.assertRaises(KeyError):
            self.render(changed)

    def test_html_report_presents_actual_current_values_as_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            validator.write_markdown(self.report, path)
            html = path.with_suffix(".html").read_text(encoding="utf-8")
        self.assertIn('<html lang="en">', html)
        self.assertIn("<td>29</td><td>6</td><td>0</td><td>23</td>", html)
        self.assertIn("<td>59</td><td>11</td><td>0</td><td>48</td>", html)
        self.assertIn("<td>22</td><td>10/22</td><td>10/22</td>", html)
        self.assertIn("14 failed updater calls with unrecorded usage across 8 runs", html)
        self.assertLess(html.index("Current manuscript results"), html.index("Historical contrasts"))
        self.assertEqual(html.count("<table>"), html.count("</table>"))
        self.assertIn("<th>Counting unit</th>", html)

    def test_html_report_escapes_data_values(self) -> None:
        changed = copy.deepcopy(self.report)
        changed["validated_at"] = '<script>alert("x")</script> & test'
        changed["checks"]['<img src=x onerror="alert(1)">'] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            validator.write_markdown(changed, path)
            html = path.with_suffix(".html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; test", html)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", html)


class DurableReviewerLinksTests(unittest.TestCase):
    def payload(self, status: str = "PASS") -> dict:
        return {"status": status, "generated_at": "test", "checks": [],
                "scientific_review_status": "REVIEW_REQUIRED"}

    def test_saved_report_links_resolve_after_temporary_source_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as destination:
            output = Path(destination)
            with tempfile.TemporaryDirectory() as source:
                temporary = Path(source)
                for filename, content in (("ARTIFACT_VALIDATION_REPORT.html", "<h1>Saved current results</h1>\n"),
                                          ("ARTIFACT_VALIDATION_REPORT.md", "# Saved current results\n"),
                                          ("artifact_validation_report.json", '{"status":"PASS"}\n')):
                    (temporary / filename).write_text(content, encoding="utf-8")
                    REVIEWER._copy_if_present(temporary / filename, output / "artifact_validation" / filename)
            self.assertFalse(temporary.exists())
            logs = output / "logs"
            logs.mkdir()
            (logs / "06_artifact_validator.txt").write_text("temporary source was cleaned up", encoding="utf-8")
            with patch.object(REVIEWER, "OUTPUT", output):
                REVIEWER._write_summaries(self.payload())
            html = (output / "REVIEWER_CHECK_SUMMARY.html").read_text(encoding="utf-8")
            parser = LinkParser()
            parser.feed(html)
            expected = {"artifact_validation/ARTIFACT_VALIDATION_REPORT.html",
                        "artifact_validation/ARTIFACT_VALIDATION_REPORT.md",
                        "artifact_validation/artifact_validation_report.json"}
            self.assertTrue(expected <= set(parser.links))
            self.assertEqual(parser.links[0], "artifact_validation/ARTIFACT_VALIDATION_REPORT.html")
            for link in parser.links:
                self.assertFalse(urlparse(link).scheme)
                self.assertFalse(Path(link).is_absolute())
                self.assertTrue((output / link).is_file(), link)
                self.assertTrue((output / link).resolve().is_relative_to(output.resolve()))
            self.assertNotIn(str(temporary), html)
            self.assertLess(html.index("Read the manuscript results"), html.index("Raw logs"))
            markdown = (output / "REVIEWER_CHECK_SUMMARY.md").read_text(encoding="utf-8")
            for link in expected:
                self.assertIn(f"]({link})", markdown)

    def test_failed_or_partial_run_does_not_publish_broken_links(self) -> None:
        with tempfile.TemporaryDirectory() as destination:
            output = Path(destination)
            with patch.object(REVIEWER, "OUTPUT", output):
                REVIEWER._write_summaries(self.payload("FAIL"))
            html = (output / "REVIEWER_CHECK_SUMMARY.html").read_text(encoding="utf-8")
            parser = LinkParser()
            parser.feed(html)
            self.assertNotIn("artifact_validation/ARTIFACT_VALIDATION_REPORT.md", parser.links)
            self.assertNotIn("artifact_validation/ARTIFACT_VALIDATION_REPORT.html", parser.links)
            self.assertNotIn("logs/06_artifact_validator.txt", parser.links)
            self.assertIn("full artifact report is not available", html)
            self.assertTrue(all((output / link).is_file() for link in parser.links))
            saved = json.loads((output / "REVIEWER_CHECK_SUMMARY.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, self.payload("FAIL"))


if __name__ == "__main__":
    unittest.main()
