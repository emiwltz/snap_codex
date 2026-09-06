# Provenance du dossier de manuscrit

Reconstitution locale effectuée le 6 septembre 2026, dans `/Users/emi/.codex/worktrees/1f77/snap_codex`, depuis le checkout original `/Users/emi/code/side/snap_codex`. Le sibling `snap` n'a pas été utilisé. Aucun fichier original n'a été modifié.

## Base de comparaison et travail hérité

Les deux checkouts avaient le même HEAD : `eae718894aafad84e61febc2848dc6300c25403b`. Le worktree Codex était propre. Le `AGENTS.md` original a été lu avant toute analyse.

Sept modifications suivies ont été récupérées à l'identique : `README.md`, `config/manual_adjudication_workflow.md`, `config/methodology_h4.md`, les instructions des deux documents d'archive v3.1 concernés, `src/db.py` et `tests/test_db.py`. Douze fichiers non suivis utiles ont aussi été récupérés : `AGENTS.md`, deux scripts de reproduction, cinq agrégats de reproduction publication et quatre rapports de reproduction core.

Le [manifeste d'import](provenance/inherited_manifest.json) donne les 19 chemins exacts et leurs SHA-256, ainsi que ceux de 41 fichiers de référence vérifiés identiques entre original et worktree (données, config, code et sorties retenues). Le [patch suivi hérité](provenance/inherited_tracked.patch) isole intégralement les modifications qui existaient avant cette tâche. Les nouveaux travaux de cette tâche sont exclusivement sous `paper/`. Aucun commit n'a été créé ; un `git diff` à HEAD inclut donc aussi les modifications héritées, qu'il ne faut pas attribuer au manuscrit.

La correction de l'échantillonnage dans `src/db.py` et son test sont préservés. Leur objet est l'allocation des futurs échantillons par modèle avant sous-stratification. Aucun nouvel échantillon ni label n'a remplacé les 200 lignes historiques. Le zéro de couverture de Claude est une propriété de la preuve historique conservée.

## Fichiers volontairement exclus de l'import nouveau

Aucun secret, `.env`, environnement virtuel, log fournisseur, WAL/SHM ou autre runtime n'a été importé depuis l'original. Les diagnostics non suivis pouvant contenir des extraits bruts n'ont pas été recopiés. Les bases et textes bruts déjà suivis dans HEAD restent des références privées locales ; ils ne font pas partie du nouveau dossier de diffusion `paper/`. Aucune publication ni export externe n'a été effectué.

Les copies SQLite cohérentes, dépendances, caches et logs de calcul sont placés sous `paper/private/`, ignoré par Git. Les rendus de contrôle sont sous `paper/qa/`, également ignoré. Les scripts ne lancent aucun serveur local : aucun port n'est occupé.

## Audits des scripts hérités

- `scripts/reproduce_article_artifacts.sh` copie une base avec `cp`, ce qui ne garantit pas la prise en compte d'un WAL actif ; il produit aussi des diagnostics avec extraits. Il n'a pas été exécuté. Le nouveau script utilise `sqlite3.Connection.backup` et n'exporte pas d'extraits.
- `scripts/reproduce_preliminary.py` ouvre SQLite en lecture seule et fournit des calculs d'accord, de corrélation et de bootstrap utiles. Ses fonctions statistiques sont réutilisées avec les empreintes et paramètres consignés. Sa commande principale n'est pas exécutée : elle exclut l'échec de couverture humaine de son code de sortie. La couverture insuffisante est un résultat explicite du nouveau dossier, jamais un contrôle implicitement réussi.
- L'intervalle bootstrap par items respecte le regroupement des runs, mais suppose l'échangeabilité de 15 items choisis, sans donner un échantillon représentatif d'items. Le bootstrap et les p-values de la cellule critique sont post-sélection ; la rédaction ne les transforme pas en résultat confirmatoire.
- `src/decision.py` reçoit ses rapports sans vérification interne de provenance. Le nouveau script génère les analyses et la décision séquentiellement sur le même backup/config, vérifie les hashes et compare aux archives.
- `src/analyzer.py` appelle ICC2 de Pingouin, ne peut calculer l'ICC Claude après les deux refus, et calcule des eta-carrés unifactoriels séparés. Le LMM demeure exploratoire malgré son nom JSON ; les composantes de variance sont construites au sein des groupes item, ce qui limite l'interprétation de la formule historique comme effets aléatoires globalement croisés.

## Chaîne de preuve

1. Lire les entrées de référence sans migration et vérifier leurs empreintes.
2. Produire deux backups cohérents et une copie de la configuration dans un dossier temporaire privé.
3. Vérifier couverture, unicité, calendrier et fidélité des prompts ; joindre CSV/validation/campagne sans exporter le texte.
4. Recalculer stabilité, sensibilité, variance et décision, puis kappas sur la copie de validation distincte.
5. Recalculer indépendamment les ICC complets avec la formule ANOVA ; produire corrélations, kappas, bootstrap, sensibilités et figures agrégées.
6. Comparer aux rapports archivés en ignorant uniquement les timestamps de génération, avec une tolérance absolue et relative de 10^-8.
7. Vérifier à nouveau les inputs. Le rendu du manuscrit refuse des inputs devenus différents de ceux du calcul.

Les résultats chiffrés et l'environnement exécuté sont dans [audit.json](results/audit.json). L'audit distingue les contrôles d'intégrité réussis des limites scientifiques connues : couverture incomplète, provenance humaine non établie, preregistration non vérifiée et révisions backend absentes. Un code de sortie nul signifie que la reproduction des preuves a réussi ; il ne signifie jamais PASS scientifique.

## Bibliographie

[references.json](references.json) consigne pour chaque citation le titre, les auteurs, DOI, URL, date de vérification et mode de consultation. Les articles ACL et arXiv ont des textes primaires consultés ; pour des liens éditeur inaccessibles, les limites et corroborations sont écrites explicitement. Les DOI sont vérifiés dans des notices bibliographiques ou sources primaires, sans prétendre que chaque serveur DOI a répondu directement. La version 2 du papier de Zierahn et al. du 2 septembre 2026 est distinguée des anciens résultats de recherche. Aucun DOI de proceedings non vérifié n'est ajouté.
