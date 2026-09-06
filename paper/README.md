# Premier manuscrit scientifique SNAP

Le dossier prépare un **préprint en anglais avec synthèse française**, sans cible éditoriale fixée. Il décrit la campagne v3.1 existante et préserve son **FAIL**. Aucun nouveau modèle n'a été appelé, aucune donnée n'a été collectée et rien n'a été publié ou soumis.

## Parcours de lecture

1. [Synthèse française](SYNTHESE_FR.md) : constat scientifique, chiffres, limites et décisions utiles.
2. [Manuscrit anglais](manuscript.md) et [PDF de lecture](output/pdf/snap_v3_1_manuscript.pdf) : texte substantiel, méthodes, résultats, discussion, validité, éthique et reproductibilité.
3. [Matrice de 30 affirmations](CLAIMS.md), également en [CSV](claims.csv) : preuve, calcul, statut et limite pour chaque conclusion.
4. [Supplément](supplement.md) : prompts système exacts, pôles de codage et accès aux tableaux numériques.
5. [Plan d'expériences priorisé](EXPERIMENT_PLAN.md) : provenance humaine, validation indépendante des réponses existantes, puis micro-campagne à définir et autoriser.
6. [Provenance](PROVENANCE.md), [contrôles effectués](QA.md), [bibliographie vérifiée](references.json) et [BibTeX](references.bib).

## Modifier et reproduire

Le texte éditable principal est `manuscript.template.md`. Les valeurs et tableaux automatiques sont matérialisés dans `manuscript.md` par le script de rendu ; modifier directement le fichier généré serait écrasé au prochain rendu. Les affirmations interprétatives et les TODO restent volontairement révisables.

Depuis la racine de ce worktree, l'environnement isolé déjà installé permet :

```bash
paper/private/venv/bin/python paper/scripts/reproduce.py
MPLCONFIGDIR=paper/private/matplotlib paper/private/venv/bin/python paper/scripts/build_manuscript.py
```

La première commande est locale et sans réseau : elle crée des backups SQLite cohérents, recalcule les métriques et les figures dans `paper/results/`, compare les rapports aux archives et contrôle les empreintes. Elle réutilise certaines fonctions statistiques du script de reproduction hérité, dont la provenance est conservée. Les migrations et écritures de kappas ne concernent que les backups temporaires. Elle peut prendre quelques minutes selon le chargement des bibliothèques et le calcul des 5 000 rééchantillonnages.

La seconde génère le Markdown, le BibTeX, le supplément et le PDF. Elle vérifie les inputs consignés par le calcul et refuse un état périmé. Après une modification significative, rendre les pages du PDF et les inspecter avant de le considérer prêt à partager. Les images PNG/SVG des figures sont dans `paper/results/figures/`.

Pour rendre les pages avec le Poppler système disponible sur ce Mac :

```bash
mkdir -p paper/qa/pages
XDG_CACHE_HOME="$PWD/paper/private/cache" /opt/homebrew/bin/pdftoppm -r 110 -png paper/output/pdf/snap_v3_1_manuscript.pdf paper/qa/pages/page
```

Pour refaire une comparaison dans un nouveau dossier de résultats, sans remplacer ceux livrés :

```bash
paper/private/venv/bin/python paper/scripts/reproduce.py --output-dir paper/results-review
```

Le constructeur du manuscrit utilise volontairement `paper/results/` comme source canonique de ce brouillon. Il ne sélectionne pas automatiquement le rapport donnant le résultat le plus favorable.

Sur une autre machine, créer un environnement Python 3.12 et installer [requirements.lock.txt](requirements.lock.txt). Il fige les versions effectivement utilisées, y compris les dépendances de rendu. L'installation télécharge des paquets publics ; l'analyse elle-même n'effectue aucune connexion et n'a besoin d'aucune clé OpenRouter. La liste est un gel de versions, pas un verrou cryptographique de wheels ni une promesse d'identité des bibliothèques système entre plateformes.

## Portée des modifications

Tous les nouveaux travaux de cette tâche sont sous `paper/`. Les différences dans `README.md`, `config/`, les archives, `src/db.py` et `tests/test_db.py`, ainsi que les scripts et agrégats sous `artifacts/reproduction/`, proviennent du travail local préexistant récupéré. Voir le [manifeste](provenance/inherited_manifest.json) et le [patch hérité](provenance/inherited_tracked.patch) avant d'attribuer un changement. Aucun commit n'a été créé.

Les répertoires `paper/private/` (copies de bases, environnement, caches, logs) et `paper/qa/` (rendus de contrôle) sont ignorés par Git et ne doivent pas être diffusés. Les scripts ne réexportent aucun extrait brut de réponse ou justification de codage dans les nouveaux livrables. Les données déjà présentes dans le dépôt restent des références locales distinctes du manuscrit. Ne pas partager le dépôt complet en assimilant ses données historiques au dossier rédactionnel.

## Révision scientifique nécessaire

Le texte contient des TODO explicites pour l'identité des auteurs et codeurs, les conditions de codage/aveuglement, la chronologie méthodologique, les déclarations éthiques et les droits de diffusion. Ces lacunes n'empêchent pas la reproduction numérique ; elles empêchent des affirmations plus fortes sur la validation humaine, le préenregistrement ou une diffusion prête à approuver. Les compléter avec des faits attestés est la prochaine étape avant circulation externe.
