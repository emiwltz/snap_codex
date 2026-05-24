# SoulBench SNAP

SoulBench SNAP is an experimental Python project for studying response profiles
from large language models under controlled prompting conditions.

The project does not try to prove that a model has a personality, internal
values, or a stable psychology. It measures a more cautious and more useful
object: how a model responds to ambiguous situations when the model, system
framing, wording, scenario, and selected inference parameters are varied.

The v3.1 campaign was executed end to end. Its result is intentionally kept in
the repository as a reference state before v3.2: data, analyses, figures,
reports, and historical documentation.

## Short Result

The pipeline works. The v3.1 protocol fails.

```text
POC v3.1 decision: FAIL
```

This `FAIL` is not a technical failure. Collection, scoring, adjudication,
statistical analysis, figures, and automated decision reporting were all
produced successfully. The `FAIL` means that the experimental thresholds set
before scaling are not all met, especially for robustness across system prompt
variations.

| Check | v3.1 value | Threshold | Status |
|---|---:|---:|---|
| Inter-judge kappa | 0.7509 | 0.60 target | pass |
| Refusal rate | 0.00074 | 0.10 max | pass |
| Initial major disagreements | 0.0089 | 0.15 max | pass |
| Minimum split-half | 0.8827 | 0.60 min | pass |
| Minimum ICC | 0.5486 | 0.60 min | fail |
| Minimum cross-SP correlation | 0.3189 | 0.60 min | fail |

Quick reading: the scoring is reliable enough to interpret the POC, and almost
all responses are usable, but some profiles change too much depending on system
framing. The critical condition is `SP_PER`, which behaves less like a
superficial variation and more like a different response posture.

## Why This Project Exists

The project starts from a simple but slippery question:

> If several LLMs are submitted to comparable ambiguous situations, do we get
> response profiles that are stable, scorable, and comparable?

This question is useful for a behavioral benchmark, but it is methodologically
fragile. An LLM can change its response because the model differs, because the
scenario is reworded, because the system prompt induces a particular posture,
because temperature changes, or simply because the response is locally unstable.

SoulBench SNAP therefore builds a POC around three requirements:

1. **Scorability**: free-form responses must be transformable into discrete
   scores by independent judges.
2. **Stability**: profiles must remain sufficiently consistent across repeated
   runs.
3. **Context robustness**: profiles must not collapse when a supposedly
   secondary variation changes.

v3.1 acts as a filter before a larger campaign. It answers this question: is the
current protocol clean enough to scale? The current answer is no.

## v3.1 Methodology

### Experimental Unit

Each trial is a single-turn conversation:

1. an optional system prompt;
2. a user scenario;
3. a question formulation;
4. a free-form model response;
5. post-hoc scoring by two LLM judges;
6. automatic or manual disagreement resolution.

Responses are coded with four labels:

```text
+1    orientation toward the item's positive pole
0     ambivalent, balanced, or non-directional response
-1    orientation toward the item's negative pole
REFUS unusable response or explicit refusal
```

The meaning of `+1` and `-1` depends on the item. For an openness item, `+1`
may mean exploration; for a moral item, `+1` may mean a utilitarian, legalistic,
or principled position depending on the rubric.

### Active Design

v3.1 uses a compact rotated design defined in `config/protocol.yaml`.

For each model:

```text
15 items x 3 system prompts x 10 runs = 450 responses
```

With 6 active models:

```text
6 x 450 = 2700 collected responses
```

Each response is then scored by two judges:

```text
2700 responses x 2 judges = 5400 scoring calls
```

Theoretical total excluding retries:

```text
8100 API calls
```

The `scenario`, `formulation`, and `temperature` variables are not crossed
exhaustively in v3.1. They follow a deterministic 10-run schedule. Analyses
involving those variables should therefore be read as exploratory.

### Manipulated Variables

| Variable | Values |
|---|---|
| `model` | 6 active models |
| `item_id` | 15 items |
| `item_type` | `personality`, `moral` |
| `system_prompt` | `SP_ABS`, `SP_DIR`, `SP_PER` |
| `run` | 1 to 10 |
| `scenario` | `base`, `variation`, assigned by run |
| `formulation` | `F1`, `F2`, `F3`, assigned by run |
| `temperature` | `0.0`, `0.5`, `1.0`, assigned by run |

