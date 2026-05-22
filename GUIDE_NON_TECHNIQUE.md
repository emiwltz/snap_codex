# Guide Non Technique
## SoulBench SNAP Pipeline v3.1 POC

Ce guide explique comment utiliser la pipeline sans lire le code.

## 0) Etat reel aujourd hui

Etat actuel du repo:

- Le pipeline est executable de bout en bout via la CLI.
- La configuration experimentale est remplie: modeles, items, rubriques, protocole v3.1.
- Le protocole actif est `config/protocol.yaml`.
- Le design actif prevoit `450` conditions par modele.
- La campagne v3.1 locale est maintenant complete: `2700/2700` reponses collectees.
- Le scoring final est complet: `2700/2700` reponses ont un `score_final`.
- La decision POC finale est `FAIL`.
- Ce `FAIL` vient de la stabilite/context robustness, pas d un probleme de collecte ou de scoring.
- Les deux checks echoues sont `minimum_model_icc = 0.5486` et `minimum_cross_sp_corr = 0.3189`, tous deux sous le seuil `0.60`.
- Le kappa inter-juges passe: `0.7509`.
- Les refus sont quasi absents: `0.00074`.
- Les tests se lancent avec `.venv/bin/python -m pytest -q`.

Conclusion simple: l outillage fonctionne et le POC v3.1 a produit un resultat interpretable, mais le protocole ne justifie pas encore une extension plus large. La suite doit diagnostiquer l effet des system prompts, surtout `SP_PER`, avant de relancer une campagne.

## 1) Ce que fait le projet

Le projet automatise 7 etapes:

1. Collecter des reponses LLM.
2. Faire scorer chaque reponse par 2 juges LLM.
3. Resoudre les desaccords de scoring.
4. Exporter un echantillon pour verification humaine.
5. Reimporter les annotations humaines et calculer des kappas.
6. Produire des rapports statistiques JSON.
7. Produire des figures PNG.

## 2) Fichiers importants

- `config/`: regles de l experience (modeles, items, rubriques).
- `src/`: logique de la pipeline.
- `data/`: base SQLite + fichiers CSV manuels.
- `outputs/reports/`: rapports JSON.
- `outputs/figures/`: graphiques PNG.
- `README.md`: reference technique rapide.

## 3) Prerequis

1. Python 3.11+ installe.
2. Acces terminal.
3. Cle OpenRouter (pour collecte/scoring).

Installation standard:

```bash
cd /Users/emi/code/side/snap_codex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4) Avant de lancer une vraie campagne

Point critique: choisir explicitement une base de campagne pour eviter de melanger des essais.

Recommandation pratique pour eviter toute confusion:

- Repartir sur une nouvelle base avec `--db-path`.
- Garder le `dataset_id` et le `protocol_version` du fichier `config/protocol.yaml`.

Exemple avec nouvelle base:

```bash
python -m src.runner --db-path data/snap_poc_v3_1.db collect --model claude-sonnet-4-5
```

## 5) Procedure complete (pas a pas)

### Etape A - Verifier que la CLI repond

```bash
python -m src.runner --help
```

### Etape B - Creer une base v3.1 propre

```bash
python -m src.runner init-db --reset
```

### Etape C - Verifier OpenRouter et le cout estime

```bash
python -m src.runner preflight
```

Le rapport est ecrit dans `outputs/reports/preflight_report.json`.

### Etape D - Verifier que les tests passent

```bash
python -m pytest -q
```

Attendu: tests verts.

### Etape E - Definir la cle API

```bash
export OPENROUTER_API_KEY="votre_cle"
```

### Etape F - Lancer la collecte

Smoke test limite:

```bash
python -m src.runner collect --model claude-sonnet-4-5 --max-rows 10
```

Un modele:

```bash
python -m src.runner collect --model claude-sonnet-4-5
```

Tous les modeles actifs:

```bash
python -m src.runner collect --all
```

### Etape G - Lancer le scoring

```bash
python -m src.runner score --judge haiku --max-rows 100
python -m src.runner score --judge kimi --max-rows 100
```

Puis resolution:

```bash
python -m src.runner score --resolve-disagreements
```

Alias equivalent:

```bash
python -m src.runner resolve-disagreements
```

### Etape H - Verification humaine

Exporter un echantillon:

```bash
python -m src.runner export-sample --n 200 --output data/manual_sample.csv
```

Pour le snapshot v3.1 actuel, un fichier de travail existe deja:

```bash
data/manual_sample_coded.csv
```

Le coder manuellement, puis importer dans la copie de travail de la base, pas
dans la base finale:

```bash
python -m src.runner --db-path data/snap_poc_v3_1_human_validation_working.db import-manual --file data/manual_sample_coded.csv
```

Si des lignes demandent une revue manuelle:

```bash
python -m src.runner adjudicate --limit 0
```

Calculer les kappas:

```bash
python -m src.runner --db-path data/snap_poc_v3_1_human_validation_working.db compute-kappa
```

La commande calcule maintenant aussi `kappa_human_score_final`, en plus de
`kappa_human_judge1` et `kappa_human_judge2`.

### Etape I - Generer les rapports

```bash
python -m src.runner analyze --stability
python -m src.runner analyze --sensitivity
python -m src.runner analyze --variance-decomposition
python -m src.runner analyze --cross-sp-diagnostic
```

### Etape J - Generer les figures

```bash
python -m src.runner visualize --all
```

### Etape K - Generer la decision POC

```bash
python -m src.runner decision
```

Le rapport est ecrit dans `outputs/reports/decision_report.json`.

## 6) Ou recuperer les resultats

### Donnees brutes

- Base SQLite: votre chemin `--db-path`, par exemple `data/snap_poc_v3_1.db`.

### CSV de verification manuelle

- Export: `data/manual_sample.csv`
- Import attendu: `data/manual_sample_coded.csv`

### Rapports JSON

Dossier: `outputs/reports/`

- `stability_report.json`
- `sensitivity_report.json`
- `variance_decomposition_report.json`
- `decision_report.json`
- `cross_sp_diagnostic.json`
- `cross_sp_model_pairs.csv`
- `cross_sp_item_amplitudes.csv`
- `cross_sp_top_cells.csv`

### Figures PNG

Dossier: `outputs/figures/`

- `radar_<model>.png` (ou `radar_empty.png`)
- `scores_heatmap.png`
- `stability_boxplots.png`
- `variance_eta_squared.png`
- `cross_temperature_profiles.png`
- `cross_sp_profiles.png`

### Resume final v3.1

- `POC_v3_1_summary.md`

## 7) Comment lire les resultats (sans jargon)

### Stabilite

Dans `stability_report.json`, regarder:

- `test_retest_pearson`
- `icc`
- `cross_temperature_corr`
- `cross_sp_corr`

Lecture simple:

- Plus c est eleve, plus les scores sont stables.
- Plus c est bas, plus les scores changent selon le contexte.
- En v3.1, la stabilite est calculee sur `item_id x system_prompt` observe
  sur les 10 runs.

### Sensibilite

Dans `sensitivity_report.json`, regarder:

- `scenario_effect_wilcoxon`
- `formulation_effect_friedman`

Lecture simple:

- Si l effet est fort, le modele reagit beaucoup au contexte/au wording.

### Decomposition de variance

Dans `variance_decomposition_report.json`, regarder:

- `factors`
- `ranking`

Lecture simple:

- Les premiers facteurs du ranking expliquent la plus grande part de variation.

## 8) Controle qualite avant interpretation

Verifier au minimum:

1. Donnees valides collectees (pas seulement des erreurs API).
2. Les deux juges ont score les memes lignes.
3. Les desaccords ont ete resolus ou adjudicates.
4. Les rapports JSON sont en `status: "ok"`.
5. Les figures ne sont pas des placeholders "No data available".

Si un de ces points echoue, ne pas conclure scientifiquement.

## 9) Problemes frequents

### Cas 1 - `OPENROUTER_API_KEY` absente

Symptome:

- Collecte/scoring skips avec warning.

Action:

```bash
export OPENROUTER_API_KEY="votre_cle"
```

### Cas 2 - `No rows pending scoring`

Symptome:

- Rien a scorer.

Ca signifie:

- soit la collecte n a pas produit de reponses valides,
- soit ce juge a deja tout score.

### Cas 3 - Rapports/figures vides

Symptome:

- `status: "empty"` dans les rapports,
- figures avec "No data available".

Cause la plus probable:

- pas de `score_final` exploitable dans la base.

### Cas 4 - Warnings statistiques pendant les tests

Observation actuelle:

- 12 warnings (scipy/statsmodels) apparaissent sur donnees synthetiques de test.

Interpretation:

- ce n est pas un echec de test,
- mais c est un signal que la partie LMM peut etre numeriquement sensible.

## 10) Checklist execution rapide

### Avant campagne

1. Environnement Python pret.
2. Tests verts.
3. Base v3.1 propre creee avec `init-db --reset`.
4. Preflight OpenRouter OK.
5. Cle API definie.
6. Choix explicite du `--db-path` de campagne.

### Pendant campagne

1. Collecte en cours avec progression.
2. Scoring des 2 juges termine.
3. Resolution des desaccords effectuee.

### Apres campagne

1. Kappa calcule.
2. Rapports JSON generes.
3. Figures PNG generees.
4. Rapport `decision` genere.
5. Verification qualite faite avant interpretation.

## 11) Limites actuelles a garder en tete

- Certains providers ne supportent pas tous les parametres OpenRouter. Quand un
  parametre est omis par modele, la DB trace `temperature_applied` et
  `top_p_applied`.
- `thinking_enabled` est derive du `thinking_mode` configure pour le modele. Ce
  n est pas une observation du contenu interne de la reponse.
- Le cout OpenRouter de `preflight` est une estimation avant campagne, pas une facture finale.
- `decision` retourne `NOT_READY` tant que les donnees scorees et les rapports d analyse ne sont pas disponibles.
- La base `data/snap_poc_v3_1.db` sert de snapshot final v3.1. Utiliser une copie de travail pour les imports manuels.
- `data/manual_sample_coded.csv` est prepare mais non code: il ne faut pas importer ce fichier tant que `human_score` est vide.
- Le diagnostic actuel pointe une sensibilite forte au system prompt, notamment autour de `SP_PER`; une v3.2 doit traiter ce point explicitement.
