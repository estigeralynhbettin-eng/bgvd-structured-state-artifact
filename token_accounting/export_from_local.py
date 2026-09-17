#!/usr/bin/env python3
"""Build the whitelist-only usage projection from four existing local runs.

Authors only: supplying source directories reads archived outputs, never calls
models. Reviewers can use score_token_accounting.py on the projected data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from score_token_accounting import (  # noqa: E402
    AccountingError, call_id, canonical_json_sha256, project_usage, read_json, sha256, validate_records,
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract(root: Path, dirs: dict[tuple[str, str], Path]) -> dict[str, object]:
    records = []
    origins = []
    for (prefix, provider), source in sorted(dirs.items()):
        arm = "weak_curated_state" if prefix == "v3g" else "strong_curated_state"
        source_summary = source / "summary.json"
        summary = read_json(source_summary)
        released_name = f"{prefix}_{provider}_summary.json"
        released = read_json(root / released_name)
        local_rows = [r for r in summary["rows"] if r["provider"] == provider and r["arm"] == arm]
        public_rows = [r for r in released["rows"] if r["provider"] == provider and r["arm"] == arm]
        if len(local_rows) != 15 or len(public_rows) != 15:
            raise AccountingError("expected 15 held-out rows in each source dataset")
        public_index = {r["episode"]: r for r in public_rows}
        origins.append({"dataset_id": f"{prefix}_{provider}",
                        "source_summary_sha256": sha256(source_summary),
                        "released_summary_file": released_name,
                        "released_summary_canonical_sha256": canonical_json_sha256(root / released_name)})
        for row in local_rows:
            episode = row["episode"]
            public = public_index[episode]
            for field in ("state_update_tokens", "finalizer_tokens", "strong_paid_tokens",
                          "state_update_ok", "parse_ok", "usage"):
                if row[field] != public[field]:
                    raise AccountingError(f"local/public accounting field differs: {field}")
            final_dir = source / provider / arm / episode
            final_raw = final_dir / "raw_response.json"
            if not (final_dir / "parsed.json").is_file() or not row["parse_ok"]:
                raise AccountingError("selected finalizer has no successful parsed/raw evidence")
            raw = read_json(final_raw)
            usage = project_usage(raw["usage"])
            if usage != project_usage(public["usage"]):
                raise AccountingError("finalizer raw usage differs from public row")
            records.append({
                "call_id": call_id(arm, provider, episode, "finalizer", None),
                "arm": arm, "provider": provider, "episode": episode,
                "stage": "finalizer", "round": None, "outcome": "success",
                "usage_status": "reported", "usage": usage,
                "recorded_proxy_tokens": usage["total_tokens"],
                "source_kind": "raw_response", "source_sha256": sha256(final_raw),
            })
            if prefix == "v3g":
                continue
            key = f"{provider}::{arm}::{episode}"
            status = summary["strong_curated_status"][key]
            if status != released["strong_curated_status"][key]:
                raise AccountingError("local/public strong-curated statuses differ")
            failures = {r["round"]: r for r in status["round_failures"]}
            updates_root = source / provider / "strong_curated_state_updates" / episode
            for number in range(1, status["rounds"] + 1):
                directory = updates_root / f"round_{number:02d}"
                raw_path = directory / "raw_response.json"
                failure_path = directory / "failure.txt"
                base = {"call_id": call_id(arm, provider, episode, "state_update", number),
                        "arm": arm, "provider": provider, "episode": episode,
                        "stage": "state_update", "round": number}
                if number in failures:
                    if raw_path.exists() or not failure_path.is_file():
                        raise AccountingError("failed-call raw/failure evidence conflicts with summary")
                    failure = failures[number]
                    if failure["failure_type"] != "schema_failure" or failure["tokens"] != 0:
                        raise AccountingError("unrecognized failed-call accounting convention")
                    base.update(outcome="schema_failure", usage_status="unavailable", usage=None,
                                recorded_proxy_tokens=0, source_kind="failure_record",
                                source_sha256=sha256(failure_path))
                else:
                    if failure_path.exists() or not (directory / "parsed_state.json").is_file():
                        raise AccountingError("successful updater has inconsistent parse evidence")
                    usage = project_usage(read_json(raw_path)["usage"])
                    base.update(outcome="success", usage_status="reported", usage=usage,
                                recorded_proxy_tokens=usage["total_tokens"],
                                source_kind="raw_response", source_sha256=sha256(raw_path))
                records.append(base)
    records.sort(key=lambda r: r["call_id"])
    report = validate_records(root, records)
    folder = root / "token_accounting"
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "calls.json", {"schema_version": "bgvd.token_accounting.calls.v1",
                                        "records": records})
    write_json(folder / "origin_manifest.json", {
        "schema_version": "bgvd.token_accounting.origins.v1",
        "checksum_algorithm": "canonical-json-utf8-sorted-compact-v1",
        "records_canonical_sha256": canonical_json_sha256(folder / "calls.json"),
        "exporter_sha256": sha256(Path(__file__).resolve()),
        "source_runs": origins,
        "fixture_canonical_sha256": {name: canonical_json_sha256(root / name) for name in
                                     ("v3g_episodes.redacted.json", "v3h_episodes.redacted.json")},
        "projection": "Only call identities, numeric usage, statuses and source hashes; no prompts or raw response text.",
    })
    return {k: v for k, v in report.items() if k != "runs"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=ROOT)
    parser.add_argument("--weak-glm", type=Path, required=True)
    parser.add_argument("--weak-deepseek", type=Path, required=True)
    parser.add_argument("--strong-glm", type=Path, required=True)
    parser.add_argument("--strong-deepseek", type=Path, required=True)
    args = parser.parse_args()
    report = extract(args.artifact, {
        ("v3g", "glm"): args.weak_glm, ("v3g", "deepseek"): args.weak_deepseek,
        ("v3h", "glm"): args.strong_glm, ("v3h", "deepseek"): args.strong_deepseek,
    })
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