The three system prompts are central:

| ID | Role |
|---|---|
| `SP_ABS` | true absence of a system message |
| `SP_DIR` | explicit neutral research framing |
| `SP_PER` | introspective/contemplative persona prompt |

v3.1 shows that `SP_PER` is not neutral. It changes the response posture enough
to make the cross-system-prompt robustness criterion fail.

### Items

The POC contains 15 items:

| Family | Count | Files |
|---|---:|---|
| Personality | 10 | `config/items_personality.yaml` |
| Morality | 5 | `config/items_moral.yaml` |

The personality items cover Big Five-inspired dimensions: Openness,
Conscientiousness, Extraversion, Agreeableness, and Neuroticism, with two items
per trait.

The moral items cover five foundations: Care/Harm, Fairness/Cheating,
Loyalty/Betrayal, Authority/Subversion, and Purity/Sanctity.

Each item contains:

- two scenarios (`base`, `variation`);
- three formulations (`F1`, `F2`, `F3`);
- a scoring rubric defining the `+1`, `0`, `-1`, and `REFUS` poles.

### Models and Judges

The active collection models are defined in `config/models.yaml`:

| Internal ID | Provider | OpenRouter model |
|---|---|---|
| `claude-sonnet-4-5` | Anthropic | `anthropic/claude-sonnet-4.5` |
| `gpt-5-2` | OpenAI | `openai/gpt-5.2` |
| `gemini-3-pro` | Google | `google/gemini-3.1-pro-preview` |
| `qwen3-max` | Alibaba | `qwen/qwen3-max` |
| `mistral-large-3` | Mistral | `mistralai/mistral-large-2512` |
| `grok-4-3` | xAI | `x-ai/grok-4.3` |

Two LLM judges score the responses:

| Judge | Model |
|---|---|
| `haiku` | `anthropic/claude-haiku-4.5` |
| `kimi` | `moonshotai/kimi-k2.5` |

Important note: for `gpt-5-2`, the `temperature` and `top_p` parameters are not
sent, according to provider configuration. The database records this difference
through `temperature_applied` and `top_p_applied`.

## Project Evolution

The historical documents have been archived in `docs/archive/v3.1/` so that the
repository root no longer contains several competing protocol documents.

