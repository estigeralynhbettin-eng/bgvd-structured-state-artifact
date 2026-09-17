"""Author-side deterministic extraction; this never loads keys or calls a model.

Reviewers use score_cross_family.py with the included JSON, not this extractor.
The extraction requires the author's original local archive supplied by argument.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal_assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                               for t in node.targets):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
    raise ValueError(f"Cannot find frozen literal: {name}")


def convert_condition(node: ast.expr) -> dict[str, Any]:
    if isinstance(node, ast.BoolOp):
        return {"all" if isinstance(node.op, ast.And) else "any":
                [convert_condition(value) for value in node.values]}
    if (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In)
            and isinstance(node.left, ast.Constant) and isinstance(node.comparators[0], ast.Name)
            and node.comparators[0].id == "text"):
        return {"contains": node.left.value}
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "gate_words"):
        return {"gate_words": True}
    raise ValueError(f"Unsupported historical oracle expression: {ast.dump(node)}")


def extract_oracle(g_path: Path, h_path: Path) -> tuple[dict[str, Any], Any]:
    g_tree = ast.parse(g_path.read_text(encoding="utf-8-sig"))
    h_tree = ast.parse(h_path.read_text(encoding="utf-8-sig"))
    required = literal_assignment(g_tree, "REQUIRED_FINAL_KEYS")
    tasks = literal_assignment(h_tree, "PHASE9G_H_TASKS")
    gate_function = next(node for node in g_tree.body
                         if isinstance(node, ast.FunctionDef) and node.name == "gate_words")
    gate_words = literal_assignment(ast.Module(body=gate_function.body, type_ignores=[]), "terms")
    validator = next(node for node in h_tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "validate_final_h")
    oracle_tasks = {}
    for node in ast.walk(validator):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "task_id"):
            continue
        task_id = ast.literal_eval(node.test.comparators[0])
        assignment = next(item for item in node.body if isinstance(item, ast.Assign))
        checks = {ast.literal_eval(key): convert_condition(value)
                  for key, value in zip(assignment.value.keys, assignment.value.values)
                  if key is not None}
        oracle_tasks[task_id] = {"family": tasks[task_id]["category"], "checks": checks}
    # Execute only the audited pure historical validator function, not its runner.
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=[validator], type_ignores=[]), str(h_path.name), "exec"), namespace)
    historical = namespace["validate_final_h"]
    historical.g_module = SimpleNamespace(
        REQUIRED_FINAL_KEYS=required,
        flatten_json_text=lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True).lower(),
        gate_words=lambda text: any(word in text for word in gate_words),
    )
    return {"rule": "Historical validate_final_h lexical source-anchor acceptance",
            "required_final_keys": required, "gate_words": gate_words,
            "tasks": dict(sorted(oracle_tasks.items()))}, historical


REDACTIONS = {
    "local_absolute_path": r"(?i)(?:[A-Z]:\\|/(?:root|mnt|home|tmp|etc)/)[^\s\"<>]*",
    "url": r"https?://[^\s\"<>]+",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "benchmark_identifier": r"CVE-\d{4}-\d+",
    "shell_download_command": r"(?i)\b(?:curl|wget)\s+[^\n]*",
    "injection_example": r"(?i)\b(?:union\s+select|or\s+1\s*=\s*1)[^\n]*",
    "traversal_example": r"(?:\.\.[\\/])+[^\s'\"),\]]*",
}


def sanitize(obj: Any, counts: dict[str, int]) -> Any:
    if isinstance(obj, dict):
        return {key: sanitize(value, counts) for key, value in obj.items()}
    if isinstance(obj, list):
        return [sanitize(value, counts) for value in obj]
    if isinstance(obj, str):
        for label, pattern in REDACTIONS.items():
            obj, count = re.subn(pattern, f"<REDACTED_{label.upper()}>", obj)
            counts[label] += count
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    project = args.project_root
    l_dir = project / "outputs/phase9l_cross_family_source_rq1/phase9l_full_clean_12task_glm_deepseek_20260708"
    m_dir = project / "outputs/phase9m_extended_source_schema/phase9m_full_extended_source_schema_20260708_1605"
    l_path, m_path = l_dir / "summary.json", m_dir / "summary_protocol_repaired.json"
    l_summary, m_summary = read(l_path), read(m_path)
    original_m = read(m_dir / "summary.json")
    g_path = project / "scripts/run_phase9g_g_noisy_handoff_source_audit.py"
    h_path = project / "scripts/run_phase9g_h_powered_noisy_handoff_source_audit.py"
    oracle, historical = extract_oracle(g_path, h_path)
    spec = importlib.util.spec_from_file_location("cross_family_scorer", args.out_dir.parent / "score_cross_family.py")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    retries = {(r["provider"], r["task_id"], r["arm"]): r for r in m_summary["protocol_retry_rows"]}
    retry_dir = m_dir / m_summary["protocol_retry_dir"].replace("\\", "/").split("/")[-1]
    counts = {name: 0 for name in REDACTIONS}
    attempts, sources, check_mismatches = [], [], []
    # Phase9m reused the original baselines; assert identity rather than duplicate them.
    if l_summary["strong_rows"] != m_summary["phase9l_baseline_rows_reused"]:
        raise ValueError("Phase9m reused baselines are not identical to frozen Phase9l rows")
    for phase, rows, base in (("phase9l", l_summary["strong_rows"], l_dir),
                              ("phase9m", original_m["strong_rows"], m_dir),
                              ("phase9m", m_summary["protocol_retry_rows"], retry_dir)):
        for row in rows:
            key = (row["provider"], row["task_id"], row["arm"])
            is_retry = row.get("stage") == "strong_round2_protocol_retry"
            suffix = "retry1" if is_retry else "original"
            attempt_id = ":".join((phase, *key, suffix))
            data_dir = base.joinpath(*key)
            parsed_path = data_dir / "parsed_response.json"
            response = read(parsed_path) if parsed_path.exists() else None
            sanitized = sanitize(response, counts)
            if isinstance(response, dict):
                raw_score = historical(response, row["task_id"], row["arm"])
                sanitized_score = scorer.score_response(sanitized, row["task_id"], oracle)
                if raw_score["checks"] != sanitized_score["checks"]:
                    raise ValueError(f"Redaction or oracle extraction changed scoring: {attempt_id}")
                if raw_score["checks"] != row.get("validation_checks"):
                    check_mismatches.append(attempt_id)
                source = {"attempt_id": attempt_id, "source_role": "parsed_response",
                          "source_sha256": digest(parsed_path),
                          "released_response_sha256": hashlib.sha256(json.dumps(sanitized,
                            sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
                sources.append(source)
            selected = phase == "phase9l" or is_retry or key not in retries
            prompt_path = data_dir / "prompt_sent.md"
            public = {name: row.get(name) for name in (
                "provider", "model", "task_id", "arm", "parse_status", "failure_type",
                "finish_reason", "weak_parse_status", "weak_failure_type", "content_empty")}
            public.update({"phase": phase, "attempt_id": attempt_id, "selected_for_analysis": selected,
                           "attempt_kind": suffix, "response": sanitized,
                           "archived_accepted": row["accepted"],
                           "completion_token_budget": row.get("retry_max_tokens", 4096),
                           "prompt_sha256": digest(prompt_path),
                           "retry_of": ":".join((phase, *key, "original")) if is_retry else None})
            attempts.append(public)
    if check_mismatches:
        raise ValueError(f"Historical raw scorer differs from archived checks: {check_mismatches}")
    bundle = {"schema_version": "bgvd.cross_family.evidence.v1", "oracle": oracle,
              "design": {"task_count": 12, "providers": ["glm", "deepseek"],
                         "analysis_unit": "provider-task pair", "repetitions": 1,
                         "phase9m_baselines_reused_from_phase9l": True,
                         "target_runtime_calls": 0,
                         "weak_model": "qwen3.5:9b",
                         "upstream_parse_failure_fallback": "raw weak output text retained by original runner",
                         "outcome_meaning": "fixed lexical source-audit acceptance, not verified vulnerability"},
              "attempts": attempts}
    result = scorer.score_bundle(bundle)
    if result["status"] != "PASS":
        raise ValueError("Independent scoring differs from archived acceptance labels")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = args.out_dir / "source_audit_evidence.json"
    evidence_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["input_canonical_sha256"] = scorer.canonical_json_sha256(bundle)
    (args.out_dir / "cross_family_rescore.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    private_sources = {"phase9l_summary": l_path, "phase9m_original_summary": m_dir / "summary.json",
                       "phase9m_repaired_summary": m_path, "historical_validator": h_path,
                       "historical_common_helpers": g_path,
                       "phase9l_runner": project / "scripts/run_phase9l_cross_family_source_rq1.py",
                       "phase9m_runner": project / "scripts/run_phase9m_extended_source_schema.py",
                       "protocol_retry_runner": project / "scripts/retry_phase9m_protocol_failures.py"}
    provenance = {"schema_version": "bgvd.cross_family.provenance.v1", "publication_status": "local preparation",
                  "private_source_digests": {name: digest(path) for name, path in private_sources.items()},
                  "response_sources": sources, "redaction_counts": counts,
                  "historical_raw_vs_released_check_mismatches": check_mismatches,
                  "released_evidence_canonical_sha256": scorer.canonical_json_sha256(bundle),
                  "released_hash_rule": "UTF-8 of json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))",
                  "exclusions": ["raw prompts", "raw API responses", "local absolute paths",
                                 "provider endpoints", "credentials", "target source bundles"],
                  "scope": "Recompute fixed acceptance from parsed response fields; model calls and source execution not reproduced"}
    (args.out_dir / "source_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = scorer.validate_release(args.out_dir.parent)
    (args.out_dir / "cross_family_rescore.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "attempts": len(attempts),
                      "selected_attempts": result["selected_attempts"], "redactions": counts,
                      "comparisons": result["comparisons"]}, indent=2))


if __name__ == "__main__":
    main()
