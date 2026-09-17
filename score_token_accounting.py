#!/usr/bin/env python3
"""Recompute the recorded strong-token proxy from sanitized per-call usage.

No model calls or billing assumptions are made. Missing failed-call usage stays
unknown; the historical zero contribution is an accounting convention only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ARMS = ("weak_curated_state", "strong_curated_state")
PROVIDERS = ("glm", "deepseek")
BASE_USAGE_KEYS = {"prompt_tokens", "completion_tokens", "total_tokens"}
USAGE_KEYS = BASE_USAGE_KEYS | {
    "reasoning_tokens", "cached_prompt_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"
}
RECORD_KEYS = {
    "call_id", "arm", "provider", "episode", "stage", "round", "outcome",
    "usage_status", "usage", "recorded_proxy_tokens", "source_kind", "source_sha256",
}


class AccountingError(ValueError):
    """Required accounting evidence is missing, conflicting or malformed."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(path: Path) -> str:
    """Hash JSON content identically across Git LF/CRLF and formatting changes."""
    canonical = json.dumps(read_json(path), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def project_usage(raw: dict[str, Any]) -> dict[str, int]:
    """Whitelist numeric usage fields; never copy a raw response or free text."""
    projected = {key: raw[key] for key in BASE_USAGE_KEYS if key in raw}
    for key in ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens"):
        if key in raw:
            projected[key] = raw[key]
    for container, field, output in (
        ("completion_tokens_details", "reasoning_tokens", "reasoning_tokens"),
        ("prompt_tokens_details", "cached_tokens", "cached_prompt_tokens"),
    ):
        value = raw.get(container)
        if isinstance(value, dict) and field in value:
            projected[output] = value[field]
    validate_usage(projected)
    return projected


def validate_usage(usage: Any) -> None:
    if not isinstance(usage, dict) or not BASE_USAGE_KEYS <= set(usage) <= USAGE_KEYS:
        raise AccountingError("reported usage must have only whitelisted numeric token fields")
    if any(type(value) is not int or value < 0 for value in usage.values()):
        raise AccountingError("token counts must be nonnegative integers, not booleans")
    if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
        raise AccountingError("provider total_tokens disagrees with prompt + completion")
    for subfield, upper in (("reasoning_tokens", "completion_tokens"),
                           ("cached_prompt_tokens", "prompt_tokens"),
                           ("prompt_cache_hit_tokens", "prompt_tokens"),
                           ("prompt_cache_miss_tokens", "prompt_tokens")):
        if usage.get(subfield, 0) > usage[upper]:
            raise AccountingError(f"{subfield} exceeds its containing token count")


def call_id(arm: str, provider: str, episode: str, stage: str, number: int | None) -> str:
    suffix = "final" if number is None else f"round_{number:02d}"
    return f"{arm}::{provider}::{episode}::{stage}::{suffix}"


def accounting_sources(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    summaries = {}
    fixtures = {}
    for prefix, arm in (("v3g", ARMS[0]), ("v3h", ARMS[1])):
        episodes = read_json(root / f"{prefix}_episodes.redacted.json")
        mapped = {e["name"]: e for e in episodes}
        if len(mapped) != len(episodes) or len(mapped) != 15:
            raise AccountingError(f"{prefix}: expected 15 unique held-out fixtures")
        fixtures[arm] = mapped
        for provider in PROVIDERS:
            summaries[(arm, provider)] = read_json(root / f"{prefix}_{provider}_summary.json")
    if set(fixtures[ARMS[0]]) != set(fixtures[ARMS[1]]):
        raise AccountingError("curated routes do not use identical fixture IDs")
    return summaries, fixtures


def validate_records(root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    summaries, fixtures = accounting_sources(root)
    indexed = {}
    for row in records:
        if set(row) != RECORD_KEYS:
            raise AccountingError("call record has missing or non-whitelisted fields")
        if row["arm"] not in ARMS or row["provider"] not in PROVIDERS:
            raise AccountingError("unexpected arm or provider")
        if row["episode"] not in fixtures[row["arm"]]:
            raise AccountingError("unexpected fixture ID")
        stage, number = row["stage"], row["round"]
        if stage == "finalizer":
            if number is not None:
                raise AccountingError("finalizer round must be null")
        elif stage == "state_update":
            if row["arm"] != ARMS[1] or type(number) is not int or number < 1:
                raise AccountingError("invalid strong updater round")
        else:
            raise AccountingError("unrecognized call stage")
        identity = call_id(row["arm"], row["provider"], row["episode"], stage, number)
        if identity != row["call_id"] or identity in indexed:
            raise AccountingError("invalid or duplicate call identifier")
        if not isinstance(row["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"]):
            raise AccountingError("missing source content hash")
        if type(row["recorded_proxy_tokens"]) is not int or row["recorded_proxy_tokens"] < 0:
            raise AccountingError("recorded proxy must be a nonnegative integer")
        if row["outcome"] == "success":
            if row["usage_status"] != "reported" or row["source_kind"] != "raw_response":
                raise AccountingError("successful call must retain reported usage and raw source hash")
            validate_usage(row["usage"])
            if row["recorded_proxy_tokens"] != row["usage"]["total_tokens"]:
                raise AccountingError("proxy token contribution differs from reported usage")
        elif row["outcome"] == "schema_failure":
            if stage != "state_update" or row["usage_status"] != "unavailable":
                raise AccountingError("failed updater usage must be explicitly unavailable")
            if row["usage"] is not None or row["recorded_proxy_tokens"] != 0:
                raise AccountingError("unknown usage cannot be fabricated or interpreted as known zero")
            if row["source_kind"] != "failure_record":
                raise AccountingError("missing failure-record provenance")
        else:
            raise AccountingError("unrecognized outcome")
        indexed[identity] = row

    expected = set()
    for arm in ARMS:
        for provider in PROVIDERS:
            for episode, fixture in fixtures[arm].items():
                expected.add(call_id(arm, provider, episode, "finalizer", None))
                if arm == ARMS[1]:
                    for number in range(1, len(fixture["rounds"]) + 1):
                        expected.add(call_id(arm, provider, episode, "state_update", number))
    if set(indexed) != expected:
        raise AccountingError(
            f"incomplete or unexpected call inventory: missing={len(expected - set(indexed))}, "
            f"unexpected={len(set(indexed) - expected)}"
        )

    totals = {}
    runs = []
    for arm in ARMS:
        totals[arm] = {
            "runs": 0, "finalizer_calls": 0, "state_update_calls": 0,
            "reported_usage_calls": 0, "unknown_usage_calls": 0,
            "finalizer_tokens": 0, "recorded_state_update_tokens": 0,
            "recorded_token_proxy": 0, "runs_with_failed_state_update": 0,
        }
        for provider in PROVIDERS:
            summary = summaries[(arm, provider)]
            matching = [r for r in summary["rows"] if r["provider"] == provider and r["arm"] == arm]
            by_episode = {r["episode"]: r for r in matching}
            if len(matching) != 15 or set(by_episode) != set(fixtures[arm]):
                raise AccountingError("summary run inventory is incomplete or duplicated")
            for episode in sorted(fixtures[arm]):
                summary_row = by_episode[episode]
                final = indexed[call_id(arm, provider, episode, "finalizer", None)]
                updates = [r for r in records if r["arm"] == arm and r["provider"] == provider
                           and r["episode"] == episode and r["stage"] == "state_update"]
                failed = [r for r in updates if r["usage_status"] == "unavailable"]
                final_tokens = final["usage"]["total_tokens"]
                update_tokens = sum(r["usage"]["total_tokens"] for r in updates if r["usage"] is not None)
                if project_usage(summary_row["usage"]) != final["usage"]:
                    raise AccountingError("finalizer raw usage differs from released summary usage")
                if (summary_row["finalizer_tokens"] != final_tokens
                        or summary_row["state_update_tokens"] != update_tokens
                        or summary_row["strong_paid_tokens"] != final_tokens + update_tokens):
                    raise AccountingError("raw per-call sum differs from released summary token totals")
                if arm == ARMS[1]:
                    status = summary["strong_curated_status"][f"{provider}::{arm}::{episode}"]
                    expected_failed = {r["round"] for r in status["round_failures"]}
                    if expected_failed != {r["round"] for r in failed}:
                        raise AccountingError("per-call failures differ from released summary")
                    if status["rounds"] != len(updates) or status["state_update_tokens"] != update_tokens:
                        raise AccountingError("updater round inventory or sum differs from released status")
                item = totals[arm]
                item["runs"] += 1
                item["finalizer_calls"] += 1
                item["state_update_calls"] += len(updates)
                item["reported_usage_calls"] += 1 + len(updates) - len(failed)
                item["unknown_usage_calls"] += len(failed)
                item["finalizer_tokens"] += final_tokens
                item["recorded_state_update_tokens"] += update_tokens
                item["recorded_token_proxy"] += final_tokens + update_tokens
                item["runs_with_failed_state_update"] += bool(failed)
                runs.append({"arm": arm, "provider": provider, "episode": episode,
                             "finalizer_tokens": final_tokens, "state_update_tokens": update_tokens,
                             "unknown_usage_rounds": [r["round"] for r in failed]})
    return {
        "status": "PASS", "scope": "recorded token proxy reconstructed from sanitized per-call usage",
        "accounting_completeness": "OBSERVED_USAGE_ONLY",
        "total_call_records": len(records),
        "raw_usage_records": sum(r["usage_status"] == "reported" for r in records),
        "unknown_usage_records": sum(r["usage_status"] == "unavailable" for r in records),
        "arms": totals, "runs": runs,
        "limitations": [
            "Unknown usage for 14 failed updater calls remains null; zero is only their historical proxy contribution.",
            "The strong-route proxy is a recorded-token lower bound, not complete billed usage or monetary cost.",
            "Local/weak-model tokens, runtime, hardware, pricing and cache discounts are outside this proxy.",
            "Per-call source hashes preserve provenance, but raw content is not published with this sanitized projection.",
        ],
    }


def validate_accounting(root: Path) -> dict[str, Any]:
    folder = root / "token_accounting"
    manifest = read_json(folder / "origin_manifest.json")
    if manifest.get("schema_version") != "bgvd.token_accounting.origins.v1":
        raise AccountingError("unsupported origin manifest schema")
    if manifest.get("checksum_algorithm") != "canonical-json-utf8-sorted-compact-v1":
        raise AccountingError("unsupported accounting checksum algorithm")
    if manifest.get("records_canonical_sha256") != canonical_json_sha256(folder / "calls.json"):
        raise AccountingError("per-call accounting data checksum mismatch")
    document = read_json(folder / "calls.json")
    if document.get("schema_version") != "bgvd.token_accounting.calls.v1":
        raise AccountingError("unsupported per-call schema")
    runs = manifest.get("source_runs", [])
    expected_runs = {f"{prefix}_{provider}" for prefix in ("v3g", "v3h") for provider in PROVIDERS}
    if len(runs) != 4 or {r["dataset_id"] for r in runs} != expected_runs:
        raise AccountingError("expected four original source runs")
    for item in runs:
        if item["released_summary_file"] != f"{item['dataset_id']}_summary.json":
            raise AccountingError("origin manifest has an unexpected summary filename")
        if canonical_json_sha256(root / item["released_summary_file"]) != item["released_summary_canonical_sha256"]:
            raise AccountingError("released summary content changed after accounting extraction")
    expected_fixtures = {"v3g_episodes.redacted.json", "v3h_episodes.redacted.json"}
    if set(manifest.get("fixture_canonical_sha256", {})) != expected_fixtures:
        raise AccountingError("fixture hash inventory is incomplete")
    for filename, digest in manifest["fixture_canonical_sha256"].items():
        if canonical_json_sha256(root / filename) != digest:
            raise AccountingError("fixture content changed after accounting extraction")
    report = validate_records(root, document["records"])
    report["data_canonical_sha256"] = manifest["records_canonical_sha256"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    try:
        report = validate_accounting(args.artifact.resolve())
    except (AccountingError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        report = {"status": "FAIL", "error": str(exc)}
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "token_accounting_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "runs"}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
