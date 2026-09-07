# Expériences complémentaires : ordre de décision proposé

État : propositions de recherche à discuter. Aucun appel payant, nouvelle collecte, nouveau codage humain ni modification de protocole n'est autorisé ou effectué par ce document. Le verdict v3.1 reste FAIL. Préprint en anglais d'abord, avec synthèse française ; cible éditoriale à définir.

## P0 - Rendre la preuve existante défendable avant de collecter

**Question.** Peut-on établir qui a produit les 200 labels dits humains et les 30 adjudications, dans quelles conditions, et quand les règles de décision ont été arrêtées ?

**Action proposée.** Faire compléter par le responsable scientifique une fiche de provenance : nombre de personnes, rôle, formation, informations affichées, accès éventuel aux labels des juges et au score final, consentement/rémunération/exemption le cas échéant. Vérifier les archives de protocole et leur chronologie. Relever les versions de modèles ou logs de requêtes historiques uniquement s'ils existent et peuvent être consultés sans divulgation.

**Livrable et décision.** Annexe de provenance attestée. En l'absence de preuve, maintenir « labels historiques présentés comme humains », caractère rétrospectif et versions backend inconnues. Ne pas combler ces lacunes par une reconstruction narrative. Cette étape ne modifie aucune donnée historique.

## P1 - Validation humaine indépendante sur les réponses déjà collectées

**Question.** Les rubriques permettent-elles à des personnes indépendantes de coder les réponses avec un accord suffisant, et la règle de consensus dégrade-t-elle certaines catégories ?

**Design proposé à valider.** Échantillon nouveau tiré uniquement parmi les réponses existantes, avec quotas explicites pour les six modèles et trois prompts, couverture des 15 items et séparation d'un échantillon probabiliste d'un lot de cas difficiles. Faire coder en aveugle par au moins deux personnes ; masquer modèle, prompt système, juges et score final, tout en décidant à l'avance quel contexte de scénario est nécessaire au codage. Le code actuellement utilisé par les juges ne reçoit pas ce scénario explicitement : une version enrichie serait un changement de méthode à enregistrer, pas une reproduction.

**Taille proposée pour discussion.** Une première tranche de 180 réponses permettrait 10 observations par modèle-prompt et 360 actes de codage à deux personnes, sous réserve de l'allocation aux items. Ce nombre est une unité logistique, pas un calcul de puissance. Estimer la précision des accords et la charge de travail sur une courte calibration distincte, puis fixer la taille avant le codage du jeu évaluatif. Aucune promesse de puissance à 180.

**Mesures.** Matrices de confusion, accord exact, kappa nominal, kappas pondérés sur catégories ordinales seulement, taux de zéro/refus, intervalles tenant compte des items. Accords personne/personne puis personne/juge1, personne/juge2, personne/score final séparés. Comparer la règle historique avec des alternatives uniquement en sensibilité, sur un jeu tenu à l'écart du développement des rubriques. Rapporter les refus et manquants sans substitution.

**Décision.** Figer les définitions ambiguës et la politique d'adjudication avant la prochaine campagne. Une forte concordance entre deux juges LLM ne remplace pas cette étape. Ne jamais inscrire le jugement d'un agent comme codage humain.

## P2 - Distinguer les effets d'instruction et le construit mesuré

**Question.** E1/E2 mesurent-ils surtout longueur, style et degré d'initiative imposés par l'instruction ? Quel est le statut de SP_PER dans l'usage visé ?

**Design proposé.** Audit qualitatif aveugle des cellules critiques et d'un échantillon de cellules ordinaires. Conserver une version v3.1 intacte. Développer en parallèle des items candidats et des rubriques qui distinguent explicitement contenu de décision, degré d'initiative et longueur. Préparer des contrôles d'instruction de style dont l'effet attendu est explicite ; garder des items et formulations de validation distincts de ceux utilisés pour la révision.

**Décision requise.** Définir avant toute nouvelle réponse si SP_PER appartient au domaine de robustesse ordinaire ou à une épreuve séparée de modification de posture. Le retirer après observation ne constitue pas un PASS v3.1. Le critère de réussite futur doit découler de l'usage, pas du seuil le plus facile à franchir.

## P3 - Micro-campagne factorielle avec répétitions planifiées à configuration fixe

