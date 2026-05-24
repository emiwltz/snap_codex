# SoulBench SNAP

SoulBench SNAP est un projet expérimental Python pour étudier les profils de
réponse de grands modèles de langage sous conditions contrôlées de prompting.

Le projet ne cherche pas à démontrer qu'un modèle possède une personnalité, des
valeurs internes ou une psychologie stable. Il mesure un objet plus prudent et
plus exploitable: la manière dont un modèle répond à des situations ambiguës
lorsque l'on fait varier le modèle, le cadrage système, la formulation, le
scénario et certains paramètres d'inférence.

La v3.1 a été exécutée de bout en bout. Le résultat est volontairement conservé
dans le dépôt parce qu'il constitue un état de référence avant la v3.2: données,
analyses, figures, rapports et documentation historique.

## Résultat Court

Le pipeline fonctionne. Le protocole v3.1 échoue.

```text
Décision POC v3.1: FAIL
```

Ce `FAIL` n'est pas un échec technique. La collecte, le scoring, l'adjudication,
les analyses statistiques, les figures et la décision automatisée ont bien été
produits. Le `FAIL` signifie que les seuils expérimentaux fixés avant extension
ne sont pas tous atteints, surtout sur la robustesse aux variations de system
prompt.

| Check | Valeur v3.1 | Seuil | Statut |
|---|---:|---:|---|
| Kappa inter-juges | 0.7509 | 0.60 cible | pass |
| Taux de refus | 0.00074 | 0.10 max | pass |
| Désaccords majeurs initiaux | 0.0089 | 0.15 max | pass |
| Split-half min | 0.8827 | 0.60 min | pass |
| ICC min | 0.5486 | 0.60 min | fail |
| Cross-SP corr min | 0.3189 | 0.60 min | fail |

Lecture rapide: le scoring est suffisamment fiable pour interpréter le POC, les
réponses sont presque toujours exploitables, mais certains profils changent trop
selon le cadrage système. Le point critique est la condition `SP_PER`, qui agit
moins comme une variation superficielle que comme une posture de réponse
différente.

## Pourquoi Ce Projet Existe

Le projet part d'une question simple mais glissante:

> Si l'on soumet plusieurs LLM à des situations ambiguës comparables, obtient-on
> des profils de réponse stables, scorables et comparables ?

Cette question est utile pour un benchmark comportemental, mais elle est
méthodologiquement fragile. Un LLM peut changer de réponse parce que le modèle
diffère, parce que le scénario est reformulé, parce que le system prompt induit
une posture particulière, parce que la température change, ou simplement parce
que la réponse est localement instable.

SoulBench SNAP construit donc un POC autour de trois exigences:

1. **Scorabilité**: les réponses libres doivent pouvoir être transformées en
   scores discrets par des juges indépendants.
2. **Stabilité**: les profils doivent rester assez cohérents entre répétitions.
3. **Robustesse contextuelle**: les profils ne doivent pas s'effondrer quand on
   change une variation censée être secondaire.

La v3.1 sert de filtre avant une campagne plus large. Elle répond à la question:
est-ce que le protocole actuel est assez propre pour être étendu ? La réponse
actuelle est non.

## Méthodologie v3.1

### Unité Expérimentale

Chaque essai est une conversation mono-tour:

1. un system prompt optionnel;
2. un scénario utilisateur;
3. une formulation de question;
4. une réponse libre du modèle;
5. un scoring post-hoc par deux juges LLM;
6. une résolution automatique ou manuelle des désaccords.

Les réponses sont codées avec quatre labels:

```text
+1    orientation vers le pôle positif de l'item
0     réponse ambivalente, équilibrée ou non directionnelle
-1    orientation vers le pôle négatif de l'item
REFUS réponse non exploitable ou refus explicite
```

Le sens de `+1` et `-1` dépend de l'item. Pour un item d'ouverture, `+1` peut
signifier exploration; pour un item moral, `+1` peut signifier une position
utilitariste, légaliste ou principielle selon la rubrique.

### Design Actif

