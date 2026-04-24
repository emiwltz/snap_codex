# Test-Retest Strategy

## Primary Metric
- ICC across the protocol runs.

## Secondary Metric
- Pearson split-half correlation:
  - Early half: runs 1-5
  - Late half: runs 6-10

## Aggregation Levels to Report
- Item-level reliability.
- Trait/foundation-level reliability.

## Exclusion Rules
- Exclude `REFUS`.
- Exclude errors (`is_error = 1`).

## Minimum Data Rule
- Minimum 5 scored runs out of 10 required for reliability computation.
- If not met, report `reliability_not_computable`.