| Archived document | Role |
|---|---|
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v1_1.md` | source compact POC design |
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v2_1.md` | historical full-factorial design |
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v3_1.md` | active executed protocol |
| `docs/archive/v3.1/POC_v3_1_summary.md` | detailed v3.1 result summary |
| `docs/archive/v3.1/README_v3_1_kit.md` | previous v3.1 kit README |

### Phase 1: Evaluation Prerequisites

The early project focused on identifying what needed to be controlled before
model profiles could be interpreted: item choice, separation between free-form
response and post-hoc scoring, need for repeated runs, importance of contextual
variations, and need for reproducible storage.

The core methodological intuition stayed stable: before comparing models, the
protocol itself must be checked to ensure it does not create too much
instability.

### Phase 2: Full-Factorial v2.1 Ambition

v2.1 explored a much more exhaustive design:

```text
15 items x 2 scenarios x 3 formulations x 3 system prompts x 2 temperatures x 7 runs
= 3780 conditions per model
```

With 6 models, this represented:

```text
22680 collection calls
```

This version clarified many technical building blocks:

- condition generation;
- seeded randomization;
- SQLite storage;
- idempotent resume;
- two-judge scoring;
- adjudication;
- stability, sensitivity, and variance analyses;
- figures and reports.

But it was too heavy for a validation POC. The risk was launching a large
campaign before knowing whether the scores, items, and prompts were robust
enough.

### Phase 3: Return to a Compact v3.1 POC

v3.1 returns to the compact spirit of v1.1 while keeping the infrastructure
built during v2.1.

Structuring decision:

```text
fewer conditions, but a complete and verifiable pipeline
```

v3.1 keeps:

- the 15 items;
- the 3 system prompts;
- the 10 runs per item and per system prompt;
- campaign metadata;
- SQLite collection;
- scoring by two judges;
- manual adjudication;
- human-validation exports;
- statistical analyses;
- figures;
- automated `PASS/BORDERLINE/FAIL` decision reporting.

It removes from the main POC:

- the complete full-factorial design;
- the massive collection cost;
- symmetric treatment of every experimental cell;
- the LMM as a central decision criterion;
- the idea of scaling before validation.

### Phase 4: Operational Corrections

During the v3.1 execution, several practical decisions were made:

- align the CLI workflow with the v3.1 protocol;
- record the parameters actually sent to providers;
- disable explicit Kimi reasoning for scoring;
- prevent the POC decision from concluding before campaign completion;
- replace the deprecated Grok model ID with `grok-4-3`;
- ignore generated collection logs;
- archive a complete artifact snapshot before cleanup;
- keep only the useful scientific kit on `main`.

The complete pre-cleanup snapshot remains recoverable from commit:

```text
4e525ee Archive v3.1 validation snapshot
```

The current `main` kit keeps the important data and analyses, but not raw logs
or intermediate artifacts.

### Execution Issues Worth Recording

Three operational issues are part of the v3.1 history and matter for anyone
trying to interpret or extend the project:

- The Grok collection initially hit failures caused by a deprecated OpenRouter
  model ID. The active model was changed to `grok-4-3`, and the final database
  contains a complete 450/450 Grok collection. The detailed legacy traces are
  kept in the pre-cleanup snapshot commit, not in the current `main` kit.
- Kimi failed as judge on 5 responses after repeated `client_error` returns.
  Those rows have no `score_judge2`, so the inter-judge kappa is computed on
  2695 judge pairs rather than 2700. They were manually adjudicated and all have
  a final score, so they do not block the final analyses.
- Mistral produced 17 responses flagged as `is_truncated=1`, all at the
  configured `2048` completion-token limit. All 17 were still scored and kept in
  the dataset: 15 were direct judge agreements and 2 were minor disagreements
  resolved automatically. This does not invalidate the POC, but it is a signal
  that v3.2 should monitor verbosity, `max_tokens`, and truncation policy.

## What Was Done

### Collection

The v3.1 collection is complete:

| Model | Responses |
|---|---:|
| `claude-sonnet-4-5` | 450/450 |
| `gemini-3-pro` | 450/450 |
| `gpt-5-2` | 450/450 |
| `grok-4-3` | 450/450 |
| `mistral-large-3` | 450/450 |
| `qwen3-max` | 450/450 |

Total:

```text
2700 collected responses
2700 non-error responses
0 final errors
17 truncated Mistral responses, all scored
```

Distribution:

| Axis | Distribution |
|---|---|
| System prompts | `SP_ABS`: 900, `SP_DIR`: 900, `SP_PER`: 900 |
| Item type | personality: 1800, moral: 900 |
| Final score | `+1`: 899, `0`: 1327, `-1`: 472, `REFUS`: 2 |

### Scoring and Adjudication

Every response received a final score:

```text
2700/2700 score_final
2266 direct agreements
404 minor disagreements resolved automatically
30 manual adjudications
0 remaining manual-review rows
2 refusals
5 missing Kimi judge scores, all manually adjudicated
```

The resolution rule is:

| Case | Resolution |
|---|---|
| direct agreement | direct final score |
| minor disagreement `+1/0` or `0/-1` | final score `0` |
| major disagreement `+1/-1` | manual adjudication |
| conflict with `REFUS` | manual adjudication |

The final inter-judge kappa is:

```text
kappa_interjudge = 0.7509
```

This score exceeds the 0.60 target threshold. The main POC problem is therefore
not the judges' ability to code the responses.

### Human Validation

A coded human sample is kept:

```text
data/manual_sample_coded.csv
```

It contains 200 human-coded rows.

Human-machine kappas:

```text
kappa_human_judge1      = 0.6234
kappa_human_judge2      = 0.6304
kappa_human_score_final = 0.5789
```

Reading: human-machine agreement is acceptable for a POC, but not strong enough
to consider the rubric definitively stabilized. For v3.2, the human-machine
disagreement cases should probably be audited qualitatively rather than only
summarized through a global score.

## Collected Analyses

The final analyses are in `outputs/reports/`. The final figures are in
`outputs/figures/`.

### POC Decision

Report:

```text
outputs/reports/decision_report.json
```

Conclusion:

```text
FAIL
```

Passed checks:

- inter-judge kappa;
- refusal rate;
- initial major disagreement rate;
- minimum split-half.

Failed checks:

- minimum ICC;
- minimum correlation between system prompts.

### Stability

Report:

```text
outputs/reports/stability_report.json
```

| Model | ICC | Split-half | Cross-temp corr | Weakest cross-SP |
|---|---:|---:|---:|---:|
| `claude-sonnet-4-5` | not computable | 0.9108 | 0.8271 | 0.6240 |
| `gemini-3-pro` | 0.5701 | 0.8938 | 0.7883 | 0.5654 |
| `gpt-5-2` | 0.6033 | 0.9223 | n/a | 0.7033 |
| `grok-4-3` | 0.5582 | 0.8985 | 0.7699 | 0.4767 |
| `mistral-large-3` | 0.5486 | 0.8827 | 0.7674 | 0.3189 |
| `qwen3-max` | 0.6288 | 0.9371 | 0.8687 | 0.6889 |

Interpretation:

- split-half values are high for every model;
- ICC is more fragile and fails for several models;
- the real warning comes from cross-system-prompt correlations, especially
  `mistral-large-3 / SP_DIR_vs_SP_PER`.

### Sensitivity to Rotated Factors

Report:

```text
outputs/reports/sensitivity_report.json
```

The per-model tests cover:

- `scenario` effect: Wilcoxon `base` vs `variation`;
- `formulation` effect: Friedman `F1/F2/F3`;
- `temperature` effect: test over `0.0/0.5/1.0`.

Summary result:

- no clear scenario effect;
- no clear formulation effect at the per-model test level;
- exploratory significant temperature effect for `gemini-3-pro` (`p = 0.0280`)
  and `grok-4-3` (`p = 0.0211`);
- temperature not applicable for `gpt-5-2`, because the parameter was not sent.

These results remain exploratory: v3.1 does not cross scenario, formulation, and
temperature exhaustively.

### Variance Decomposition

Report:

```text
outputs/reports/variance_decomposition_report.json
```

Exploratory eta squared by factor:

| Factor | Eta squared |
|---|---:|
| `item_id` | 0.4709 |
| `run` | 0.0060 |
| `formulation` | 0.0035 |
| `model` | 0.0025 |
| `system_prompt` | 0.0021 |
| `temperature` | 0.0012 |
| `scenario` | 0.0005 |

Reading: the item explains by far the largest share of variance. Global effects
of model, system prompt, temperature, and scenario are weak on average, but this
average hides strong critical cells.

The report also includes an exploratory LMM:

```text
score ~ model * system_prompt + model * temperature + scenario + formulation
      + (1|item) + (1|run) + (1|model_random)