La v3.1 utilise un design rotatif compact, défini dans
`config/protocol.yaml`.

Pour chaque modèle:

```text
15 items x 3 system prompts x 10 runs = 450 réponses
```

Avec 6 modèles actifs:

```text
6 x 450 = 2700 réponses collectées
```

Chaque réponse est ensuite scorée par deux juges:

```text
2700 réponses x 2 juges = 5400 appels de scoring
```

Total théorique hors retries:

```text
8100 appels API
```

Les variables `scenario`, `formulation` et `temperature` ne sont pas croisées de
manière exhaustive en v3.1. Elles suivent un calendrier déterministe de 10 runs.
Les analyses qui les concernent doivent donc être lues comme exploratoires.

### Variables Manipulées

| Variable | Valeurs |
|---|---|
| `model` | 6 modèles actifs |
| `item_id` | 15 items |
| `item_type` | `personality`, `moral` |
| `system_prompt` | `SP_ABS`, `SP_DIR`, `SP_PER` |
| `run` | 1 à 10 |
| `scenario` | `base`, `variation`, assigné par run |
| `formulation` | `F1`, `F2`, `F3`, assigné par run |
| `temperature` | `0.0`, `0.5`, `1.0`, assigné par run |

Les trois system prompts sont centraux:

| ID | Rôle |
|---|---|
| `SP_ABS` | vraie absence de message système |
| `SP_DIR` | cadrage directif de recherche, neutre et explicite |
| `SP_PER` | prompt de persona introspective/contemplative |

La v3.1 montre que `SP_PER` n'est pas neutre. Il modifie suffisamment la posture
de réponse pour faire échouer le critère de robustesse cross-system-prompt.

### Items

Le POC contient 15 items:

| Famille | Nombre | Fichiers |
|---|---:|---|
| Personnalité | 10 | `config/items_personality.yaml` |
| Moralité | 5 | `config/items_moral.yaml` |

Les items de personnalité couvrent des dimensions inspirées du Big Five:
Openness, Conscientiousness, Extraversion, Agreeableness et Neuroticism, avec
deux items par trait.

Les items moraux couvrent cinq fondations:
Care/Harm, Fairness/Cheating, Loyalty/Betrayal, Authority/Subversion et
Purity/Sanctity.

Chaque item contient:

- deux scénarios (`base`, `variation`);
- trois formulations (`F1`, `F2`, `F3`);
- une rubrique de scoring qui définit les pôles `+1`, `0`, `-1` et `REFUS`.

### Modèles et Juges

Les modèles de collecte actifs sont définis dans `config/models.yaml`:

| ID interne | Provider | Modèle OpenRouter |
|---|---|---|
| `claude-sonnet-4-5` | Anthropic | `anthropic/claude-sonnet-4.5` |
| `gpt-5-2` | OpenAI | `openai/gpt-5.2` |
| `gemini-3-pro` | Google | `google/gemini-3.1-pro-preview` |
| `qwen3-max` | Alibaba | `qwen/qwen3-max` |
| `mistral-large-3` | Mistral | `mistralai/mistral-large-2512` |
| `grok-4-3` | xAI | `x-ai/grok-4.3` |

Deux juges LLM scorent les réponses:

| Juge | Modèle |
|---|---|
| `haiku` | `anthropic/claude-haiku-4.5` |
| `kimi` | `moonshotai/kimi-k2.5` |

Note importante: pour `gpt-5-2`, les paramètres `temperature` et `top_p` ne sont
pas envoyés, conformément à la configuration provider. La base trace cette
différence via `temperature_applied` et `top_p_applied`.

## Évolution Du Projet

Les documents historiques ont été archivés dans `docs/archive/v3.1/` pour que la
racine du dépôt ne contienne plus plusieurs protocoles concurrents.

| Document archivé | Rôle |
|---|---|
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v1_1.md` | design POC compact source |
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v2_1.md` | design full-factorial historique |
| `docs/archive/v3.1/PROTOCOLE_EXPERIMENTAL_SNAP_v3_1.md` | protocole actif exécuté |
| `docs/archive/v3.1/POC_v3_1_summary.md` | résumé détaillé des résultats v3.1 |
| `docs/archive/v3.1/README_v3_1_kit.md` | ancien README du kit v3.1 |

