# SoulBench SNAP - POC v3.1 Summary

Date: 2026-05-23  
Dataset: `snap_poc_v3_1_2026-04`  
Protocol version: `3.1`  
Items version: `items_v1_2026-04`  
Source DB snapshot: `data/snap_poc_v3_1.db`

## 1. Executive Summary

The v3.1 POC has been executed end to end.

The pipeline is operational: collection, scoring, adjudication, analysis,
visualization, and automated POC decision all run on the local dataset. The
campaign is complete on the configured matrix:

```text
15 items x 3 system prompts x 10 runs = 450 conditions/model
6 models x 450 = 2700 collected responses
2700/2700 non-error responses
2700/2700 final scores
0 pending manual adjudications
```

The final automated POC decision is:

```text
FAIL
```

This is a scientific/protocol-level fail, not an engineering failure. The
pipeline produced interpretable data and passed most operational checks, but
the POC does not meet the configured stability/context-robustness thresholds.

## 2. Current Artifact State

Final analysis reports:

- `outputs/reports/decision_report.json`
- `outputs/reports/stability_report.json`
- `outputs/reports/sensitivity_report.json`
- `outputs/reports/variance_decomposition_report.json`
- `outputs/reports/cross_sp_diagnostic.json`

Diagnostic CSV outputs:

- `outputs/reports/cross_sp_model_pairs.csv`
- `outputs/reports/cross_sp_item_amplitudes.csv`
- `outputs/reports/cross_sp_top_cells.csv`

Generated figures:

- `outputs/figures/radar_claude-sonnet-4-5.png`
- `outputs/figures/radar_gemini-3-pro.png`
- `outputs/figures/radar_gpt-5-2.png`
- `outputs/figures/radar_grok-4-3.png`
- `outputs/figures/radar_mistral-large-3.png`
- `outputs/figures/radar_qwen3-max.png`
- `outputs/figures/scores_heatmap.png`
- `outputs/figures/stability_boxplots.png`
- `outputs/figures/variance_eta_squared.png`
- `outputs/figures/cross_temperature_profiles.png`
- `outputs/figures/cross_sp_profiles.png`

DB copies:

- Final active DB: `data/snap_poc_v3_1.db`
- Archived final snapshot: `data/legacy/snap_poc_v3_1_final_snapshot_2026-05-22.db`
- Clean working copy for human validation/imports:
  `data/snap_poc_v3_1_human_validation_clean.db`
- Historical mixed working copy kept for traceability:
  `data/snap_poc_v3_1_human_validation_working.db`

Rule from this point: do not import manual coding or run destructive updates on
`data/snap_poc_v3_1.db`. Use the clean working copy for validation
experiments.

## 3. Collection State

Collection is complete for all six active models:

```text
claude-sonnet-4-5  450/450
gemini-3-pro       450/450
gpt-5-2            450/450
grok-4-3           450/450
mistral-large-3    450/450
qwen3-max          450/450
```

There are no final collection errors. Earlier Grok collection failures were
caused by a deprecated OpenRouter model ID and are preserved only in the legacy
pre-fix DB/logs. The active model is now `grok-4-3`.

Provider/request notes:

- `gpt-5-2` omits `temperature` and `top_p` by explicit config policy.
- `thinking_enabled` is a provider/config trace, not an observed reasoning
  measurement.
- `SP_ABS` is a real no-system-message condition.

## 4. Scoring And Adjudication State

Scoring is complete:

```text
score_final rows:       2700/2700
agreement_status agree: 2266
minor_disagree:         404
manual_adjudicated:     30
manual pending:         0
```

Kimi has 5 missing judge scores due to repeated client errors. Those rows were
manually adjudicated, so they no longer block final scoring or analysis.

Inter-judge agreement is strong enough for the POC thresholds:

```text
kappa_interjudge = 0.7509
threshold min    = 0.50
threshold target = 0.60
status           = pass
```

Refusals are nearly absent:

```text
refusal_rate = 0.00074
2 refusals over 2700 non-error responses
threshold max = 0.10
status = pass
```

Initial major disagreements are rare:

```text
initial_major_disagreement_rate = 0.0089
initial major disagreements     = 24
initial type disagreements      = 1
threshold max                   = 0.15
status                          = pass
```

## 5. Final Decision Checks

The automated decision report contains six checks.

Passed:

```text
kappa_interjudge
refusal_rate
initial_major_disagreement_rate
minimum_model_test_retest_pearson
```

Failed:

```text
minimum_model_icc
minimum_cross_sp_corr
```

Key failed metrics:

```text
minimum_model_icc      = 0.5486  threshold = 0.60
minimum_cross_sp_corr  = 0.3189  threshold = 0.60
```

