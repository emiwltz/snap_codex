# Vérifications du premier manuscrit

Date : 6 septembre 2026, avant le nettoyage du dépôt. Ce document conserve les vérifications du premier brouillon. Les vérifications de la révision et de l’export sont dans [l’inventaire du nettoyage](../docs/CLEANUP.md). Périmètre : ce worktree de SoulBench SNAP, campagne retenue v3.1. Les contrôles de reproduction réussis ne changent pas le résultat scientifique FAIL.

## Données et calculs

- Les 41 fichiers de référence comparés entre le checkout original et ce worktree étaient identiques par SHA-256 lors de l'import. Les 19 fichiers de travail local nécessaires ont été récupérés et fingerprintés ; le détail est dans `provenance/inherited_manifest.json`.
- Les deux copies initiales SQLite, puis les backups temporaires du script de reproduction, ont passé `PRAGMA integrity_check`.
- Les contrôles de `results/audit.json` vérifient l'unicité des 2 700 essais, les 270 cellules modèle-item-prompt de dix runs, la complétude des scores, le calendrier et les textes de prompts, la correspondance CSV/base de validation/campagne, et les empreintes avant/après.
- Stabilité, sensibilité, variance et décision ont été recalculées sur une même copie isolée avec configuration copiée. La comparaison récursive aux archives ignore uniquement `generated_at` et accepte une tolérance absolue/relative de 10^-8. Les quatre familles de rapports n'ont aucune différence à ce niveau de tolérance.
- Les cinq ICC numériques ont aussi été recalculés par une formule ANOVA indépendante de Pingouin. Le cas Claude non calculable a été conservé ; aucun score de refus n'a été imputé.
- Les accords nominal/ordinal, 18 corrélations entre prompts, 5 000 rééchantillonnages par analyse, diagnostics d'agrégation, sensibilités aux réponses tronquées et aux codes de chaque juge, et la correction de Holm sur les 17 tests applicables ont été exécutés. Les fichiers machine portent leurs dénominateurs et paramètres.
- Les analyses utilisent un blocage des connexions socket. Aucun `collect`, `score`, catalogue payant, scoring humain artificiel ou appel de complétion n'a été exécuté.

## Tests du dépôt

Commande exécutée dans l'environnement isolé : appel à `pytest.main(['-q', '-p', 'no:cacheprovider', 'tests'])`, avec `socket.socket.connect`, `connect_ex` et `create_connection` remplacés par une fonction levant une erreur. Cache Matplotlib séparé dans un répertoire temporaire. Les tests utilisent des bases temporaires et des clients/transport simulés.

**Résultat : 41 tests réussis, 12 avertissements, 49,44 secondes.** Les avertissements concernent les données synthétiques de tests d'analyse : divisions indéfinies de tests non paramétriques, convergence/gradient et Hessienne d'un modèle mixte. Ils ne sont pas des erreurs ignorées d'une campagne réelle. La convergence du LMM sur les données de référence est contrôlée séparément, et n'est pas utilisée comme preuve de validité confirmatoire.

La correction héritée de `src/db.py` et son test n'ont pas été modifiés. Aucun nouveau test n'effectue de collecte réseau ou de mutation d'une base de référence.

## Documents, figures et liens

Les trois figures ont été générées depuis les agrégats, en PNG et SVG. La revue visuelle a détecté une légende empiétant sur les points Qwen de la figure E2 ; elle a été déplacée hors du panneau avant le rendu final.

Le générateur de PDF vérifie l'absence de variables de gabarit non résolues, l'usage de toutes les références, la présence des résultats clés dans le texte extrait, le nombre de tableaux/figures et les hashes du manuscrit/PDF. Le document final compte **14 pages, 6 065 mots Markdown (références et tableaux compris), cinq tableaux, trois figures et huit références**. Le compte et les empreintes sont consignés dans `results/document_checks.json`.

Les **14 pages du PDF final ont été rendues par Poppler à 110 dpi et inspectées visuellement**, en sept planches de deux pages. Titres, paragraphes, tableaux, figures, légendes, références, numéros de page et marges ne présentent pas de débordement, superposition ou glyphe manquant repéré. Les tableaux restent entiers et les figures restent avec leur légende. Une partie de la page 8 reste volontairement blanche pour conserver la figure suivante avec sa légende.

Le Poppler fourni par le runtime a produit des avertissements de configuration/cache Fontconfig tout en terminant le rendu des 14 pages avec code 0 ; les fontes intégrées au PDF sont correctement visibles. Il ne faut pas confondre ce diagnostic d'environnement avec une preuve de défaut de mise en page. Une commande utilisant le Poppler système disponible est donnée dans le README pour les revues ultérieures.

Tous les liens locaux des documents Markdown livrés ont été vérifiés : aucun chemin manquant. Les huit références citées figurent dans le registre bibliographique et le BibTeX ; aucune variable de gabarit ne subsiste dans le manuscrit généré. `git diff --check` et la compilation Python des deux nouveaux scripts réussissent. Une vérification finale des empreintes a confirmé que tous les fichiers hérités/référence sont encore identiques au manifeste, dans l'original comme dans le worktree.

## Limites des checks

Les hashes attestent la stabilité des entrées utilisées, pas la véracité des labels historiques. L'égalité des deux bases n'est pas une réplication indépendante : elles partagent les mêmes réponses. La correction de Holm est exploratoire et ne résout ni le regroupement par items ni le calendrier partiellement confondu. La disponibilité actuelle des endpoints, leur authentification, leurs prix et leurs révisions backend n'ont pas été testés. Aucune nouvelle validation humaine ou expérience confirmatoire n'a eu lieu. Les détails non attestés restent des TODO dans le manuscrit.