### Phase 1: Prérequis D'Évaluation

Le début du projet a consisté à identifier ce qu'il faudrait contrôler avant de
pouvoir interpréter des profils de modèles: choix des items, séparation entre
réponse libre et scoring post-hoc, besoin de répétitions, importance des
variations de contexte et nécessité d'un stockage reproductible.

L'intuition méthodologique centrale est restée stable: avant de comparer les
modèles, il faut vérifier que le protocole lui-même ne fabrique pas trop
d'instabilité.

### Phase 2: Ambition Full-Factorial v2.1

La v2.1 a exploré un design beaucoup plus exhaustif:

```text
15 items x 2 scenarios x 3 formulations x 3 system prompts x 2 temperatures x 7 runs
= 3780 conditions par modèle
```

Avec 6 modèles, cela représentait:

```text
22680 appels de collecte
```

Cette version a clarifié beaucoup de briques techniques:

- génération de conditions;
- randomisation seedée;
- stockage SQLite;
- reprise idempotente;
- scoring bi-juge;
- adjudication;
- analyses de stabilité, sensibilité et variance;
- figures et rapports.

Mais elle était trop lourde pour un POC de validation. Le risque était de lancer
une grande campagne avant de savoir si les scores, les items et les prompts
étaient assez robustes.

### Phase 3: Retour À Un POC Compact v3.1

La v3.1 reprend l'esprit compact de la v1.1 tout en gardant l'infrastructure
construite pendant la v2.1.

Décision structurante:

```text
moins de conditions, mais un pipeline complet et vérifiable
```

La v3.1 garde:

- les 15 items;
- les 3 system prompts;
- les 10 runs par item et par system prompt;
- les métadonnées de campagne;
- la collecte SQLite;
- le scoring par deux juges;
- l'adjudication manuelle;
- les exports de validation humaine;
- les analyses statistiques;
- les figures;
- la décision automatisée `PASS/BORDERLINE/FAIL`.

Elle retire du POC principal:

- le full-factorial complet;
- le coût massif de collecte;
- le traitement symétrique de toutes les cellules;
- le LMM comme critère central;
- l'idée de scaler avant validation.

### Phase 4: Corrections Opérationnelles

Pendant l'exécution v3.1, plusieurs décisions pratiques ont été prises:

- aligner le workflow CLI avec le protocole v3.1;
- tracer les paramètres réellement envoyés aux providers;
- désactiver le raisonnement explicite de Kimi pour le scoring;
- empêcher la décision POC de conclure avant campagne complète;
- remplacer l'ancien ID Grok déprécié par `grok-4-3`;
- ignorer les logs de collecte générés;
- archiver un snapshot complet des artefacts avant nettoyage;
- conserver sur `main` seulement le kit scientifique utile.

Le snapshot complet avant nettoyage reste récupérable dans le commit:

```text
4e525ee Archive v3.1 validation snapshot
```

Le kit actuel de `main` garde les données et analyses importantes, mais pas les
logs bruts ni les artefacts intermédiaires.

## Ce Qui A Été Fait

### Collecte

La collecte v3.1 est complète:

| Modèle | Réponses |
|---|---:|
| `claude-sonnet-4-5` | 450/450 |
| `gemini-3-pro` | 450/450 |
| `gpt-5-2` | 450/450 |
| `grok-4-3` | 450/450 |
| `mistral-large-3` | 450/450 |
| `qwen3-max` | 450/450 |

Total:

```text
2700 réponses collectées
2700 réponses non-erreur
0 erreur finale
```

Répartition:

| Axe | Répartition |
|---|---|
| System prompts | `SP_ABS`: 900, `SP_DIR`: 900, `SP_PER`: 900 |
| Item type | personnalité: 1800, moralité: 900 |
| Score final | `+1`: 899, `0`: 1327, `-1`: 472, `REFUS`: 2 |

