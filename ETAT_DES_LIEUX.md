# SoulBench — État des lieux du pipeline
*Généré le 18 février 2026*

## 1. Vue d'ensemble
SoulBench est une pipeline Python qui orchestre une expérience de stabilité des valeurs chez des LLMs en variant systématiquement le contexte de réponse. Le flux commence par la lecture de fichiers YAML de configuration (modèles, items, prompts système, rubriques de scoring). Pour chaque modèle, la collecte génère toutes les conditions expérimentales possibles (items x scénarios x formulations x prompts système x températures x runs), puis interroge OpenRouter et stocke chaque réponse brute dans SQLite. Ensuite, deux juges LLM relisent chaque réponse avec une consigne de codage stricte et attribuent un score discret (`+1`, `0`, `-1`, `REFUS`). Les désaccords sont résolus automatiquement quand ils sont mineurs, et envoyés en adjudication humaine quand ils sont majeurs ou de type différent. Une étape de vérification manuelle permet d’exporter un échantillon CSV, réimporter des codages humains, puis calculer des kappas d’accord. Enfin, le pipeline génère des rapports statistiques JSON (stabilité, sensibilité, décomposition de variance) et des figures PNG. À date, le code est structurellement complet, les tests unitaires passent, mais aucune sortie expérimentale réelle n’est présente dans `data/` ou `outputs/`.

## 2. Architecture du pipeline

### 2.1 Structure des fichiers
```
.
├── README.md                              — Documentation opératoire rapide, commandes CLI, TODOs explicites.
├── GUIDE_NON_TECHNIQUE.md                 — Guide pas-à-pas orienté non-technique (procédure complète).
├── requirements.txt                       — Dépendances Python (httpx, pandas, scipy, pingouin, statsmodels, matplotlib, seaborn, pyyaml, pytest, black, isort).
├── ETAT_DES_LIEUX.md                      — (ce document).
├── config/
│   ├── items_personality.yaml             — 10 items Big Five (2 facettes par trait), scénarios base/variation, formulations F1/F2/F3, règles de scoring.
│   ├── items_moral.yaml                   — 5 items moraux (Care/Harm, Fairness/Cheating, etc.), mêmes structures contextuelles.
│   ├── models.yaml                        — Paramètres de collecte, panel de 6 modèles, 2 juges, TODOs de validation IDs/coûts.
│   ├── system_prompts.yaml                — 3 contextes système (`SP_ABS`, `SP_DIR`, `SP_PER`).
│   ├── scoring_rubrics.yaml               — 15 rubriques de codage textuelles (1 par item).
│   ├── manual_adjudication_workflow.md    — Spécification du workflow d’adjudication humaine.
│   ├── methodology_h4.md                  — Décision méthodologique H4: ANOVA exploratoire + LMM confirmatoire.
│   └── methodology_retest.md              — Stratégie test-retest (ICC + split-half, exclusions).
├── src/
│   ├── __init__.py                        — Marqueur de package.
│   ├── prompt_builder.py                  — Chargement/validation config, assemblage prompts, génération déterministe des conditions.
│   ├── api_client.py                      — Client OpenRouter async avec retry/backoff/rate-limit.
│   ├── db.py                              — Schéma SQLite, CRUD, reprise idempotente, échantillonnage manuel, exports/imports.
│   ├── scorer.py                          — Prompt de codage, parser sorties juges, résolution désaccords, kappa, adjudication interactive.
│   ├── analyzer.py                        — Calcul des rapports statistiques et exclusions protocole.
│   ├── visualizer.py                      — Génération des figures PNG (avec fallback "No data available").
│   └── runner.py                          — CLI unique: collect, score, analyze, visualize, manual workflow.
├── tests/
│   ├── test_prompt_builder.py             — Vérifie génération 3780 conditions/modèle, déterminisme seed, règles SP_ABS.
│   ├── test_db.py                         — Vérifie schéma/indexes, idempotence, remplacement erreurs, adjudication.
│   ├── test_scorer.py                     — Vérifie parsing, résolution désaccords, retry scoring, export échantillon.
│   └── test_analyzer.py                   — Vérifie rapports vides/non-vides et génération des JSON de sortie.
├── data/                                  — Dossier prévu pour `soulbench.db` et CSV manuels; actuellement vide.
├── outputs/
│   ├── reports/                           — Cible des rapports JSON; actuellement vide.
│   └── figures/                           — Cible des PNG; actuellement vide.
├── .pytest_cache/
│   ├── README.md                          — Cache pytest (technique, non métier).
│   ├── CACHEDIR.TAG                       — Tag standard cache.
│   ├── .gitignore                         — Ignore interne du cache.
│   └── v/cache/{nodeids,lastfailed}       — Métadonnées exécution tests.
└── .venv/                                 — Environnement virtuel local (dépendances tierces, hors logique métier SoulBench).
```

