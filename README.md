# SoulBench - SNAP Pipeline v3.1 POC

Pipeline Python pour collecter, scorer, analyser et visualiser des reponses LLM selon le protocole SoulBench.

Guide non-technique: `GUIDE_NON_TECHNIQUE.md`.
Protocole experimental actif: `PROTOCOLE_EXPERIMENTAL_SNAP_v3_1.md`.
Ancien protocole POC source: `PROTOCOLE_EXPERIMENTAL_SNAP_v1_1.md`.
Ancien protocole full-factorial: `PROTOCOLE_EXPERIMENTAL_SNAP_v2_1.md`.

## Etat actuel de la codebase

Le depot utilise maintenant le protocole v3.1: un POC gerable proche du design v1.1, mais avec les briques techniques utiles de la v2.1.

- CLI operationnelle via `python -m src.runner` avec 12 sous-commandes: `init-db`, `preflight`, `collect`, `score`, `resolve-disagreements`, `export-sample`, `import-manual`, `compute-kappa`, `adjudicate`, `analyze`, `visualize`, `decision`.
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
python -m src.runner import-manual --file data/manual_sample_coded.csv
python -m src.runner adjudicate --limit 0
python -m src.runner compute-kappa

# Analyse
python -m src.runner analyze --stability
python -m src.runner analyze --sensitivity
python -m src.runner analyze --variance-decomposition

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
8. Export/import manuel si necessaire, puis `compute-kappa`.
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

## TODO ouverts

- Revalider les model IDs, les parametres supportes et le pricing OpenRouter juste avant la campagne.
- Ajouter une strategie formelle de double codage humain si le POC passe en campagne plus large.
