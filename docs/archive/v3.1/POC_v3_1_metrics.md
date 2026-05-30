# SoulBench SNAP v3.1 - Consolidated Metrics Report

Date de consolidation: 2026-05-30

Ce document regroupe les donnees et metriques produites pendant l'execution du
POC SoulBench SNAP v3.1. Il est volontairement analytique et descriptif: il ne
formule pas de conclusion scientifique supplementaire et ne propose pas de
decision de protocole. Les statuts `pass`, `fail`, `ok` ou `not_applicable`
repris ci-dessous sont les statuts calcules dans les rapports existants.

## 1. Sources

| Source | Role |
|---|---|
| `data/snap_poc_v3_1.db` | base principale collecte + scoring + adjudication |
| `data/snap_poc_v3_1_human_validation_clean.db` | base propre avec validation humaine importee |
| `data/manual_sample_coded.csv` | echantillon manuel code, 200 lignes |
| `outputs/reports/decision_report.json` | decision automatique et checks globaux |
| `outputs/reports/stability_report.json` | stabilite, ICC, split-half, cross-temperature, cross-SP |
| `outputs/reports/sensitivity_report.json` | effets scenario, formulation, temperature |
| `outputs/reports/variance_decomposition_report.json` | eta squared et LMM exploratoire |
| `outputs/reports/cross_sp_diagnostic.json` | diagnostic cible system prompts |
| `outputs/reports/cross_sp_model_pairs.csv` | correlations cross-SP par modele et paire de prompts |
| `outputs/reports/cross_sp_item_amplitudes.csv` | amplitude system-prompt par item |
| `outputs/reports/cross_sp_top_cells.csv` | cellules model x item les plus sensibles au system prompt |

## 2. Identifiants Et Protocole

| Champ | Valeur |
|---|---|
| `dataset_id` | `snap_poc_v3_1_2026-04` |
| `protocol_version` | `3.1` |
| `items_version` | `items_v1_2026-04` |
| `design` | `rotated_poc` |
| `condition_block` | `main` |
| `primary_system_prompt` | `SP_DIR` |

Design effectif:

| Niveau | Valeur |
|---|---:|
| Items | 15 |
| System prompts | 3 |
| Runs par item x system prompt | 10 |
| Conditions par modele | 450 |
| Modeles actifs | 6 |
| Reponses collectees attendues | 2700 |
| Juges LLM | 2 |
| Appels de scoring attendus | 5400 |
| Appels API theoriques hors retries | 8100 |

Modeles de collecte:

| Model id | Provider | OpenRouter id | `thinking_mode` | Actif |
|---|---|---|---|---|
| `claude-sonnet-4-5` | Anthropic | `anthropic/claude-sonnet-4.5` | `enabled_by_default` | true |
| `gpt-5-2` | OpenAI | `openai/gpt-5.2` | `enabled_by_default` | true |
| `gemini-3-pro` | Google | `google/gemini-3.1-pro-preview` | `not_available` | true |
| `qwen3-max` | Alibaba | `qwen/qwen3-max` | `not_available` | true |
| `mistral-large-3` | Mistral | `mistralai/mistral-large-2512` | `disabled` | true |
| `grok-4-3` | xAI | `x-ai/grok-4.3` | `enabled_by_default` | true |

Juges de scoring:

| Judge id | OpenRouter id | Parametres specifiques |
|---|---|---|
| `haiku` | `anthropic/claude-haiku-4.5` | aucun parametre specifique |
| `kimi` | `moonshotai/kimi-k2.5` | `reasoning.enabled=false` |

## 3. Calendrier De Runs

| Run | Scenario | Formulation | Temperature | Reponses |
|---:|---|---|---:|---:|
| 1 | `base` | `F1` | 0.0 | 270 |
| 2 | `variation` | `F2` | 0.5 | 270 |
| 3 | `base` | `F3` | 1.0 | 270 |
| 4 | `variation` | `F1` | 0.0 | 270 |
| 5 | `base` | `F2` | 0.5 | 270 |
| 6 | `variation` | `F3` | 1.0 | 270 |
| 7 | `base` | `F1` | 0.5 | 270 |
| 8 | `variation` | `F2` | 1.0 | 270 |
| 9 | `base` | `F3` | 0.0 | 270 |
| 10 | `variation` | `F1` | 0.5 | 270 |

Distributions de design:

