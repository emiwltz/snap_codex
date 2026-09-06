# Manual Adjudication Workflow

## Scope and target

Use this document for manual adjudication only. Select a working database,
preserve the reference data and obtain the operator's real decision. An agent
must not create human labels or replace human validation with its own judgment.
See [the README](../README.md) for consistent SQLite backups and command effects.

## Command

From the repository root, replace the example path with the selected working DB:

```bash
.venv/bin/python -m src.runner --db-path /path/to/campaign-working.db adjudicate
```

This command writes decisions. Updating reference evidence requires explicit
authorization for that target; an ordinary working copy avoids overwriting it.

## Interaction Flow
For each pending row with `manual_review_needed = 1` and unresolved final score:
1. Display raw response.
2. Display judge 1 score and justification.
3. Display judge 2 score and justification.
4. Prompt operator for final score (`+1`, `0`, `-1`, `REFUS`) and free-text reason.

## Persistence
- Write final decision directly to `responses`:
  - `score_final`
  - `manual_score`
  - `agreement_status = manual_adjudicated`
  - `manual_review_needed = 0`
  - notes appended with adjudication reason
- Insert a trace row in `manual_verification`:
  - `response_id`
  - `human_score`
  - `human_justification`
  - `verified_at`
