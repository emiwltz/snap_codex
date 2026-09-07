# Audit SNAP — constats disponibles pour la coordination

**Revue finale terminée, 6 septembre 2026. Aucun constat restant n'exige une correction du worktree pour la présentation privée.** Le PDF final (14 pages, SHA-256 `fc5d07097e2b21f68ad38fe6f7b0d259c0015b0ded925d332faba6e561380d49`) et le ZIP final **102 fichiers** (`20d35b85fa0aac1a1576ed0f0af3a75be8b3b4238b87f485119a4c0b27e1f179`) ont été revus indépendamment. Contrôles ZIP/empreintes/liens conformes, six tests ciblés passent dans l'extraction finale ; erreur de quatre entrées manquantes explicite, sans sortie créée. Les 180 paires et quinze résumés d'items intégrés concordent exactement avec nos calculs. Identité publique, affiliation, licence, accès/droits des données et provenance du codage restent des décisions/informations de diffusion, non des défauts à corriger par invention. Preuves : [contrôles finaux](evidence/final_candidate_checks.json), [classification du scan textuel](evidence/final_text_match_classification.json). Addendum : [REVUE_FINALE.md](REVUE_FINALE.md).

Ce fichier conserve ci-dessous la chronologie des constats initiaux. Aucune référence n'a été modifiée. Le verdict scientifique historique reste **FAIL**.

## Confirmé : exception GPT-5.2 aux répétitions

Sur la capture auteur du 6 septembre à 01:57:38 UTC (HEAD `eae718894aafad84e61febc2848dc6300c25403b` et modifications locales ensuite conservées dans `d9fa3de`) : `temperature_applied=0` et `top_p_applied=0` sur 450/450 réponses GPT. Les 450 messages conservés forment 270 signatures de requête reconstructibles : 180 groupes de deux et 90 occurrences seules. Les quatre paires 1/7, 2/8, 3/9, 4/10 comptent chacune 45 paires, soit **180**.

- Les mêmes messages sont stockés ; le modèle et `max_tokens=2048` sont des paramètres inférés du code/config historique. `run`, `trial_id` et la graine de permutation ne sont pas transmis au fournisseur (`src/runner.py:172`, `src/api_client.py:144`).
- Scores finaux : **142/180 accords (78,8889 %), kappa nominal 0,646017699115, Pearson 0,744037789021**. Aucun texte de réponse strictement identique.
- Dates GPT : 12 mai 2026 ; écarts absolus de timestamps entre partenaires **33,570237–9305,727882 secondes**, médiane **3112,16338**. Les timestamps sont ceux de stockage après réponse.
- **Réserve supplémentaire : 2/180 paires ont des comptes `prompt_tokens` différents** (M_LB/DIR runs 1/7, M_PS/DIR runs 3/9). Les champs ne permettent pas d'établir la cause. Ne pas transformer l'égalité reconstructible en identité attestée du backend ou de toute l'exécution fournisseur.
- Les cinq autres modèles n'ont pas de requêtes reconstructibles répétées dans ce calendrier lorsque leur température envoyée est prise en compte.

Formulation proposée : “The rotated design is not a systematic fixed-configuration test–retest study. GPT-5.2 provides an opportunistic exception: omission of temperature and top-p yields 180 pairs with identical reconstructible request messages and configured generation parameters. Backend identity and provider execution equivalence are not established.”

À aligner : `paper/manuscript.template.md` / manuscrit §3.2 et §6 ; `paper/CLAIMS.md` et `claims.csv` C04 ; synthèses qui affirment une absence globale de répétitions. Aucun nouveau seuil, label humain ou changement de FAIL n'est justifié par cette analyse exploratoire.

Preuves réutilisables : [résultats indépendants](evidence/independent_results.json), [180 paires sans texte brut](evidence/gpt52_opportunistic_pairs.csv), [script autonome sans dépendance ni import SNAP](audit_recalculate.py).

## Confirmé : intégrité et chiffres centraux

Deux `integrity_check=ok`, 2 700 `trial_id` uniques, 270 cellules modèle/item/SP de dix réponses. Tables `responses` des deux bases strictement identiques, 200 IDs/labels CSV identiques à `human_validation`, aucune divergence des champs de contexte vérifiés. Aucune violation de la règle de résolution détectée ; 30 adjudications distinctes, aucune orpheline ni divergence de score final.

Kappa inter-juges **0,7509073105151067 sur 2 695 paires**, accord **84,08163265 %**. Kappas des 200 labels historiques : 0,623424531202 / 0,630383948103 / 0,578899875926. Couverture Claude = **0** ; les cinq autres effectifs sont 43 GPT, 25 Gemini, 43 Qwen, 44 Mistral, 45 Grok. Ce recoupement ne prouve pas la qualité ou l'origine humaine des labels.

## Précisions de chronologie à intégrer si nécessaire

