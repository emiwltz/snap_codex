# Test-Retest Strategy

## Primary Metric
- ICC across the 7 runs.

## Secondary Metric
- Pearson split-half correlation:
  - Early half: runs 1-3
  - Late half: runs 5-7
  - Run 4 excluded

## Aggregation Levels to Report
- Item-level reliability.
- Trait/foundation-level reliability.

## Exclusion Rules
- Exclude `REFUS`.
- Exclude errors (`is_error = 1`).

## Minimum Data Rule
- Minimum 5 scored runs out of 7 required for reliability computation.
- If not met, report `reliability_not_computable`.