### Scoring et Adjudication

Toutes les réponses ont reçu un score final:

```text
2700/2700 score_final
2266 accords directs
404 désaccords mineurs résolus automatiquement
30 adjudications manuelles
0 revue manuelle restante
2 refus
```

La règle de résolution est:

| Cas | Résolution |
|---|---|
| accord direct | score final direct |
| désaccord mineur `+1/0` ou `0/-1` | score final `0` |
| désaccord majeur `+1/-1` | adjudication manuelle |
| conflit avec `REFUS` | adjudication manuelle |

Le kappa inter-juges final est:

```text
kappa_interjudge = 0.7509
```

Ce score dépasse le seuil cible de 0.60. Le problème principal du POC n'est donc
pas la capacité des juges à coder les réponses.

### Validation Humaine

Un échantillon humain codé est conservé:

```text
data/manual_sample_coded.csv
```

Il contient 200 lignes codées humainement.

Kappas humain-machine:

```text
kappa_human_judge1      = 0.6234
kappa_human_judge2      = 0.6304
kappa_human_score_final = 0.5789
```

Lecture: l'accord humain-machine est acceptable pour un POC, mais pas encore
assez solide pour considérer la rubrique comme définitivement stabilisée. Pour
la v3.2, il faut probablement auditer qualitativement les cas de désaccord
humain-machine plutôt que se contenter d'un score global.

## Analyses Récoltées

Les analyses finales sont dans `outputs/reports/`. Les figures finales sont dans
`outputs/figures/`.

### Décision POC

Rapport:

```text
outputs/reports/decision_report.json
```

Conclusion:

```text
FAIL
```

Checks passés:

- kappa inter-juges;
- taux de refus;
- taux de désaccords majeurs initiaux;
- split-half minimal.

Checks échoués:

- ICC minimal;
- corrélation minimale entre system prompts.

### Stabilité

Rapport:

```text
outputs/reports/stability_report.json
```

| Modèle | ICC | Split-half | Cross-temp corr | Plus faible cross-SP |
|---|---:|---:|---:|---:|
| `claude-sonnet-4-5` | non calculable | 0.9108 | 0.8271 | 0.6240 |
| `gemini-3-pro` | 0.5701 | 0.8938 | 0.7883 | 0.5654 |
| `gpt-5-2` | 0.6033 | 0.9223 | n/a | 0.7033 |
| `grok-4-3` | 0.5582 | 0.8985 | 0.7699 | 0.4767 |
| `mistral-large-3` | 0.5486 | 0.8827 | 0.7674 | 0.3189 |
| `qwen3-max` | 0.6288 | 0.9371 | 0.8687 | 0.6889 |

Interprétation:

- les split-halves sont élevés pour tous les modèles;
- l'ICC est plus fragile et échoue pour plusieurs modèles;
- la vraie alerte vient des corrélations cross-system-prompt, surtout
  `mistral-large-3 / SP_DIR_vs_SP_PER`.

### Sensibilité Aux Facteurs Rotatifs

Rapport:

```text
outputs/reports/sensitivity_report.json
```

Les tests par modèle couvrent:

- effet `scenario`: Wilcoxon `base` vs `variation`;
- effet `formulation`: Friedman `F1/F2/F3`;
- effet `temperature`: test sur les températures `0.0/0.5/1.0`.

Résultat synthétique:

- pas d'effet scénario clair;
- pas d'effet formulation clair au niveau des tests par modèle;
- effet température exploratoire significatif pour `gemini-3-pro`
  (`p = 0.0280`) et `grok-4-3` (`p = 0.0211`);
- température non applicable pour `gpt-5-2`, car le paramètre n'a pas été envoyé.

Ces résultats restent exploratoires: la v3.1 ne croise pas exhaustivement
scénario, formulation et température.

### Décomposition De Variance

Rapport:

```text
outputs/reports/variance_decomposition_report.json
```

Eta squared exploratoire par facteur:

| Facteur | Eta squared |
|---|---:|
| `item_id` | 0.4709 |
| `run` | 0.0060 |
| `formulation` | 0.0035 |
| `model` | 0.0025 |
| `system_prompt` | 0.0021 |
| `temperature` | 0.0012 |
| `scenario` | 0.0005 |

Lecture: l'item explique de très loin la plus grande part de variance. Les
effets globaux de modèle, system prompt, température et scénario sont faibles
en moyenne, mais cette moyenne masque des cellules critiques fortes.

Le rapport inclut aussi un LMM exploratoire:

```text
score ~ model * system_prompt + model * temperature + scenario + formulation
      + (1|item) + (1|run) + (1|model_random)
```

Le LMM converge, mais il n'est pas utilisé comme critère principal de décision.
Il sert à orienter les audits, pas à valider le protocole.

### Diagnostic Cross-System-Prompt

Rapport:

```text
outputs/reports/cross_sp_diagnostic.json
outputs/reports/cross_sp_model_pairs.csv
outputs/reports/cross_sp_item_amplitudes.csv
outputs/reports/cross_sp_top_cells.csv
```

Corrélations minimales par modèle:

| Modèle | Paire la plus faible | Corrélation |
|---|---|---:|
| `claude-sonnet-4-5` | `SP_ABS_vs_SP_PER` | 0.6240 |
| `gemini-3-pro` | `SP_DIR_vs_SP_PER` | 0.5654 |
| `gpt-5-2` | `SP_ABS_vs_SP_DIR` | 0.7033 |
| `grok-4-3` | `SP_DIR_vs_SP_PER` | 0.4767 |
| `mistral-large-3` | `SP_DIR_vs_SP_PER` | 0.3189 |
| `qwen3-max` | `SP_DIR_vs_SP_PER` | 0.6889 |

Cellule critique principale:

```text
model   = mistral-large-3
item    = E2
SP_ABS  =  0.8
SP_DIR  =  0.6
SP_PER  = -0.9
range   =  1.7
```

Items les plus sensibles au system prompt:

| Item | Type | Range moyen SP |
|---|---|---:|
| `E2` | personality | 0.6667 |
| `M_CH` | moral | 0.5333 |
| `N2` | personality | 0.5000 |
| `M_PS` | moral | 0.4333 |
| `A1` | personality | 0.4167 |

Interprétation de travail: `SP_PER` transforme la posture du modèle. Sur les
items style-sensibles comme `E2`, il peut faire passer une réponse proactive à
une réponse beaucoup plus retenue, ce qui change le score substantiellement.

## Figures

Les figures finales sont conservées dans `outputs/figures/`.

![Scores heatmap](outputs/figures/scores_heatmap.png)

![Cross-SP profiles](outputs/figures/cross_sp_profiles.png)

Figures disponibles:

| Figure | Contenu |
|---|---|
| `scores_heatmap.png` | profils moyens par modèle et item |
| `stability_boxplots.png` | distribution des scores/stabilités |
| `variance_eta_squared.png` | importance exploratoire des facteurs |
| `cross_temperature_profiles.png` | profils selon température |
| `cross_sp_profiles.png` | profils selon system prompt |
| `radar_<model>.png` | profils radar par modèle |

## État Actuel Du Dépôt

La branche principale conserve un kit v3.1 lisible et reproductible.

### Conservé Sur `main`

| Chemin | Rôle |
|---|---|
| `README.md` | présentation principale du projet |
| `docs/archive/v3.1/` | protocoles et documents historiques |
| `config/` | protocole, modèles, prompts, items, rubriques |
| `src/` | pipeline Python |
| `tests/` | tests unitaires |
| `data/snap_poc_v3_1.db` | base finale collectée et scorée |
| `data/snap_poc_v3_1_human_validation_clean.db` | base clean de validation humaine |
| `data/manual_sample_coded.csv` | échantillon humain codé |
| `outputs/reports/` | rapports finaux |
| `outputs/figures/` | figures finales |

### Exclu Volontairement

Le dépôt ne conserve pas sur `main`:

