# SoulBench — SNAP Pipeline v2.1

Pipeline modulaire Python 3.11+ pour la collecte, le scoring, l'analyse et la visualisation selon le protocole SoulBench v2.1.

## Guide Non-Technique

Consulter le guide complet: `GUIDE_NON_TECHNIQUE.md`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commandes

```bash
# Collecte
python -m src.runner collect --model <model_id>
python -m src.runner collect --all

# Scoring
python -m src.runner score --judge haiku
python -m src.runner score --judge kimi
python -m src.runner score --resolve-disagreements
python -m src.runner resolve-disagreements

# Vérification manuelle
python -m src.runner export-sample --n 4536
python -m src.runner import-manual --file data/manual_sample_coded.csv
python -m src.runner compute-kappa
python -m src.runner adjudicate

# Analyse
python -m src.runner analyze --stability
python -m src.runner analyze --sensitivity
python -m src.runner analyze --variance-decomposition

# Visualisation
python -m src.runner visualize --all

# Tests
python -m pytest -v
```

## FAIT

- Architecture complète créée: `config/`, `src/`, `data/`, `outputs/`, `tests/`.
- Schéma SQLite implémenté (tables `responses`, `collection_metadata`, `manual_verification`).
- Index protocole implémentés + index unique idempotence pour checkpoint/reprise.
- Couche DB modulaire avec CRUD, reprise, export/import manuel, accès analyse, kappa.
- Client OpenRouter async (`httpx`) implémenté avec:
  - timeout retry 30s max 3,
  - rate limit 429 backoff 60/120/240,
  - 5xx retry 60s max 3,
  - 4xx (hors 429) skip structuré,
  - réponse vide retry 1 fois.
- Assembleur de prompts implémenté:
  - `SP_ABS` sans message `system`,
  - assemblage `scenario + "\n\n" + formulation`,
  - génération et shuffle déterministe des 3780 conditions/modèle.
- Orchestrateur CLI complet (`src/runner.py`) avec toutes les sous-commandes demandées.
- Alias CLI supporté: `resolve-disagreements`.
- Scoring pipeline implémenté:
  - prompt standardisé §9.2,
  - parsing `SCORE/INDICATEURS/JUSTIFICATION`,
  - retry parsing invalide (1 fois),
  - résolution des désaccords (agree/minor/major/type),
  - arrondi minor disagreement: banker’s rounding.
- Analyse skeleton exécutable implémentée:
  - stabilité, sensibilité, décomposition de variance,
  - rapports JSON écrits dans `outputs/reports/`,
  - gestion safe sur DB vide.
- Visualisations skeleton implémentées:
  - radar Big Five,
  - heatmap,
  - boxplots,
  - bar chart eta²,
  - profils cross-température,
  - profils cross-SP,
  - gestion safe sur DB vide.
- Fichiers YAML créés et validables.
- Tests unitaires créés:
  - `tests/test_db.py`
  - `tests/test_prompt_builder.py`
  - `tests/test_scorer.py`
  - `tests/test_analyzer.py`

## CONFIGURATION STATUS

- `config/models.yaml`
  - IDs OpenRouter renseignés (6 modèles panel + 2 juges).
  - matrice thinking/reasoning finale par modèle à confirmer avant lancement.
- `config/items_personality.yaml`
  - 10 items renseignés (scénarios, formulations, scoring).
- `config/items_moral.yaml`
  - 5 items renseignés (scénarios, formulations, scoring).
- `config/scoring_rubrics.yaml`
  - 15 rubriques générées depuis les champs `scoring` des items (à valider scientifiquement).
- `config/methodology_h4.md`
  - décision H4 ANOVA (exploratoire) + LMM (confirmatoire) documentée.
- `config/methodology_retest.md`
  - stratégie test-retest documentée.
- `config/manual_adjudication_workflow.md`
  - workflow d adjudication manuelle documenté.

## TODOs

- `# TODO: Compléter la matrice thinking/reasoning par modèle (vérification OpenRouter).`
- `# TODO: Mettre à jour config/methodology_h4.md et config/methodology_retest.md en cas de changement méthodologique.`
- `# TODO: Calcul coût total (collecte + scoring) avec pricing OpenRouter au moment du lancement.`

## PROCHAINES ÉTAPES

1. Vérifier la matrice thinking/reasoning par modèle et exporter `OPENROUTER_API_KEY`.
2. Lancer un test smoke collecte/scoring sur un seul modèle avec petit volume.
3. Traiter les cas `manual_review_needed` avec `python -m src.runner adjudicate`.
4. Calculer kappa puis lancer analyses et visualisations.
5. Lancer collecte/scoring complets et calculer le coût final OpenRouter.
