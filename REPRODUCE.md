# Reproduction Notes

Date: 2026-07-09

## Validate the Release Artifact

The release candidate includes an offline validator. It performs no model calls,
starts no containers, and reads only the sanitized files in this artifact. From
an extracted artifact directory, run with Python 3.10 or newer:

```bash
python validate_structured_state_artifact.py --artifact . --out-dir artifact_validation_output
```

On the authors' Windows workstation, the same check can be run with the local
UTF-8 wrapper:

```powershell
<PYTHON_UTF8_WRAPPER> .\validate_structured_state_artifact.py --artifact . --out-dir .\artifact_validation_output
```

From a full BGVD project checkout, validation can also be run against the ZIP:

```powershell
<PYTHON_UTF8_WRAPPER> .\scripts\validate_structured_state_artifact.py --artifact .\outputs\paper_evidence\structured_state_interface_20260708\BGVD_structured_state_interface_artifact_release_candidate_20260709.zip --out-dir .\outputs\artifact_validation\structured_state_interface_20260709_phase9r_zip_validation
```

Expected current validation status:

- `PASS`;
- required files present;
- strict leakage audit passes with zero strict secret-shape matches;
- schema-guided weak memory vs matched free-form memory: provider-episode `12:0`, fixture-level `7:0`;
- schema-guided weak memory vs generic structured memory: `22:0`;
- schema-guided weak memory vs simple lexical event retrieval: `10:0`;
- schema-guided weak memory vs BM25-style event retrieval: `10:0`;
- schema-guided weak memory vs hashed dense-vector event retrieval: `10:0`;
- BM25-style event retrieval vs generic structured memory: `13:1`;
- hashed dense-vector event retrieval vs generic structured memory: `14:2`;
- Phase9q targeted open-weight finalizer subset schema vs matched free-form: `6:0`;
- low-pressure schema vs raw logs and lexical retrieval: `0:0` with 16 ties;
- typed protocol surface vs curated prose: `0:0` with 60 ties;
- weak/local curated handoff and strong-curated handoff both reach `30/30`, with `24,391` versus `146,855` strong paid-token proxy.

## Regenerate Figures

The following steps require the full BGVD project checkout, not only this
sanitized fixture ZIP. They are not needed for artifact-level validation.

From the project root:

```powershell
<PYTHON_UTF8_WRAPPER> .\scripts\build_structured_state_interface_figures.py
```

Outputs:

- `<BGVD_PROJECT_ROOT>\manuscript\structured_state_interface_20260708\figures\fig_structured_interface_accuracy.pdf`
- `<BGVD_PROJECT_ROOT>\manuscript\structured_state_interface_20260708\figures\fig_structured_interface_contrasts.pdf`

These figures are generated from:

`<BGVD_PROJECT_ROOT>\outputs\phase9i_verifier_handoff\phase9i_v3k_generic_structured_baseline_20260708_121052\summary.json`

The release-candidate copy is:

`v3k_summary.json`

The figure script also reads `v3j_summary.json` as a fallback for the older curated-versus-schema contrast, because V3k only adds the generic structured-memory control.

After Phase9p/Phase9r integration, the figure script also reads:

`<BGVD_PROJECT_ROOT>\outputs\phase9i_verifier_handoff\phase9p_bm25_memory_baseline_20260708_203410\summary_protocol_repaired.json`

`<BGVD_PROJECT_ROOT>\outputs\phase9i_verifier_handoff\phase9r_hashed_dense_retrieval_memory_baseline_20260709_011243\summary.json`

The release-candidate copies are:

`phase9p_summary_protocol_repaired.json`

`phase9r_summary.json`

The Phase9q open-weight finalizer subset sensitivity check reads:

`phase9q_open_weight_summary.json`

## Regenerate Runtime-Curation Evidence Tables

The earlier V3e/V3g/V3h paper evidence package can be regenerated from the project root:

```powershell
<PYTHON_UTF8_WRAPPER> .\scripts\build_phase9i_paper_evidence.py
```

This produces:

- aggregate by phase/provider/arm;
- paired sign-test contrasts;
- held-out cost table;
- V3e accuracy/failure figures;
- optional V3g/V3h cost figure, no longer used in the current manuscript body.

## Main Manuscript Compile

From:

`<BGVD_PROJECT_ROOT>\manuscript\structured_state_interface_20260708`

Run:

```powershell
$xelatex='<USER_HOME>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe'
$bibtex='<USER_HOME>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\bibtex.exe'
& $xelatex -interaction=nonstopmode -halt-on-error main.tex
& $bibtex main
& $xelatex -interaction=nonstopmode -halt-on-error main.tex
& $xelatex -interaction=nonstopmode -halt-on-error main.tex
```

Expected current output:

- `main.pdf`, 24 pages;
- 71 cited references in `main.bbl`;
- no unresolved citations;
- no overfull or underfull box warnings in the current compile log;
- only the expected XeTeX `inputenc` notice.

## Result-to-Claim Mapping

| Claim | Source file | Manuscript location |
|---|---|---|
| Structured interface beats matched-budget free-form | `v3j_summary.json` | Results RQ1, Fig. structured-interface accuracy/contrasts |
| Security-specific interface beats generic structure | `v3k_summary.json`, `v3k_result.md` | Results RQ1, Fig. structured-interface accuracy/contrasts |
| Security-specific interface beats simple lexical event retrieval under state pressure | `phase9n_summary_protocol_repaired.json`, `phase9n_result.md` | Results RQ1, retrieval-control boundary |
| Security-specific interface beats BM25-style event retrieval under state pressure | `phase9p_summary_protocol_repaired.json`, `phase9p_result.md` | Results RQ1, retrieval-control boundary |
| Security-specific interface beats hashed dense-vector event retrieval under state pressure | `phase9r_summary.json`, `phase9r_result.md` | Results RQ1, retrieval-control boundary |
| Targeted open-weight finalizer subset preserves schema-favoring direction | `phase9q_open_weight_summary.json`, `phase9q_open_weight_result.md` | Results RQ1, Threats |
| Low-pressure replay saturates and does not require the structured interface | `phase9o_summary_protocol_repaired.json`, `phase9o_result.md` | Results boundary check, Threats |
| Deterministic curation not uniquely superior | `v3i_summary.json`, `v3j_summary.json` | Results RQ2, Threats |
| Typed surface adds no correctness gain | `v3e_summary.json`, `v3e_stats.md` | Results RQ3 |
| Held-out strong paid-token proxy observation | `v3g_*_summary.json`, `v3h_*_summary.json` | Results RQ4 table; optional supplementary cost figure |
| Redacted replay fixture scope | `v3e_episodes.redacted.json`, `v3g_episodes.redacted.json` | Experimental Design, Threats |