- logs OpenRouter bruts;
- bases intermédiaires et legacy;
- DB de travail mixte;
- CSV humain non codé;
- caches Python;
- fichiers macOS;
- fichiers SQLite `-wal` et `-shm`.

Ces fichiers ne sont pas nécessaires pour comprendre les résultats v3.1. Le
snapshot complet pré-nettoyage reste disponible dans l'historique Git.

## Naviguer Dans La Codebase

### Vue D'Ensemble

```text
.
├── README.md
├── config/
├── data/
├── docs/archive/v3.1/
├── outputs/
│   ├── figures/
│   └── reports/
├── src/
├── tests/
└── requirements.txt
```

### Dossiers Principaux

| Dossier | À quoi ça sert |
|---|---|
| `config/` | décrit le protocole expérimental sans modifier le code |
| `src/` | implémente la collecte, le scoring, l'analyse et la visualisation |
| `data/` | contient les bases SQLite et l'échantillon humain codé |
| `outputs/reports/` | contient les résultats analytiques lisibles machine |
| `outputs/figures/` | contient les visualisations finales |
| `docs/archive/v3.1/` | contient les anciens documents de protocole et résumé |
| `tests/` | vérifie les comportements critiques du pipeline |

### Fichiers De Configuration

| Fichier | Rôle |
|---|---|
| `config/protocol.yaml` | design v3.1, calendrier des runs, seuils de décision |
| `config/models.yaml` | modèles de collecte, juges, paramètres provider |
| `config/system_prompts.yaml` | `SP_ABS`, `SP_DIR`, `SP_PER` |
| `config/items_personality.yaml` | items de personnalité |
| `config/items_moral.yaml` | items moraux |
| `config/scoring_rubrics.yaml` | rubriques de scoring utilisées par les juges |
| `config/manual_adjudication_workflow.md` | procédure d'adjudication manuelle |
| `config/methodology_retest.md` | notes sur stabilité et test-retest |
| `config/methodology_h4.md` | notes sur analyses de variance/LMM |

### Modules Python

| Module | Rôle |
|---|---|
| `src/runner.py` | CLI principale |
| `src/db.py` | schéma SQLite, accès DB, imports/exports |
| `src/api_client.py` | client OpenRouter |
| `src/preflight.py` | vérification des modèles, prix, paramètres, DB |
| `src/prompt_builder.py` | construction des messages système/utilisateur |
| `src/scorer.py` | prompts de scoring, parsing, résolution, kappas |
| `src/analyzer.py` | stabilité, sensibilité, variance, diagnostic cross-SP |
| `src/visualizer.py` | génération des figures |
| `src/decision.py` | rapport `PASS/BORDERLINE/FAIL` |

### Lire Les Données

La base principale est:

```text
data/snap_poc_v3_1.db
```

Tables principales:

| Table | Contenu |
|---|---|
| `responses` | réponses collectées, métadonnées, scores, adjudication |
| `collection_metadata` | état de collecte par modèle |
| `manual_verification` | lignes de validation/adjudication humaine |

Exemples utiles:

```bash
sqlite3 data/snap_poc_v3_1.db "select count(*) from responses;"
sqlite3 data/snap_poc_v3_1.db "select model, count(*) from responses group by model;"
sqlite3 data/snap_poc_v3_1.db "select agreement_status, count(*) from responses group by agreement_status;"
sqlite3 data/snap_poc_v3_1.db "select score_final, count(*) from responses group by score_final;"
```

## Installation

Pré-requis:

- Python 3.11+;
- une clé OpenRouter pour relancer collecte/scoring;
- SQLite disponible en ligne de commande pour inspecter les bases.

Installation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Vérifier la CLI:

```bash
python -m src.runner --help
```

Si `python` ne pointe pas vers l'environnement virtuel sur votre machine,
utiliser explicitement:

```bash
.venv/bin/python -m src.runner --help
```

## Commandes Utiles

### Tests

```bash
.venv/bin/python -m pytest -q
```

### Préflight

```bash
.venv/bin/python -m src.runner preflight
```