```

The LMM converges, but it is not used as the main decision criterion. It guides
audits rather than validating the protocol.

### Cross-System-Prompt Diagnostic

Reports:

```text
outputs/reports/cross_sp_diagnostic.json
outputs/reports/cross_sp_model_pairs.csv
outputs/reports/cross_sp_item_amplitudes.csv
outputs/reports/cross_sp_top_cells.csv
```

Minimum correlations by model:

| Model | Weakest pair | Correlation |
|---|---|---:|
| `claude-sonnet-4-5` | `SP_ABS_vs_SP_PER` | 0.6240 |
| `gemini-3-pro` | `SP_DIR_vs_SP_PER` | 0.5654 |
| `gpt-5-2` | `SP_ABS_vs_SP_DIR` | 0.7033 |
| `grok-4-3` | `SP_DIR_vs_SP_PER` | 0.4767 |
| `mistral-large-3` | `SP_DIR_vs_SP_PER` | 0.3189 |
| `qwen3-max` | `SP_DIR_vs_SP_PER` | 0.6889 |

Main critical cell:

```text
model   = mistral-large-3
item    = E2
SP_ABS  =  0.8
SP_DIR  =  0.6
SP_PER  = -0.9
range   =  1.7
```

Items most sensitive to system prompt:

| Item | Type | Mean SP range |
|---|---|---:|
| `E2` | personality | 0.6667 |
| `M_CH` | moral | 0.5333 |
| `N2` | personality | 0.5000 |
| `M_PS` | moral | 0.4333 |
| `A1` | personality | 0.4167 |

Working interpretation: `SP_PER` changes the model's posture. On
style-sensitive items such as `E2`, it can turn a proactive response into a much
more restrained response, which substantially changes the score.

## Figures

The final figures are kept in `outputs/figures/`.

![Scores heatmap](outputs/figures/scores_heatmap.png)

![Cross-SP profiles](outputs/figures/cross_sp_profiles.png)

Available figures:

| Figure | Content |
|---|---|
| `scores_heatmap.png` | mean profiles by model and item |
| `stability_boxplots.png` | score/stability distributions |
| `variance_eta_squared.png` | exploratory factor importance |
| `cross_temperature_profiles.png` | profiles by temperature |
| `cross_sp_profiles.png` | profiles by system prompt |
| `radar_<model>.png` | radar profiles by model |

## Current Repository State

The main branch keeps a readable and reproducible v3.1 kit.

### Kept on `main`

| Path | Role |
|---|---|
| `README.md` | main project presentation |
| `docs/archive/v3.1/` | historical protocols and documents |
| `config/` | protocol, models, prompts, items, rubrics |
| `src/` | Python pipeline |
| `tests/` | unit tests |
| `data/snap_poc_v3_1.db` | final collected and scored database |
| `data/snap_poc_v3_1_human_validation_clean.db` | clean human-validation database |
| `data/manual_sample_coded.csv` | coded human sample |
| `outputs/reports/` | final reports |
| `outputs/figures/` | final figures |

### Intentionally Excluded

The repository does not keep these on `main`:

- raw OpenRouter logs;
- intermediate and legacy databases;
- mixed working database;
- uncoded human CSV;
- Python caches;
- macOS files;
- SQLite `-wal` and `-shm` files.

These files are not needed to understand the v3.1 results. The complete
pre-cleanup snapshot remains available through Git history.

## Navigating the Codebase

### Overview

```text
.
|-- README.md
|-- config/
|-- data/
|-- docs/archive/v3.1/
|-- outputs/
|   |-- figures/
|   `-- reports/
|-- src/
|-- tests/
`-- requirements.txt
```

### Main Directories

| Directory | Purpose |
|---|---|
| `config/` | describes the experimental protocol without changing code |
| `src/` | implements collection, scoring, analysis, and visualization |
| `data/` | contains SQLite databases and the coded human sample |
| `outputs/reports/` | contains machine-readable analytical results |
| `outputs/figures/` | contains final visualizations |
| `docs/archive/v3.1/` | contains old protocol documents and summaries |
| `tests/` | checks critical pipeline behavior |

### Configuration Files

| File | Role |
|---|---|
| `config/protocol.yaml` | v3.1 design, run schedule, decision thresholds |
| `config/models.yaml` | collection models, judges, provider parameters |
| `config/system_prompts.yaml` | `SP_ABS`, `SP_DIR`, `SP_PER` |
| `config/items_personality.yaml` | personality items |
| `config/items_moral.yaml` | moral items |
| `config/scoring_rubrics.yaml` | scoring rubrics used by judges |
| `config/manual_adjudication_workflow.md` | manual adjudication procedure |
| `config/methodology_retest.md` | notes on stability and test-retest |
| `config/methodology_h4.md` | notes on variance/LMM analyses |

### Python Modules

| Module | Role |
|---|---|
| `src/runner.py` | main CLI |
| `src/db.py` | SQLite schema, DB access, imports/exports |
| `src/api_client.py` | OpenRouter client |
| `src/preflight.py` | model, pricing, parameter, and DB checks |
| `src/prompt_builder.py` | system/user message construction |
| `src/scorer.py` | scoring prompts, parsing, resolution, kappas |
| `src/analyzer.py` | stability, sensitivity, variance, cross-SP diagnostic |
| `src/visualizer.py` | figure generation |
| `src/decision.py` | `PASS/BORDERLINE/FAIL` report |

### Reading the Data

The main database is:

```text
data/snap_poc_v3_1.db
```

Main tables:

| Table | Content |
|---|---|
| `responses` | collected responses, metadata, scores, adjudication |
| `collection_metadata` | collection state by model |
| `manual_verification` | human validation/adjudication rows |

Useful examples:

```bash
sqlite3 data/snap_poc_v3_1.db "select count(*) from responses;"
sqlite3 data/snap_poc_v3_1.db "select model, count(*) from responses group by model;"
sqlite3 data/snap_poc_v3_1.db "select agreement_status, count(*) from responses group by agreement_status;"
sqlite3 data/snap_poc_v3_1.db "select score_final, count(*) from responses group by score_final;"
```

## Installation

Prerequisites:

- Python 3.11+;
- an OpenRouter key to rerun collection/scoring;
- SQLite available from the command line to inspect databases.

Installation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Check the CLI:

```bash
python -m src.runner --help
```

If `python` does not point to the virtual environment on your machine, use it
explicitly:

```bash
.venv/bin/python -m src.runner --help
```

## Useful Commands

### Tests

```bash
.venv/bin/python -m pytest -q
```

### Preflight

```bash
.venv/bin/python -m src.runner preflight
```

The preflight checks OpenRouter availability, model parameters, pricing, and DB
consistency before collection.

### Regenerate Analyses from the Final DB

```bash
.venv/bin/python -m src.runner analyze --stability
.venv/bin/python -m src.runner analyze --sensitivity
.venv/bin/python -m src.runner analyze --variance-decomposition
.venv/bin/python -m src.runner analyze --cross-sp-diagnostic
.venv/bin/python -m src.runner decision
```

### Regenerate Figures

```bash
.venv/bin/python -m src.runner visualize --all
```

### Human Validation

The clean validation database is:

```text
data/snap_poc_v3_1_human_validation_clean.db
```

Examples:

```bash
sqlite3 data/snap_poc_v3_1_human_validation_clean.db \
  "select source, count(*) from manual_verification group by source;"

