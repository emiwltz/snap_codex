# Guide Non-Technique Complet
## SoulBench SNAP Pipeline v2.1

Ce document est un guide pratique pour les personnes non techniques.
Il explique clairement:

- ce qui existe deja dans la codebase,
- ce qui reste a configurer,
- comment verifier que tout fonctionne,
- comment lancer les tests,
- comment recuperer les resultats,
- comment lire et interpreter les sorties.

Ce guide est fait pour une execution pas a pas, sans besoin de lire le code.

---

## 1. Ce que fait ce projet

Le projet SoulBench sert a executer une experience sur des modeles de langage:

1. Collecter des reponses de modeles LLM sur une grille experimentale.
2. Scorer ces reponses via 2 juges LLM.
3. Resoudre automatiquement les desaccords de scoring.
4. Exporter un echantillon pour verification humaine.
5. Calculer les accords (kappa).
6. Produire des analyses statistiques.
7. Generer des graphiques interpretables.

Le systeme utilise une base locale SQLite pour garder toutes les donnees.

---

## 2. Ce qui est deja implemente

La structure complete du projet est en place:

- base de donnees (schema complet, index, reprise),
- client API OpenRouter async avec retry/backoff,
- assembleur de prompts,
- orchestrateur CLI complet,
- scoring 2 juges + resolution des desaccords,
- squelettes d analyses,
- squelettes de visualisations,
- tests unitaires de base,
- fichiers de configuration YAML.

La reprise de collecte est idempotente:

- pas de doublons sur une condition,
- si une condition avait echoue, une reexecution peut la remplacer par un succes.

---

## 3. Ce qui n est pas encore renseigne (placeholders)

Avant une vraie campagne experimentale, il faut remplir:

1. Les model IDs OpenRouter exacts dans `config/models.yaml`.
2. Les textes finaux des 10 items personnalite dans `config/items_personality.yaml`.
3. Les textes finaux des 5 items moraux dans `config/items_moral.yaml`.
4. Les grilles de codage finales dans `config/scoring_rubrics.yaml`.
5. Les informations thinking/reasoning par modele.
6. La decision methodologique finale H4 (ANOVA vs modele mixte).
7. La strategie finale test-retest (runs individuels vs agregats).
8. Le calcul de cout total avec pricing OpenRouter.

---

## 4. Dossiers et fichiers importants

- `config/`:
  - parametres modeles, items, prompts systeme, rubrics scoring.
- `src/`:
  - logique de la pipeline (collecte, scoring, analyse, visualisation).
- `data/`:
  - base SQLite (`soulbench.db`) et echantillon manuel (`manual_sample.csv`).
- `outputs/reports/`:
  - rapports analyses au format JSON.
- `outputs/figures/`:
  - graphiques PNG.
- `tests/`:
  - tests unitaires.

---

## 5. Prerequis avant execution

1. Avoir Python 3.11+ installe.
2. Ouvrir un terminal dans le dossier projet.
3. Installer les dependances Python.
4. Definir la cle API OpenRouter pour les etapes qui appellent des modeles.

Commandes conseillees:

