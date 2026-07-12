# Candidate Replacement Example

This defensive replay contains no target address, payload, credential, or
operational exploit instruction. It demonstrates that evidence for `C_OLD`
cannot be reused after invalidation and that only `C_CURRENT` is finalizable.

```bash
bgvd-state replay \
  --events examples/candidate_replacement/events.json \
  --state-out examples/candidate_replacement/state.json \
  --handoff-out examples/candidate_replacement/handoff.json

bgvd-state gate \
  --state examples/candidate_replacement/state.json \
  --candidate C_CURRENT
```

