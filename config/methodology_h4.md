# H4 Method Decision

## Decision
- Exploratory stage: factorial ANOVA-style decomposition using eta squared per factor.
- Confirmatory stage: linear mixed model (LMM).

## Confirmatory Formula
`score ~ model * system_prompt + model * temperature + scenario + formulation + (1|item) + (1|run) + (1|model_random)`

## Fallback Rule (Non-Convergence)
- Remove `(1|model_random)`.
- Keep `(1|item) + (1|run)`.

## Exclusion Rules
- Exclude rows with `is_error = 1`.
- Exclude `REFUS` rows.
- Exclude rows where `manual_review_needed = 1` and `manual_score` is missing.

## Reporting Outputs
- Exploratory: eta squared by factor + ranking.
- Confirmatory: convergence status, model variant used (primary/fallback), log-likelihood, AIC/BIC, coefficients, p-values, random-effect components.
