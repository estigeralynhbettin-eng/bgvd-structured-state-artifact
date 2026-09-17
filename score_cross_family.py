"""Offline acceptance scoring for the archived cross-family source-audit boundary test.

The fixed oracle checks response schema keys, finding_present, and lexical source
anchors. This reproduces the historical source-audit acceptance rule; it does not
execute targets or independently establish a vulnerability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ARMS = ("schema_guided_security_memory", "matched_freeform_weak_memory",
        "generic_structured_memory", "extended_source_schema_memory")
PROVIDERS = ("glm", "deepseek")
TASKS = tuple(f"WP-H-{number:03d}" for number in range(1, 13))


class EvidenceError(ValueError):
    """Required scoring evidence is absent, contradictory, or duplicated."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate_condition(condition: dict[str, Any], text: str, gate_words: list[str]) -> bool:
    if not isinstance(condition, dict) or len(condition) != 1:
        raise EvidenceError("Malformed source-anchor oracle condition")
    kind, value = next(iter(condition.items()))
    if kind in {"all", "any"} and isinstance(value, list) and value:
        answers = [evaluate_condition(item, text, gate_words) for item in value]
        return all(answers) if kind == "all" else any(answers)
    if kind == "contains" and isinstance(value, str) and value:
        return value in text
    if kind == "gate_words" and value is True:
        return any(word in text for word in gate_words)
    raise EvidenceError(f"Unsupported source-anchor oracle condition: {kind}")


