# Provenance of the manual codes

Status: draft for the author's review. Each statement is marked as **recorded**
(observable in the retained files), **declared** (stated by the author,
Emilien Waltz, retrospectively on 3 October 2026, without independent
evidence) or **unknown**.

## Two different sets of manual codes

| Set | Rows | Purpose | Where |
|---|---:|---|---|
| Adjudications | 30 | Resolve judge pairs that could not be resolved automatically (24 opposite poles, 1 type/refusal disagreement, 5 missing second-judge scores) | Both databases, `manual_verification`; `source = adjudication` in the clean database |
| Human validation | 200 | Compare stored manual labels with the judges and the final score | Clean database, `source = human_validation`; `data/manual_sample_coded.csv` |

The adjudications are part of the reference scores. The validation labels never
change a reference score; they only enter the validation kappas.

## Adjudications

- **Recorded.** Written between 2026-05-18 and 2026-05-22 (UTC) through the
  interactive `adjudicate` command. That command displays the response and both
  judges' scores and justifications before asking for the decision
  ([workflow](../config/manual_adjudication_workflow.md)), so adjudications are
  **not blind** to the judges by design.
- **Recorded.** `human_justification` is empty for all 30 rows; the `notes`
  column of `responses` keeps the adjudication trail.
- **Declared.** Most manual coding was done by the author.
- **Unknown.** Whether every adjudication was made by the author.

## Human-validation labels

- **Recorded.** 200 labels (`+1` 91, `0` 58, `-1` 51) covering five models:
  Gemini 25, GPT-5.2 43, Grok 45, Mistral 44, Qwen 43; **no Claude response**.
  All share one import timestamp (2026-05-22 22:37:58 UTC), which dates the
  import into the database, not the coding itself.
- **Recorded.** The CSV export places `score_final` next to `human_score`; the
  file format alone therefore cannot establish blinding.
- **Declared.** Most labels were coded by the author, blind to the judges'
  scores and to the final score.
- **Unknown.** Who coded the remaining labels and how many; how the 200 rows
  were sampled; whether model identity and system condition were visible; the
  dates of coding; inter-coder reliability (no row was coded twice).

## Consequences for interpretation

- The validation kappas (human vs final score κ = 0.5789) describe agreement
  between stored labels and the pipeline, with mostly a single coder. They are
  **not** an independent multi-rater validation and do not cover Claude.
- No agent or model output is recorded as a human code.

Questions still open for the author: sampling of the 200 rows, identity and
share of other coders, coding dates, visibility of model and condition, and the
ethics statement (recruitment, compensation, review or exemption).