### 2.2 Flux de données
1. Chargement config: `src/prompt_builder.py` lit les YAML et valide une structure minimale.
2. Génération des conditions: pour un modèle donné, full-factorial sur `15 items x 2 scénarios x 3 formulations x 3 system prompts x 2 températures x 7 runs = 3780` conditions.
3. Randomisation déterministe: la liste des conditions est mélangée avec un seed stocké en base (`collection_metadata`) pour reprise stable.
4. Collecte API: `src/runner.py` appelle `OpenRouterClient.generate(...)` condition par condition, puis écrit dans `responses` (texte brut, tokens, latence, flags erreur/troncature).
5. Reprise/idempotence: les conditions déjà réussies (`is_error=0`) sont sautées; une condition en erreur peut être réécrite par un succès ultérieur.
6. Scoring juge 1 puis juge 2: `src/scorer.py` construit un prompt de codage pour chaque réponse et parse `SCORE/INDICATORS/RATIONALE`.
7. Résolution: accords directs, désaccords mineurs moyennés, désaccords majeurs/type marqués `manual_review_needed`.
8. Vérification humaine: export CSV stratifié, réimport de codage humain, adjudication interactive, calcul kappa.
9. Analyse: production de rapports JSON (`stability`, `sensitivity`, `variance_decomposition`) dans `outputs/reports/`.
10. Visualisation: production de figures PNG dans `outputs/figures/`.

### 2.3 Stack technique
- Langage: Python (README annonce `3.11+`; l’environnement local visible est en Python 3.14). [AMBIGU : version minimale réellement testée en production]
- Stockage: SQLite local (`data/soulbench.db`).
- Appels LLM: OpenRouter (HTTP via `httpx.AsyncClient`).
- Analyse données: `pandas`, `scipy`, `pingouin`, `statsmodels`.
- Visualisation: `matplotlib`, `seaborn`, `numpy`.
- Configuration: YAML (`pyyaml`).
- Test/lint format: `pytest`, `black`, `isort`.
- Dépendances externes critiques: endpoint OpenRouter + variable d’environnement `OPENROUTER_API_KEY`.
- Aucune infra cloud propre (pas de service DB distant, pas d’orchestrateur externe).

## 3. Design expérimental

### 3.1 Variables manipulées
| Variable | Valeurs dans le code | Rôle expérimental |
|---|---|---|
| `model` | 6 modèles actifs (`claude-sonnet-4-5`, `gpt-5-2`, `gemini-3-pro`, `qwen3-max`, `mistral-large-3`, `grok-4-1-thinking`) | Variable principale inter-modèles |
| `item_id` | 15 items (10 personnalité + 5 moral) | Stimuli/mesure des construits |
| `scenario` | `base`, `variation` | Variation de contexte narratif |
| `formulation` | `F1`, `F2`, `F3` | Variation de wording de la consigne |
| `system_prompt` | `SP_ABS`, `SP_DIR`, `SP_PER` | Variation d’état/cadre système |
| `temperature` | `0.1`, `1.0` | Variation de stochasticité |
| `run` | `1..7` | Retest intra-condition |

Paramètres de collecte globaux (`config/models.yaml`): `max_tokens=2048`, `top_p=1.0`, `min_delay_seconds=1.0`.

### 3.2 Plan expérimental
Le plan implémenté est un **full factorial complet** par modèle, sans sous-échantillonnage:
- `15 x 2 x 3 x 3 x 2 x 7 = 3780` conditions/modèle.
- Avec 6 modèles actifs: `22680` réponses attendues en collecte.

Ordonnancement:
- Conditions mélangées aléatoirement, mais de manière déterministe via seed stocké.
- En reprise, le seed du modèle est réutilisé (`db.get_model_seed`) pour retrouver le même ordre.
- Les conditions réussies sont ignorées au redémarrage; les erreurs restent re-tentables.