**Constat préalable.** Les 180 paires opportunistes GPT-5.2 déjà présentes sont documentées dans la revue. Elles ne couvrent qu’un endpoint sur une journée et n’attestent pas l’équivalence complète des exécutions fournisseur. Le nouveau design doit planifier et tracer ces répétitions pour toutes ses cellules.

**Question.** Quelle part de variation relève de l'instruction système, du scénario, de la formulation, de la température réellement appliquée et de la répétition à configuration identique ?

**Exemple de tranche à chiffrer, non arrêté.** Deux endpoints choisis avant collecte, quatre items sélectionnés pour couvrir les mécanismes étudiés et pas seulement les échecs, trois prompts, deux scénarios, trois formulations, une température fixe effectivement supportée, cinq répétitions indépendantes par configuration : 2 x 4 x 3 x 2 x 3 x 1 x 5 = **720 réponses**, soit **1 440 évaluations de juges** pour deux juges, hors reprises. Ajouter une deuxième température multiplie le volume par deux et nécessite une décision distincte. Ce design permet des répétitions identiques et le croisement des trois facteurs de prompt, mais sa généralisation resterait limitée à quatre items et deux endpoints.

**Avant exécution.** Estimer le coût actuel à partir du catalogue public, du nombre de tokens et des reprises bornées ; obtenir une autorisation de budget, modèles, données envoyées et limites. Enregistrer les prompts complets, hashes, règles d'arrêt, exclusions, versions/configurations disponibles, ordre aléatoire, temps de collecte et prix au lancement. Aucune clé disponible ni crédit Codex ne remplace cette autorisation.

**Estimands à choisir.** Effets de contraste sur scores ordinaux et probabilities de catégories ; accord intra-configuration ; comparaison entre prompts à configuration identique ; interactions item-prompt. Ne pas imposer une échelle continue commune à des pôles sémantiquement différents sans justification. Distinguer le score d'une réponse de celui d'une moyenne de plusieurs réponses. Un modèle ordinal hiérarchique peut être candidat, avec contrôle explicite de ses hypothèses et structure de dépendance.

**Précision et puissance.** Choisir une différence minimale pertinente ou une marge d'équivalence à partir de l'usage, puis simuler sous plusieurs distributions plausibles de catégories, variances entre items et dépendances intra-cellule. Rapporter précision attendue, taux de faux positifs, puissance pour chaque estimand prioritaire et sensibilité aux hypothèses. Utiliser la v3.1 pour encadrer les scénarios, pas pour retenir seulement le paramètre le plus favorable. Fixer le nombre d'items et de répétitions après cette étude, avant d'observer les réponses du suivi. L'absence de significativité ne démontrera pas l'équivalence.

## P4 - Confirmation indépendante et extension

**Question.** Les scores améliorés prédisent-ils un comportement externe pertinent et se maintiennent-ils dans une autre session, des items tenus à l'écart ou un contexte conversationnel défini ?

**Conditions d'entrée.** Provenance du codage documentée, rubriques stabilisées hors jeu évaluatif, protocole et analyse prospectifs fixés, micro-campagne interprétable. Définir un critère externe comportemental qui ne soit pas simplement une paraphrase des items ; comparer aux baselines nécessaires et aux effets de style. Envisager plusieurs langues ou le multi-tour seulement avec un plan de validation propre.

**Décision.** Une campagne large se justifie si le petit protocole mesure un objet utile avec une incertitude acceptable pour l'usage visé. Une invariance absolue n'est pas nécessairement l'objectif ; ce choix conceptuel doit précéder la collecte. Aucun résultat de ces étapes ne doit être présenté comme personnalité intrinsèque sans une théorie et des preuves supplémentaires indépendantes.

## Ordre de revue du préprint

1. Valider le cadrage « faisabilité d'une mesure de profils conditionnés » et le FAIL.
2. Résoudre P0 ou rendre ses lacunes explicites dans les déclarations.
3. Revoir méthode, dénominateurs, polarités et figures avec la matrice des claims.
4. Relire les scripts et refaire la reproduction locale ; choisir un dépôt scientifique après revue des droits.
5. Décider ce qui doit précéder une diffusion du préprint : une rédaction honnête peut conserver des limites, mais une affirmation de validation humaine indépendante exige les preuves correspondantes.
