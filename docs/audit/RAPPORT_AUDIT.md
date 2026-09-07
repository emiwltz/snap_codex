# SoulBench SNAP v3.1 — audit indépendant avant présentation

**6 septembre 2026 — audit indépendant et revue finale achevés.** Le [verdict final du candidat nettoyé](REVUE_FINALE.md) clôt les points ci-dessous : corrections intégrées, PDF de 14 pages et ZIP de 102 fichiers vérifiés. Aucun défaut restant n'exige une correction pour la présentation privée ; les décisions et déclarations de diffusion restent explicites. La section 3 conserve l'état des constats lors de l'audit initial ; l'addendum fait foi pour leur statut actuel.

**Conclusion : le corpus retenu est cohérent et les résultats numériques centraux se reproduisent. Le verdict scientifique historique est bien FAIL. Le projet peut soutenir une présentation honnête d'un pilote rétrospectif de mesure des réponses sous prompting. Il ne soutient pas encore la présentation d'un benchmark validé de personnalité ou de valeurs intrinsèques.**

Deux corrections concrètes ont été identifiées : une affirmation excessive sur l'absence de répétitions identiques, et une incompatibilité réelle entre la plage de dépendances autorisée et la sélection du coefficient ICC. Le nettoyage les prend en compte. L'accord par item, le plafond complet de E1, la provenance des annotations et les limites d'accès aux données doivent rester visibles. L'identité publique, l'affiliation et la licence restent expressément **indécises**, selon Emi ; elles ne bloquent pas ce travail local.

## 1. Périmètre, indépendance et versions examinées

L'audit utilise le worktree auteur `/Users/emi/.codex/worktrees/1f77/snap_codex`, et non le checkout ancien du worktree d'audit. Capture initiale : **2026-09-06 01:57:38 UTC**, HEAD **`eae718894aafad84e61febc2848dc6300c25403b`**, avec les modifications non committées du manuscrit, des scripts et du nettoyage hérités. Ce travail a ensuite été conservé par l'auteur dans **`d9fa3defa6a1baa69d67243b4aaad73a66923e4f`**. Les corrections du nettoyage postérieures à cette capture sont distinguées dans la section 3 et l'addendum final.

Le [manifeste initial](evidence/initial_snapshot_manifest.json) contient les empreintes des fichiers réellement capturés, l'état Git et les hashes des sauvegardes SQLite. Les lignes de code citées ci-dessous sont celles de cette capture, sauf mention explicite du candidat nettoyé. La capture reste dans `work/source_snapshot/` du worktree d'audit ; les environnements et rendus privés ne font pas partie des livrables.

Le [contrôle croisé des références](evidence/reference_comparison.json) a retrouvé **41 fichiers identiques** entre la capture, le worktree auteur et le dépôt original `/Users/emi/code/side/snap_codex` : les deux bases, le CSV, les configurations YAML, le code concerné et les rapports/figures historiques. Les références n'ont pas été modifiées.

| Référence | SHA-256 du fichier source initial |
|---|---|
| `data/snap_poc_v3_1.db` | `bbcd28fb99554dc8a7ef308b181e4ff5374d1617abb389cdfd297b1ba847b59a` |
| `data/snap_poc_v3_1_human_validation_clean.db` | `f8d51bd86399a68b460fa77d54b113659ca234fb9fb02d937d1c1d692e84ea34` |

Les WAL étaient vides lors de la capture. Les backups cohérents ont des hashes binaires différents, ce qui est compatible avec la réécriture SQLite ; leur intégrité et leurs contenus ont été examinés. Les accès aux références utilisent SQLite `mode=ro` et `query_only`. Aucun `SoulBenchDB` n'a été instancié sur elles ; les analyses qui migrent ou écrivent n'ont opéré que sur des copies privées. Aucun appel de collecte, de juge, publication, push ou soumission n'a eu lieu. Le seul téléchargement technique ajouté par l'audit est un wheel **public** de Pingouin pour le test de compatibilité, isolé dans `work/`.

## 2. Données : résultats indépendamment confirmés

