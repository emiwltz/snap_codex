# Protocole experimental SoulBench SNAP v3.1

**Version active**: 3.1  
**Objectif**: POC rapide, gerable, interpretable.  
**Config source**: `config/protocol.yaml`

La v3.1 est la version active du protocole. Elle repart du design compact de la
v1.1, tout en gardant les elements utiles construits dans la v2.1: pipeline CLI,
SQLite, reprise idempotente, scoring bi-juge, verification manuelle, kappa,
analyses, visualisations et metadonnees de campagne.

La v1.1 reste la trace du design POC source. La v2.1 reste la trace du design
full-factorial exhaustif. La v3.1 est l'hybride actuel.

## 1. Question du POC

La v3.1 cherche a repondre rapidement a une question de faisabilite:

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

## 5. Ce que la v3.1 garde de la v1.1

La v3.1 garde de la v1.1:

- un POC compact;
- 15 items;
- 3 prompts systeme;
- 10 runs;
- une rotation deterministe des scenarios, formulations et temperatures;
- une logique de decision POC autour de la stabilite, du scoring et des refus.

## 6. Ce que la v3.1 garde de la v2.1

La v3.1 garde de la v2.1:

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
  exploratoires;
- les metadonnees `dataset_id`, `protocol_version`, `items_version`,
  `condition_block` et `trial_id`.

## 7. Ce que la v3.1 retire de la v2.1

La v3.1 retire du POC principal:

- le full-factorial `15 x 2 x 3 x 3 x 2 x 7`;
- les 22 680 appels de collecte;
- le traitement symetrique de toutes les cellules experimentales;
- le LMM comme analyse centrale;
- l'idee de lancer une grande campagne avant validation du scoring.

## 8. Versioning et tracabilite

La v3.1 enregistre dans la base:

- `dataset_id`;
- `protocol_version`;
- `items_version`;
- `condition_block`;
- `trial_id`.
- `temperature_applied` et `top_p_applied`, pour distinguer la valeur prevue
  par le protocole de ce qui a réellement ete envoye au provider;
- `thinking_enabled`, derive du `thinking_mode` configure pour le modele.

Ces champs servent a separer clairement les campagnes et a eviter de melanger
des resultats de protocoles differents.

La v3.1 ne manipule pas le reasoning/thinking comme facteur experimental. Le
champ `thinking_enabled` est une trace de configuration provider/default, pas
une mesure du raisonnement interne.

## 9. Scoring

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

## 10. Analyses principales

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

Dans le design rotatif v3.1, l'unite repetee pour l'ICC et le split-half est:

```text
item_id x system_prompt
```

Les variables `scenario`, `formulation` et `temperature` sont assignees par le
calendrier de runs. Les effets de sensibilite sur ces facteurs sont donc lus
comme des analyses exploratoires sur moyennes pairées par `item_id x
system_prompt`, pas comme des tests full-factorial exhaustifs.

Si `temperature_applied = 0` pour un modele, les sorties liees a la temperature
sont marquees comme non applicables pour ce modele.

La decomposition de variance reste exploratoire.

## 11. Seuils de decision POC

Les seuils cibles sont stockes dans `config/protocol.yaml`.

Lecture recommandee:

- `PASS`: scoring acceptable, stabilite suffisante, peu de refus, pas
  d'effondrement massif des profils.
- `BORDERLINE`: signal partiel mais corrections necessaires avant extension.
- `FAIL`: scoring non fiable, instabilite forte ou trop de reponses non
  interpretables.

La decision PASS/BORDERLINE/FAIL est automatisee par la commande:

```bash
python -m src.runner decision
```

Avant scoring complet et generation des rapports d analyse, cette commande
retourne `NOT_READY` plutot qu'une conclusion experimentale.