Interpretation: the POC is not blocked by API collection or judge reliability.
It is blocked by stability/context robustness, especially across system prompt
conditions.

## 6. Stability Readout

Split-half reliability is high for every model:

```text
claude-sonnet-4-5  0.9108
gemini-3-pro       0.8938
gpt-5-2            0.9223
grok-4-3           0.8985
mistral-large-3    0.8827
qwen3-max          0.9371
```

ICC is weaker:

```text
claude-sonnet-4-5  not computable globally
gemini-3-pro       0.5701
gpt-5-2            0.6033
grok-4-3           0.5582
mistral-large-3    0.5486
qwen3-max          0.6288
```

Cross-SP correlations reveal the main instability:

```text
claude-sonnet-4-5  min cross-SP = 0.6240
gemini-3-pro       min cross-SP = 0.5654
gpt-5-2            min cross-SP = 0.7033
grok-4-3           min cross-SP = 0.4767
mistral-large-3    min cross-SP = 0.3189
qwen3-max          min cross-SP = 0.6889
```

The weakest pair is:

```text
mistral-large-3 / SP_DIR_vs_SP_PER = 0.3189
```

## 7. Cross-SP Diagnostic

The targeted diagnostic report confirms that system prompt sensitivity is
concentrated in specific model x item cells.

Top cells by system-prompt amplitude:

```text
mistral-large-3 / E2    range = 1.7
qwen3-max / M_CH        range = 0.9
claude-sonnet-4-5 / A1  range = 0.8
gemini-3-pro / M_CH     range = 0.8
mistral-large-3 / M_PS  range = 0.7
```

Most sensitive items by mean SP range:

```text
E2    mean range = 0.667
M_CH  mean range = 0.533
N2    mean range = 0.500
M_PS  mean range = 0.433
A1    mean range = 0.417
```

The most extreme cell is `mistral-large-3 / E2`:

```text
SP_ABS =  0.8
SP_DIR =  0.6
SP_PER = -0.9
range  =  1.7
```

Working hypothesis: `SP_PER` is not a superficial context variation. It can
change the response stance enough to affect style-sensitive items such as E2
and some moral decision items.

## 8. Manual Human Validation State

The representative manual sample has been exported and coded:

```text
data/manual_sample.csv
200 rows
```

The coded CSV is:

```text
data/manual_sample_coded.csv
200 rows
200 coded human_score values
```

On 2026-05-23, this coded sample was imported into:

```text
data/snap_poc_v3_1_human_validation_clean.db
```

This is now the recommended validation target. The older
`data/snap_poc_v3_1_human_validation_working.db` file is preserved only as a
historical mixed artifact.

The clean validation DB now contains:

```text
30 rows with source='adjudication'
200 rows with source='human_validation'
0 duplicate (response_id, source) pairs
```

Recommended import / recompute commands:

```bash
.venv/bin/python -m src.runner --db-path data/snap_poc_v3_1_human_validation_clean.db import-manual --file data/manual_sample_coded.csv
.venv/bin/python -m src.runner --db-path data/snap_poc_v3_1_human_validation_clean.db compute-kappa
```

`compute-kappa` continues to report:

```text
kappa_interjudge
kappa_human_judge1
kappa_human_judge2
kappa_human_score_final
```

For human-vs-machine metrics, it now reads only
`manual_verification.source='human_validation'`. Adjudication rows remain
traceable but are excluded from those kappas, and their stored
`kappa_judge1/kappa_judge2` values are kept `NULL`.

Final human-validation kappas measured on 2026-05-23:

```text
kappa_human_judge1      = 0.6234
kappa_human_judge2      = 0.6304
kappa_human_score_final = 0.5789
```

These kappas close the manual validation workflow for v3.1. They do not change
the automated POC decision, which remains `FAIL`, because the fail is driven by
the stability/context-robustness checks (`minimum_model_icc`,
`minimum_cross_sp_corr`), not by the human-validation metrics.

## 9. What This Means For The Next Protocol

The v3.1 result argues against scaling immediately.

Before a larger campaign, the next protocol pass should decide:

1. Whether `SP_PER` should be removed, rewritten, or treated as a separate
   stress-test condition.
2. Whether style-sensitive items such as `E1` and `E2` should be kept in the
   same score family as value/content items.
3. Whether decision thresholds should distinguish core repeatability,
   superficial prompt robustness, and persona sensitivity.
4. Whether human validation confirms the LLM judge scoring on a representative
   sample.

Recommended next move: produce a v3.2 micro-POC focused on the unstable cells
instead of rerunning the full campaign immediately.
