# SoulBench SNAP v3.1 - synthèse scientifique

Le premier manuscrit présente un résultat de faisabilité négatif et informatif : **les réponses se codent de façon assez cohérente selon les règles historiques du projet, mais le protocole ne satisfait pas tous ses critères de stabilité et de robustesse. Le verdict v3.1 est FAIL.** Il porte sur des profils de réponse sous prompting contrôlé, sans inférence de personnalité intrinsèque.

## Ce que contient réellement la preuve

Le corpus comprend 2 700 réponses, soit six endpoints x 15 items x trois conditions système x dix runs. Les réponses ont été enregistrées du 12 au 16 mai 2026 ; le nom du dataset contient avril, mais ce n'est pas la date de collecte. Tous les essais ont un score final et aucune ligne finale d'erreur ne subsiste. Le nombre réel de tentatives API et leur coût ne sont pas déductibles du nombre de lignes.

Les deux juges disposent de 2 695 paires complètes : cinq scores du second juge manquent et ont été résolus par adjudication. L'accord exact juge/juge est 84,08 %, le kappa nominal 0,7509. La résolution aboutit à 2 266 accords directs, 404 désaccords voisins ramenés automatiquement à zéro et 30 adjudications. Deux réponses sont des refus ; les calculs numériques utilisent donc 2 698 réponses.

Le terme « validation humaine » doit rester prudent. Les 200 labels historiques correspondent bien au CSV et à la base, mais leur auteur, l'indépendance du codage, la formation et l'aveuglement n'ont pas été établis par les fichiers examinés. Le CSV exporté affiche le score final. Claude Sonnet 4.5 n'est pas représenté ; les autres effectifs vont de 25 à 45. Les kappas personne/juge1, personne/juge2 et personne/score final sont respectivement 0,6234, 0,6304 et 0,5789, sur cet échantillon incomplet. Ils ne démontrent ni une vérité terrain indépendante ni une validation représentative des six modèles.

## Le résultat central, avec ses dénominateurs

| Mesure historique | Résultat | Lecture |
| --- | --- | --- |
| Kappa juge/juge | 0,7509 ; 2 695 paires | Cible 0,60 atteinte ; floor historique 0,50 |
| Refus | 2/2 700 = 0,074 % | Maximum historique 10 % respecté |
| Désaccords majeurs initiaux | 24/2 695 = 0,891 % | À distinguer des 30 adjudications |
| Minimum split-half | 0,8827 ; six modèles | Corrélation de moyennes de runs, critère atteint |
| Minimum ICC(2,1) | 0,5486 ; cinq valeurs disponibles | Critère 0,60 manqué ; Claude non calculable |
| Minimum corrélation entre prompts | 0,3189 ; 18 comparaisons | Critère 0,60 manqué ; Mistral DIR/PER |

Les règles figurent dans le protocole et la configuration conservés. La présente inspection n'établit pas leur préenregistrement daté ; le manuscrit ne les qualifie donc pas de préenregistrées. Les reproduire permet de vérifier le verdict historique, sans transformer cette analyse rétrospective en test confirmatoire.

## Pourquoi les corrélations ne racontent pas toutes la même chose

La corrélation split-half compare, sur 45 cibles item-prompt, les moyennes des runs 1-5 aux moyennes des runs 6-10. L'ICC traite chaque run comme une mesure unique. Or ces runs changent scénario, formulation et température nominale selon un calendrier fixe : ce ne sont pas dix répétitions identiques. Pour GPT 5.2, température et top-p ne sont même pas envoyés. La stabilité temporelle pure n'est donc pas identifiée.

Le pire cas entre prompts, Mistral DIR/PER, donne une corrélation de 0,3189 sur 150 paires item-run. La corrélation des quinze moyennes d'items monte à 0,5186 et celle des réponses centrées au sein des items descend à 0,0606. L'intervalle descriptif obtenu par rééchantillonnage des quinze items est large : [-0,0672 ; 0,6413]. Ces calculs concernent des niveaux différents. L'incertitude traverse le seuil historique et n'autorise pas à transformer son franchissement ponctuel en preuve générale d'invariance ou d'absence d'invariance.

La condition introspective PER modifie explicitement la posture attendue. Pour Mistral sur E2, qui code l'initiative, les moyennes sont 0,8 en ABS, 0,6 en DIR et -0,9 en PER. Le contraste est grand dans les données observées, mais le cas a été sélectionné après inspection. Les figures montrent les autres modèles et les 18 paires pour rendre visible cette sélection. Mistral échoue aussi pour ABS/DIR ; PER n'explique donc pas à lui seul toutes les fragilités.

## Diagnostics supplémentaires inclus

- Les 17 réponses tronquées de Mistral, toutes au plafond de 2 048 tokens, restent dans la référence. Les retirer dans une analyse de sensibilité laisse la corrélation Mistral DIR/PER à 0,3189 sur 149 paires ; cela ne répare pas la mesure.
- Utiliser séparément les codes de chaque juge donne, pour cette paire, 0,3316 et 0,3575. La sensibilité au choix de codage est exposée sans remplacer le score final historique.
- Les p-values température de Gemini et Grok sont environ 0,0280 et 0,0211 avant correction. Aucune des 17 comparaisons applicables ne reste significative après correction post-hoc de Holm ; le minimum ajusté est 0,3588. Cela ne démontre pas l'absence d'effet : les facteurs sont partiellement confondus et la puissance n'a pas été établie pour une marge d'intérêt définie à l'avance.
- L'eta-carré par item est 0,4709, mais ce sont des associations unifactorielles séparées, sur des codes dont les polarités diffèrent selon les items. Ce n'est pas une décomposition causale additive. Le LMM reste exploratoire et ses p-values ne soutiennent pas les conclusions principales.

## Ce qui est livré et ce qui reste ouvert

Le dossier contient le manuscrit anglais complet, son PDF, les figures agrégées PNG/SVG, cinq tableaux dans le texte, huit références vérifiées avec un registre de consultation, un supplément reprenant les prompts/rubriques, la matrice des claims, le plan d'expériences et les scripts de reproduction. Les quatre rapports core sont retrouvés sans différence au niveau de tolérance 10^-8, timestamps de génération exclus. Les ICC complets sont aussi vérifiés par une formule ANOVA indépendante.

La prochaine décision utile porte sur la provenance du codage humain et l'objet à mesurer : profil moyen, réponse individuelle, robustesse ordinaire ou épreuve de posture. Le plan proposé privilégie d'abord la documentation et un vrai codage humain indépendant des réponses existantes, puis une petite campagne où les facteurs sont croisés et où des répétitions réellement identiques sont présentes. Les tailles données dans ce plan sont des exemples logistiques, pas des résultats de puissance.

Les auteurs, affiliations, contributions, financement, conflits, statut éthique du codage et droits de diffusion restent à compléter. Aucun nouvel appel de modèle, aucune collecte, aucun contact, aucune soumission ou publication n'a été réalisé. Le préprint est préparé pour une revue scientifique ; son lancement public et les éventuelles expériences restent des décisions ultérieures.
