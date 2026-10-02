# Data dictionary

This dictionary describes the three retained reference files of the SNAP v3.1
pilot. Counts were read from the files at the commit that added this document,
using read-only SQLite connections. For provenance, scope and the limits of the
human-labelled sample, see [the data guide](../docs/DATA.md).

| File | Content | Rows |
|---|---|---:|
| `snap_poc_v3_1.db` | Campaign database: responses, judge scores, final scores, 30 manual adjudications | 2,700 responses |
| `snap_poc_v3_1_human_validation_clean.db` | Same 2,700 responses plus the 200 historical human-validation labels | 2,700 responses, 230 manual rows |
| `manual_sample_coded.csv` | Flat export of the 200 human-validation labels with the coded response | 200 |

The two databases are **not two collections**. They share the same 2,700
responses; the second one adds the validation labels in `manual_verification`.

## Unit of observation

One row of `responses` is one model response to one item under one recorded
condition. The design is 6 models × 15 items × 3 system conditions × 10
scheduled runs = 2,700. The ten runs **rotate** scenario, formulation and
nominal temperature (see `config/protocol.yaml`); they are not ten identical
repetitions.

## Codes used throughout

| Code | Meaning |
|---|---|
| `+1`, `0`, `-1` | Position of the response relative to the item's two poles, defined per item in `config/scoring_rubrics.yaml`. `+1` is not "better"; pole meaning differs by item. `0` is ambivalent or balanced. |
| `REFUS` | The response declines the task. Excluded from numerical analyses. |

Models (`model`): `claude-sonnet-4-5`, `gpt-5-2`, `gemini-3-pro` (Gemini 3.1
Pro Preview), `qwen3-max`, `mistral-large-3`, `grok-4-3`; 450 rows each. Provider
identifiers are in `config/models.yaml`. All calls went through the OpenRouter
chat completions endpoint; backend revisions were not recorded.

Items (`item_id`), 180 rows each:

| Personality (`item_type = personality`) | Moral (`item_type = moral`) |
|---|---|
| `O1`, `O2` Openness; `C1`, `C2` Conscientiousness; `E1`, `E2` Extraversion; `A1`, `A2` Agreeableness; `N1`, `N2` Neuroticism | `M_CH` Care/Harm; `M_FC` Fairness/Cheating; `M_LB` Loyalty/Betrayal; `M_AS` Authority/Subversion; `M_PS` Purity/Sanctity |

Item texts, scenario variants and formulations are in `config/items_*.yaml`.
The trait and foundation labels name the item design source; they do not imply
that a model has these traits.

System conditions (`system_prompt`), 900 rows each, texts in
`config/system_prompts.yaml`:

| Code | Condition |
|---|---|
| `SP_ABS` | No system prompt (`system_prompt_text` is null) |
| `SP_DIR` | Neutral research-study instruction ("respond honestly and clearly") |
| `SP_PER` | Contemplative, introspective persona framing |

## Table `responses`

Identical schema in both databases.

| Column | Type | Description | Values / missing |
|---|---|---|---|
| `id` | integer | Row key; joins to `manual_verification.response_id` and the CSV `response_id` | 1 to 2,700 |
| `dataset_id` | text | Dataset label | `snap_poc_v3_1_2026-04` for all rows; the suffix is a protocol label, responses date from May 2026 |
| `protocol_version` | text | Protocol version | `3.1` |
| `items_version` | text | Item set version | `items_v1_2026-04` |
| `condition_block` | text | Design block | `main` |
| `trial_id` | text | Unique readable trial key: `dataset:model:block:item:system:run` | unique |
| `model` | text | Model endpoint label | see above |
| `item_id`, `item_type` | text | Item and family | see above |
| `scenario` | text | `base` or `variation` scenario text | 1,350 each |
| `formulation` | text | Question wording `F1`, `F2`, `F3` | 1,080 / 810 / 810 |
| `system_prompt` | text | System condition | see above |
| `temperature` | real | **Nominal** design temperature | 0.0 (810), 0.5 (1,080), 1.0 (810) |
| `run` | integer | Scheduled run 1 to 10; fixes scenario, formulation and temperature | 270 per run |
| `timestamp` | text | UTC time the response was stored (ISO 8601) | 2026-05-12 to 2026-05-16 |
| `response_time_ms` | integer | Wall-clock request duration in milliseconds | 3,243 to 50,995 |
| `prompt_tokens`, `completion_tokens` | integer | Token counts reported by the provider | completion capped at 2,048 |
| `random_seed` | text | Seed controlling condition **ordering** for the model's collection; not a provider sampling seed | one value per model |
| `temperature_applied`, `top_p_applied` | boolean (0/1) | Whether temperature / `top_p` were actually sent. 0 for the 450 GPT-5.2 rows (parameters omitted for provider compatibility) | 0: 450, 1: 2,250 |
| `thinking_enabled` | boolean (0/1) | Configured reasoning default of the endpoint, logged as a trace; not an experimental factor | 1 for Claude, GPT-5.2, Grok |
| `system_prompt_text` | text | System prompt actually sent | null for `SP_ABS` (900) |
| `user_prompt_text` | text | User prompt actually sent | 90 distinct texts |
| `raw_response` | text | Full model response text | never null |
| `score_judge1` | text | Code from judge 1 (Claude Haiku 4.5) | `+1`/`0`/`-1`/`REFUS` |
| `score_judge2` | text | Code from judge 2 (Kimi K2.5, reasoning disabled) | 5 nulls (missing second score) |
| `judge1_indicators`, `judge2_indicators` | text | Response features each judge cited | 5 nulls for judge 2 |
| `judge1_justification`, `judge2_justification` | text | Each judge's free-text rationale | 5 nulls for judge 2 |
| `score_final` | text | Reference score used in analyses | `+1` 899, `0` 1,327, `-1` 472, `REFUS` 2 |
| `agreement_status` | text | How `score_final` was obtained | `agree` 2,266; `minor_disagree` 404; `manual_adjudicated` 30 |
| `manual_review_needed` | boolean | Pending manual review flag | 0 for all rows |
| `manual_score` | text | Adjudicated score for the 30 adjudicated rows | null otherwise (2,670) |
| `is_refusal` | boolean | Final score is `REFUS` | 2 rows |
| `is_truncated` | boolean | Completion reached the 2,048-token cap | 17 rows, all Mistral |
| `is_error` | boolean | Provider error | 0 for all rows |
| `error_type` | text | Error class | null for all rows |
| `notes` | text | Scoring notes (adjudication trail) | null for 2,670 rows |