| Axe | Distribution |
|---|---|
| `scenario` | `base`: 1350, `variation`: 1350 |
| `formulation` | `F1`: 1080, `F2`: 810, `F3`: 810 |
| `temperature` | `0.0`: 810, `0.5`: 1080, `1.0`: 810 |
| `system_prompt` | `SP_ABS`: 900, `SP_DIR`: 900, `SP_PER`: 900 |
| `item_type` | `personality`: 1800, `moral`: 900 |

Temperature appliquee par niveau planifie:

| Temperature planifiee | Reponses | `temperature_applied=1` | `temperature_applied=0` |
|---:|---:|---:|---:|
| 0.0 | 810 | 675 | 135 |
| 0.5 | 1080 | 900 | 180 |
| 1.0 | 810 | 675 | 135 |

## 4. Etat De Collecte

Compteurs globaux:

| Metrique | Valeur |
|---|---:|
| Reponses en DB principale | 2700 |
| Reponses non-erreur | 2700 |
| Reponses avec `score_final` | 2700 |
| Reponses avec revue manuelle restante | 0 |
| Refus | 2 |
| Reponses tronquees | 17 |

Compteurs par modele:

| Modele | Reponses | Non-erreur | Scorees | Refus | Tronquees | Missing judge 1 | Missing judge 2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `claude-sonnet-4-5` | 450 | 450 | 450 | 2 | 0 | 0 | 2 |
| `gemini-3-pro` | 450 | 450 | 450 | 0 | 0 | 0 | 2 |
| `gpt-5-2` | 450 | 450 | 450 | 0 | 0 | 0 | 0 |
| `grok-4-3` | 450 | 450 | 450 | 0 | 0 | 0 | 0 |
| `mistral-large-3` | 450 | 450 | 450 | 0 | 17 | 0 | 0 |
| `qwen3-max` | 450 | 450 | 450 | 0 | 0 | 0 | 1 |

Metadonnees de collecte:

| Modele | Planned | Completed | Errors | Refusals | Seed | Thinking mode | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| `claude-sonnet-4-5` | 450 | 450 | 0 | 0 | 951927470 | `enabled_by_default` |  |
| `gemini-3-pro` | 450 | 450 | 0 | 0 | 1192924562 | `not_available` |  |
| `gpt-5-2` | 450 | 450 | 0 | 0 | 302931177 | `enabled_by_default` | disabled `temperature`, `top_p` |
| `grok-4-3` | 450 | 450 | 0 | 0 | 478444003 | `enabled_by_default` |  |
| `mistral-large-3` | 450 | 450 | 0 | 0 | 631056076 | `disabled` |  |
| `qwen3-max` | 450 | 450 | 0 | 0 | 474354439 | `not_available` |  |

Parametres effectivement traces:

| Modele | `temperature_applied` | `top_p_applied` | `thinking_enabled` | Reponses |
|---|---:|---:|---:|---:|
| `claude-sonnet-4-5` | 1 | 1 | 1 | 450 |
| `gemini-3-pro` | 1 | 1 | 0 | 450 |
| `gpt-5-2` | 0 | 0 | 1 | 450 |
| `grok-4-3` | 1 | 1 | 1 | 450 |
| `mistral-large-3` | 1 | 1 | 0 | 450 |
| `qwen3-max` | 1 | 1 | 0 | 450 |

## 5. Distribution Des Scores Finaux

Distribution globale:

| Score final | N |
|---|---:|
| `0` | 1327 |
| `+1` | 899 |
| `-1` | 472 |
| `REFUS` | 2 |

Distribution par modele:

| Modele | `+1` | `0` | `-1` | `REFUS` | Total |
|---|---:|---:|---:|---:|---:|
| `claude-sonnet-4-5` | 168 | 174 | 106 | 2 | 450 |
| `gemini-3-pro` | 153 | 205 | 92 | 0 | 450 |
| `gpt-5-2` | 147 | 235 | 68 | 0 | 450 |
| `grok-4-3` | 176 | 201 | 73 | 0 | 450 |
| `mistral-large-3` | 107 | 294 | 49 | 0 | 450 |
| `qwen3-max` | 148 | 218 | 84 | 0 | 450 |

Distribution par system prompt:

| System prompt | `+1` | `0` | `-1` | `REFUS` | Total |
|---|---:|---:|---:|---:|---:|
| `SP_ABS` | 318 | 421 | 160 | 1 | 900 |
| `SP_DIR` | 335 | 397 | 168 | 0 | 900 |
| `SP_PER` | 246 | 509 | 144 | 1 | 900 |

