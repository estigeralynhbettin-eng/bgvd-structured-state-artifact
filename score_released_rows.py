#!/usr/bin/env python3
"""Recompute released response scores from fixture oracles, without model calls.

The decision rule is the historical ``score_final`` in
``scripts/run_phase9i_v3_replayed_tool_loop.py`` (lines 495-542), not a rule
inferred from the stored ``correct`` labels. Published summary rows preserve
the response's decision, selected candidate and supporting references. The
fixture supplies the independent expected decision/candidate/current/stale refs.

This re-scores those preserved response fields; it cannot independently repeat
the original raw-text-to-JSON parsing, because raw responses are not released.
Protocol-failure records are excluded from semantic scoring. Their historical
False verdict is reproduced only in the explicitly labelled archival view.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SOURCES = {
    "v3e_summary.json": "v3e_episodes.redacted.json",
    "v3i_summary.json": "v3i_episodes.redacted.json",
    "v3j_summary.json": "v3j_episodes.redacted.json",
    "v3k_summary.json": "v3k_episodes.redacted.json",
    "phase9n_summary_protocol_repaired.json": "phase9n_episodes.redacted.json",
    "phase9p_summary_protocol_repaired.json": "phase9p_episodes.redacted.json",
    "phase9r_summary.json": "phase9r_episodes.redacted.json",
    "phase9o_summary_protocol_repaired.json": "phase9o_episodes.redacted.json",
    "phase9q_open_weight_summary.json": "v3i_episodes.redacted.json",
    "v3g_glm_summary.json": "v3g_episodes.redacted.json",
    "v3g_deepseek_summary.json": "v3g_episodes.redacted.json",
    "v3h_glm_summary.json": "v3h_episodes.redacted.json",
    "v3h_deepseek_summary.json": "v3h_episodes.redacted.json",
}
PRESSURE_SOURCES = tuple(SOURCES)[:7]
SCHEMA_ARM = "schema_guided_weak_memory"
MATCHED_ARM = "matched_freeform_weak_memory"
EXPECTED_ARMS = {
    "v3e_summary.json": {"raw_running_log", "typed_protocol_state", "untyped_curated_state",
                         "untyped_weak_mistral_7b", "untyped_weak_qwen25_coder_7b", "untyped_weak_qwen35_9b"},
    "v3i_summary.json": {SCHEMA_ARM},
    "v3j_summary.json": {MATCHED_ARM},
    "v3k_summary.json": {"generic_structured_memory"},
    "phase9n_summary_protocol_repaired.json": {"rag_retrieval_memory"},
    "phase9p_summary_protocol_repaired.json": {"bm25_retrieval_memory"},
    "phase9r_summary.json": {"hashed_dense_retrieval_memory"},
    "phase9o_summary_protocol_repaired.json": {SCHEMA_ARM, MATCHED_ARM,
        "generic_structured_memory", "rag_retrieval_memory", "raw_running_log"},
    "phase9q_open_weight_summary.json": {SCHEMA_ARM, MATCHED_ARM},
}
for _provider in ("glm", "deepseek"):
    EXPECTED_ARMS[f"v3g_{_provider}_summary.json"] = {
        "all_strong_state", "raw_running_log", "weak_curated_state", "weak_raw_qwen35_state"}
    EXPECTED_ARMS[f"v3h_{_provider}_summary.json"] = {"strong_curated_state"}


class UnscorableError(ValueError):
    """The released evidence is incomplete or structurally invalid."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows_from(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = summary.get("rows", summary.get("new_rows"))
    if not isinstance(rows, list):
        raise UnscorableError("summary must contain rows or new_rows list")
    return rows


def ref_set(record: dict[str, Any], name: str) -> set[str]:
    if name not in record or not isinstance(record[name], list):
        raise UnscorableError(f"{name} must be a present list")
    if any(not isinstance(x, str) for x in record[name]):
        raise UnscorableError(f"{name} must contain strings")
    return set(record[name])