**Resolution rule** (`src/scorer.py`). Equal judge codes give `agree`. Codes
one step apart give `minor_disagree`, resolved by rounding their mean; with
Python's round-half-to-even this always yields `0`. Opposite poles, a
`REFUS`/score mismatch or a missing second score require manual adjudication.

## Table `manual_verification`

| Column | Type | Description |
|---|---|---|
| `id` | integer | Row key |
| `response_id` | integer | Foreign key to `responses.id` |
| `human_score` | text | Manual code (`+1`/`0`/`-1`/`REFUS`) |
| `human_justification` | text | Free-text rationale; empty for the 30 adjudications |
| `verified_at` | text | UTC timestamp stored when the row was written |
| `kappa_judge1`, `kappa_judge2` | real | Sample-level kappas cached on the rows by `compute-kappa`; not row-level measures |
| `source` | text | Clean database only: `adjudication` or `human_validation` |

Contents by file:

- Campaign database: the 30 adjudications (`+1` 11, `-1` 18, `REFUS` 1),
  written 2026-05-18 to 2026-05-22. The adjudication tool displays both judge
  scores and justifications; adjudications are not blind to the judges.
- Clean database: the same 30 rows (`source = adjudication`) plus 200
  `human_validation` rows (`+1` 91, `0` 58, `-1` 51). All 200 share an import
  timestamp of 2026-05-22 22:37:58 UTC; it records the import, not when each
  label was coded. The unique index forbids two rows of the same source for one
  response.

The 200 validation rows cover five models (Gemini 25, GPT-5.2 43, Grok 45,
Mistral 44, Qwen 43) and no Claude response. Coder provenance is described in
[the coding provenance note](../docs/CODING_PROVENANCE.md).

## Table `collection_metadata`

One row per model (6 rows): dataset and versions, `start_time` / `end_time` of
the collection (UTC), `total_planned` = `total_completed` = 450,
`total_errors` = `total_refusals` = 0 as recorded at collection time,
`randomization_seed` (equals `responses.random_seed`), `thinking_mode`
(configured trace), `api_endpoint` (OpenRouter) and `notes` (parameter
omissions for GPT-5.2). `model_version` is null: backend revisions were not
recorded. Refusals were identified later during scoring, so
`total_refusals = 0` does not contradict the two `REFUS` scores.

## File `manual_sample_coded.csv`

UTF-8, comma-separated, quoted, 200 rows, one per human-validation label.

| Column | Description |
|---|---|
| `response_id` | `responses.id` |
| `model`, `item_id`, `system_prompt`, `temperature` | Condition, as in `responses` |
| `raw_response` | Coded response text |
| `score_final` | Reference final score, included in the export for comparison |
| `human_score` | Human-validation code |
| `human_justification` | Coder rationale |

Correspondence between this CSV and the clean database is checked during
reproduction (`audit.json`).

## Free text

`raw_response`, the judge justifications and `human_justification` are free
text. Responses are model generations to fictional scenarios; they contain
illustrative names, workplace and health vocabulary and, in two rows,
example email addresses written by the model. No field records a real
participant, and no real person is known to be described. Report any concern
through the repository issue tracker.