Distribution par item:

| Item | Type | `+1` | `0` | `-1` | `REFUS` | Total |
|---|---|---:|---:|---:|---:|---:|
| `A1` | personality | 27 | 110 | 43 | 0 | 180 |
| `A2` | personality | 2 | 151 | 27 | 0 | 180 |
| `C1` | personality | 9 | 170 | 1 | 0 | 180 |
| `C2` | personality | 1 | 61 | 118 | 0 | 180 |
| `E1` | personality | 180 | 0 | 0 | 0 | 180 |
| `E2` | personality | 55 | 54 | 71 | 0 | 180 |
| `M_AS` | moral | 126 | 53 | 1 | 0 | 180 |
| `M_CH` | moral | 80 | 88 | 10 | 2 | 180 |
| `M_FC` | moral | 21 | 157 | 2 | 0 | 180 |
| `M_LB` | moral | 159 | 21 | 0 | 0 | 180 |
| `M_PS` | moral | 11 | 53 | 116 | 0 | 180 |
| `N1` | personality | 16 | 92 | 72 | 0 | 180 |
| `N2` | personality | 48 | 130 | 2 | 0 | 180 |
| `O1` | personality | 104 | 70 | 6 | 0 | 180 |
| `O2` | personality | 60 | 117 | 3 | 0 | 180 |

## 6. Scoring, Juges Et Adjudication

Distribution des scores juge 1 (`haiku`):

| Score juge 1 | N |
|---|---:|
| `0` | 1105 |
| `+1` | 1094 |
| `-1` | 499 |
| `REFUS` | 2 |

Distribution des scores juge 2 (`kimi`):

| Score juge 2 | N |
|---|---:|
| `0` | 1147 |
| `+1` | 987 |
| `-1` | 560 |
| `REFUS` | 1 |

Matrice juge 1 x juge 2 sur les 2695 paires disponibles:

| Juge 1 | Juge 2 | N |
|---|---|---:|
| `+1` | `+1` | 888 |
| `+1` | `0` | 185 |
| `+1` | `-1` | 17 |
| `-1` | `+1` | 7 |
| `-1` | `0` | 38 |
| `-1` | `-1` | 454 |
| `0` | `+1` | 92 |
| `0` | `0` | 923 |
| `0` | `-1` | 89 |
| `REFUS` | `0` | 1 |
| `REFUS` | `REFUS` | 1 |

Statuts d'accord:

| `agreement_status` | N |
|---|---:|
| `agree` | 2266 |
| `minor_disagree` | 404 |
| `manual_adjudicated` | 30 |

Statuts d'accord par modele:

| Modele | `agree` | `minor_disagree` | `manual_adjudicated` | Total |
|---|---:|---:|---:|---:|
| `claude-sonnet-4-5` | 395 | 45 | 10 | 450 |
| `gemini-3-pro` | 353 | 88 | 9 | 450 |
| `gpt-5-2` | 349 | 97 | 4 | 450 |
| `grok-4-3` | 398 | 50 | 2 | 450 |
| `mistral-large-3` | 396 | 53 | 1 | 450 |
| `qwen3-max` | 375 | 71 | 4 | 450 |

Rows avec score Kimi manquant:

| Modele | Item | SP | Run | Juge 1 | Juge 2 | Final | Notes synthetiques |
|---|---|---|---:|---|---|---|---|
| `claude-sonnet-4-5` | `M_AS` | `SP_ABS` | 3 | `+1` | missing | `+1` | `kimi_parse_error: client_error`; adjudication |
| `claude-sonnet-4-5` | `M_AS` | `SP_PER` | 7 | `+1` | missing | `+1` | `kimi_parse_error: client_error`; adjudication |
| `gemini-3-pro` | `M_AS` | `SP_ABS` | 7 | `0` | missing | `+1` | `kimi_parse_error: client_error`; adjudication |
| `gemini-3-pro` | `M_AS` | `SP_DIR` | 3 | `+1` | missing | `+1` | `kimi_parse_error: client_error`; adjudication |
| `qwen3-max` | `M_AS` | `SP_ABS` | 7 | `+1` | missing | `+1` | `kimi_parse_error: client_error`; adjudication |

Refus:

