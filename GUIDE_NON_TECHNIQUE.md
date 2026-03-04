# Guide Non Technique
## SoulBench SNAP Pipeline v2.1

Ce guide explique comment utiliser la pipeline sans lire le code.

## 0) Etat reel aujourd hui (4 mars 2026)

Etat observe localement dans ce repo:

- Le pipeline est executable de bout en bout via la CLI.
- La configuration experimentale est deja remplie (modeles, items, rubriques).
- Les tests passent: `16 passed, 12 warnings`.
- Une base existe deja (`data/soulbench.db`) avec une run `test` inachevee:
1. 30 reponses stockees.
2. 30 erreurs API.
3. 0 reponse valide.
4. 0 score final.
- Aucun rapport JSON ni figure PNG n est encore genere dans `outputs/`.

Conclusion simple: l outillage est pret, mais il n y a pas encore de resultats experimentaux exploitables.

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

Point critique: une ancienne base `data/soulbench.db` est deja presente avec des erreurs.

Recommandation pratique pour eviter toute confusion:

- Soit repartir sur une nouvelle base avec `--db-path`.
- Soit supprimer/archiver la base existante avant campagne.

Exemple avec nouvelle base:

```bash
python -m src.runner --db-path data/soulbench_campaign_20260304.db collect --model claude-sonnet-4-5
```

## 5) Procedure complete (pas a pas)

### Etape A - Verifier que la CLI repond

```bash
python -m src.runner --help
```

### Etape B - Verifier que les tests passent

```bash
python -m pytest -q
```

Attendu: tests verts.

### Etape C - Definir la cle API

```bash
export OPENROUTER_API_KEY="votre_cle"
```

### Etape D - Lancer la collecte

Un modele:

```bash
python -m src.runner collect --model claude-sonnet-4-5
```

Tous les modeles actifs:

```bash
python -m src.runner collect --all
```

### Etape E - Lancer le scoring

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

### Etape F - Verification humaine

Exporter un echantillon:

```bash
python -m src.runner export-sample --n 200 --output data/manual_sample.csv
```

Coder le fichier manuellement, puis importer:

```bash
python -m src.runner import-manual --file data/manual_sample_coded.csv
```

Si des lignes demandent une revue manuelle:

```bash
python -m src.runner adjudicate --limit 0
```

Calculer les kappas:

```bash
python -m src.runner compute-kappa
```

### Etape G - Generer les rapports

```bash
python -m src.runner analyze --stability
python -m src.runner analyze --sensitivity
python -m src.runner analyze --variance-decomposition
```

### Etape H - Generer les figures

```bash
python -m src.runner visualize --all
```

## 6) Ou recuperer les resultats

### Donnees brutes

- Base SQLite: `data/soulbench.db` (ou votre chemin `--db-path`).

### CSV de verification manuelle

- Export: `data/manual_sample.csv`
- Import attendu: `data/manual_sample_coded.csv`

### Rapports JSON

Dossier: `outputs/reports/`

- `stability_report.json`
- `sensitivity_report.json`
- `variance_decomposition_report.json`

### Figures PNG

Dossier: `outputs/figures/`

- `radar_<model>.png` (ou `radar_empty.png`)
- `scores_heatmap.png`
- `stability_boxplots.png`
- `variance_eta_squared.png`
- `cross_temperature_profiles.png`
- `cross_sp_profiles.png`

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
3. Cle API definie.
4. Choix explicite du `--db-path` de campagne.

### Pendant campagne

1. Collecte en cours avec progression.
2. Scoring des 2 juges termine.
3. Resolution des desaccords effectuee.

### Apres campagne

1. Kappa calcule.
2. Rapports JSON generes.
3. Figures PNG generees.
4. Verification qualite faite avant interpretation.

## 11) Limites actuelles a garder en tete

- Le calcul de cout OpenRouter n est pas automatise.
- Le suivi fin du `thinking_enabled` n est pas encore renseigne ligne par ligne.
- La base locale actuelle contient surtout un run de test en erreur, pas une campagne complete.