def score_response(response: dict[str, Any], task_id: str, oracle: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise EvidenceError("A parsed response object is required for acceptance scoring")
    tasks = oracle.get("tasks")
    if not isinstance(tasks, dict) or task_id not in tasks:
        raise EvidenceError(f"Missing task oracle: {task_id}")
    required = oracle.get("required_final_keys")
    gate_words = oracle.get("gate_words")
    task_checks = tasks[task_id].get("checks")
    if (not isinstance(required, list) or not required
            or not all(isinstance(key, str) for key in required)
            or not isinstance(gate_words, list) or not gate_words
            or not all(isinstance(word, str) and word for word in gate_words)
            or not isinstance(task_checks, dict) or not task_checks):
        raise EvidenceError("Incomplete source-audit oracle")
    missing = [key for key in required if key not in response]
    text = json.dumps(response, ensure_ascii=False, sort_keys=True).lower()
    checks = {"schema_keys_present": not missing,
              "finding_present_true": response.get("finding_present") is True,
              "handoff_or_no_handoff_recorded": "handoff_use" in response}
    checks.update({name: evaluate_condition(condition, text, gate_words)
                   for name, condition in task_checks.items()})
    return {"accepted": all(checks.values()), "checks": checks, "missing_keys": missing}


def score_attempt(row: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    for field in ("attempt_id", "task_id", "provider", "arm", "parse_status", "failure_type",
                  "weak_parse_status", "weak_failure_type"):
        if not isinstance(row.get(field), str) or not row[field]:
            raise EvidenceError(f"Attempt is missing required status or identity: {field}")
    for prefix in ("", "weak_"):
        if row[prefix + "parse_status"] not in {"ok", "failed"}:
            raise EvidenceError("Unrecognized parse status")
        if row[prefix + "failure_type"] not in {"ok", "schema_failure", "provider_or_transport_failure"}:
            raise EvidenceError("Unrecognized failure type")
        if row[prefix + "parse_status"] == "failed" and row[prefix + "failure_type"] == "ok":
            raise EvidenceError("Failed parse contradicts successful protocol status")
    protocol_valid = row["parse_status"] == "ok" and row["failure_type"] == "ok"
    response = row.get("response")
    if row["task_id"] not in oracle.get("tasks", {}):
        raise EvidenceError("Missing task oracle")
    if protocol_valid and not isinstance(response, dict):
        raise EvidenceError("Successful protocol row has no response")
    result = score_response(response, row["task_id"], oracle) if isinstance(response, dict) else None
    if protocol_valid and result["missing_keys"]:
        raise EvidenceError("Successful protocol status contradicts missing response schema keys")
    accepted = result["accepted"] if protocol_valid else None
    return {"attempt_id": row["attempt_id"], "task_id": row["task_id"],
            "provider": row["provider"], "arm": row["arm"],
            "final_response_eligible": protocol_valid, "accepted": accepted,
            "end_to_end_eligible": protocol_valid and row["weak_parse_status"] == "ok"
            and row["weak_failure_type"] == "ok",
            "historical_acceptance_for_archive_only": accepted if protocol_valid else False,
            "checks": result["checks"] if result else {},
            "missing_keys": result["missing_keys"] if result else []}


def paired(rows: list[dict[str, Any]], arm_a: str, arm_b: str,
           eligibility: str = "final_response_eligible") -> dict[str, Any]:
    if eligibility not in {"final_response_eligible", "end_to_end_eligible"}:
        raise EvidenceError("Unknown eligibility rule")
    indexed = {}
    for row in rows:
        key = (row["provider"], row["task_id"], row["arm"])
        if key in indexed:
            raise EvidenceError(f"Duplicate comparison row: {key}")
        indexed[key] = row
    wins = losses = ties = a_accepted = b_accepted = 0
    excluded = []
    for provider in PROVIDERS:
        for task_id in TASKS:
            key_a = (provider, task_id, arm_a)
            key_b = (provider, task_id, arm_b)
            if key_a not in indexed or key_b not in indexed:
                raise EvidenceError(f"Incomplete paired inventory for {provider}/{task_id}")
            a, b = indexed[key_a], indexed[key_b]
            if not a[eligibility] or not b[eligibility]:
                excluded.append({"provider": provider, "task_id": task_id})
                continue
            if type(a["accepted"]) is not bool or type(b["accepted"]) is not bool:
                raise EvidenceError("Eligible row lacks a boolean acceptance result")
            a_accepted += int(a["accepted"])
            b_accepted += int(b["accepted"])
            wins += int(a["accepted"] and not b["accepted"])
            losses += int(b["accepted"] and not a["accepted"])
            ties += int(a["accepted"] == b["accepted"])
    n = wins + losses
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n) if n else 1.0
    return {"arm_a": arm_a, "arm_b": arm_b, "unit": "provider-task pair",
            "eligibility": eligibility, "comparable": wins + losses + ties,
            "a_accepted": a_accepted, "b_accepted": b_accepted,
            "a_better": wins, "b_better": losses, "ties": ties,
            "p_one_sided_a_gt_b": p, "excluded_units": excluded}


def validate_inventory(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    oracle, attempts = bundle.get("oracle"), bundle.get("attempts")
    if not isinstance(oracle, dict) or set(oracle.get("tasks", {})) != set(TASKS):
        raise EvidenceError("Expected the frozen 12-task oracle inventory")
    if not isinstance(attempts, list) or not attempts:
        raise EvidenceError("No archived attempts")
    by_id, selected = {}, {}
    for row in attempts:
        attempt_id = row.get("attempt_id")
        key = (row.get("provider"), row.get("task_id"), row.get("arm"))
        if not isinstance(attempt_id, str) or attempt_id in by_id:
            raise EvidenceError("Missing or duplicate attempt identity")
        if key[0] not in PROVIDERS or key[1] not in TASKS or key[2] not in ARMS:
            raise EvidenceError(f"Unexpected comparison identity: {key}")
        if type(row.get("selected_for_analysis")) is not bool:
            raise EvidenceError("Missing selected-attempt flag")
        by_id[attempt_id] = row
        if row["selected_for_analysis"]:
            if key in selected:
                raise EvidenceError(f"Two selected attempts for one analysis unit: {key}")
            selected[key] = row
    expected = {(p, t, a) for p in PROVIDERS for t in TASKS for a in ARMS}
    if set(selected) != expected:
        raise EvidenceError("Selected rows do not cover the full 2 x 12 x 4 inventory")
    replaced_ids = set()
    for row in attempts:
        retry = row.get("retry_of")
        if retry is None:
            continue
        original = by_id.get(retry)
        if original is None or original["selected_for_analysis"]:
            raise EvidenceError("Retry does not replace a retained unselected original attempt")
        if any(row[key] != original[key] for key in ("provider", "task_id", "arm")):
            raise EvidenceError("Retry identity differs from its original")
        if original["parse_status"] == "ok" and original["failure_type"] == "ok":
            raise EvidenceError("A successful attempt cannot be replaced as a protocol retry")
        if not row.get("prompt_sha256") or row["prompt_sha256"] != original.get("prompt_sha256"):
            raise EvidenceError("Retry does not attest the identical saved prompt")
        if retry in replaced_ids or not row["selected_for_analysis"]:
            raise EvidenceError("Ambiguous or unselected retry replacement")
        replaced_ids.add(retry)
    if replaced_ids != {key for key, row in by_id.items() if not row["selected_for_analysis"]}:
        raise EvidenceError("An unselected archived attempt has no selected retry replacement")
    return [score_attempt(row, oracle) for row in selected.values()], by_id


def score_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    rows, attempts = validate_inventory(bundle)
    aggregates = {}
    for arm in ARMS:
        members = [row for row in rows if row["arm"] == arm]
        aggregates[arm] = {}
        for eligibility in ("final_response_eligible", "end_to_end_eligible"):
            eligible = [row for row in members if row[eligibility]]
            aggregates[arm][eligibility] = {
                "accepted": sum(row["accepted"] for row in eligible), "denominator": len(eligible),
                "excluded": len(members) - len(eligible)}
    mismatch = []
    for row in rows:
        old = attempts[row["attempt_id"]].get("archived_accepted")
        if type(old) is not bool or old != row["historical_acceptance_for_archive_only"]:
            mismatch.append(row["attempt_id"])
    comparisons = {}
    for eligibility in ("final_response_eligible", "end_to_end_eligible"):
        comparisons[eligibility] = {
            "schema_vs_matched": paired(rows, ARMS[0], ARMS[1], eligibility),
            "extended_vs_matched": paired(rows, ARMS[3], ARMS[1], eligibility),
        }
    return {"schema_version": "bgvd.cross_family.rescore.v1",
            "status": "PASS" if not mismatch else "FAIL",
            "meaning": "Archived lexical source-audit acceptance recomputed; no target execution",
            "selected_attempts": len(rows), "retained_attempts": len(attempts),
            "protocol_failure_attempts": [key for key, row in attempts.items()
                if row["parse_status"] != "ok" or row["failure_type"] != "ok"],
            "upstream_handoff_failure_selected_attempts": [row["attempt_id"] for row in rows
                if row["final_response_eligible"] and not row["end_to_end_eligible"]],
            "archived_verdict_mismatches": mismatch, "aggregates": aggregates,
            "comparisons": comparisons, "scored_selected_rows": rows}


def validate_release(root: Path) -> dict[str, Any]:
    """Check canonical public-data identity, then independently rescore it."""
    directory = root / "cross_family"
    bundle = read_json(directory / "source_audit_evidence.json")
    manifest = read_json(directory / "source_provenance.json")
    actual = canonical_json_sha256(bundle)
    if manifest.get("released_evidence_canonical_sha256") != actual:
        raise EvidenceError("Cross-family evidence differs from its canonical provenance digest")
    sources = manifest.get("response_sources")
    if not isinstance(sources, list) or not sources:
        raise EvidenceError("Missing cross-family response provenance inventory")
    by_id = {}
    for item in sources:
        identity = item.get("attempt_id")
        if not isinstance(identity, str) or identity in by_id:
            raise EvidenceError("Duplicate or missing response provenance identity")
        by_id[identity] = item
    expected = {row["attempt_id"] for row in bundle["attempts"] if row.get("response") is not None}
    if set(by_id) != expected:
        raise EvidenceError("Response provenance does not cover exactly the available parsed responses")
    for row in bundle["attempts"]:
        if row["attempt_id"] not in expected:
            continue
        payload = json.dumps(row["response"], sort_keys=True, ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != by_id[row["attempt_id"]].get("released_response_sha256"):
            raise EvidenceError("Released response differs from its provenance digest")
    result = score_bundle(bundle)
    result["input_canonical_sha256"] = actual
    result["public_data_integrity"] = {"status": "PASS", "parsed_response_count": len(expected)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_release(args.artifact)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({"status": result["status"], "selected_attempts": result["selected_attempts"],
                      "comparisons": result["comparisons"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
