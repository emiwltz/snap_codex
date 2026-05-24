# SoulBench - SNAP Pipeline v3.1 POC

Pipeline Python pour collecter, scorer, analyser et visualiser des reponses LLM selon le protocole SoulBench.

Guide non-technique: `GUIDE_NON_TECHNIQUE.md`.
Protocole experimental actif: `PROTOCOLE_EXPERIMENTAL_SNAP_v3_1.md`.
Ancien protocole POC source: `PROTOCOLE_EXPERIMENTAL_SNAP_v1_1.md`.
Ancien protocole full-factorial: `PROTOCOLE_EXPERIMENTAL_SNAP_v2_1.md`.
Resume final du POC v3.1: `POC_v3_1_summary.md`.

## Etat actuel de la codebase

Le depot utilise maintenant le protocole v3.1: un POC gerable proche du design v1.1, mais avec les briques techniques utiles de la v2.1.

Etat experimental local au 23 mai 2026:

- Campagne v3.1 complete: `2700/2700` reponses collectees, `0` erreur finale.
- Scoring final complet: `2700/2700` lignes avec `score_final`.
- Adjudication complete: `30` lignes `manual_adjudicated`, `0` revue manuelle restante.
- Decision POC automatisee: `FAIL`.
- Cause du `FAIL`: seuils de stabilite non atteints sur `minimum_model_icc` (`0.5486 < 0.60`) et `minimum_cross_sp_corr` (`0.3189 < 0.60`).
- Les checks operationnels passent: kappa inter-juges `0.7509`, refus `0.00074`, desaccords majeurs initiaux `0.0089`.
- Figures generees dans `outputs/figures/`.
- Diagnostic cross-SP genere dans `outputs/reports/cross_sp_diagnostic.json`.
- Base finale a conserver comme snapshot: `data/snap_poc_v3_1.db`.
- Base recommandee pour la validation humaine: `data/snap_poc_v3_1_human_validation_clean.db`.
- Ancien artefact mixte conserve a titre historique: `data/snap_poc_v3_1_human_validation_working.db`.
- Echantillon humain code et importe: `data/manual_sample_coded.csv` contient `200` lignes et `200` `human_score`.
- Validation humaine cloturee le `2026-05-23`: `30` lignes `adjudication`, `200` lignes `human_validation`, `0` doublon `(response_id, source)`.
- Kappas humains calcules sur `manual_verification.source='human_validation'` uniquement: `judge1=0.6234`, `judge2=0.6304`, `score_final=0.5789`.

- CLI operationnelle via `python -m src.runner` avec 13 sous-commandes: `init-db`, `preflight`, `collect`, `score`, `resolve-disagreements`, `export-sample`, `manual-score-sample`, `import-manual`, `compute-kappa`, `adjudicate`, `analyze`, `visualize`, `decision`.
- Configuration presente dans `config/`:
1. 6 modeles actifs (`models.yaml`).
2. 2 juges (`haiku`, `kimi`).
3. 15 items (10 personnalite + 5 moraux).
4. 15 rubriques de scoring.
5. Protocole actif v3.1 (`protocol.yaml`) avec `450` conditions par modele.
- Design actif: `15 items x 3 system prompts x 10 runs = 450` conditions/modele.
- Campagne complete sur 6 modeles: `2700` appels de collecte.
- Scoring bi-juge complet: `5400` appels juge.
- Total theorique hors retries: `8100` appels API.
- Tests unitaires: utiliser `.venv/bin/python -m pytest -q`.

## Architecture

- `src/runner.py`: orchestrateur CLI.
- `src/prompt_builder.py`: chargement YAML et generation des conditions.
- `src/api_client.py`: client OpenRouter async (retry/backoff/ratelimit).
- `src/preflight.py`: verification catalogue OpenRouter + estimation de cout.
- `src/db.py`: schema SQLite, reprise idempotente, export/import manuel, rapports JSON.
- `src/scorer.py`: scoring bi-juge, parsing, resolution des desaccords, kappa.
- `src/analyzer.py`: analyses statistiques.
- `src/visualizer.py`: figures PNG.
- `src/decision.py`: rapport POC `PASS/BORDERLINE/FAIL`.
- `tests/`: tests unitaires.

## Prerequis

- Python 3.11+
- Environnement virtuel recommande
- Cle OpenRouter pour `collect` et `score`

## Installation

```bash
cd /Users/emi/code/side/snap_codex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commandes CLI

```bash
# Preparation
python -m src.runner init-db --reset
python -m src.runner preflight

# Collecte
python -m src.runner collect --model <model_id>
python -m src.runner collect --model <model_id> --max-rows 10
python -m src.runner collect --all

# Scoring
python -m src.runner score --judge haiku --max-rows 100
python -m src.runner score --judge kimi --max-rows 100
python -m src.runner score --resolve-disagreements
python -m src.runner resolve-disagreements