Le [script principal autonome](audit_recalculate.py) recalcule les comptes, la résolution, Cohen kappa, Pearson et ICC par la formule ANOVA, **sans importer le pipeline SNAP**. Le [script complémentaire](audit_additional_checks.py) contrôle directement les YAML et les jointures. Ce sont des vérifications indépendantes du script de manuscrit ; les données sources demeurent celles du même pilote.

| Contrôle | Résultat |
|---|---|
| Intégrité SQLite / clés étrangères | Deux `integrity_check=ok` ; aucun échec `foreign_key_check` |
| Volume et identifiants | 2 700 lignes, 2 700 `trial_id` uniques ; reconstruction des IDs conforme |
| Cellules | 270 cellules modèle × item × SP, chacune de dix runs ; six modèles × 450 |
| Conditions et prompts | Calendrier, texte utilisateur et texte système conformes aux YAML sur les 2 700 lignes |
| Scores finaux | 899 `+1`, 1 327 `0`, 472 `-1`, deux `REFUS` ; 2 698 scores numériques |
| État final | Zéro ligne en erreur, zéro score final absent, zéro revue manuelle en attente |
| Résolution | 2 266 accords directs, 404 désaccords adjacents, 30 adjudications ; aucune violation des règles vérifiées |
| Accord des deux juges | 2 695 paires ; accord exact **84,0816 %** ; κ **0,7509073105151067** |
| Désaccords initiaux | 24 oppositions `+1/-1` sur 2 695 paires, un conflit avec refus, cinq scores juge2 absents |
| Adjudications | 30 IDs distincts, zéro orphelin, chaque score manuel correspond au score final |
| Bases campagne / validation | Tables `responses` strictement identiques, y compris textes et scores |
| CSV / validation | 200 IDs, labels, justifications et champs de contexte conformes ; aucune duplication ou jointure perdue |
| Séparation des usages | 30 lignes `adjudication` et 200 `human_validation` ; aucun chevauchement d'IDs entre ces populations |
| Couverture des 200 labels | Claude 0 ; GPT 43 ; Gemini 25 ; Qwen 43 ; Mistral 44 ; Grok 45 |
| Kappas historiques avec les 200 labels | Juge1 **0,623424531202** ; juge2 **0,630383948103** ; final **0,578899875926** |
| Minimum ICC calculable | **0,548627174897**, Mistral ; cinq modèles calculables, Claude manquant |
| Split-half | **0,882749410058–0,937145247957**, corrélations de moyennes |
| Minimum cross-SP | **0,318909766466**, Mistral DIR/PER, 150 paires item/run |
| Reproduction des rapports | Zéro différence à tolérance absolue/relative 10⁻⁸ dans stabilité, sensibilité, variance et décision |
| Verdict historique | Campagne complète ; **FAIL** pour ICC et corrélation cross-SP |

Les [résultats indépendants](evidence/independent_results.json), la [comparaison de fiabilité](evidence/reliability_comparison.json), les [contrôles supplémentaires](evidence/additional_checks.json) et le [rapport de reproduction](evidence/reproduction_initial_audit.json) donnent les valeurs non arrondies et dénominateurs. Les IDs numériques s'étendent de 1 à 3 161 malgré 2 700 lignes ; des trous dans une séquence SQLite ne sont pas des preuves de réponses manquantes lorsque la matrice de conditions est complète.

Les cinq scores juge2 absents concernent tous **M_AS** : deux Claude, deux Gemini et un Qwen. Les deux refus finaux concernent **Claude/M_CH**, sous ABS et PER. Les 17 drapeaux de troncature concernent **Mistral** : 16 ABS, un DIR, zéro PER, tous à 2 048 tokens enregistrés. Ces anomalies sont concentrées par item/condition ; elles ne doivent pas être décrites comme une perte aléatoire uniforme. Les analyses de sensibilité déjà livrées ne renversent pas le résultat Mistral DIR/PER.

## 3. Constats priorisés et état de correction

Sévérité utilisée : **P1** = correction nécessaire dans le parcours livré ou avant de reprendre l'affirmation concernée ; **P2** = limite/interprétation à rendre explicite, sans invalider les calculs ; **P3** = précision utile ou évolution facultative. Ces priorités ne sont pas de nouveaux seuils scientifiques.

