"""Post-audit retry exclusions; reuse the unchanged historical scoring rules.

This descriptive diagnostic is not a prespecified experiment or a new scorer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import score_cross_family as cross
import score_released_rows as continuation


def paired_counts(rows, left, right, excluded):
    groups = {}
    for row in rows:
        if row['arm'] not in (left, right):
            continue
        key = (row['provider'], row['episode'])
        group = groups.setdefault(key, {})
        if row['arm'] in group:
            raise ValueError('Duplicate paired row')
        group[row['arm']] = row['score']
    if not groups or not excluded <= groups.keys():
        raise ValueError('Empty population or unknown exclusion identity')
    wins = losses = ties = 0
    for key, group in groups.items():
        if set(group) != {left, right}:
            raise ValueError('Incomplete paired inventory')
        if key in excluded:
            continue
        a, b = group[left], group[right]
        if type(a) is not bool or type(b) is not bool:
            raise ValueError('Retained pair lacks valid semantic scores')
        wins += int(a and not b)
        losses += int(b and not a)
        ties += int(a == b)
    if wins + losses + ties == 0:
        raise ValueError('No retained pairs')
    return {'wins': wins, 'losses': losses, 'ties': ties,
            'pairs': wins + losses + ties, 'excluded_pairs': sorted(excluded)}


def analyze(root):
    name = 'phase9o_summary_protocol_repaired.json'
    summary = continuation.read_json(root / name)
    episodes = continuation.read_json(root / 'phase9o_episodes.redacted.json')
    oracle = {ep['name']: ep for ep in episodes}
    if len(oracle) != len(episodes):
        raise ValueError('Duplicate fixture oracle')
    rows = continuation.rows_from(summary)
    continuation.require_inventory(name, rows, oracle)
    scored = [{**r, 'score': continuation.score_released_row(oracle[r['episode']], r)
               ['semantic_correct']} for r in rows]
    retries = summary['protocol_repair']['retried_rows']
    if not isinstance(retries, list) or not retries:
        raise ValueError('Missing historical retry identity list')
    keys = {(r['provider'], r['episode'], r['arm']) for r in rows}
    retry_keys = [(r['provider'], r['episode'], r['arm']) for r in retries]
    if len(set(retry_keys)) != len(retry_keys) or not set(retry_keys) <= keys:
        raise ValueError('Duplicate or unknown retry identity')
    low = {}
    for control in (continuation.MATCHED_ARM, 'raw_running_log', 'rag_retrieval_memory'):
        excluded = {(p, ep) for p, ep, arm in retry_keys
                    if arm in (continuation.SCHEMA_ARM, control)}
        low[control] = paired_counts(scored, continuation.SCHEMA_ARM, control, excluded)

    bundle = cross.read_json(root / 'cross_family/source_audit_evidence.json')
    cross_rows, attempts = cross.validate_inventory(bundle)
    left, right = 'extended_source_schema_memory', continuation.MATCHED_ARM
    cross_scored = [{**r, 'episode': r['task_id'], 'score': r['accepted']}
                    for r in cross_rows]
    retry_pairs = {(r['provider'], r['task_id']) for r in cross_rows
                   if r['arm'] in (left, right) and attempts[r['attempt_id']].get('retry_of')}
    fallback_pairs = {(r['provider'], r['task_id']) for r in cross_rows
                      if r['arm'] in (left, right) and not r['end_to_end_eligible']}
    return {
        'scope': 'Post-audit descriptive sensitivity; no new model calls or superiority test',
        'rule': 'Symmetrically remove a pair from both arms if either selected arm was retried',
        'low_pressure': low,
        'cross_family_extended': {
            'exclude_retries': paired_counts(cross_scored, left, right, retry_pairs),
            'exclude_retries_and_handoff_fallback': paired_counts(
                cross_scored, left, right, retry_pairs | fallback_pairs)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, default=Path('protocol_sensitivity.json'))
    args = parser.parse_args()
    result = analyze(args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Post-audit sensitivity written: {args.output}')


if __name__ == '__main__':
    main()