# Verification manuelle
python -m src.runner export-sample --n 200 --output data/manual_sample.csv

# Codage interactif optionnel pour un nouveau sample ou un recodage
python -m src.runner manual-score-sample --file data/manual_sample_coded.csv

# Import / kappa sur la base propre recommandee
python -m src.runner --db-path data/snap_poc_v3_1_human_validation_clean.db import-manual --file data/manual_sample_coded.csv
python -m src.runner adjudicate --limit 0
python -m src.runner --db-path data/snap_poc_v3_1_human_validation_clean.db compute-kappa

# Analyse
python -m src.runner analyze --stability
python -m src.runner analyze --sensitivity
python -m src.runner analyze --variance-decomposition
python -m src.runner analyze --cross-sp-diagnostic

# Visualisation
python -m src.runner visualize --all

# Decision POC
python -m src.runner decision

# Tests
python -m pytest -v
```

## Flux de travail recommande

1. Valider l environnement (`pip install`, puis `pytest`).
2. Creer une base v3.1 propre:
```bash
python -m src.runner init-db --reset
```
3. Verifier les IDs OpenRouter, les prix et le cout estime:
```bash
python -m src.runner preflight
```
4. Exporter la cle API:
```bash
export OPENROUTER_API_KEY="votre_cle"
```
5. Lancer une collecte smoke sur 1 modele avec `--max-rows 10`.
6. Lancer le scoring sur les 2 juges.
7. Resoudre les desaccords.
8. Pour le snapshot actuel, importer `data/manual_sample_coded.csv` dans
   `data/snap_poc_v3_1_human_validation_clean.db`, puis lancer
   `compute-kappa`. `manual-score-sample` reste utile pour un nouveau sample
   ou un recodage, pas comme etape obligatoire de cloture v3.1.
9. Produire les rapports (`analyze`) puis les figures (`visualize`).
10. Generer la decision POC avec `decision`.

## Verification rapide de l etat local

```bash
# Aide CLI
python -m src.runner --help

# Compteurs DB
sqlite3 data/snap_poc_v3_1.db "select count(*) from responses;"
sqlite3 data/snap_poc_v3_1.db "select count(*) from responses where is_error=0;"
sqlite3 data/snap_poc_v3_1.db "select count(*) from responses where score_final is not null;"
sqlite3 data/snap_poc_v3_1.db "select dataset_id, protocol_version, total_planned from collection_metadata;"
sqlite3 data/snap_poc_v3_1_human_validation_clean.db "select source, count(*) from manual_verification group by source order by source;"
sqlite3 data/snap_poc_v3_1_human_validation_clean.db "select source, count(*) from manual_verification where kappa_judge1 is not null group by source order by source;"

# Tests
python -m pytest -q
```

## Limitations connues

- Sans `OPENROUTER_API_KEY`, `collect` et `score` sont skips (warning) et n ecrivent pas de resultats utiles.
- Les sorties d analyse/figures sont pertinentes seulement si des lignes scorees existent (`score_final`).
- Les analyses v3.1 traitent `item_id x system_prompt` comme cible repetee sur les 10 runs; `scenario`, `formulation` et `temperature` sont des attributs de rotation.
- Les parametres OpenRouter peuvent etre adaptes par modele via `disabled_request_parameters`; dans ce cas la DB trace `temperature_applied` et `top_p_applied`.
- Le champ `thinking_enabled` est derive de `thinking_mode` en config. Il trace le mode provider/default attendu, pas une mesure introspective de la reponse.
- Le cout OpenRouter produit par `preflight` est une estimation fondee sur le catalogue courant et des hypotheses de tokens, pas une facture finale.
- La decision `PASS/BORDERLINE/FAIL` depend de rapports d analyse deja generes; avant scoring complet, `decision` peut retourner `NOT_READY`.
- La base finale `data/snap_poc_v3_1.db` sert maintenant de snapshot v3.1. Pour importer du codage humain ou recalculer des kappas avec annotations, utiliser `data/snap_poc_v3_1_human_validation_clean.db`.
- `compute-kappa` continue de calculer `kappa_interjudge` depuis `responses`, mais les metriques humain-vs-machine lisent uniquement `manual_verification.source='human_validation'`.
- `data/snap_poc_v3_1_human_validation_working.db` est conserve comme artefact historique mixte; il n est plus la base recommandee pour cloturer la validation humaine.

## TODO ouverts

- Interpretrer les kappas humains finaux (`0.6234`, `0.6304`, `0.5789`) dans la note methodologique v3.2.
- Lire qualitativement les cellules critiques du diagnostic cross-SP, surtout `mistral-large-3 / E2`.
- Decider si `SP_PER` doit etre retire, reecrit ou traite comme stress-test separe en v3.2.
- Auditer les items style-sensibles (`E1`, `E2`) avant toute extension.