### F01 — P1 : absence globale de répétitions identiques, affirmation trop forte

**Preuve.** `config/models.yaml:23`, `src/runner.py:172–189`, `src/api_client.py:144–154` et les drapeaux des **450/450** réponses GPT montrent que `temperature` et `top_p` sont omis. Les messages enregistrés et les paramètres reconstructibles forment **270 signatures** : 180 groupes de deux et 90 occurrences seules. Les paires de runs 1/7, 2/8, 3/9 et 4/10 comptent chacune 45 paires, soit **180** au total. Les cinq autres modèles ont 450 signatures distinctes lorsque leur température envoyée est prise en compte.

**Résultat exploratoire.** 142/180 paires ont le même score final (**78,8889 %**, κ nominal **0,646017699115**, Pearson **0,744037789021**). Aucun texte de réponse n'est strictement identique. Toutes les observations GPT datent du 12 mai ; l'écart absolu des timestamps entre partenaires va de **33,57 secondes à 155,10 minutes**, médiane **51,87 minutes**. Ces positions de runs ne sont pas une succession chronologique.

**Borne de preuve.** Les champs `prompt_tokens` diffèrent pour **deux paires**. Le payload HTTP intégral, la révision backend et le routage fournisseur ne sont pas conservés. `max_tokens=2048` et l'alias sont reconstitués à partir du code/config, non d'un reçu immuable par requête. L'égalité reconstructible des requêtes ne prouve donc ni une exécution fournisseur identique ni l'indépendance statistique des réponses. Les 180 paires, regroupées par item et prompt, ne constituent pas 180 sujets indépendants.

**Correction requise.** Nuancer `paper/manuscript.md` §3.2 / §6, son template, C04 et les synthèses : absence de **plan systématique** de test–retest à configuration fixe, avec exception opportuniste GPT. Ne pas remplacer le FAIL, ni présenter ces kappas comme une nouvelle validation confirmatoire.

**État initial de clôture.** Correction présente dans le README nettoyé ; intégration du manuscrit/PDF encore à revérifier. Preuves : [CSV des 180 paires sans texte brut](evidence/gpt52_opportunistic_pairs.csv), [résultats](evidence/independent_results.json).

### F02 — P1 : la dépendance autorisée pouvait faire disparaître cinq ICC valides

**Preuve.** La contrainte initiale `requirements.txt:4` était `pingouin>=0.5.4`. Le sélecteur `src/analyzer.py:715` exige `Type == "ICC2"`. Pingouin 0.6.1 utilise **`ICC(A,1)`** pour ce coefficient. Il s'agit d'un changement d'API documenté par le [changelog officiel](https://pingouin-stats.org/changelog.html) et la [PR 501](https://github.com/raphaelvallat/pingouin/pull/501).

**Test réel.** L'audit a téléchargé le wheel public 0.6.1, vérifié son SHA-256 puis exécuté le sélecteur sur les données en lecture seule. La bibliothèque produit les cinq coefficients attendus ; SNAP renvoie pour chacun `value: null`, `reason: "ICC2 row not available"`. Claude demeure le seul vrai cas de matrice incomplète. Voir le [test de compatibilité](evidence/pingouin061_compatibility.json), son [script](audit_pingouin.py) et la [provenance du wheel](evidence/pingouin061_download.json).

**Conséquence.** Une installation autorisée par les anciennes contraintes pouvait dégrader la reproduction en masquant les ICC, même avec les bonnes données. Le FAIL global peut persister à cause de cross-SP ; cela ne rend pas cette disparition acceptable.

**Correction intégrée à vérifier au gel.** Le nettoyeur a remplacé `requirements.txt` par un renvoi au fichier figé `paper/requirements.lock.txt`, qui fixe **Pingouin 0.5.5**. C'est suffisant pour le parcours livré et préserve les calculs historiques. Le support 0.6+ peut rester une évolution distincte. Aucune nouvelle analyse scientifique n'est nécessaire pour cette correction de dépendance.