Interprétation méthodologique:
- Choix implicite d’un design exhaustif plutôt qu’un plan fractionné. [AMBIGU : justification statistique/puissance non documentée explicitement]

### 3.3 Modèles et paramètres testés
Panel de collecte (`config/models.yaml`):
- Claude Sonnet 4.5 (`anthropic/claude-sonnet-4.5`), `thinking_mode=enabled_by_default`.
- GPT 5.2 (`openai/gpt-5.2`), `thinking_mode=enabled_by_default`.
- Gemini 3 Pro (`google/gemini-3-pro-preview`), `thinking_mode=not_available`.
- Qwen3 Max (`qwen/qwen3-max`), `thinking_mode=not_available`.
- Mistral Large 3 (`mistralai/mistral-large-2512`), `thinking_mode=disabled`.
- Grok 4.1 Thinking (`x-ai/grok-4.1-fast`), `thinking_mode=enabled_by_default`.

Juges de scoring:
- `haiku`: Claude Haiku 4.5 (`anthropic/claude-haiku-4.5`).
- `kimi`: Kimi K2.5 (`moonshotai/kimi-k2.5`).

Paramètres scoring (code):
- Température juge forcée à `0.0`.
- `max_tokens=512` pour la sortie de codage.
- `max_rows` par run CLI par défaut: `100`.

Notes de complétude:
- `config/models.yaml` contient explicitement: `# TODO: Renseigner les model IDs OpenRouter exacts (panel + juges).`
- `# TODO: Compléter la matrice thinking/reasoning par modèle (vérification OpenRouter).`
- Version exacte des endpoints au moment de campagne réelle: [INFORMATION MANQUANTE].

## 4. Stimuli et items

### 4.1 Nature des stimuli
Les stimuli sont des **dilemmes textuels contextualisés** (professionnels, organisationnels, éthiques) suivis d’une formulation de demande de conseil.
Chaque item contient:
- un scénario `base`;
- une variante contextuelle `variation`;
- trois formulations (`F1/F2/F3`) pour faire varier le wording.

Concrètement, le prompt utilisateur final est assemblé comme:
`scenario_text + "\n\n" + formulation_text`.

### 4.2 Origine et sélection
Les items sont codés manuellement dans `config/items_personality.yaml` et `config/items_moral.yaml`.
Aucune source externe (papier, banque d’items validée, adaptation d’échelle) n’est mentionnée dans le code/config.
- [INFORMATION MANQUANTE] Processus de génération initiale des items.
- [INFORMATION MANQUANTE] Procédure de prétest linguistique/psychométrique.
- [INFORMATION MANQUANTE] Critères d’exclusion/réécriture d’items.

### 4.3 Construits ciblés
Construits explicitement ciblés:
- Big Five (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism), 2 facettes par trait, 10 items total.
- Moral Foundations (Care/Harm, Fairness/Cheating, Loyalty/Betrayal, Authority/Subversion, Purity/Sanctity), 5 items total.

Références théoriques:
- Les labels correspondent à des cadres connus (Big Five, Moral Foundations), mais il n’y a pas de citation bibliographique formelle (MFQ, BFI, etc.) dans les fichiers.
- [AMBIGU : ancrage théorique implicite mais non référencé explicitement].

## 5. Mesure et scoring

### 5.1 Format de réponse
Collecte primaire:
- Réponse libre du modèle (`raw_response` texte), sans format imposé.
- Métadonnées associées: temps de réponse, tokens prompt/completion, flags `is_error`, `is_truncated`.

Scoring secondaire (juges LLM):
- Prompt de codage standardisé exigeant strictement:
  - `SCORE: <+1|0|-1|REFUS>`
  - `INDICATORS: ...` (ou `INDICATEURS`)
  - `RATIONALE: ...` (ou `JUSTIFICATION`)

