"""Release identity and evidence links must be checked, not manually copied."""
import csv
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def resolve_evidence(data, path):
    for segment in path.split("."):
        if "[" not in segment:
            data = data[segment]
            continue
        name, selector = segment[:-1].split("[", 1)
        data = data[name]
        if selector.isdigit():
            data = data[int(selector)]
        elif isinstance(data, dict):
            data = data[selector]
        else:
            matches = [item for item in data if item.get("check_id") == selector]
            if len(matches) != 1:
                raise KeyError(segment)
            data = matches[0]
    return data


class ReleaseProvenanceTests(unittest.TestCase):
    def test_public_case_hash_has_a_valid_explicit_representation(self):
        manifest = json.loads((ROOT / "validation/runtime/authorized_review_use_manifest.json").read_text(encoding="utf-8"))
        case = manifest["released_deidentified_case"]
        self.assertRegex(case["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("CRLF normalized to LF", case["sha256_representation"])
        payload = (ROOT / case["path"]).read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), case["sha256"])

    def test_historical_evidence_pointers_resolve(self):
        with (ROOT / "RESULT_TRACEABILITY.csv").open(encoding="utf-8", newline="") as handle:
            records = list(csv.DictReader(handle))
        self.assertGreater(len(records), 0)
        for record in records:
            data = json.loads((ROOT / record["source_file"]).read_text(encoding="utf-8"))
            for field in record["json_path_or_test"].split(";"):
                with self.subTest(result=record["result_id"], field=field):
                    resolve_evidence(data, field.strip())

    def test_nonexistent_evidence_pointer_is_rejected(self):
        for field in ("case_validation", "checkpoint_resume", "invalid_input", "compatibility"):
            with self.subTest(field=field), self.assertRaises(KeyError):
                resolve_evidence({"case": {}, "checks": {}}, field)
