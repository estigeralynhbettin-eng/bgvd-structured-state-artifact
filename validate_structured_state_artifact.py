#!/usr/bin/env python3
"""Validate the structured-state-interface artifact release candidate.

The validator intentionally performs no model calls and starts no benchmark
services. It only reads the sanitized release-candidate files and recomputes the
paper-facing contrasts that a reviewer should be able to verify after download.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

# The no-install reviewer launcher uses Python -I. Add only this trusted
# artifact directory, never PYTHONPATH or a caller-selected working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_released_rows import SOURCES, UnscorableError, rescore_release, usage_total  # noqa: E402
from score_token_accounting import validate_accounting  # noqa: E402
from score_cross_family import validate_release as validate_cross_family  # noqa: E402


REQUIRED_FILES = [
    "README.md",
    "REPRODUCE.md",
    "score_token_accounting.py",
    "score_cross_family.py",
    "token_accounting/calls.json",
    "token_accounting/origin_manifest.json",
    "cross_family/source_audit_evidence.json",
    "cross_family/source_provenance.json",
    "LEAKAGE_AUDIT_COUNTS.json",
    "LEAKAGE_AUDIT_STRICT_COUNTS.json",
    "v3e_summary.json",
    "v3e_stats.md",
    "v3i_summary.json",
    "v3j_summary.json",
    "v3k_summary.json",
    "phase9n_summary_protocol_repaired.json",
    "phase9p_summary_protocol_repaired.json",
    "phase9r_summary.json",
    "phase9o_summary_protocol_repaired.json",
    "phase9q_open_weight_summary.json",
    "phase9n_result.md",
    "phase9p_result.md",
    "phase9r_result.md",
    "phase9o_result.md",
    "phase9q_open_weight_result.md",
    "phase9q_prompt_audit.json",
    "v3g_glm_summary.json",
    "v3g_deepseek_summary.json",
    "v3h_glm_summary.json",
    "v3h_deepseek_summary.json",
]


def load_release_path(path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if path.is_dir():
        return path, None
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise SystemExit(f"artifact path must be a directory or .zip file: {path}")
    tmp = tempfile.TemporaryDirectory(prefix="bgvd_artifact_validate_")
    with zipfile.ZipFile(path) as zf:
        zf.extractall(tmp.name)
    return Path(tmp.name), tmp


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(root: Path, name: str) -> Any:
    with (root / name).open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def rows_from(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = summary.get("rows")
    if rows is None:
        rows = summary.get("new_rows")
    if rows is None:
        return []
    return list(rows)


def row_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["provider"]), str(row["episode"]), str(row["arm"]))
        if key in out:
            raise UnscorableError(f"duplicate provider/episode/arm: {key}")
        out[key] = row
    return out


def merge_indexes(*indexes: dict[tuple[str, str, str], dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for idx in indexes:
        if merged.keys() & idx.keys():
            raise UnscorableError("overlapping result sets; refusing silent row replacement")
        merged.update(idx)
    return merged


def sign_p_one_sided(a_better: int, b_better: int) -> float:
    n = a_better + b_better
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(a_better, n + 1)) / (2**n)


def paired_contrast(
    rows: dict[tuple[str, str, str], dict[str, Any]],
    arm_a: str,
    arm_b: str,
) -> dict[str, Any]:
    a_keys = {(provider, episode) for provider, episode, arm in rows if arm == arm_a}
    b_keys = {(provider, episode) for provider, episode, arm in rows if arm == arm_b}
    common = sorted(a_keys & b_keys)
    a_better = 0
    b_better = 0
    ties = 0
    for provider, episode in common:
        a = bool(rows[(provider, episode, arm_a)].get("correct"))
        b = bool(rows[(provider, episode, arm_b)].get("correct"))
        if a and not b:
            a_better += 1
        elif b and not a:
            b_better += 1
        else:
            ties += 1
    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "comparable": len(common),
        "a_better": a_better,
        "b_better": b_better,
        "ties": ties,
        "p_one_sided_a_gt_b": sign_p_one_sided(a_better, b_better),
    }


def fixture_level_contrast(
    rows: dict[tuple[str, str, str], dict[str, Any]],
    arm_a: str,
    arm_b: str,
) -> dict[str, Any]:
    episodes = sorted({episode for _, episode, arm in rows if arm in {arm_a, arm_b}})
    a_better = 0
    b_better = 0
    ties = 0
    comparable = 0
    for episode in episodes:
        providers_a = [p for p, ep, arm in rows if ep == episode and arm == arm_a]
        providers_b = [p for p, ep, arm in rows if ep == episode and arm == arm_b]
        providers = sorted(set(providers_a) & set(providers_b))
        if not providers:
            continue
        comparable += 1
        provider_diffs = []
        for provider in providers:
            a = bool(rows[(provider, episode, arm_a)].get("correct"))
            b = bool(rows[(provider, episode, arm_b)].get("correct"))
            provider_diffs.append((a > b) - (b > a))
        if sum(provider_diffs) > 0:
            a_better += 1
        elif sum(provider_diffs) < 0:
            b_better += 1
        else:
            ties += 1
    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "comparable_fixtures": comparable,
        "a_better": a_better,
        "b_better": b_better,
        "ties": ties,
        "p_one_sided_a_gt_b": sign_p_one_sided(a_better, b_better),
    }


def aggregate_totals(summaries: list[dict[str, Any]], arm: str) -> dict[str, int]:
    total = correct = strong_tokens = parse_failures = 0
    for summary in summaries:
        for row in rows_from(summary):
            if row["arm"] == arm:
                total += 1
                correct += row["correct"]
                strong_tokens += usage_total(row["usage"]) + row["state_update_tokens"]
                parse_failures += not row["parse_ok"]
    return {
        "total": total,
        "correct": correct,
        "strong_paid_tokens": strong_tokens,
        "parse_failures": parse_failures,
    }


def summarize_aggregate(summary: dict[str, Any], arm: str) -> dict[str, int]:
    total = correct = parse_failures = 0
    for row in rows_from(summary):
        if row["arm"] == arm:
            total += 1
            correct += row["correct"]
            parse_failures += not row["parse_ok"]
    return {"total": total, "correct": correct, "parse_failures": parse_failures}


def leakage_status(root: Path) -> dict[str, Any]:
    strict = read_json(root, "LEAKAGE_AUDIT_STRICT_COUNTS.json")
    broad = read_json(root, "LEAKAGE_AUDIT_COUNTS.json")
    strict_counts = {item["pattern"]: int(item["count"]) for item in strict.get("pattern_counts", [])}
    broad_counts = {item["pattern"]: int(item["count"]) for item in broad.get("pattern_counts", [])}
    expected_strict = {"api_key_like", "private_key", "secret_assignment_like", "bearer_like",
                       "basic_auth_url", "url", "ipv4"}
    expected_broad = {"api_key_like", "private_key", "credential_words", "url", "ipv4"}
    inventory_complete = (
        set(strict_counts) == expected_strict
        and len(strict.get("pattern_counts", [])) == len(expected_strict)
        and set(broad_counts) == expected_broad
        and len(broad.get("pattern_counts", [])) == len(expected_broad)
    )
    strict_zero = inventory_complete and all(value == 0 for value in strict_counts.values())
    broad_blocking_zero = all(
        broad_counts.get(pattern, 0) == 0
        for pattern in ["api_key_like", "private_key", "url", "ipv4"]
    )
    return {
        "strict_status": strict.get("status"),
        "recorded_pattern_inventory_complete": inventory_complete,
        "scope": "validation of archived audit-count records; not a new scan of current files",
        "strict_zero": strict_zero,
        "strict_counts": strict_counts,
        "broad_status": broad.get("status"),
        "broad_blocking_zero": broad_blocking_zero,
        "broad_counts": broad_counts,
    }


def validate_artifact(root: Path, source_path: Path | None = None) -> dict[str, Any]:
    required = set(REQUIRED_FILES) | set(SOURCES.values()) | {"score_released_rows.py"}
    missing = [name for name in sorted(required) if not (root / name).is_file()]
    if missing:
        raise UnscorableError(f"required artifact files missing: {missing}")
    rescored, row_scoring = rescore_release(root)

    v3e = rescored["v3e_summary.json"]
    v3i = rescored["v3i_summary.json"]
    v3j = rescored["v3j_summary.json"]
    v3k = rescored["v3k_summary.json"]
    phase9n = rescored["phase9n_summary_protocol_repaired.json"]
    phase9p = rescored["phase9p_summary_protocol_repaired.json"]
    phase9r = rescored["phase9r_summary.json"]
    phase9o = rescored["phase9o_summary_protocol_repaired.json"]
    phase9q = rescored["phase9q_open_weight_summary.json"]
    v3g_glm = rescored["v3g_glm_summary.json"]
    v3g_deepseek = rescored["v3g_deepseek_summary.json"]
    v3h_glm = rescored["v3h_glm_summary.json"]
    v3h_deepseek = rescored["v3h_deepseek_summary.json"]

    row_sets = {
        "v3e": row_index(rows_from(v3e)),
        "v3i": row_index(rows_from(v3i)),
        "v3j": row_index(rows_from(v3j)),
        "v3k": row_index(rows_from(v3k)),
        "phase9n": row_index(rows_from(phase9n)),
        "phase9p": row_index(rows_from(phase9p)),
        "phase9r": row_index(rows_from(phase9r)),
        "phase9o": row_index(rows_from(phase9o)),
        "phase9q": row_index(rows_from(phase9q)),
    }
    pressure_rows = merge_indexes(
        row_sets["v3e"],
        row_sets["v3i"],
        row_sets["v3j"],
        row_sets["v3k"],
        row_sets["phase9n"],
        row_sets["phase9p"],
        row_sets["phase9r"],
    )
    low_pressure_rows = row_sets["phase9o"]
    phase9q_rows = row_sets["phase9q"]

    contrasts = {
        "schema_vs_matched_provider_episode": paired_contrast(
            pressure_rows, "schema_guided_weak_memory", "matched_freeform_weak_memory"
        ),
        "schema_vs_matched_fixture_level": fixture_level_contrast(
            pressure_rows, "schema_guided_weak_memory", "matched_freeform_weak_memory"
        ),
        "schema_vs_generic_provider_episode": paired_contrast(
            pressure_rows, "schema_guided_weak_memory", "generic_structured_memory"
        ),
        "schema_vs_lexical_provider_episode": paired_contrast(
            pressure_rows, "schema_guided_weak_memory", "rag_retrieval_memory"
        ),
        "schema_vs_bm25_provider_episode": paired_contrast(
            pressure_rows, "schema_guided_weak_memory", "bm25_retrieval_memory"
        ),
        "schema_vs_hashed_dense_provider_episode": paired_contrast(
            pressure_rows, "schema_guided_weak_memory", "hashed_dense_retrieval_memory"
        ),
        "lexical_vs_generic_provider_episode": paired_contrast(
            pressure_rows, "rag_retrieval_memory", "generic_structured_memory"
        ),
        "bm25_vs_generic_provider_episode": paired_contrast(
            pressure_rows, "bm25_retrieval_memory", "generic_structured_memory"
        ),
        "hashed_dense_vs_generic_provider_episode": paired_contrast(
            pressure_rows, "hashed_dense_retrieval_memory", "generic_structured_memory"
        ),
        "curated_vs_schema_provider_episode": paired_contrast(
            pressure_rows, "untyped_curated_state", "schema_guided_weak_memory"
        ),
        "typed_surface_vs_curated_prose": paired_contrast(
            pressure_rows, "typed_protocol_state", "untyped_curated_state"
        ),
        "low_pressure_schema_vs_matched": paired_contrast(
            low_pressure_rows, "schema_guided_weak_memory", "matched_freeform_weak_memory"
        ),
        "low_pressure_schema_vs_lexical": paired_contrast(
            low_pressure_rows, "schema_guided_weak_memory", "rag_retrieval_memory"
        ),
        "low_pressure_schema_vs_raw": paired_contrast(
            low_pressure_rows, "schema_guided_weak_memory", "raw_running_log"
        ),
        "phase9q_open_weight_schema_vs_matched": paired_contrast(
            phase9q_rows, "schema_guided_weak_memory", "matched_freeform_weak_memory"
        ),
    }

    arm_totals = {
        "schema_guided_weak_memory": summarize_aggregate(v3i, "schema_guided_weak_memory"),
        "matched_freeform_weak_memory": summarize_aggregate(v3j, "matched_freeform_weak_memory"),
        "generic_structured_memory": summarize_aggregate(v3k, "generic_structured_memory"),
        "rag_retrieval_memory": summarize_aggregate(phase9n, "rag_retrieval_memory"),
        "bm25_retrieval_memory": summarize_aggregate(phase9p, "bm25_retrieval_memory"),
        "hashed_dense_retrieval_memory": summarize_aggregate(
            phase9r, "hashed_dense_retrieval_memory"
        ),
        "low_pressure_schema_guided_weak_memory": summarize_aggregate(
            phase9o, "schema_guided_weak_memory"
        ),
        "low_pressure_raw_running_log": summarize_aggregate(phase9o, "raw_running_log"),
        "low_pressure_rag_retrieval_memory": summarize_aggregate(phase9o, "rag_retrieval_memory"),
        "phase9q_open_weight_schema_guided_weak_memory": summarize_aggregate(
            phase9q, "schema_guided_weak_memory"
        ),
        "phase9q_open_weight_matched_freeform_weak_memory": summarize_aggregate(
            phase9q, "matched_freeform_weak_memory"
        ),
    }

    weak_curated_cost = aggregate_totals([v3g_glm, v3g_deepseek], "weak_curated_state")
    strong_curated_cost = aggregate_totals([v3h_glm, v3h_deepseek], "strong_curated_state")
    cost_ratio = (
        strong_curated_cost["strong_paid_tokens"] / weak_curated_cost["strong_paid_tokens"]
        if weak_curated_cost["strong_paid_tokens"]
        else None
    )

    file_manifest = []
    for path in sorted(root.iterdir()):
        if path.is_file():
            file_manifest.append(
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )

    accounting = validate_accounting(root)
    cross_family = validate_cross_family(root)
    leakage = leakage_status(root)
    checks = {
        "required_files_present": not missing,
        "per_call_token_accounting": accounting["status"] == "PASS",
        "cross_family_independent_scoring": cross_family["status"] == "PASS",
        "independent_response_scores_match_archived_verdicts": row_scoring["status"] == "PASS",
        "strong_token_record_components_reconcile": all(
            not row_scoring["token_proxy"][arm]["inconsistencies"]
            for arm in ("weak_curated_state", "strong_curated_state")
        ),
        "table5_complete_denominators":
            contrasts["schema_vs_matched_fixture_level"]["comparable_fixtures"] == 30
            and contrasts["schema_vs_matched_provider_episode"]["comparable"] == 60
            and contrasts["low_pressure_schema_vs_matched"]["comparable"] == 16
            and contrasts["typed_surface_vs_curated_prose"]["comparable"] == 60,
        "strict_leakage_pass": leakage["strict_status"] == "PASS" and leakage["strict_zero"],
        "schema_beats_matched_provider_episode_12_0": contrasts[
            "schema_vs_matched_provider_episode"
        ]["a_better"]
        == 12
        and contrasts["schema_vs_matched_provider_episode"]["b_better"] == 0,
        "schema_beats_matched_fixture_7_0": contrasts["schema_vs_matched_fixture_level"][
            "a_better"
        ]
        == 7
        and contrasts["schema_vs_matched_fixture_level"]["b_better"] == 0,
        "schema_beats_generic_22_0": contrasts["schema_vs_generic_provider_episode"][
            "a_better"
        ]
        == 22
        and contrasts["schema_vs_generic_provider_episode"]["b_better"] == 0,
        "schema_beats_lexical_10_0": contrasts["schema_vs_lexical_provider_episode"][
            "a_better"
        ]
        == 10
        and contrasts["schema_vs_lexical_provider_episode"]["b_better"] == 0,
        "schema_beats_bm25_10_0": contrasts["schema_vs_bm25_provider_episode"][
            "a_better"
        ]
        == 10
        and contrasts["schema_vs_bm25_provider_episode"]["b_better"] == 0,
        "schema_beats_hashed_dense_10_0": contrasts[
            "schema_vs_hashed_dense_provider_episode"
        ]["a_better"]
        == 10
        and contrasts["schema_vs_hashed_dense_provider_episode"]["b_better"] == 0,
        "bm25_beats_generic_13_1": contrasts["bm25_vs_generic_provider_episode"][
            "a_better"
        ]
        == 13
        and contrasts["bm25_vs_generic_provider_episode"]["b_better"] == 1,
        "hashed_dense_beats_generic_14_2": contrasts[
            "hashed_dense_vs_generic_provider_episode"
        ]["a_better"]
        == 14
        and contrasts["hashed_dense_vs_generic_provider_episode"]["b_better"] == 2,
        "low_pressure_schema_ties_raw_and_lexical": contrasts["low_pressure_schema_vs_raw"][
            "a_better"
        ]
        == 0
        and contrasts["low_pressure_schema_vs_raw"]["b_better"] == 0
        and contrasts["low_pressure_schema_vs_lexical"]["a_better"] == 0
        and contrasts["low_pressure_schema_vs_lexical"]["b_better"] == 0,
        "typed_surface_null_0_0": contrasts["typed_surface_vs_curated_prose"]["a_better"] == 0
        and contrasts["typed_surface_vs_curated_prose"]["b_better"] == 0,
        "weak_and_strong_curated_both_30_30": weak_curated_cost["correct"] == 30
        and weak_curated_cost["total"] == 30
        and strong_curated_cost["correct"] == 30
        and strong_curated_cost["total"] == 30,
        "phase9q_open_weight_subset_schema_beats_matched_6_0": contrasts[
            "phase9q_open_weight_schema_vs_matched"
        ]["a_better"]
        == 6
        and contrasts["phase9q_open_weight_schema_vs_matched"]["b_better"] == 0,
    }

    status = "PASS" if all(checks.values()) else "FAIL"

    return {
        "validated_at": datetime.now().isoformat(timespec="seconds"),
        "artifact_source": source_path.name if source_path else root.name,
        "artifact_sha256": sha256_file(source_path) if source_path and source_path.is_file() else None,
        "status": status,
        "validation_scope": "archived score reconstruction and artifact integrity, not revision approval",
        "scientific_review_status": "REVIEW_REQUIRED" if row_scoring["scientific_review_required"] else "NO_PROTOCOL_EXCLUSIONS",
        "row_scoring": {k: v for k, v in row_scoring.items() if k != "rows"},
        "token_accounting": accounting,
        "cross_family": cross_family,
        "missing_files": missing,
        "checks": checks,
        "leakage": leakage,
        "arm_totals": arm_totals,
        "contrasts": contrasts,
        "cost_proxy": {
            "weak_curated_state": weak_curated_cost,
            "strong_curated_state": strong_curated_cost,
            "strong_to_weak_token_ratio": cost_ratio,
        },
        "file_manifest": file_manifest,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    checks = report["checks"]
    contrasts = report["contrasts"]
    cost = report["cost_proxy"]
    current = report["row_scoring"]["table5"]["semantic_valid_only"]
    cross_family = report["cross_family"]
    accounting = report["token_accounting"]
    lines = [
        "# Structured-State Artifact Validation",
        "",
        f"Validated at: `{report['validated_at']}`",
        "",
        f"Status: `{report['status']}`",
        "",
        f"Scientific review status: `{report['scientific_review_status']}`. "
        "A reproducibility PASS confirms the checks below; it does not approve a manuscript or public release.",
        "",
        "## Current manuscript results: continuation comparisons",
        "",
        "The current valid-output analysis is shown first. Historical failure-as-incorrect results are in a separate section below.",
        "",
        "| Comparison | Counting unit | Comparable | A wins | B wins | Ties | One-sided p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    current_rows = [
        ("High pressure: schema-guided / matched free-form", "fixtures; correct-provider counts", current["high_pressure"]),
        ("High pressure: provider-level sensitivity", "provider-episode pairs", current["high_pressure_provider_sensitivity"]),
        ("Pressure-reduced: schema-guided / matched free-form", "provider-episode pairs", current["low_pressure"]),
        ("Pressure-reduced: schema-guided / raw log", "provider-episode pairs", contrasts["low_pressure_schema_vs_raw"]),
        ("Pressure-reduced: schema-guided / lexical retrieval", "provider-episode pairs", contrasts["low_pressure_schema_vs_lexical"]),
        ("Information-equivalent: typed protocol / curated prose", "provider-episode pairs", current["information_equivalent"]),
    ]
    for label, unit, value in current_rows:
        lines.append(
            f"| {label} | {unit} | {value['comparable']} | {value['a_better']} | "
            f"{value['b_better']} | {value['ties']} | {value['p_one_sided_a_gt_b']:.10g} |"
        )
    excluded_fixtures = current["high_pressure"]["excluded_units"]
    excluded_pairs = current["high_pressure_provider_sensitivity"]["excluded_units"]
    lines.extend([
        "",
        f"High-pressure fixture sensitivity excludes {len(excluded_fixtures)} affected fixture(s) from both arms: "
        + ", ".join(f"`{item}`" for item in excluded_fixtures) + ".",
        f"Provider-level sensitivity excludes {len(excluded_pairs)} failed pair(s): "
        + ", ".join(f"`{provider} / {episode}`" for provider, episode in excluded_pairs) + ".",
        "These are post-audit sensitivities. Provider outputs on one fixture are not independent fixture replications. "
        "The sign test conditions on discordant units; p=1 is the reporting convention when all pairs tie. "
        "Pressure-reduced results use the released protocol-repaired records; repair conditions are documented in REPRODUCE.md.",
        "",
        "## Current manuscript results: cross-family source audit",
        "",
        "Acceptance below uses the separate source-audit lexical scorer, not continuation correctness or verified vulnerability discovery. "
        "Counts are descriptive: two providers share each task and are not independent task replications.",
        "",
        "| Comparison | Eligibility | Counting unit | Comparable | A accepted | B accepted | A wins | B wins | Ties |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for policy, description in (
        ("final_response_eligible", "Valid final response; selected repairs retained"),
        ("end_to_end_eligible", "Valid final response and upstream handoff"),
    ):
        for name, label in (("schema_vs_matched", "Schema-guided / matched free-form"),
                            ("extended_vs_matched", "Extended schema / matched free-form")):
            value = cross_family["comparisons"][policy][name]
            n = value["comparable"]
            lines.append(
                f"| {label} | {description} | {value['unit']} | {n} | "
                f"{value['a_accepted']}/{n} | {value['b_accepted']}/{n} | "
                f"{value['a_better']} | {value['b_better']} | {value['ties']} |"
            )
    lines.extend([
        "",
        "No cross-family advantage was reproduced under these recorded criteria. "
        "The end-to-end view symmetrically excludes pairs affected by an upstream handoff failure. "
        "Selected repaired responses and retained original failures remain identifiable in the full JSON report.",
        "",
        "## Current manuscript results: recorded strong-token proxy",
        "",
        f"Accounting completeness: `{accounting['accounting_completeness']}`. "
        f"Call records: {accounting['total_call_records']}; reported usage: {accounting['raw_usage_records']}; "
        f"unrecorded usage: {accounting['unknown_usage_records']}.",
        "",
        "| Route | Correct final decisions | Finalizer parse failures | Recorded finalizer tokens | Recorded updater tokens | Recorded proxy | Updater calls with unrecorded usage | Runs with failed update |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for arm, label in (("weak_curated_state", "Weak/local curated handoff"),
                       ("strong_curated_state", "Strong-curated handoff")):
        tokens = accounting["arms"][arm]
        outcomes = cost[arm]
        lines.append(
            f"| {label} | {outcomes['correct']}/{outcomes['total']} | {outcomes['parse_failures']} | "
            f"{tokens['finalizer_tokens']} | {tokens['recorded_state_update_tokens']} | "
            f"{tokens['recorded_token_proxy']} | {tokens['unknown_usage_calls']} | "
            f"{tokens['runs_with_failed_state_update']} |"
        )
    strong = accounting["arms"]["strong_curated_state"]
    lines.extend([
        "",
        f"The strong-curated route has {strong['unknown_usage_calls']} failed updater calls with unrecorded usage "
        f"across {strong['runs_with_failed_state_update']} runs. Its finalizer parse failures are "
        f"{cost['strong_curated_state']['parse_failures']}; these are different stages and counts. "
        "Unrecorded updater usage remains null and is excluded from the recorded sum. "
        "Local/weak-model costs are outside this proxy.",
        "",
        "## Historical contrasts: failure-as-incorrect archival reconstruction",
        "",
        "The following reproduces the archived analysis, including its treatment of failed finalizers as incorrect. "
        "It is retained for traceability and is not the current valid-output sensitivity table above.",
        "",
        "| Archived contrast | Comparable | A wins | B wins | Ties | One-sided p |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for name, value in contrasts.items():
        comparable = value.get("comparable", value.get("comparable_fixtures"))
        lines.append(
            f"| `{name}` | {comparable} | {value['a_better']} | {value['b_better']} | "
            f"{value['ties']} | {value['p_one_sided_a_gt_b']:.10g} |"
        )
    lines.extend(["", "## Mechanical checks", "", "| Check | Result |", "|---|---|"])
    for name, value in checks.items():
        lines.append(f"| `{name}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Leakage Audit",
            "",
            f"Strict status: `{report['leakage']['strict_status']}`; strict zero: `{report['leakage']['strict_zero']}`.",
            "",
            f"Broad status: `{report['leakage']['broad_status']}`; blocking broad patterns zero: `{report['leakage']['broad_blocking_zero']}`.",
            "",
            "## Interpretation",
            "",
            "This check independently scores preserved response fields against fixture oracles and compares the results with archived verdicts. "
            "Current sensitivities, cross-family descriptive counts and unrecorded updater usage are displayed above; "
            "the adjacent artifact_validation_report.json retains their full machine-readable details. "
            "The archived leakage-count records are checked for completeness but this is not a fresh leakage scan. "
            "A PASS is not approval of manuscript claims or of a public release.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    # Render only the controlled headings, tables and paragraphs above. This is
    # not a general Markdown engine; every data value is escaped before HTML.
    from html import escape

    def display_text(value: str) -> str:
        parts = value.split("`")
        return "".join(
            f"<code>{escape(part)}</code>" if index % 2 else escape(part)
            for index, part in enumerate(parts)
        )

    body = []
    in_table = False
    for line in lines:
        if line.startswith("|"):
            if set(line) <= set("|-: "):
                continue
            tag = "td" if in_table else "th"
            if not in_table:
                body.append('<div class="table-scroll"><table>')
                in_table = True
            cells = line.strip("|").split("|")
            body.append("<tr>" + "".join(
                f"<{tag}>{display_text(cell.strip())}</{tag}>" for cell in cells
            ) + "</tr>")
            continue
        if in_table:
            body.append("</table></div>")
            in_table = False
        if not line:
            continue
        if line.startswith("## "):
            body.append(f"<h2>{display_text(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{display_text(line[2:])}</h1>")
        else:
            body.append(f"<p>{display_text(line)}</p>")
    if in_table:
        body.append("</table></div>")
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BGVD-State: Current Results and Validation</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
       color: #182230; background: #f5f7fa; margin: 0; line-height: 1.5; }
main { max-width: 1100px; margin: 24px auto; padding: 24px; background: white; }
h2 { margin-top: 2em; border-bottom: 1px solid #d8dee8; padding-bottom: .3em; }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .94em; }
th, td { border: 1px solid #d8dee8; padding: 9px; text-align: left; }
th { background: #eef2f6; } code { overflow-wrap: anywhere; }
</style></head><body><main>""" + "\n".join(body) + "</main></body></html>\n"
    path.with_suffix(".html").write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, help="Release-candidate ZIP or extracted directory")
    parser.add_argument("--out-dir", required=True, help="Directory for validation JSON/Markdown")
    args = parser.parse_args()

    artifact_path = Path(args.artifact).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    root, tmp = load_release_path(artifact_path)
    try:
        try:
            report = validate_artifact(root, artifact_path)
        except (UnscorableError, KeyError, TypeError, FileNotFoundError, ValueError) as exc:
            print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
            raise SystemExit(1) from exc
    finally:
        if tmp is not None:
            tmp.cleanup()

    json_path = out_dir / "artifact_validation_report.json"
    md_path = out_dir / "ARTIFACT_VALIDATION_REPORT.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