### 5.2 Méthode de scoring
Étapes:
1. Chaque réponse est scorée par deux juges indépendants (`haiku`, `kimi`).
2. Si parsing invalide, retry une fois; si nouvel échec, `manual_review_needed=1`.
3. Résolution automatique:
- Même score: `agree`, score final direct.
- Écart de 1 (`+1` vs `0`, `0` vs `-1`): `minor_disagree`, moyenne arrondie (`round`, donc 0 dans ces cas).
- Écart de 2 (`+1` vs `-1`) ou conflit avec `REFUS`: review manuelle requise.
4. Adjudication humaine possible via CLI interactive (`adjudicate`).
5. Les scores finaux sont transformés en numérique pour analyses: `+1 -> 1`, `0 -> 0`, `-1 -> -1`, `REFUS` exclu des analyses numériques.

### 5.3 Métriques calculées
Fiabilité/stabilité (`stability_report.json`):
- Cronbach alpha global par modèle.
- Test-retest split-half Pearson (runs 1-3 vs 5-7, run 4 exclu).
- ICC runs (objectif ICC2, via `pingouin`).
- Corrélation cross-température (`0.1` vs `1.0`).
- Corrélations cross-system prompts (paires `SP_ABS/SP_DIR/SP_PER`).
- Résumés par item et par agrégation trait/fondement.

Sensibilité (`sensitivity_report.json`):
- Effet scénario: Wilcoxon (`base` vs `variation`).
- Effet formulation: Friedman (`F1/F2/F3`).

Décomposition de variance (`variance_decomposition_report.json`):
- Eta² exploratoire par facteur (`model`, `system_prompt`, `temperature`, `scenario`, `formulation`, `item_id`, `run`).
- LMM confirmatoire avec fallback de convergence.

Accords:
- Kappa inter-juges.
- Kappa humain-vs-juge1 et humain-vs-juge2.

## 6. Décisions clés et justifications
| Décision prise | Alternative écartée (visible) | Justification (explicite/inférée) |
|---|---|---|
| Stockage local SQLite (`responses`, `collection_metadata`, `manual_verification`) | DB distante/non-SQL [INFORMATION MANQUANTE] | Simplicité, portabilité locale, pipeline offline-friendly (explicite dans structure code). |
| Index unique condition + upsert limité aux lignes en erreur | Écraser aussi les succès précédents | Éviter doublons et garder idempotence/reprise (explicite dans SQL `WHERE responses.is_error = 1`). |
| Full-factorial exhaustif (3780 conditions/modèle) | Plan fractionné/sampling | Couverture maximale des interactions de contexte; alternative non documentée [AMBIGU]. |
| Shuffle déterministe avec seed stocké en DB | Ordre fixe sans seed | Reproductibilité + reprise cohérente d’une campagne interrompue. |
| `SP_ABS` sans message système | Prompt système vide explicite | Comparer un contexte “sans cadrage système” versus prompts dirigés/persona. |
| Client OpenRouter avec policy retry stricte (timeout/429/5xx/empty) | Échec immédiat sans retry | Robustesse collecte/scoring face aléas réseau/provider. |
| En absence de clé API, skip proprement sans crash | Stop dur de la CLI | Permet smoke-tests et diagnostics locaux sans credentials. |
| Double jugement LLM (`haiku` + `kimi`) | Un seul juge | Réduire variance/erreur de codage et mesurer accord inter-juges. |
| Parsing strict formaté + retry unique | Parsing permissif/multiligne | Standardiser le codage; compromis simplicité vs robustesse sémantique. |
| Résolution auto des désaccords mineurs, manuel pour majeurs/type | Tout manuel / tout auto | Compromis coût-qualité; règles clairement codées (`agree/minor/major/type`). |
| H4 en deux temps: eta² exploratoire puis LMM confirmatoire | Un seul cadre statistique | Décision explicitée dans `config/methodology_h4.md`. |
| Exclusions analyses (`is_error`, `REFUS`, manual pending) | Conserver toutes lignes | Nettoyage qualité données explicitement documenté dans code + méthodologie. |
| Visualisations “safe” (figure vide si pas de données) | Lever erreur sur DB vide | Robustesse opérationnelle, expérience CLI stable même avant collecte. |

## 7. État d'avancement

### Ce qui est fonctionnel
- Pipeline CLI complet câblé (`collect`, `score`, `resolve-disagreements`, `export-sample`, `import-manual`, `compute-kappa`, `adjudicate`, `analyze`, `visualize`).
- Schéma DB + index + reprise idempotente opérationnels.
- Génération déterministe des conditions et calcul attendu `3780`/modèle testé.
- Client API avec retry/backoff implémenté.
- Scoring bi-juge, parsing, résolution et adjudication manuelle implémentés.
- Analyses JSON et visualisations PNG implémentées avec gestion DB vide.
- Tests unitaires passants localement via `.venv`: `16 passed, 12 warnings in 10.90s`.