- “early- and late-run mean profiles” dans l'abstract est trompeur si lu chronologiquement : les runs sont mélangés. Préférer “first- and second-half **scheduled-run** mean profiles”, ou explicitement “runs 1–5 versus runs 6–10”.
- Le début de métadonnées Mistral est 12:27 UTC alors que les réponses commencent à 11:14 UTC le 16 mai : il reflète une reprise. Pour dater les observations, utiliser les timestamps des réponses et distinguer ceux de `collection_metadata`.
- Les commits locaux `be15135` (24 avril) et `0646789` (10 mai) contiennent déjà le calendrier et les seuils, avant les premières réponses conservées (12 mai). Cela appuie une chronologie locale ; ce n'est pas un enregistrement préalable indépendant et immuable. Ni une preuve d'antidatage, ni une preuve de preregistration externe.

## Contrôles encore en cours

Exécution hors réseau de la suite et de la reproduction sur la copie d'audit ; contrôle des fichiers du paquet de présentation ; révision bibliographique ciblée ; revue du PDF final et des corrections du nettoyeur. Identité publique, affiliation et licence restent indécises selon Emi, sans empêcher l'audit ou la présentation privée.

## Nouveau constat prioritaire — incompatibilité réelle avec Pingouin 0.6.1

**P1 pour une installation de développement avec `requirements.txt` ; le lock du manuscrit fonctionne.** `requirements.txt:4` autorise `pingouin>=0.5.4`, mais `src/analyzer.py:715` sélectionne strictement `Type == "ICC2"`. La version 0.6.1 renvoie désormais `ICC(A,1)` pour ce coefficient. Le changement est documenté dans le [changelog officiel](https://pingouin-stats.org/changelog.html) et la [PR 501](https://github.com/raphaelvallat/pingouin/pull/501).

Test **effectivement exécuté**, sans simulation : téléchargement du wheel public 0.6.1 dans `work/pingouin061`, SHA-256 vérifié auprès de PyPI, puis import isolé avec les dépendances déjà figées et connexion SQLite en lecture seule. Pingouin calcule bien 0,548627174897 pour Mistral (et les quatre autres ICC complets), mais SNAP renvoie **`value: null`, `reason: "ICC2 row not available"` pour les cinq modèles complets**. Le cas Claude reste la véritable matrice incomplète ; ne pas confondre les deux causes.

Preuves : [test réel de compatibilité](evidence/pingouin061_compatibility.json) et [script](audit_pingouin.py). Le wheel utilisé est `pingouin-0.6.1-py3-none-any.whl`, SHA-256 `514f2897d7ee354723268551147bbc95849ccec83d6f1dddde1395779c6a7b15`.

Correction minimale au choix du nettoyeur : contraindre la plage réellement prise en charge, ou accepter les deux noms équivalents avec un test ciblé et contrôle de formule/valeurs. Le README en cours recommande déjà le lock 0.5.5, ce qui protège la voie principale ; sa phrase indiquant que les contraintes larges sont « supported » reste trop forte tant que ce cas n'est pas traité. Aucun seuil ni donnée historique à changer.

## Reproduction initiale terminée

Suite locale : **41 tests passent, 12 avertissements**, 35,76 s, connexions sortantes bloquées. Reproduction complète avec 5 000 rééchantillonnages : **18 contrôles vrais**, zéro différence à tolérance 1e-8 dans les quatre familles de rapports, **FAIL**. Kappa, six split-half, cinq ICC calculables et les 18 corrélations cross-SP ont également été recomputés indépendamment sans imports SNAP dans `audit_recalculate.py`.

## Nouveau diagnostic scientifique — accord global et items saturés

Le kappa global ne décrit pas uniformément les quinze rubriques. Recalcul par item, **exploratoire sans nouvelle règle de décision** : cinq des quatorze kappas finis sont sous 0,60 (A2 0,4214 ; C1 0,3271 ; M_AS 0,5446 sur 175 paires ; N1 0,5212 ; O1 0,4869). Leurs accords exacts sont respectivement 76,11 %, 82,78 %, 83,43 %, 68,89 %, 76,11 % : la prévalence des catégories compte dans l'interprétation.

E1 est **entièrement constant** : les deux juges et le score final donnent +1 à **180/180 réponses**. L'accord vaut 100 %, mais son kappa est indéfini puisque l'accord attendu vaut aussi 100 %. Cet item ne discrimine ni modèle ni prompt dans le corpus. La rubrique comporte des bandes de longueur ; 178 réponses dépassent 150 mots au comptage par espaces, deux sont entre 100 et 150 mots. Ce dernier écran automatique n'établit pas à lui seul une erreur de codage : la rubrique combine longueur et contenu. Aucune étiquette n'a été remplacée.

Pour la présentation : préserver la formulation d'« accord agrégé » et signaler cette hétérogénéité/plafond plutôt que conclure que le codage ne pose plus de problème. Un tableau d'accord par item en supplément serait utile ; ce diagnostic ne modifie pas le FAIL historique. Preuve : [item_agreement_screen.json](evidence/item_agreement_screen.json), [écran de longueur E1](evidence/e1_wordband_screen.json).