| Modele | Item | SP | Scenario | Formulation | Temperature | Run | Final | Agreement |
|---|---|---|---|---|---:|---:|---|---|
| `claude-sonnet-4-5` | `M_CH` | `SP_PER` | `base` | `F3` | 1.0 | 3 | `REFUS` | `manual_adjudicated` |
| `claude-sonnet-4-5` | `M_CH` | `SP_ABS` | `variation` | `F3` | 1.0 | 6 | `REFUS` | `agree` |

Troncatures:

| Modele | Item | SP | Final | Agreement | N |
|---|---|---|---|---|---:|
| `mistral-large-3` | `C1` | `SP_ABS` | `0` | `agree` | 1 |
| `mistral-large-3` | `E1` | `SP_ABS` | `+1` | `agree` | 1 |
| `mistral-large-3` | `E2` | `SP_ABS` | `+1` | `agree` | 1 |
| `mistral-large-3` | `M_CH` | `SP_ABS` | `0` | `agree` | 4 |
| `mistral-large-3` | `M_FC` | `SP_ABS` | `0` | `agree` | 5 |
| `mistral-large-3` | `M_PS` | `SP_ABS` | `0` | `agree` | 2 |
| `mistral-large-3` | `M_PS` | `SP_DIR` | `0` | `minor_disagree` | 1 |
| `mistral-large-3` | `O2` | `SP_ABS` | `0` | `agree` | 1 |
| `mistral-large-3` | `O2` | `SP_ABS` | `0` | `minor_disagree` | 1 |

## 7. Validation Humaine

Sources `manual_verification` dans la DB propre:

| Source | N | Rows avec `kappa_judge1` | Rows avec `kappa_judge2` |
|---|---:|---:|---:|
| `adjudication` | 30 | 0 | 0 |
| `human_validation` | 200 | 200 | 200 |

Distribution de l'echantillon code dans `data/manual_sample_coded.csv`:

| Axe | Distribution |
|---|---|
| `human_score` | `+1`: 91, `0`: 58, `-1`: 51 |
| `score_final` dans l'echantillon | `+1`: 61, `0`: 109, `-1`: 30 |
| `system_prompt` | `SP_ABS`: 66, `SP_DIR`: 66, `SP_PER`: 68 |
| `model` | `gemini-3-pro`: 25, `gpt-5-2`: 43, `grok-4-3`: 45, `mistral-large-3`: 44, `qwen3-max`: 43 |

Kappas humain-machine:

| Metrique | Valeur |
|---|---:|
| `kappa_human_judge1` | 0.6234 |
| `kappa_human_judge2` | 0.6304 |
| `kappa_human_score_final` | 0.5789 |

Matrice humain x score final:

| Human score | Score final | N |
|---|---|---:|
| `+1` | `+1` | 60 |
| `+1` | `0` | 30 |
| `+1` | `-1` | 1 |
| `-1` | `0` | 23 |
| `-1` | `-1` | 28 |
| `0` | `+1` | 1 |
| `0` | `0` | 56 |
| `0` | `-1` | 1 |

Matrice humain x juge 1:

| Human score | Score juge 1 | N |
|---|---|---:|
| `+1` | `+1` | 71 |
| `+1` | `0` | 19 |
| `+1` | `-1` | 1 |
| `-1` | `+1` | 2 |
| `-1` | `0` | 19 |
| `-1` | `-1` | 30 |
| `0` | `+1` | 6 |
| `0` | `0` | 50 |
| `0` | `-1` | 2 |

Matrice humain x juge 2:

| Human score | Score juge 2 | N |
|---|---|---:|
| `+1` | `+1` | 64 |
| `+1` | `0` | 26 |
| `+1` | `-1` | 1 |
| `-1` | `0` | 18 |
| `-1` | `-1` | 33 |
| `0` | `+1` | 1 |
| `0` | `0` | 54 |
| `0` | `-1` | 3 |

## 8. Checks Du Rapport De Decision

| Metrique | Valeur | Seuil | N | Statut |
|---|---:|---:|---:|---|
| `kappa_interjudge` | 0.7509073105 | 0.50 min / 0.60 target | 2695 paires | `pass` |
| `refusal_rate` | 0.0007407407 | 0.10 max | 2700 rows | `pass` |
| `initial_major_disagreement_rate` | 0.0089053803 | 0.15 max | 2695 paires | `pass` |
| `minimum_model_icc` | 0.5486271749 | 0.60 min | 5 modeles avec valeur | `fail` |
| `minimum_model_test_retest_pearson` | 0.8827494101 | 0.60 min | 6 modeles | `pass` |
| `minimum_cross_sp_corr` | 0.3189097665 | 0.60 min | 18 paires | `fail` |