### Ce qui est partiel ou en cours
- Couches analyse/visualisation annoncées comme “skeleton” dans le README; elles produisent des sorties mais avec simplifications assumées (ex: eta² approximatif facteur par facteur).
- LMM confirmatoire implémenté mais potentiellement instable selon données (warnings de convergence observés sur tests synthétiques).
- Champ `thinking_mode` configuré dans YAML mais `thinking_enabled` est stocké à `None` à la collecte: la traçabilité effective de ce facteur est partielle.
- Workflow coût API présent en TODO, pas de module de costing implémenté.

### Ce qui est absent ou en TODO
- Aucune donnée expérimentale réelle présente (`data/` vide, pas de `soulbench.db`).
- Aucun rapport JSON réel généré (`outputs/reports/` vide).
- Aucune figure réelle générée (`outputs/figures/` vide).
- TODO explicites:
- `# TODO: Renseigner les model IDs OpenRouter exacts (panel + juges).`
- `# TODO: Compléter la matrice thinking/reasoning par modèle (vérification OpenRouter).`
- `# TODO: Calcul coût total (collecte + scoring) avec pricing OpenRouter au moment du lancement.`
- [INFORMATION MANQUANTE] Fichier `.env.example` ou procédure standardisée de secrets.
- [INFORMATION MANQUANTE] Validation psychométrique formelle des rubriques/items avant campagne.

## 8. Outputs actuels
État actuel du workspace:
- `data/` : vide (0 fichier).
- `outputs/reports/` : vide (0 fichier).
- `outputs/figures/` : vide (0 fichier).

Donc aucune sortie expérimentale exploitable n’est encore produite.

Formats attendus par le pipeline (quand exécuté):
- Base SQLite: `data/soulbench.db`.
- CSV vérification manuelle: `data/manual_sample.csv` puis import codé.
- Rapports JSON: `stability_report.json`, `sensitivity_report.json`, `variance_decomposition_report.json`.
- Figures PNG: radar Big Five, heatmap, boxplots, bar chart eta², profils cross-température et cross-SP.

Exemple de sortie technique vérifiée aujourd’hui (tests):
- `................ [100%]`
- `16 passed, 12 warnings in 10.90s`

## 9. Points d'attention
- Risque méthodologique: aucun résultat réel n’existe encore; tout jugement de validité empirique est prématuré.
- Risque de traçabilité: `thinking_mode` est défini par modèle mais pas réellement enregistré comme variable observée (`thinking_enabled=None` en collecte).
- Risque coût/temps: full-factorial complet implique volume élevé (collecte `22680` réponses; scoring bi-juge `45360` appels juge), sans module de pré-estimation coût intégré.
- Risque de robustesse parser: le parser juge repose sur un format ligne stricte; réponses multi-lignes/atypiques peuvent tomber en review manuelle.
- Risque statistique: scores ordinaux `{-1,0,+1}` sont injectés dans tests paramétriques et LMM; pertinence dépendra de la distribution réelle.
- Risque de convergence: LMM peut échouer/non converger; fallback prévu mais pas de stratégie plus riche documentée.
- Risque psychométrique: 1 item par fondement moral, donc fiabilité interne par fondement intrinsèquement limitée (le code note: "Alpha moral par fondement incalculable avec 1 item/fondement.").
- Risque process: `score --max-rows` par défaut à 100 impose plusieurs relances manuelles pour gros volumes; pas de boucle automatique “jusqu’à vide”.
- Risque gouvernance code: historique git minimal (1 commit unique le 10 février 2026), faible traçabilité des itérations de design.
- Hygiène repo: absence de `.gitignore` racine visible; des artefacts `.pyc` et `.pytest_cache` sont versionnés, ce qui peut polluer les revues et masquer les changements utiles.
- [INFORMATION MANQUANTE] Stratégie d’assurance qualité des labels humains (double codage humain, protocole de consensus, audit inter-codeurs).
- [INFORMATION MANQUANTE] Seuils de décision finaux “go/no-go” pour interprétation scientifique en production.
