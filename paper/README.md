# Manuscrit scientifique SNAP

Le dossier contient un **préprint de travail en anglais avec synthèse française**.
Il présente la campagne v3.1 existante et son **FAIL**, sans inférence de
personnalité intrinsèque. Le nom d'auteur, l'affiliation, la licence et la cible
éditoriale restent à décider.

## Lire et réviser

1. [Synthèse française](SYNTHESE_FR.md) : résultats, portée et limites.
2. [Manuscrit anglais](manuscript.md) et [PDF de lecture](output/pdf/snap_v3_1_manuscript.pdf).
3. [Matrice des affirmations](CLAIMS.md), aussi en [CSV](claims.csv) : calculs,
   preuves et limites de chaque conclusion.
4. [Supplément](supplement.md) : prompts, pôles de codage et tableaux numériques.
5. [Plan d'expériences complémentaires](EXPERIMENT_PLAN.md) : priorités,
   propositions et décisions à prendre avant une nouvelle campagne.
6. [Provenance](PROVENANCE.md), [QA du premier brouillon](QA.md),
   [registre bibliographique](references.json) et [BibTeX](references.bib).

Le texte éditable est `manuscript.template.md`. Les tableaux automatiques et la
bibliographie sont matérialisés dans `manuscript.md`. La correction éditoriale
apportée lors de la revue reconnaît les répétitions opportunistes de GPT-5.2 ;
elle ne transforme pas le calendrier complet en test-retest contrôlé et ne
modifie pas les seuils ou les scores historiques.

## Reproduire et construire une copie de revue

Installer l'environnement Python 3.12 selon le [README du projet](../README.md),
puis, depuis la racine :

```bash
.venv/bin/python scripts/reproduce.py --output-dir artifacts/runs/review-01
.venv/bin/python paper/scripts/build_manuscript.py --results-dir artifacts/runs/review-01 --output-dir paper/build/review-01
```

Les destinations doivent être nouvelles. Les calculs utilisent des backups
SQLite cohérents, sans réseau ni scoring fournisseur ; le constructeur vérifie
les empreintes des sources de ce calcul. Le nouveau PDF et les fichiers associés
sont sous `paper/build/review-01/`. Les preuves conservées dans `paper/results/`
ne sont pas écrasées par ces commandes.

Le [guide de reproduction](../docs/REPRODUCING.md) décrit les contrôles attendus,
les entrées manquantes dans l'export de présentation et le rendu Poppler pour
l'inspection visuelle. Les hashes de l'audit historique se rapportent à la version
de code de ce calcul ; les nouvelles exécutions portent leurs propres audits.

## Revue et diffusion

Le [nettoyage et ses contrôles](../docs/CLEANUP.md) distinguent le premier manuscrit
conservé au commit `d9fa3de` des corrections et outils de préparation ultérieurs.
Le [guide des données](../docs/DATA.md) précise la provenance et la couverture
incomplète des labels historiques. Le [guide de préparation](../docs/RELEASING.md)
donne la commande d'export et les décisions de diffusion restantes.

Les bases, extraits bruts, dossiers `private/`, rendus `qa/` et traces d'import
locales ne font pas partie de l'export de présentation. Aucun codage d'agent n'est
présenté comme humain. L'identité des codeurs, l'indépendance et l'aveuglement,
la chronologie et les déclarations éthiques restent des faits à attester.