Autres champs du rapport:

| Champ | Valeur |
|---|---:|
| `response_count` | 2700 |
| `scored_count` | 2700 |
| `non_error_count` | 2700 |
| `failed_checks` | 2 |
| `borderline_checks` | 0 |
| `missing_checks` | 0 |
| `campaign_completion.status` | `complete` |
| `expected_total_conditions` | 2700 |
| `completed_total` | 2700 |
| `scored_total` | 2700 |

Details desaccords initiaux:

| Champ | Valeur |
|---|---:|
| Initial major disagreements | 24 |
| Initial type disagreements | 1 |
| Current pending disagreements | 0 |
| Current pending major disagreements | 0 |
| Current pending type disagreements | 0 |
| Manual adjudicated count | 30 |
| Manual adjudicated with judge pairs | 25 |

## 9. Stabilite

Regles du rapport:

| Champ | Valeur |
|---|---|
| `n_rows_raw` | 2698 |
| `n_rows_after_exclusions` | 2698 |
| Exclusions | `is_error=1`, `score_final=REFUS`, revue manuelle non resolue |
| Primary metric | ICC sur runs |
| Secondary metric | Pearson split-half runs 1-5 vs 6-10 |
| Target identifier | `item_id x system_prompt` |
| Minimum runs required | 5 |

Metriques par modele:

| Modele | Cronbach alpha | Split-half | Split status | Split pairs | ICC | ICC status | Cross-temp | SP_ABS/SP_DIR | SP_ABS/SP_PER | SP_DIR/SP_PER |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| `claude-sonnet-4-5` | -0.561654 | 0.910827 | `ok` | 45 | n/a | `reliability_not_computable` | 0.827139 | 0.672025 | 0.624048 | 0.693535 |
| `gemini-3-pro` | -0.083700 | 0.893754 | `ok` | 45 | 0.570115 | `ok` | 0.788348 | 0.752227 | 0.621418 | 0.565435 |
| `gpt-5-2` | 0.281213 | 0.922317 | `ok` | 45 | 0.603334 | `ok` | n/a | 0.703313 | 0.734847 | 0.703925 |
| `grok-4-3` | -0.058046 | 0.898457 | `ok` | 45 | 0.558211 | `ok` | 0.769892 | 0.714076 | 0.538668 | 0.476709 |
| `mistral-large-3` | 0.117723 | 0.882749 | `ok` | 45 | 0.548627 | `ok` | 0.767426 | 0.578006 | 0.373934 | 0.318910 |
| `qwen3-max` | -0.051346 | 0.937145 | `ok` | 45 | 0.628767 | `ok` | 0.868704 | 0.716802 | 0.739210 | 0.688899 |

Note de calcul pour `claude-sonnet-4-5` ICC global: `ICC computation failed:
Either missing values are present in data or data are unbalanced. Please remove
them manually or use nan_policy='omit'.`

Computabilite des sous-niveaux de fiabilite:

| Modele | Items total | Items ICC computable | Items split computable | Groupes total | Groupes ICC computable | Groupes split computable |
|---|---:|---:|---:|---:|---:|---:|
| `claude-sonnet-4-5` | 15 | 13 | 13 | 10 | 9 | 10 |
| `gemini-3-pro` | 15 | 13 | 13 | 10 | 10 | 10 |
| `gpt-5-2` | 15 | 13 | 10 | 10 | 9 | 8 |
| `grok-4-3` | 15 | 14 | 12 | 10 | 10 | 8 |
| `mistral-large-3` | 15 | 12 | 11 | 10 | 9 | 9 |
| `qwen3-max` | 15 | 12 | 11 | 10 | 10 | 9 |

## 10. Sensibilite Aux Facteurs Rotatifs

Regles du rapport:

| Champ | Valeur |
|---|---|
| `n_rows_raw` | 2698 |
| `n_rows_after_exclusions` | 2698 |
| Pairing unit | `item_id x system_prompt` |
| Scenario test | Wilcoxon `base` vs `variation` |
| Formulation test | Friedman `F1/F2/F3` |
| Temperature test | Wilcoxon ou Friedman selon nombre de niveaux |

P-values et statuts:

