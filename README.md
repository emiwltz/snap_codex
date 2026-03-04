# SoulBench - SNAP Pipeline v2.1

Pipeline Python pour collecter, scorer, analyser et visualiser des reponses LLM selon le protocole SoulBench.

Guide non-technique: `GUIDE_NON_TECHNIQUE.md`.

## Etat actuel de la codebase (snapshot du 4 mars 2026)

Ce snapshot decrit l etat observe localement dans ce repo au moment de la mise a jour.

- CLI operationnelle via `python -m src.runner` avec 9 sous-commandes: `collect`, `score`, `resolve-disagreements`, `export-sample`, `import-manual`, `compute-kappa`, `adjudicate`, `analyze`, `visualize`.
- Configuration presente dans `config/`:
1. 6 modeles actifs (`models.yaml`).
2. 2 juges (`haiku`, `kimi`).
3. 15 items (10 personnalite + 5 moraux).
4. 15 rubriques de scoring.
- Base SQLite locale presente: `data/soulbench.db`.
1. `responses`: 30 lignes.
2. `is_error=0`: 0 ligne.
3. `is_error=1`: 30 lignes.
4. `score_final` non null: 0 ligne.
5. `collection_metadata`: 1 run (`model=test`, `total_planned=3780`, `end_time` vide).
- `outputs/reports/` et `outputs/figures/` sont vides.
- Tests unitaires: `16 passed, 12 warnings` avec `.venv/bin/python -m pytest -q` (execute le 4 mars 2026).

## Architecture

- `src/runner.py`: orchestrateur CLI.
- `src/prompt_builder.py`: chargement YAML et generation des conditions.
- `src/api_client.py`: client OpenRouter async (retry/backoff/ratelimit).
- `src/db.py`: schema SQLite, reprise idempotente, export/import manuel, rapports JSON.
- `src/scorer.py`: scoring bi-juge, parsing, resolution des desaccords, kappa.
- `src/analyzer.py`: analyses statistiques.
- `src/visualizer.py`: figures PNG.
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
# Collecte
python -m src.runner collect --model <model_id>
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

# Tests
python -m pytest -v
```

## Flux de travail recommande

1. Valider l environnement (`pip install`, puis `pytest`).
2. Exporter la cle API:
```bash
export OPENROUTER_API_KEY="votre_cle"
```
3. Lancer une collecte smoke sur 1 modele.
4. Lancer le scoring sur les 2 juges.
5. Resoudre les desaccords.
6. Export/import manuel si necessaire, puis `compute-kappa`.
7. Produire les rapports (`analyze`) puis les figures (`visualize`).

## Verification rapide de l etat local

```bash
# Aide CLI
python -m src.runner --help

# Compteurs DB
sqlite3 data/soulbench.db "select count(*) from responses;"
sqlite3 data/soulbench.db "select count(*) from responses where is_error=0;"
sqlite3 data/soulbench.db "select count(*) from responses where score_final is not null;"

# Tests
python -m pytest -q
```

## Limitations connues

- Sans `OPENROUTER_API_KEY`, `collect` et `score` sont skips (warning) et n ecrivent pas de resultats utiles.
- Les sorties d analyse/figures sont pertinentes seulement si des lignes scorees existent (`score_final`).
- Le champ `thinking_mode` existe en config/metadata, mais `thinking_enabled` est stocke a `None` ligne par ligne pendant la collecte actuelle.
- Le calcul de cout OpenRouter n est pas automatise dans la codebase.

## TODO ouverts

- Verifier les IDs OpenRouter finaux du panel et des juges.
- Finaliser la matrice thinking/reasoning par modele.
- Ajouter un calcul de cout total (collecte + scoring) au moment du lancement campagne.