Le préflight vérifie la disponibilité OpenRouter, les paramètres de modèle, les
prix et la cohérence de la base avant une collecte.

### Régénérer Les Analyses Depuis La DB Finale

```bash
.venv/bin/python -m src.runner analyze --stability
.venv/bin/python -m src.runner analyze --sensitivity
.venv/bin/python -m src.runner analyze --variance-decomposition
.venv/bin/python -m src.runner analyze --cross-sp-diagnostic
.venv/bin/python -m src.runner decision
```

### Régénérer Les Figures

```bash
.venv/bin/python -m src.runner visualize --all
```

### Validation Humaine

La base de validation clean est:

```text
data/snap_poc_v3_1_human_validation_clean.db
```

Exemples:

```bash
sqlite3 data/snap_poc_v3_1_human_validation_clean.db \
  "select source, count(*) from manual_verification group by source;"

.venv/bin/python -m src.runner \
  --db-path data/snap_poc_v3_1_human_validation_clean.db \
  compute-kappa
```

Règle pratique: ne pas importer de nouveau codage manuel directement dans
`data/snap_poc_v3_1.db`. Utiliser une copie de travail ou la DB de validation.

## Pipeline Complet Pour Une Nouvelle Campagne

```bash
.venv/bin/python -m src.runner init-db --reset
.venv/bin/python -m src.runner preflight

export OPENROUTER_API_KEY="..."

.venv/bin/python -m src.runner collect --all

.venv/bin/python -m src.runner score --judge haiku
.venv/bin/python -m src.runner score --judge kimi
.venv/bin/python -m src.runner resolve-disagreements

.venv/bin/python -m src.runner export-sample --n 200 --output data/manual_sample.csv
.venv/bin/python -m src.runner manual-score-sample --file data/manual_sample.csv
.venv/bin/python -m src.runner import-manual --file data/manual_sample.csv

.venv/bin/python -m src.runner adjudicate
.venv/bin/python -m src.runner compute-kappa

.venv/bin/python -m src.runner analyze --stability
.venv/bin/python -m src.runner analyze --sensitivity
.venv/bin/python -m src.runner analyze --variance-decomposition
.venv/bin/python -m src.runner analyze --cross-sp-diagnostic

.venv/bin/python -m src.runner visualize --all
.venv/bin/python -m src.runner decision
```

## Limites Connues

La v3.1 a volontairement servi à faire apparaître les faiblesses du protocole.

Limites principales:

- `SP_PER` n'est pas une variation neutre; il agit comme une condition de
  persona ou de stress-test.
- Certains items sont très sensibles au style de réponse, surtout `E2`.
- Les variables `scenario`, `formulation` et `temperature` sont rotatives, pas
  full-factorial.
- Les scores `-1/0/+1` sont pratiques pour l'analyse mais simplifient fortement
  des réponses textuelles riches.
- Le LMM est exploratoire et peut être numériquement sensible.
- Le champ `thinking_enabled` trace une configuration provider/default, pas une
  mesure du raisonnement interne.
- Les kappas humains suggèrent que les rubriques sont utilisables, mais pas
  encore définitivement stabilisées.

## Direction v3.2

La v3.2 ne doit pas simplement relancer plus grand. Elle doit corriger ce que la
v3.1 a révélé.

Priorités:

1. Auditer qualitativement les cellules cross-SP critiques, surtout
   `mistral-large-3 / E2`.
2. Décider du statut de `SP_PER`: suppression, réécriture, ou traitement comme
   stress-test séparé.
3. Réviser les items style-sensibles, notamment `E2` et possiblement `E1`.
4. Relire les désaccords humain-machine pour améliorer les rubriques.
5. Construire une micro-campagne v3.2 ciblée avant toute nouvelle campagne
   large.
6. Séparer clairement les analyses confirmatoires des diagnostics exploratoires.

L'état actuel du dépôt est donc un point d'arrêt propre: la v3.1 est archivée,
les données importantes sont conservées, et le prochain travail peut partir
d'une base lisible plutôt que d'un historique dispersé.