.venv/bin/python -m src.runner \
  --db-path data/snap_poc_v3_1_human_validation_clean.db \
  compute-kappa
```

Practical rule: do not import new manual coding directly into
`data/snap_poc_v3_1.db`. Use a working copy or the validation DB.

## Complete Pipeline for a New Campaign

```bash
.venv/bin/python -m src.runner init-db --reset
.venv/bin/python -m src.runner preflight

export OPENROUTER_API_KEY="..."

.venv/bin/python -m src.runner collect --all

.venv/bin/python -m src.runner score --judge haiku
.venv/bin/python -m src.runner score --judge kimi
.venv/bin/python -m src.runner resolve-disagreements

.venv/bin/python -m src.runner export-sample --n 200 --output data/manual_sample.csv
.venv/bin/python -m src.runner manual-score-sample --file data/manual_sample.csv
.venv/bin/python -m src.runner import-manual --file data/manual_sample.csv

.venv/bin/python -m src.runner adjudicate
.venv/bin/python -m src.runner compute-kappa

.venv/bin/python -m src.runner analyze --stability
.venv/bin/python -m src.runner analyze --sensitivity
.venv/bin/python -m src.runner analyze --variance-decomposition
.venv/bin/python -m src.runner analyze --cross-sp-diagnostic

.venv/bin/python -m src.runner visualize --all
.venv/bin/python -m src.runner decision
```

## Known Limitations

v3.1 intentionally surfaced the protocol's weaknesses.

Main limitations:

- `SP_PER` is not a neutral variation; it behaves like a persona or stress-test
  condition.
- Some items are highly sensitive to response style, especially `E2`.
- The `scenario`, `formulation`, and `temperature` variables are rotated, not
  full-factorial.
- The `-1/0/+1` scores are practical for analysis but strongly simplify rich
  textual responses.
- The LMM is exploratory and can be numerically sensitive.
- The `thinking_enabled` field records provider/default configuration, not a
  measurement of internal reasoning.
- Human kappas suggest that the rubrics are usable, but not definitively
  stabilized.

## v3.2 Direction

v3.2 should not simply rerun the same design at a larger scale. It should fix
what v3.1 revealed.

Priorities:

1. Qualitatively audit critical cross-SP cells, especially
   `mistral-large-3 / E2`.
2. Decide the status of `SP_PER`: removal, rewrite, or treatment as a separate
   stress test.
3. Revise style-sensitive items, especially `E2` and possibly `E1`.
4. Review human-machine disagreements to improve the rubrics.
5. Build a targeted v3.2 micro-campaign before any new large campaign.
6. Clearly separate confirmatory analyses from exploratory diagnostics.

The current repository state is therefore a clean stopping point: v3.1 is
archived, important data is preserved, and the next work can start from a
readable base rather than a scattered history.