```bash
cd /Users/emi/Documents/code/side/snap_codex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si `python` fonctionne sur votre machine, vous pouvez remplacer `python3` par `python`.

---

## 6. Verification rapide de bon fonctionnement

Cette verification valide que la CLI repond et ne crash pas sur cas vides.

```bash
python3 -m src.runner collect --model test
python3 -m src.runner score --judge haiku
python3 -m src.runner analyze --stability
```

Resultat attendu:

1. Les commandes se lancent.
2. En absence de cle API, la collecte/scoring saute proprement sans crash.
3. L analyse sur DB vide se termine sans crash.

---

## 7. Comment passer les tests

### 7.1 Lancer les tests

```bash
python3 -m pytest -v
```

### 7.2 Lire le resultat

- Chaque test doit afficher `PASSED` ou `FAILED`.
- Objectif minimal: au moins 80% des tests en vert.

### 7.3 Si les tests ne demarrent pas

Cas courant: `No module named pytest` ou autre module manquant.

Actions:

1. Activer l environnement virtuel:
```bash
source .venv/bin/activate
```
2. Reinstaller les dependances:
```bash
pip install -r requirements.txt
```
3. Relancer:
```bash
python3 -m pytest -v
```

---

## 8. Procedure complete d execution (campagne reelle)

### Etape A - Completer la configuration

1. Completer `config/models.yaml` avec les vrais model IDs.
2. Completer les items et rubrics placeholders.
3. Verifier la coherence des fichiers YAML.

### Etape B - Definir la cle API

```bash
export OPENROUTER_API_KEY="votre_cle_ici"
```

### Etape C - Collecte

Un modele:

```bash
python3 -m src.runner collect --model claude-sonnet-4-5
```

Tous les modeles actifs:

```bash
python3 -m src.runner collect --all
```

Pendant la collecte, le log affiche la progression:

`modele: n_completes/3780 (pourcentage%)`

### Etape D - Scoring LLM

```bash
python3 -m src.runner score --judge haiku
python3 -m src.runner score --judge kimi
```

Puis resolution des desaccords:

```bash
python3 -m src.runner score --resolve-disagreements
```

Alias equivalent:

```bash
python3 -m src.runner resolve-disagreements
```

### Etape E - Verification manuelle

Exporter echantillon:

```bash
python3 -m src.runner export-sample --n 4536
```

Le fichier genere est `data/manual_sample.csv`.

Apres codage humain du CSV, importer:

```bash
python3 -m src.runner import-manual --file data/manual_sample_coded.csv
```

Si des lignes sont marquees en revue manuelle (`manual_review_needed`), lancer l adjudication interactive:

```bash
python3 -m src.runner adjudicate
```

Calculer kappa:

```bash
python3 -m src.runner compute-kappa
```

### Etape F - Analyses

```bash
python3 -m src.runner analyze --stability
python3 -m src.runner analyze --sensitivity
python3 -m src.runner analyze --variance-decomposition
```

### Etape G - Visualisations

```bash
python3 -m src.runner visualize --all
```

---

## 9. Ou recuperer les resultats

### 9.1 Donnees brutes

- Base complete: `data/soulbench.db`

Cette base contient:

- les reponses,
- les metadonnees de collecte,
- la verification manuelle.

### 9.2 Echantillon manuel

- Export: `data/manual_sample.csv`
- Import attendu: `data/manual_sample_coded.csv`

### 9.3 Rapports analyses

Dossier: `outputs/reports/`

Fichiers principaux:

- `stability_report.json`
- `sensitivity_report.json`
- `variance_decomposition_report.json`

### 9.4 Figures

Dossier: `outputs/figures/`

Exemples:

- radar profils Big Five,
- heatmap model x item,
- boxplots stabilite,
- bar chart eta2,
- profils cross-temperature,
- profils cross-SP.

---

## 10. Comment lire les resultats (version non-tech)

### 10.1 Qualite de donnees

Verifier en priorite:

1. Taux de completion global >= 95%.
2. Accord inter-juge (kappa) >= 0.70.
3. Accord humain-machine >= 0.70.
4. Taux de desaccords majeurs <= 10%.

Si ces points sont faibles, il faut corriger avant interpretation scientifique.

### 10.2 Stabilite

Dans `stability_report.json`, regarder:

- test-retest (plus haut = plus stable),
- ICC (plus haut = meilleure coherence),
- correlations cross-temperature et cross-SP.

Lecture simple:

- valeurs elevees: profil plus robuste,
- valeurs faibles: profil sensible au contexte / stochasticite.

### 10.3 Sensibilite

Dans `sensitivity_report.json`, regarder:

- effet scenario (Wilcoxon),
- effet formulation (Friedman).

Lecture simple:

- effet scenario significatif: le modele reagit au contexte,
- effet formulation trop fort: possible sensibilite au wording plus qu au fond.

### 10.4 Decomposition de variance

Dans `variance_decomposition_report.json`, regarder:

- classement des facteurs par eta2.

Lecture simple:

- si `modele` domine nettement: H4 plutot confirmee,
- si `system_prompt` domine: profils possiblement instables.

---

## 11. Processus recommande de validation

1. Passer les tests unitaires.
2. Lancer un smoke test sur 1 modele.
3. Verifier format scoring et desaccords.
4. Lancer la collecte complete.
5. Lancer scoring complet.
6. Lancer verification manuelle + kappa.
7. Lancer analyses et visualisations.
8. Faire une revue de coherence avant interpretation finale.

---

## 12. Erreurs frequentes et solutions

### Erreur: module Python manquant

Symptome:

- `ModuleNotFoundError: ...`

Solution:

1. Activer `.venv`.
2. Reinstaller `requirements.txt`.
3. Relancer.

### Erreur: cle API absente

Symptome:

- warning sur `OPENROUTER_API_KEY`.

Solution:

```bash
export OPENROUTER_API_KEY="votre_cle_ici"
```

### Erreur: rien a scorer

Symptome:

- `No rows pending scoring`.

Ca veut dire:

- soit la collecte n est pas faite,
- soit ce juge a deja tout score.

### Erreur: placeholders non remplaces

Symptome:

- sorties peu exploitables,
- scoring incoherent,
- analyses peu interpretables.

Solution:

- remplir tous les placeholders de `config/` avant campagne reelle.

---

## 13. Checklists operationnelles

### Checklist pre-lancement

1. Config YAML completee.
2. Cle API active.
3. Tests unitaires executes.
4. Smoke test valide.

### Checklist post-collecte

1. Progression attendue atteinte.
2. Peu d erreurs API non recuperees.
3. DB presente et non vide.

### Checklist post-scoring

1. Scores juge 1 et juge 2 remplis.
2. Resolution des desaccords executee.
3. Echantillon manuel exporte.
4. Kappa calcule.

### Checklist post-analyse

1. Rapports JSON generes.
2. Figures PNG generees.
3. Interpretation qualite des donnees faite.
4. Limites et TODOs documentes pour la suite.

---

## 14. Prochaines etapes a implementer (projet)

1. Injecter les contenus livrables definitifs dans les YAML.
2. Finaliser le cadre statistique H4 (ANOVA/mixte) en version definitive.
3. Completer la documentation des couts OpenRouter.
4. Ajouter des exports non-tech (CSV resumes pre-formates) si besoin metier.
5. Ajouter un tableau de bord de suivi execution si usage frequent par equipe non-tech.

---

## 15. Resume executif

La pipeline est structurellement operationnelle de bout en bout.
Les composants critiques sont implementes et relies.
Le point principal avant production est de remplacer tous les placeholders de configuration.
Une fois cela fait, le flux non-tech recommande est:

1. tests,
2. collecte,
3. scoring,
4. verification manuelle,
5. analyses,
6. lecture des rapports et graphiques.