| Modele | Scenario p | Scenario status | Formulation p | Formulation status | Temperature p | Temperature status |
|---|---:|---|---:|---|---:|---|
| `claude-sonnet-4-5` | 0.838696 | `ok` | 0.835699 | `ok` | 0.925961 | `ok` |
| `gemini-3-pro` | 0.772900 | `ok` | 0.499352 | `ok` | 0.027962 | `ok` |
| `gpt-5-2` | 0.332561 | `ok` | 0.446949 | `ok` | n/a | `not_applicable` |
| `grok-4-3` | 0.664749 | `ok` | 0.095408 | `ok` | 0.021103 | `ok` |
| `mistral-large-3` | 0.296322 | `ok` | 0.224238 | `ok` | 0.808867 | `ok` |
| `qwen3-max` | 0.829034 | `ok` | 0.416862 | `ok` | 0.821797 | `ok` |

Raison `not_applicable` pour `gpt-5-2`: `Temperature parameter was not sent for
this model.`

## 11. Decomposition De Variance

Regles du rapport:

| Champ | Valeur |
|---|---|
| `n_rows_raw` | 2698 |
| `n_rows_after_exclusions` | 2698 |
| Exploratory metric | ANOVA-style eta squared |
| Confirmatory model | Linear Mixed Model |

Eta squared par facteur:

| Facteur | Eta squared |
|---|---:|
| `item_id` | 0.4708882152 |
| `run` | 0.0059799136 |
| `formulation` | 0.0035189251 |
| `model` | 0.0025257772 |
| `system_prompt` | 0.0021097949 |
| `temperature` | 0.0011773107 |
| `scenario` | 0.0005257876 |

Ranking du rapport:

```text
item_id > run > formulation > model > system_prompt > temperature > scenario
```

Resume LMM:

| Champ | Valeur |
|---|---|
| `status` | `ok` |
| `used_model` | `primary` |
| `n_obs` | 2698 |
| `converged` | true |
| `aic` | 3534.971388315702 |
| `bic` | 3753.281231676107 |
| `log_likelihood` | -1730.485694157851 |
| `attempt_history` | empty |

Random effects:

| Effet | Valeur |
|---|---:|
| `item_intercept` | 0.2155404712 |
| `vc_1` | 0.0383519471 |
| `vc_2` | 0.0439954583 |

Formule fixe reportee:

```text
score_numeric ~ C(model) * C(system_prompt)
              + C(model) * C(temperature)
              + C(scenario)
              + C(formulation)
```

## 12. Diagnostic Cross-System-Prompt

Regles du rapport:

| Champ | Valeur |
|---|---|
| `n_rows_raw` | 2700 |
| `n_rows_after_exclusions` | 2698 |
| Correlations | Pearson sur moyennes `item_id x run` |
| Amplitude SP | max(mean score by SP) - min(mean score by SP) |
| Exemples bruts | disponibles dans `cross_sp_diagnostic.json` |

Correlations cross-SP par modele et paire:

| Modele | Paire | Correlation | N paires | Status |
|---|---|---:|---:|---|
| `claude-sonnet-4-5` | `SP_ABS_vs_SP_DIR` | 0.672025 | 149 | `ok` |
| `claude-sonnet-4-5` | `SP_ABS_vs_SP_PER` | 0.624048 | 148 | `ok` |
| `claude-sonnet-4-5` | `SP_DIR_vs_SP_PER` | 0.693535 | 149 | `ok` |
| `gemini-3-pro` | `SP_ABS_vs_SP_DIR` | 0.752227 | 150 | `ok` |
| `gemini-3-pro` | `SP_ABS_vs_SP_PER` | 0.621418 | 150 | `ok` |
| `gemini-3-pro` | `SP_DIR_vs_SP_PER` | 0.565435 | 150 | `ok` |
| `gpt-5-2` | `SP_ABS_vs_SP_DIR` | 0.703313 | 150 | `ok` |
| `gpt-5-2` | `SP_ABS_vs_SP_PER` | 0.734847 | 150 | `ok` |
| `gpt-5-2` | `SP_DIR_vs_SP_PER` | 0.703925 | 150 | `ok` |
| `grok-4-3` | `SP_ABS_vs_SP_DIR` | 0.714076 | 150 | `ok` |
| `grok-4-3` | `SP_ABS_vs_SP_PER` | 0.538668 | 150 | `ok` |
| `grok-4-3` | `SP_DIR_vs_SP_PER` | 0.476709 | 150 | `ok` |
| `mistral-large-3` | `SP_ABS_vs_SP_DIR` | 0.578006 | 150 | `ok` |
| `mistral-large-3` | `SP_ABS_vs_SP_PER` | 0.373934 | 150 | `ok` |
| `mistral-large-3` | `SP_DIR_vs_SP_PER` | 0.318910 | 150 | `ok` |
| `qwen3-max` | `SP_ABS_vs_SP_DIR` | 0.716802 | 150 | `ok` |
| `qwen3-max` | `SP_ABS_vs_SP_PER` | 0.739210 | 150 | `ok` |
| `qwen3-max` | `SP_DIR_vs_SP_PER` | 0.688899 | 150 | `ok` |

