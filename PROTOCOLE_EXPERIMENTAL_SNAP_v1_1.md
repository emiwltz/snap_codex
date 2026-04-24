# Protocole experimental SoulBench SNAP v1.1

> **Statut actuel**: document historique. La version active du dépôt est la
> v3.1, documentée dans `PROTOCOLE_EXPERIMENTAL_SNAP_v3_1.md`. La v1.1 est
> conservée comme trace du design POC source.

**Version historique**: 1.1  
**Objectif**: POC rapide, gerable, interpretable.  
**Config source**: `config/protocol.yaml`

Ce protocole décrit le plan compact dont la v3.1 s'inspire. Il est conservé
pour garder une trace claire de l'évolution v1.1 -> v2.1 -> v3.1.

## 1. Question du POC

La v1.1 cherche a repondre rapidement a une question de faisabilite:

> Les LLM produisent-ils des profils de reponse assez stables, scorables et
> peu sensibles aux variations superficielles pour justifier une campagne SNAP
> plus large ?

Le POC mesure des comportements de reponse conditionnes. Il ne cherche pas a
inférer une personnalite, des croyances ou des valeurs intrinseques.

## 2. Design actif

Le design actif est un plan par rotation deterministe, pas un full-factorial.

Pour chaque modele:

```text
15 items x 3 system prompts x 10 runs = 450 conditions
```

Avec les 6 modeles actifs de `config/models.yaml`:

```text
6 x 450 = 2700 appels de collecte
```

Avec deux juges LLM pour scorer toutes les reponses:

```text
5400 appels de scoring
```

Total theorique hors retries:

```text
8100 appels API
```

## 3. Variables conservees

Les variables conservees dans le POC:

- `model`: 6 modeles actifs.
- `item_id`: 15 items.
- `system_prompt`: `SP_ABS`, `SP_DIR`, `SP_PER`.
- `run`: 1 a 10.
- `scenario`: assigne par rotation `base` / `variation`.
- `formulation`: assignee par rotation `F1` / `F2` / `F3`.
- `temperature`: assignee par rotation `0.0` / `0.5` / `1.0`.

Les scenarios, formulations et temperatures ne sont plus croises
exhaustivement. Ils sont inclus dans un calendrier de runs fixe afin de garder
un POC compact.

## 4. Calendrier de rotation

Le calendrier exact est defini dans `config/protocol.yaml`.

Il équilibre autant que possible:

- 5 runs `base` et 5 runs `variation`;
- les trois formulations `F1/F2/F3`;
- les trois temperatures `0.0/0.5/1.0`;
- les trois prompts systeme, qui restent tous testes sur chaque item.

## 5. Ce que la v1.1 garde de la v2.1

La v1.1 garde:

- les items YAML existants;
- les rubriques de scoring par item;
- les conversations mono-tour isolees;
- `SP_ABS` comme vraie absence de message systeme;
- la randomisation seedee;
- la reprise idempotente en SQLite;
- le scoring par deux juges LLM;
- la resolution automatique des desaccords mineurs;
- l'adjudication manuelle des desaccords majeurs;
- les exports de verification humaine;
- les kappas inter-juges et humain-machine;
- les analyses de stabilite, sensibilite et variance comme sorties
  exploratoires.

## 6. Ce que la v1.1 retire de la v2.1

La v1.1 retire du POC principal:

- le full-factorial `15 x 2 x 3 x 3 x 2 x 7`;
- les 22 680 appels de collecte;
- le traitement symetrique de toutes les cellules experimentales;
- le LMM comme analyse centrale;
- l'idee de lancer une grande campagne avant validation du scoring.

## 7. Versioning et tracabilite

La v1.1 ajoute dans la base:

- `dataset_id`;
- `protocol_version`;
- `items_version`;
- `condition_block`;
- `trial_id`.

Ces champs servent a separer clairement les campagnes et a eviter de melanger
des resultats de protocoles differents.

## 8. Scoring

Chaque reponse est libre puis codee post-hoc:

```text
+1 / 0 / -1 / REFUS
```

Deux juges LLM scorent les reponses. Le format attendu est:

```text
SCORE: <+1 or 0 or -1 or REFUS>
INDICATORS: <indicators>
RATIONALE: <1-2 sentences>
```

Resolution:

- accord direct: score final direct;
- desaccord mineur `+1/0` ou `0/-1`: score final `0`;
- desaccord majeur `+1/-1`: adjudication manuelle;
- conflit avec `REFUS`: adjudication manuelle.

## 9. Analyses principales

Le POC doit prioriser:

- kappa inter-juges;
- taux de refus;
- taux de desaccords majeurs;
- ICC sur runs;
- split-half Pearson runs 1-5 vs 6-10;
- stabilite par item;
- stabilite par trait/fondation;
- profils par system prompt;
- profils par temperature.

La decomposition de variance reste exploratoire.

## 10. Seuils de decision POC

Les seuils cibles sont stockes dans `config/protocol.yaml`.

Lecture recommandee:

- `PASS`: scoring acceptable, stabilite suffisante, peu de refus, pas
  d'effondrement massif des profils.
- `BORDERLINE`: signal partiel mais corrections necessaires avant extension.
- `FAIL`: scoring non fiable, instabilite forte ou trop de reponses non
  interpretables.

La decision PASS/BORDERLINE/FAIL n'est pas encore automatisee dans la CLI.
Elle doit etre etablie a partir des rapports et des kappas.
