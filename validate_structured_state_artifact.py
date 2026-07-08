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
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "README.md",
    "REPRODUCE.md",
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
        out[key] = row
    return out


def merge_indexes(*indexes: dict[tuple[str, str, str], dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for idx in indexes:
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
        if any(diff > 0 for diff in provider_diffs) and not any(diff < 0 for diff in provider_diffs):
            a_better += 1
        elif any(diff < 0 for diff in provider_diffs) and not any(diff > 0 for diff in provider_diffs):
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
        for key, value in summary.get("aggregate", {}).items():
            if key.endswith(f"::{arm}"):
                total += int(value.get("total", 0))
                correct += int(value.get("correct", 0))
                strong_tokens += int(value.get("strong_paid_tokens", 0))
                parse_failures += int(value.get("parse_failures", 0))
    return {
        "total": total,
        "correct": correct,
        "strong_paid_tokens": strong_tokens,
        "parse_failures": parse_failures,
    }


def summarize_aggregate(summary: dict[str, Any], arm: str) -> dict[str, int]:
    total = correct = parse_failures = 0
    direct = summary.get("aggregate", {}).get(arm)
    if isinstance(direct, dict):
        return {
            "total": int(direct.get("total", 0)),
            "correct": int(direct.get("correct", 0)),
            "parse_failures": int(direct.get("parse_failures", 0)),
        }
    for key, value in summary.get("aggregate", {}).items():
        if key.endswith(f"::{arm}"):
            total += int(value.get("total", 0))
            correct += int(value.get("correct", 0))
            parse_failures += int(value.get("parse_failures", 0))
    return {"total": total, "correct": correct, "parse_failures": parse_failures}


def leakage_status(root: Path) -> dict[str, Any]:
    strict = read_json(root, "LEAKAGE_AUDIT_STRICT_COUNTS.json")
    broad = read_json(root, "LEAKAGE_AUDIT_COUNTS.json")
    strict_counts = {item["pattern"]: int(item["count"]) for item in strict.get("pattern_counts", [])}
    broad_counts = {item["pattern"]: int(item["count"]) for item in broad.get("pattern_counts", [])}
    strict_zero = all(value == 0 for value in strict_counts.values())
    broad_blocking_zero = all(
        broad_counts.get(pattern, 0) == 0
        for pattern in ["api_key_like", "private_key", "url", "ipv4"]
    )
    return {
        "strict_status": strict.get("status"),
        "strict_zero": strict_zero,
        "strict_counts": strict_counts,
        "broad_status": broad.get("status"),
        "broad_blocking_zero": broad_blocking_zero,
        "broad_counts": broad_counts,
    }


def validate_artifact(root: Path, source_path: Path | None = None) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]

    v3e = read_json(root, "v3e_summary.json")
    v3i = read_json(root, "v3i_summary.json")
    v3j = read_json(root, "v3j_summary.json")
    v3k = read_json(root, "v3k_summary.json")
    phase9n = read_json(root, "phase9n_summary_protocol_repaired.json")
    phase9p = read_json(root, "phase9p_summary_protocol_repaired.json")
    phase9r = read_json(root, "phase9r_summary.json")
    phase9o = read_json(root, "phase9o_summary_protocol_repaired.json")
    phase9q = read_json(root, "phase9q_open_weight_summary.json")
    v3g_glm = read_json(root, "v3g_glm_summary.json")
    v3g_deepseek = read_json(root, "v3g_deepseek_summary.json")
    v3h_glm = read_json(root, "v3h_glm_summary.json")
    v3h_deepseek = read_json(root, "v3h_deepseek_summary.json")

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

    leakage = leakage_status(root)
    checks = {
        "required_files_present": not missing,
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
    lines = [
        "# Structured-State Artifact Validation",
        "",
        f"Validated at: `{report['validated_at']}`",
        "",
        f"Status: `{report['status']}`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for name, value in checks.items():
        lines.append(f"| `{name}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Recomputed Contrasts",
            "",
            "| Contrast | Comparable | A better | B better | Ties | One-sided p |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, value in contrasts.items():
        comparable = value.get("comparable", value.get("comparable_fixtures"))
        lines.append(
            "| `{}` | {} | {} | {} | {} | {:.10g} |".format(
                name,
                comparable,
                value["a_better"],
                value["b_better"],
                value["ties"],
                value["p_one_sided_a_gt_b"],
            )
        )
    lines.extend(
        [
            "",
            "## Strong Paid-Token Proxy",
            "",
            "| Arm | Correct/Total | Strong paid tokens | Parse failures |",
            "|---|---:|---:|---:|",
            "| Weak/local curated handoff | {}/{} | {} | {} |".format(
                cost["weak_curated_state"]["correct"],
                cost["weak_curated_state"]["total"],
                cost["weak_curated_state"]["strong_paid_tokens"],
                cost["weak_curated_state"]["parse_failures"],
            ),
            "| Strong-curated handoff | {}/{} | {} | {} |".format(
                cost["strong_curated_state"]["correct"],
                cost["strong_curated_state"]["total"],
                cost["strong_curated_state"]["strong_paid_tokens"],
                cost["strong_curated_state"]["parse_failures"],
            ),
            "",
            f"Observed strong-token ratio: `{cost['strong_to_weak_token_ratio']:.6f}`.",
            "",
            "## Leakage Audit",
            "",
            f"Strict status: `{report['leakage']['strict_status']}`; strict zero: `{report['leakage']['strict_zero']}`.",
            "",
            f"Broad status: `{report['leakage']['broad_status']}`; blocking broad patterns zero: `{report['leakage']['broad_blocking_zero']}`.",
            "",
            "## Interpretation",
            "",
            "This validation is an artifact reproducibility check. It confirms that the release candidate contains enough sanitized summary data to recompute the manuscript-level paired contrasts and leakage-audit status without external model calls. It does not replace public Zenodo/OSF/GitHub deposition.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


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
        report = validate_artifact(root, artifact_path)
    finally:
        if tmp is not None:
            tmp.cleanup()

    json_path = out_dir / "artifact_validation_report.json"
    md_path = out_dir / "ARTIFACT_VALIDATION_REPORT.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