Amplitude system-prompt par item:

| Item | Type | Mean SP range | Max SP range | Min SP range | N modeles |
|---|---|---:|---:|---:|---:|
| `E2` | personality | 0.666667 | 1.700000 | 0.100000 | 6 |
| `M_CH` | moral | 0.533333 | 0.900000 | 0.200000 | 6 |
| `N2` | personality | 0.500000 | 0.700000 | 0.200000 | 6 |
| `M_PS` | moral | 0.433333 | 0.700000 | 0.000000 | 6 |
| `A1` | personality | 0.416667 | 0.800000 | 0.100000 | 6 |
| `N1` | personality | 0.366667 | 0.600000 | 0.100000 | 6 |
| `C2` | personality | 0.366667 | 0.500000 | 0.100000 | 6 |
| `O1` | personality | 0.350000 | 0.700000 | 0.100000 | 6 |
| `O2` | personality | 0.333333 | 0.500000 | 0.100000 | 6 |
| `M_LB` | moral | 0.300000 | 0.700000 | 0.000000 | 6 |
| `M_AS` | moral | 0.266667 | 0.300000 | 0.200000 | 6 |
| `A2` | personality | 0.216667 | 0.500000 | 0.000000 | 6 |
| `M_FC` | moral | 0.166667 | 0.400000 | 0.000000 | 6 |
| `C1` | personality | 0.116667 | 0.300000 | 0.000000 | 6 |
| `E1` | personality | 0.000000 | 0.000000 | 0.000000 | 6 |

Top cellules model x item par amplitude SP:

| Rank | Modele | Item | Type | SP_ABS | SP_DIR | SP_PER | Range | N ABS | N DIR | N PER |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `mistral-large-3` | `E2` | personality | 0.800000 | 0.600000 | -0.900000 | 1.700000 | 10 | 10 | 10 |
| 2 | `qwen3-max` | `M_CH` | moral | -0.200000 | 0.400000 | -0.500000 | 0.900000 | 10 | 10 | 10 |
| 3 | `claude-sonnet-4-5` | `A1` | personality | -0.500000 | -0.300000 | 0.300000 | 0.800000 | 10 | 10 | 10 |
| 4 | `gemini-3-pro` | `M_CH` | moral | 0.500000 | 0.800000 | 0.000000 | 0.800000 | 10 | 10 | 10 |
| 5 | `mistral-large-3` | `M_PS` | moral | -0.100000 | -0.300000 | -0.800000 | 0.700000 | 10 | 10 | 10 |
| 6 | `claude-sonnet-4-5` | `M_CH` | moral | 0.000000 | 0.700000 | 0.444444 | 0.700000 | 9 | 10 | 9 |
| 7 | `gemini-3-pro` | `M_LB` | moral | 1.000000 | 1.000000 | 0.300000 | 0.700000 | 10 | 10 | 10 |
| 8 | `gemini-3-pro` | `N2` | personality | 0.700000 | 0.600000 | 0.000000 | 0.700000 | 10 | 10 | 10 |
| 9 | `grok-4-3` | `A1` | personality | -0.500000 | -0.600000 | 0.100000 | 0.700000 | 10 | 10 | 10 |
| 10 | `grok-4-3` | `E2` | personality | 0.300000 | 0.200000 | -0.400000 | 0.700000 | 10 | 10 | 10 |
| 11 | `grok-4-3` | `N2` | personality | 0.000000 | 0.500000 | -0.200000 | 0.700000 | 10 | 10 | 10 |
| 12 | `grok-4-3` | `O1` | personality | 0.600000 | 0.400000 | -0.100000 | 0.700000 | 10 | 10 | 10 |
| 13 | `qwen3-max` | `N2` | personality | 0.500000 | 0.700000 | 0.000000 | 0.700000 | 10 | 10 | 10 |
| 14 | `gemini-3-pro` | `A1` | personality | 0.100000 | -0.400000 | 0.200000 | 0.600000 | 10 | 10 | 10 |
| 15 | `claude-sonnet-4-5` | `N1` | personality | -0.200000 | -0.600000 | 0.000000 | 0.600000 | 10 | 10 | 10 |
| 16 | `gemini-3-pro` | `E2` | personality | 0.000000 | 0.100000 | -0.500000 | 0.600000 | 10 | 10 | 10 |
| 17 | `gemini-3-pro` | `M_PS` | moral | -1.000000 | -0.400000 | -0.900000 | 0.600000 | 10 | 10 | 10 |
| 18 | `gemini-3-pro` | `N1` | personality | -0.500000 | -0.600000 | 0.000000 | 0.600000 | 10 | 10 | 10 |
| 19 | `grok-4-3` | `M_PS` | moral | 0.200000 | 0.300000 | -0.300000 | 0.600000 | 10 | 10 | 10 |
| 20 | `claude-sonnet-4-5` | `O1` | personality | 1.000000 | 1.000000 | 0.500000 | 0.500000 | 10 | 10 | 10 |
| 21 | `claude-sonnet-4-5` | `O2` | personality | 0.100000 | -0.100000 | 0.400000 | 0.500000 | 10 | 10 | 10 |
| 22 | `gemini-3-pro` | `O2` | personality | 0.300000 | 0.700000 | 0.800000 | 0.500000 | 10 | 10 | 10 |
| 23 | `gpt-5-2` | `A2` | personality | -0.600000 | -0.500000 | -0.100000 | 0.500000 | 10 | 10 | 10 |
| 24 | `gpt-5-2` | `C2` | personality | -0.800000 | -0.500000 | -0.300000 | 0.500000 | 10 | 10 | 10 |
| 25 | `grok-4-3` | `N1` | personality | -0.500000 | -0.600000 | -0.100000 | 0.500000 | 10 | 10 | 10 |
| 26 | `mistral-large-3` | `C2` | personality | -0.500000 | -0.600000 | -0.100000 | 0.500000 | 10 | 10 | 10 |
| 27 | `mistral-large-3` | `M_LB` | moral | 1.000000 | 0.500000 | 0.700000 | 0.500000 | 10 | 10 | 10 |
| 28 | `qwen3-max` | `E2` | personality | 0.000000 | -0.500000 | -0.400000 | 0.500000 | 10 | 10 | 10 |
| 29 | `claude-sonnet-4-5` | `A2` | personality | -0.400000 | 0.000000 | -0.200000 | 0.400000 | 10 | 10 | 10 |
| 30 | `claude-sonnet-4-5` | `C2` | personality | -0.600000 | -1.000000 | -0.800000 | 0.400000 | 10 | 10 | 10 |

## 13. Artefacts De Sortie

Rapports:

| Fichier | Contenu |
|---|---|
| `outputs/reports/decision_report.json` | checks globaux et decision automatique |
| `outputs/reports/stability_report.json` | stabilite par modele, item, trait/fondation |
| `outputs/reports/sensitivity_report.json` | tests scenario/formulation/temperature |
| `outputs/reports/variance_decomposition_report.json` | eta squared et LMM |
| `outputs/reports/cross_sp_diagnostic.json` | diagnostic detaille cross-SP |
| `outputs/reports/cross_sp_model_pairs.csv` | correlations SP par modele |
| `outputs/reports/cross_sp_item_amplitudes.csv` | amplitudes SP par item |
| `outputs/reports/cross_sp_top_cells.csv` | top cellules SP |

Figures:

| Fichier | Contenu |
|---|---|
| `outputs/figures/scores_heatmap.png` | scores moyens par modele et item |
| `outputs/figures/stability_boxplots.png` | distribution des scores par run |
| `outputs/figures/variance_eta_squared.png` | eta squared par facteur |
| `outputs/figures/cross_temperature_profiles.png` | profils par temperature |
| `outputs/figures/cross_sp_profiles.png` | profils par system prompt |
| `outputs/figures/radar_claude-sonnet-4-5.png` | radar Big Five Claude |
| `outputs/figures/radar_gemini-3-pro.png` | radar Big Five Gemini |
| `outputs/figures/radar_gpt-5-2.png` | radar Big Five GPT |
| `outputs/figures/radar_grok-4-3.png` | radar Big Five Grok |
| `outputs/figures/radar_mistral-large-3.png` | radar Big Five Mistral |
| `outputs/figures/radar_qwen3-max.png` | radar Big Five Qwen |