### F03 — P2 : l'accord global masque une saturation et une hétérogénéité des items

**Preuve indépendante.** E1 reçoit **+1 de chacun des deux juges et en score final pour 180/180 réponses**. L'accord exact vaut 100 %, mais κ est indéfini : l'accord attendu vaut aussi 100 %. E1 ne discrimine aucun modèle ni prompt dans ce corpus. La rubrique `config/scoring_rubrics.yaml:50` combine longueur et initiative ; 178 réponses dépassent 150 mots au comptage par espaces. Deux réponses plus courtes ne suffisent pas à conclure automatiquement à une faute d'annotation, car la rubrique combine plusieurs indices.

Parmi les quatorze kappas par item calculables, cinq sont inférieurs à 0,60 : A2 **0,4214**, C1 **0,3271**, M_AS **0,5446** (175 paires), N1 **0,5212**, O1 **0,4869**. Ce ne sont pas cinq nouveaux échecs du protocole : le seuil historique portait sur l'accord global. Les accords exacts associés vont de 68,89 % à 83,43 %, ce qui montre aussi l'influence de la prévalence sur κ. Voir [table complète par item](evidence/item_agreement_screen.json).

**Action maintenant.** Conserver « accord agrégé » et signaler la saturation/hétérogénéité dans les limites ou le supplément. Éviter « le principal problème n'est pas le codage » sans cette réserve. **Action future facultative.** Examiner les rubriques/items peu discriminants avant toute campagne plus grande, avec un protocole de révision et une validation indépendante. Aucun score historique à remplacer dans cet audit.

### F04 — P1 pour toute prétention de validation humaine : origine des labels non attestée

La traçabilité de 200 lignes est excellente ; la provenance des personnes qui les ont produites n'est pas établie. Le CSV expose `score_final`, le sample omet entièrement Claude, et il n'y a pas d'accord inter-humains documenté. Les dates `verified_at` des 200 lignes sont regroupées dans quelques millisecondes le 22 mai : ce sont des dates d'import, pas des durées de travail humain ni une preuve de saisie artificielle. Les 30 adjudications et les 200 lignes de validation sont correctement séparées et disjointes.

**Action maintenant.** Maintenir « human-labelled historical records » / « labels historiques dont l'origine humaine reste à attester ». Ne pas inventer identité, aveuglement, nombre de codeurs, consentement ou validation indépendante. Le κ final plus faible que celui de chaque juge ne prouve pas qu'une personne ou un juge a raison.

**Information qu'Emi seul peut faire établir.** Qui a codé et adjudiqué, avec quels outils, consignes et informations visibles, et quelle trace l'atteste. À défaut, une publication doit décrire honnêtement des labels historiques d'origine non vérifiée, sans en tirer une validation humaine. Un nouveau codage humain est utile pour une revendication plus forte, pas une condition artificielle à la présentation du résultat rétrospectif.

### F05 — P2 : les métriques ne testent pas toutes la même forme de stabilité

`src/analyzer.py:630` corrèle les moyennes des runs 1–5 / 6–10 sur 45 cibles item/SP ; ce n'est ni une corrélation de réponses individuelles ni une mesure temporelle avant/après. `src/prompt_builder.py:334` mélange l'ordre des runs. La formule “early- and late-run mean profiles” de l'abstract doit être remplacée par une description des **positions du calendrier**, sans implication temporelle.

