# Stale Verifier Example

This replay demonstrates that an earlier positive verifier cannot support
finalization after it is invalidated and superseded by a current negative
verifier result.

```bash
bgvd-state replay \
  --events examples/stale_verifier/events.json \
  --state-out examples/stale_verifier/state.json \
  --handoff-out examples/stale_verifier/handoff.json

bgvd-state gate \
  --state examples/stale_verifier/state.json \
  --candidate C_STALE
```

The gate command intentionally exits with status `2` because finalization is
rejected.

