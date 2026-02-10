# Manual Adjudication Workflow

## Command
`python -m src.runner adjudicate`

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