ICC2 correspond ici à une mesure unique, accord absolu, avec les runs comme raters, alors que le calendrier modifie scénario, formulation et température. Le calcul ANOVA est correct mais son interprétation comme fiabilité de répétitions interchangeables est limitée. Claude n'est pas calculable après exclusion des deux refus ; le minimum de cinq valeurs ne prouve pas un passage du sixième modèle. Les distinctions entre type, modèle et définition d'ICC sont cohérentes avec [Koo et Li](https://pubmed.ncbi.nlm.nih.gov/27330520/). L'[erratum de 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5731844/) porte sur ICC(1,1), pas sur la formule ICC(2,1) vérifiée ici.

Le cross-SP historique utilise jusqu'à 150 paires item/run, et non quinze seules moyennes. Les items servent de blocs dans le bootstrap. Les intervalles postérieurs à la sélection du minimum et de la cellule E2 ne garantissent ni couverture simultanée ni généralisation à un univers d'items représentatif. La rédaction actuelle reconnaît correctement ces distinctions : les conserver.

### F06 — P2 : portée causale, seuils et modèle mixte à borner

Le calendrier est incomplet et déterministe. Les tests de scénario/formulation/température sur des moyennes item/SP ne suffisent pas à isoler leurs effets causaux de toutes les interactions ou du run. La correction Holm des 17 tests ne règle ni ce problème ni le regroupement par item. Aucune équivalence ou absence d'effet ne découle d'une p-value non significative.

Les eta-carrés (`src/analyzer.py:1050–1067`) sont des associations **unifactorielles séparées**, pas des composantes additives. La valeur item ≈0,4709 reflète aussi les polarités et distributions différentes des codes ; elle n'est pas une variance de « personnalité » commune.

Le modèle mixte `src/analyzer.py:1106–1119` fournit `groups=item_id` et des `vc_formula` pour run et modèle. Ces composantes sont évaluées **au sein de chaque item**, conformément à la [documentation Statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.regression.mixed_linear_model.MixedLM.from_formula.html). La formule en prose suggérant des effets globalement croisés n'est pas l'implémentation vérifiée. Le LMM utilise en outre les températures nominales GPT. Ses p-values ne sont pas des conclusions confirmatoires ; le manuscrit le dit déjà correctement.

Les commits locaux du [registre chronologique](evidence/local_git_chronology.json) contiennent le calendrier et les seuils le 24 avril / 10 mai, avant les réponses retenues du 12 mai. Le nom du critère cross-context a changé le 10 mai, avant celles-ci. Cette trace appuie une chronologie **locale**, sans établir un préenregistrement externe ni prouver le gel de toute interprétation avant inspection. L'audit n'a trouvé ni preuve d'une modification opportuniste des seuils après les résultats, ni preuve d'un préenregistrement indépendant. Préserver le statut rétrospectif est justifié.

### F07 — P1 pour une diffusion : le dépôt historique n'est pas le paquet de présentation

Les deux bases et le CSV contiennent les réponses, prompts et justifications. `outputs/reports/cross_sp_diagnostic.json` contient **180 champs textuels de réponse/extrait** identifiés par la structure JSON ; il ne faut pas le considérer comme purement agrégé. Le dépôt et son historique Git contiennent aussi du matériel brut et des métadonnées personnelles. Les règles d'ignore n'en retirent pas les objets déjà suivis.

La provenance initiale comportait des chemins personnels (`paper/PROVENANCE.md:3`, `paper/provenance/inherited_manifest.json:2`). Ce sont des informations de provenance locale utiles, mais elles ne sont pas nécessaires dans tous les paquets transmis à un lecteur. Les conserver dans la preuve privée et les exclure/adapter dans l'export permet de préserver la traçabilité.

**Action intégrée en cours.** Export par liste explicite, exclusion des bases/CSV brut, diagnostic brut, archives non revues, provenance privée, environnements et histoire Git ; contrôle des liens et manifeste des fichiers. La réalité du ZIP final doit encore être inspectée. Le scanner annoncé teste des motifs connus et des préfixes exacts de 160 caractères : il ne prouve pas l'absence de tout extrait paraphrasé, d'information personnelle ou de droit tiers. Le contrôle visuel des figures/PDF reste nécessaire.

**Diffusion scientifique.** Un paquet de présentation sans données brutes peut être honnêtement lisible et testable. Il ne permet pas à son destinataire de refaire les calculs complets sans accès distinct aux deux bases et au CSV. Le README/notice doivent l'annoncer. Aucun avis juridique n'est formulé : choix de licences, droits des textes/données, attribution et permission de diffusion restent à établir par le propriétaire.

### F08 — P3 : les dates de métadonnées ne sont pas toujours celles des premières réponses

Pour Mistral, `collection_metadata.start_time` vaut le 16 mai à **12:27 UTC**, tandis que la première réponse retenue date de **11:14 UTC**. Le code de reprise réenregistre une date de lancement. Le champ est utile pour l'exécution, mais un lecteur doit utiliser `responses.timestamp` pour dater les observations. Les six `model_version` restent nuls et les alias du modèle ne sont pas des révisions backend immuables. Les dates, drapeaux thinking et tokens ne remplacent pas des reçus fournisseur archivés. Cette limite n'invalide pas les calculs sur les textes conservés.

## 4. Reproductibilité effectivement testée

Environnement exécuté : **Python 3.12.14**, NumPy 2.4.2, Pandas 3.0.0, SciPy 1.17.0, Pingouin 0.5.5, Statsmodels 0.14.6, PyYAML 6.0.3, Matplotlib 3.10.8, pytest 9.0.2. Il s'agit d'une copie locale de l'environnement figé du manuscrit, pas d'une installation neuve complète depuis Internet. La compatibilité Pingouin 0.6.1 a été testée séparément avec un wheel réel dans un import isolé.

| Exécution | Résultat et preuve |
|---|---|
| `audit_recalculate.py --root work/source_snapshot --out docs/audit/evidence` | Comptes, jointures, règles et coefficients indépendants ; [JSON](evidence/independent_results.json) |
| `audit_additional_checks.py --root work/source_snapshot --out docs/audit/evidence/additional_checks.json` | Zéro écart de prompts/calendrier/IDs, zéro défaut de jointure ; [JSON](evidence/additional_checks.json) |
| `python -m pytest -q -p no:cacheprovider tests` dans la copie, sockets bloquées | **41 tests passent**, 12 avertissements, 35,76 s ; [log](evidence/pytest_initial.log) |
| `paper/scripts/reproduce.py --output-dir paper/audit-reproduction` dans la copie, sans réseau | **18 contrôles vrais**, quatre comparaisons sans écart à 1e-8, FAIL ; [log](evidence/reproduction_initial.log) et [audit](evidence/reproduction_initial_audit.json) |
| `audit_pingouin.py` avec `PYTHONPATH=work/pingouin061` | Cinq ICC calculés par la bibliothèque et perdus par le sélecteur SNAP ; [JSON](evidence/pingouin061_compatibility.json) |
| SHA-256 avant/après / comparaison original-auteur | Références identiques ; [comparaison](evidence/reference_comparison.json) |

Les avertissements portent sur calculs dégénérés et ajustements de modèles sur fixtures ; ils sont conservés dans les logs, sans être transformés en succès scientifique. Le verrouillage réseau Python est une prévention d'appel accidentel, non une preuve de confinement par le système d'exploitation. Les scripts n'ont pas besoin de clé fournisseur.

La modification de chemins et les nouveaux gardes de sortie du nettoyeur justifient une revue ciblée et les tests associés sur le candidat final. Les calculs statistiques inchangés n'ont pas besoin d'être refaits intégralement une troisième fois.

## 5. Évaluation de la littérature et des prétentions

La bibliographie est pertinente pour une étude de faisabilité et ne suffit pas à valider les items SNAP. Les notices primaires des huit références ont été revérifiées : [Huang et al.](https://aclanthology.org/2024.emnlp-main.354/), [Serapio-García et al.](https://www.nature.com/articles/s42256-025-01115-6), [CAPE](https://aclanthology.org/2025.findings-emnlp.563/), [Zierahn et al. v2](https://arxiv.org/abs/2607.02325v2), [Zheng et al.](https://arxiv.org/abs/2306.05685), [Cohen](https://journals.sagepub.com/doi/abs/10.1177/001316446002000104), [Koo et Li](https://pubmed.ncbi.nlm.nih.gov/27330520/), [Graham et al.](https://pubmed.ncbi.nlm.nih.gov/21244182/). Cette vérification ciblée porte sur les métadonnées et passages accessibles pertinents ; elle n'est pas une nouvelle revue systématique ni une lecture exhaustive indépendante des huit textes intégraux.

Le contraste entre résultats psychométriques conditionnels et critiques de validité est convenablement présenté. La version v2 de Zierahn est bien datée du 2 septembre 2026 dans le registre primaire. La critique de l'équivalence aux construits humains ne prouve pas que toute mesure comportementale est impossible. Réciproquement, des résultats de validité d'un autre questionnaire ou d'accord dans MT-Bench ne se transfèrent pas au corpus SNAP. Les déclarations du manuscrit qui limitent ces transferts sont à conserver.

Le résultat publiable le plus solide est **un audit rétrospectif explicite d'un protocole qui ne satisfait pas son propre critère de passage à l'échelle**, avec données scorablement structurées et mécanismes possibles de sensibilité. Une nouveauté scientifique générale, un classement stable des six modèles, une équivalence à la personnalité humaine ou une validation de sûreté ne sont pas établis.

## 6. Critères concrets d'achèvement

### Présentation privée ou revue scientifique interne

Prête lorsque les points suivants sont vérifiés sur le candidat final :

1. README, template, manuscrit, PDF, synthèse et claims cohérents sur le **FAIL**, les dénominateurs et l'exception GPT.
2. Chemin d'installation unique vers l'environnement figé ; sorties de reproduction nouvelles et séparées des références ; erreurs de données absentes intelligibles.
3. Accord présenté comme agrégé ; absence de Claude, origine des labels, saturation E1 et différence split-half/ICC explicitement annoncées.
4. PDF lisible, tables/figures cohérentes et liens de lecture fonctionnels ; ZIP limité aux fichiers inventoriés, sans données/extraits bruts ni chemins personnels détectés.
5. Identité/affiliation/licence et déclarations inconnues marquées comme telles. Ces TODO sont compatibles avec une présentation interne de travail ; ils ne sont pas des faits inventés.

### Mise en ligne du code, dépôt de données ou soumission

Outre les corrections techniques, il faut une décision du propriétaire sur **attribution et licence**, sur le périmètre de diffusion et les droits des matériaux, puis l'autorisation de publication/soumission. Le compte rendu de codage humain doit être attesté ou la revendication de validation humaine explicitement retirée. Les destinataires doivent disposer d'une description sincère de l'accès aux entrées nécessaires à la reproduction. La version diffusée doit être figée, identifiée et relue, avec ses déclarations réelles et les exigences du lieu de publication choisi.

L'audit n'exige pas un PASS ni une nouvelle campagne pour publier honnêtement un résultat négatif. Il n'assimile pas non plus « code exécuté » à « article accepté » ou à « instrument validé ».

### Expériences futures facultatives, distinctes des corrections actuelles

- Codage indépendant réellement humain sur réponses existantes, avec provenance, information visible et stratification documentées, si l'objectif devient une validation humaine plus forte.
- Révision préalable des items saturés ou ambigus ; définir ce que doit discriminer chaque rubrique et comment traiter zéro, refus et réponses tronquées.
- Petit suivi planifié à requêtes fixes, backends/reçus mieux consignés, répétitions temporelles et agrégation fixées à l'avance ; distinguer persona substantielle et variation superficielle.
- Plan factoriel et précision attendue définis avant toute campagne additionnelle ; hypothèses et seuils gardés séparés des résultats v3.1.

Ces pistes n'autorisent ni dépense ni appel de modèle. Elles ne sont pas nécessaires pour terminer le nettoyage et présenter le pilote existant avec ses limites.

## 7. Livrables et prochaine revue

Le présent rapport, l'addendum final, les quatre scripts `audit_*.py`, le journal [FINDINGS_EN_COURS.md](FINDINGS_EN_COURS.md) et `evidence/` sont les fichiers à recopier dans les outputs de coordination. **Ne pas recopier `work/`**, les bases ni l'environnement d'audit dans un dossier destiné à diffusion.

L'[addendum final](REVUE_FINALE.md) enregistre désormais le commit/état et les hashes du candidat nettoyé, le statut exact de F01 à F08, les contrôles du ZIP définitif et la revue des 14 pages du PDF. Le recalcul central et la revue ciblée sont terminés.