def score_response(episode: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Historical semantic rule; never read a stored verdict or citation flag.

    For a finalizable fixture: finalize, select the expected candidate, cite at
    least one current material AND verifier reference, and cite no stale ref in
    those support fields. Extra non-stale refs were not penalized historically.
    For a non-finalizable fixture: either continue or reject is correct. Merely
    mentioning a stale ref as rejected/noted evidence is not unsafe reliance.
    """
    expected = episode.get("expected_decision")
    if expected not in {"finalize", "continue", "reject"}:
        raise UnscorableError("fixture expected_decision is missing or unsupported")
    if "expected_candidate" not in episode:
        raise UnscorableError("fixture expected_candidate is missing")
    expected_candidate = episode["expected_candidate"]
    if expected == "finalize" and not isinstance(expected_candidate, str):
        raise UnscorableError("finalizable fixture requires expected_candidate")
    expected_material = ref_set(episode, "current_material_refs")
    expected_verifier = ref_set(episode, "current_verifier_refs")
    stale = ref_set(episode, "stale_refs")
    if expected == "finalize" and (not expected_material or not expected_verifier):
        raise UnscorableError("finalizable fixture lacks current supporting refs")
    if not isinstance(response.get("decision"), str):
        raise UnscorableError("response decision is missing or is not a string")
    if "selected_candidate" not in response:
        raise UnscorableError("response selected_candidate is missing")
    decision = response["decision"].lower()
    material = ref_set(response, "material_refs")
    verifier = ref_set(response, "verifier_refs")
    stale_support = stale & (material | verifier)
    unsafe = decision == "finalize" and bool(stale_support)
    material_cited = bool(expected_material & material)
    verifier_cited = bool(expected_verifier & verifier)
    if expected == "finalize":
        correct = (
            decision == "finalize"
            and response["selected_candidate"] == expected_candidate
            and material_cited
            and verifier_cited
            and not unsafe
        )
    else:
        correct = decision in {"continue", "reject"}
    return {
        "correct": correct,
        "false_finalize": expected != "finalize" and decision == "finalize",
        "wrong_candidate": expected == "finalize" and decision == "finalize"
        and response["selected_candidate"] != expected_candidate,
        "stale_or_superseded_misuse": unsafe,
        "stale_refs_in_support_fields": sorted(stale_support),
        "material_cited": material_cited if expected == "finalize" else None,
        "verifier_cited": verifier_cited if expected == "finalize" else None,
        "unsupported_decision": decision not in {"finalize", "continue", "reject"},
        "candidate_schema_warning": response["selected_candidate"] is not None
        and not isinstance(response["selected_candidate"], str),
    }


def score_released_row(episode: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    if type(row.get("parse_ok")) is not bool:
        raise UnscorableError("row parse_ok must be an explicit boolean")
    if not row["parse_ok"]:
        failure = row.get("provider_failure_type")
        if not isinstance(failure, str) or not failure or failure == "ok":
            raise UnscorableError("protocol failure must have a failure type")
        return {
            "status": "PROTOCOL_FAILURE",
            "semantic_eligible": False,
            "semantic_correct": None,
            "historical_correct": False,
            "failure_type": failure,
        }
    if row.get("provider_failure_type") != "ok":
        raise UnscorableError("parse_ok row has inconsistent provider_failure_type")
    for name in ("expected_decision", "expected_candidate"):
        if name in row and row[name] != episode.get(name):
            raise UnscorableError(f"row {name} disagrees with independent fixture oracle")
    scored = score_response(episode, row)
    return {
        "status": "SCORED",
        "semantic_eligible": True,
        "semantic_correct": scored["correct"],
        "historical_correct": scored["correct"],
        "details": scored,
    }


def index_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    result = {}
    for row in rows:
        key = tuple(row[name] for name in ("provider", "episode", "arm"))
        if key in result:
            raise UnscorableError(f"duplicate provider/episode/arm: {key}")
        result[key] = row
    return result


def require_inventory(name: str, rows: list[dict[str, Any]], oracle: dict[str, Any]) -> None:
    """Reject missing arms, providers, fixtures and duplicate/partial row grids."""
    expected_providers = {"glm", "deepseek"}
    if name.startswith(("v3g_", "v3h_")):
        expected_providers = {name.split("_")[1]}
        count = 15
    elif name == "phase9o_summary_protocol_repaired.json":
        count = 8
    elif name == "phase9q_open_weight_summary.json":
        expected_providers = {"ollama_chat"}
        count = 10
    else:
        count = 30
    indexed = index_rows(rows)
    episodes = {r["episode"] for r in rows}
    if len(episodes) != count:
        raise UnscorableError(f"{name}: expected {count} fixtures, got {len(episodes)}")
    if name != "phase9q_open_weight_summary.json" and episodes != set(oracle):
        raise UnscorableError(f"{name}: row fixture inventory differs from oracle file")
    if not episodes <= set(oracle):
        raise UnscorableError(f"{name}: unknown fixture in rows")
    expected = {(p, ep, a) for p in expected_providers for ep in episodes for a in EXPECTED_ARMS[name]}
    if set(indexed) != expected:
        raise UnscorableError(
            f"{name}: incomplete or unexpected provider/fixture/arm grid "
            f"(missing={len(expected - set(indexed))}, unexpected={len(set(indexed) - expected)})"
        )


def contrast(
    rows: list[dict[str, Any]], arm_a: str, arm_b: str,
    *, fixture_level: bool = False, semantic_only: bool = False,
) -> dict[str, Any]:
    """Compare paired verdicts; require matching provider sets within fixtures.

    At fixture level the historical analysis compares the NUMBER of correct
    providers, rather than treating two outputs on one fixture as independent.
    Semantic sensitivity excludes an entire fixture if either arm has any
    protocol-failed finalizer there, preserving identical provider counts.
    """
    indexed = index_rows(rows)
    a_keys = {(p, ep) for p, ep, arm in indexed if arm == arm_a}
    b_keys = {(p, ep) for p, ep, arm in indexed if arm == arm_b}
    if a_keys != b_keys:
        raise UnscorableError("unpaired rows; refusing a silently reduced denominator")
    wins = losses = ties = 0
    excluded = []
    if fixture_level:
        units = sorted({ep for _, ep in a_keys})
    else:
        units = sorted(a_keys)
    for unit in units:
        pairs = sorted((p, ep) for p, ep in a_keys if ep == unit) if fixture_level else [unit]
        left = [indexed[(p, ep, arm_a)] for p, ep in pairs]
        right = [indexed[(p, ep, arm_b)] for p, ep in pairs]
        if semantic_only and not all(r["semantic_eligible"] for r in left + right):
            excluded.append(unit)
            continue
        diff = sum(r["correct"] for r in left) - sum(r["correct"] for r in right)
        wins += diff > 0
        losses += diff < 0
        ties += diff == 0
    discordant = wins + losses
    p = sum(math.comb(discordant, k) for k in range(wins, discordant + 1)) / 2**discordant
    return {
        "unit": "fixture_correct_provider_count" if fixture_level else "provider_episode_pair",
        "policy": "exclude_protocol_failures" if semantic_only else "historical_failure_as_incorrect",
        "comparable": wins + losses + ties,
        "a_better": wins, "b_better": losses, "ties": ties,
        "p_one_sided_a_gt_b": p,
        "excluded_units": excluded,
    }


def usage_total(usage: dict[str, Any]) -> int:
    for name in ("total_tokens", "total_token_count"):
        value = usage.get(name)
        if type(value) is int and value >= 0:
            return value
    if "prompt_eval_count" in usage and "eval_count" in usage:
        return int(usage["prompt_eval_count"]) + int(usage["eval_count"])
    raise UnscorableError("successful finalizer is missing token usage")


def token_audit(summaries: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for prefix, arm in (("v3g", "weak_curated_state"), ("v3h", "strong_curated_state")):
        total = correct = finalizer = updates = affected = failed_calls = 0
        inconsistencies = []
        for provider in ("glm", "deepseek"):
            name = f"{prefix}_{provider}_summary.json"
            summary = summaries[name]
            for row in rows_from(summary):
                if row["arm"] != arm:
                    continue
                total += 1
                correct += row["correct"]
                ft = usage_total(row["usage"])
                st = row["state_update_tokens"]
                if type(st) is not int or st < 0:
                    raise UnscorableError("state_update_tokens must be a nonnegative integer")
                finalizer += ft
                updates += st
                if ft != row["finalizer_tokens"] or ft + st != row["strong_paid_tokens"]:
                    inconsistencies.append({"source": name, "episode": row["episode"]})
                if prefix == "v3h":
                    key = f"{provider}::{arm}::{row['episode']}"
                    state = summary["strong_curated_status"][key]
                    if st != state["state_update_tokens"]:
                        inconsistencies.append({"source": name, "state_trace_key": key})
                    failures = state["round_failures"]
                    affected += bool(failures)
                    failed_calls += len(failures)
        result[arm] = {
            "total": total, "correct": correct,
            "finalizer_tokens_from_usage": finalizer,
            "state_update_tokens_recorded": updates,
            "recorded_strong_token_proxy": finalizer + updates,
            "runs_with_failed_state_update": affected,
            "failed_state_update_calls": failed_calls,
            "inconsistencies": inconsistencies,
        }
    result["definition"] = (
        "Sum of recorded total tokens of paid strong-model finalizers and paid "
        "strong-model state-update calls, across 15 fixtures x 2 providers per route. "
        "Weak/local-model tokens, monetary pricing/cache discounts and runtime are excluded. "
        "Failed updater calls recorded zero when usage was not captured; this is not total billing."
    )
    result["scope_limit"] = (
        "Finalizer token counts are recomputed from released usage objects; state-update "
        "counts here are reconciled to released episode summaries. The companion "
        "score_token_accounting.py independently reconstructs them from sanitized "
        "per-call usage in token_accounting/. Failed-call usage remains unknown."
    )
    return result


def aggregate_audit(name: str, summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Check own-arm aggregates against re-scored rows, not inherited older arms."""
    failures = []
    rows = rows_from(summary)
    groups = {(r["provider"], r["arm"]) for r in rows}
    for provider, arm in sorted(groups):
        selected = [r for r in rows if r["provider"] == provider and r["arm"] == arm]
        key = f"{provider}::{arm}"
        aggregate = summary["aggregate"].get(key, summary["aggregate"].get(arm))
        if not isinstance(aggregate, dict):
            failures.append({"source": name, "aggregate": key, "error": "missing aggregate"})
            continue
        computed = {
            "total": len(selected), "correct": sum(r["correct"] for r in selected),
            "parse_failures": sum(not r["parse_ok"] for r in selected),
            "state_update_failures": sum(r.get("state_update_ok") is False for r in selected),
        }
        for field in ("false_finalize", "wrong_candidate", "stale_or_superseded_misuse",
                      "material_cited", "verifier_cited"):
            computed[field] = sum(r.get(field) is True for r in selected)
        if "accuracy" in aggregate:
            computed["accuracy"] = computed["correct"] / computed["total"]
        for field, value in computed.items():
            if field in aggregate and aggregate[field] != value:
                failures.append({"source": name, "aggregate": key, "field": field,
                                 "stored": aggregate[field], "recomputed": value})
    return failures


def rescore_release(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    rescored = {}
    evidence = []
    mismatches = []
    failures = []
    aggregate_mismatches = []
    source_manifest = []
    scored_count = 0
    for name, fixture_name in SOURCES.items():
        summary = read_json(root / name)
        episodes = read_json(root / fixture_name)
        oracle = {ep["name"]: ep for ep in episodes}
        if len(oracle) != len(episodes):
            raise UnscorableError(f"{fixture_name}: duplicate episode names")
        copied = copy.deepcopy(summary)
        rows = rows_from(copied)
        require_inventory(name, rows, oracle)
        for i, row in enumerate(rows):
            loc = {"source": name, "row_index": i, "provider": row["provider"],
                   "episode": row["episode"], "arm": row["arm"]}
            if row["episode"] not in oracle:
                raise UnscorableError(f"{loc}: no independent fixture oracle")
            score = score_released_row(oracle[row["episode"]], row)
            if score["status"] == "SCORED":
                scored_count += 1
                for field, recomputed in score["details"].items():
                    if field in {"unsupported_decision", "candidate_schema_warning"}:
                        continue
                    if field not in row or row[field] != recomputed:
                        mismatches.append({**loc, "field": field,
                                           "stored": row.get(field), "recomputed": recomputed})
            else:
                failures.append({**loc, "failure_type": score["failure_type"]})
                if row.get("correct") is not False:
                    mismatches.append({**loc, "field": "correct", "stored": row.get("correct"),
                                       "recomputed": False})
            row["correct"] = score["historical_correct"]
            if "details" in score:
                row.update({k: v for k, v in score["details"].items()
                            if k not in {"unsupported_decision", "candidate_schema_warning"}})
            row["semantic_eligible"] = score["semantic_eligible"]
            evidence.append({**loc, "fixture_source": fixture_name,
                             "stored_correct": rows_from(summary)[i].get("correct"), **score})
        rescored[name] = copied
        aggregate_mismatches.extend(aggregate_audit(name, copied))
    for name in sorted(set(SOURCES) | set(SOURCES.values())):
        source_manifest.append({"file": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()})
    pressure = [row for name in PRESSURE_SOURCES for row in rows_from(rescored[name])]
    low_pressure = rows_from(rescored["phase9o_summary_protocol_repaired.json"])
    table5 = {}
    for semantic in (False, True):
        view = "semantic_valid_only" if semantic else "historical_replication"
        table5[view] = {
            "high_pressure": contrast(pressure, SCHEMA_ARM, MATCHED_ARM,
                                      fixture_level=True, semantic_only=semantic),
            "high_pressure_provider_sensitivity": contrast(pressure, SCHEMA_ARM, MATCHED_ARM,
                                                           semantic_only=semantic),
            "low_pressure": contrast(low_pressure, SCHEMA_ARM, MATCHED_ARM,
                                     semantic_only=semantic),
            "information_equivalent": contrast(pressure, "typed_protocol_state",
                                               "untyped_curated_state", semantic_only=semantic),
        }
    tokens = token_audit(rescored)
    tokens_consistent = all(not tokens[arm]["inconsistencies"]
                            for arm in ("weak_curated_state", "strong_curated_state"))
    return rescored, {
        "status": "PASS" if not mismatches and not aggregate_mismatches and tokens_consistent else "FAIL",
        "scope": "reconstruct archived scores from released response fields and independent fixture oracles",
        "semantic_rows_recomputed": scored_count,
        "protocol_failure_rows": failures,
        "stored_verdict_or_auxiliary_mismatches": mismatches,
        "own_arm_aggregate_mismatches": aggregate_mismatches,
        "response_schema_warnings": [
            {key: r[key] for key in ("source", "row_index", "provider", "episode", "arm")}
            for r in evidence if r.get("details", {}).get("candidate_schema_warning")
            or r.get("details", {}).get("unsupported_decision")
        ],
        "table5": table5,
        "token_proxy": tokens,
        "scientific_review_required": bool(table5["semantic_valid_only"]["high_pressure"]["excluded_units"]),
        "limitations": [
            "Raw model responses are not included; raw-text parsing is not revalidated.",
            "The scorer verifies oracle adherence, not the external truth of the fixture labels.",
            "Historical replication retains old failure-as-incorrect treatment for traceability only.",
        ],
        "source_manifest": source_manifest,
        "rows": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=Path(__file__).resolve().parent)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--out", type=Path)
    output.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    if args.out_dir:
        args.out = args.out_dir / "row_scoring_report.json"
    try:
        _, report = rescore_release(args.artifact)
    except (UnscorableError, KeyError, TypeError, FileNotFoundError) as exc:
        report = {"status": "FAIL", "error": str(exc)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"rows", "source_manifest"}}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
