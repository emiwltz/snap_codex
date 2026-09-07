# SoulBench SNAP v3.1 — revue finale indépendante du candidat nettoyé

**6 septembre 2026 — audit et revue ciblée terminés.**

**Verdict de préparation : le projet est prêt pour une présentation privée ou une revue scientifique interne, en tant que pilote rétrospectif aux résultats négatifs. Aucun défaut restant n'exige une correction du worktree dans ce périmètre. Le verdict scientifique historique reste FAIL. La diffusion publique ou la soumission demandent encore des décisions réelles sur l'attribution, la licence, le périmètre des données et les déclarations de provenance.**

Cet addendum clôt la dernière étape annoncée dans le [rapport d'audit](RAPPORT_AUDIT.md). Il vérifie les corrections et le paquet final ; il ne répète pas le bootstrap et les recalculs centraux déjà achevés, et ne transforme pas les limites du pilote en une étude nouvelle.

## 1. Candidat réellement examiné

Worktree auteur examiné en lecture seule : `/Users/emi/.codex/worktrees/1f77/snap_codex`. HEAD au contrôle : **`d9fa3defa6a1baa69d67243b4aaad73a66923e4f`**, avec les modifications locales de nettoyage. Ce commit seul ne contient donc pas tout le candidat : les empreintes du PDF et du ZIP ci-dessous identifient exactement la version relue.

| Objet | Identification vérifiée |
|---|---|
| Capture rédactionnelle | 6 septembre 2026, **02:22:37 UTC** ; 133 fichiers, [manifeste](evidence/candidate_capture_manifest.json) |
| Manuscrit Markdown | SHA-256 **`6464320b87d67722a35e5a5a90e89bfaa09158c6e45145490c7e647924009176`** |
| PDF de lecture | `paper/output/pdf/snap_v3_1_manuscript.pdf` ; **14 pages**, 512 887 octets |
| SHA-256 PDF | **`fc5d07097e2b21f68ad38fe6f7b0d259c0015b0ded925d332faba6e561380d49`** |
| Paquet définitif | `artifacts/exports/final-review/snap-presentation-review.zip` dans le worktree auteur ; **102 fichiers**, **885 418 octets** |
| SHA-256 ZIP | **`20d35b85fa0aac1a1576ed0f0af3a75be8b3b4238b87f485119a4c0b27e1f179`** |
| État déclaré du ZIP | `local_review_only_release_pending` |

Le candidat de 100 fichiers généré initialement par l'audit a été dépassé par le ZIP définitif. La comparaison réelle trouve deux ajouts (`.gitattributes`, `docs/reference-integrity.json`) et cinq fichiers sources ajustés : documentation de nettoyage, guide des données, provenance, liste d'export et acceptation de `.gitattributes` dans l'exporteur. Le manifeste d'export change en conséquence. **Le PDF, le manuscrit, le code d'analyse, la reproduction et les tests sont identiques entre ces deux paquets.** Les changements finaux ont été lus et leurs tests ciblés exécutés dans l'extraction du ZIP définitif.

Les [contrôles finaux](evidence/final_candidate_checks.json) enregistrent cette comparaison, les hashes, les résultats des tests et le comportement de l'export sans données. Le [manifeste du ZIP](evidence/final_export_manifest.json) inventorie chaque fichier livré. L'audit a vérifié son égalité à la copie externe du manifeste et l'égalité de tous les fichiers sources exportés au worktree auteur courant.

## 2. Clôture des constats initiaux

Les sévérités indiquent l'enjeu initial ; le statut indique ce qui reste après nettoyage.

| Constat | État final vérifié | Preuve dans le candidat |
|---|---|---|
| **F01 — P1 : absence de répétitions affirmée trop largement** | **Corrigé.** Exception opportuniste GPT, 180 paires, mêmes messages reconstructibles, limites backend et deux paires aux tokens différents explicites. Aucun nouveau PASS. | `paper/manuscript.md:57`, §4.6, §6 ; PDF p. 4, 11, 12 ; C04/C32 ; synthèse et supplément |
| **F02 — P1 : disparition de cinq ICC avec Pingouin 0.6.1** | **Corrigé dans le parcours livré.** Renvoi unique au gel vérifié 0.5.5. La compatibilité 0.6+ n'est pas revendiquée. | `requirements.txt:3`, `paper/requirements.lock.txt:31`, README et guide de reproduction |
| **F03 — P2 : saturation E1 et hétérogénéité masquées par κ global** | **Correction éditoriale et diagnostic intégrés.** Quinze lignes concordantes ; cinq kappas finis <0,60 ; E1 constant et κ indéfini annoncés sans nouveau seuil ni recodage. | `paper/manuscript.md:138`, PDF p. 7–8 ; `paper/review/item_agreement.csv`, supplément, C31 |
| **F04 — P1 pour une revendication de validation humaine** | **Prétention correctement limitée ; provenance toujours à attester.** Les fichiers ne prouvent pas identité, indépendance, aveuglement ni validation représentative. Aucune identité inventée. | `paper/manuscript.md:99`, p. 6, 12–14 ; 200 labels historiques et absence de Claude explicites |
| **F05 — P2 : split-half confondu avec répétition temporelle** | **Corrigé.** Les positions 1–5/6–10 du calendrier sont explicites ; ordre mélangé et différence avec ICC de mesure unique expliqués. | Abstract, `paper/manuscript.md:57`, §3.6 ; PDF p. 1, 4, 6, 9 |
| **F06 — P2 : portée causale, seuils et LMM** | **Borné explicitement.** Modèle mixte par groupes d'items, températures GPT nominales, eta-carrés séparés et chronologie locale non équivalente à un préenregistrement exposés. | `paper/manuscript.md:200`, §3.5, §3.6, §4.5 ; PDF p. 6–7, 11 |
| **F07 — P1 pour une diffusion : dépôt brut pris pour le paquet de présentation** | **Corrigé pour le paquet examiné.** ZIP explicite, sans bases, CSV codé, diagnostic brut, histoire Git ou provenance personnelle. Accès distinct aux données requis et annoncé. | ZIP final, `EXPORT_NOTICE.md`, `docs/DATA.md`, guide de reproduction ; contrôle indépendant §4 ci-dessous |
| **F08 — P3 : dates de métadonnées utilisées comme premières observations** | **Corrigé.** Dates des réponses utilisées ; reprise Mistral explicitée. Les révisions backend manquantes restent déclarées. | `paper/manuscript.md:45`, C02 ; PDF p. 3 et 5 |

Le registre comprend **32 claims**. Les deux ajouts diagnostics sont exploratoires. Les limites restantes de validité de construit, effectif d'items, plan déterministe incomplet, catégories de score, troncatures et provenance des labels ne disparaissent pas parce que le paquet passe ses contrôles techniques.

## 3. Vérifications scientifiques et opérationnelles

La reproduction indépendante initiale conserve toute sa portée : **2 700 réponses**, **2 695 paires de juges**, κ **0,7509073105151067**, ICC minimum calculable **0,548627174897**, cross-SP minimum **0,318909766466**. La reproduction du pipeline sur copie, avec 5 000 rééchantillonnages, donne **18 contrôles vrais** et **zéro écart dans les quatre comparaisons historiques à tolérance 10⁻⁸**, avec **FAIL**. Les 41 tests initiaux avaient passé. Les preuves et limites de cet environnement sont dans le rapport principal.

La revue finale ajoute les contrôles réellement suivants :

- **Diagnostics intégrés :** égalité des 180 clés de paires, scores, indicateurs et écarts de dates avec l'audit indépendant ; égalité exacte des mesures agrégées (142/180, κ 0,646017699115, r 0,744037789021). Les quinze résumés d'items concordent, y compris la valeur indéfinie de E1. Les hashes de signatures de requête ne sont pas comparables entre scripts car l'un sérialise l'alias interne et l'autre l'endpoint configuré ; les paramètres, identités de paires et valeurs comparés sont consignés.
- **Provenance des nouveaux rapports :** zéro écart entre les hashes d'entrées de `paper/review/audit_diagnostics.json` / `reproduction_audit.json` et les sources capturées. Les rapports de `paper/results/` sont conservés comme preuves du premier manuscrit ; les métadonnées du PDF courant sont dans `paper/review/`.
- **Références :** les **31 hashes** du registre final de données et sorties historiques sont identiques dans le worktree auteur et le dépôt original. Les fichiers méthode/code capturés n'ont pas changé ; les sauvegardes SQLite privées peuvent avoir des hashes binaires différents de leurs sources, comme documenté dans l'audit initial.
- **Tests de chemins/export :** six tests passent sur la copie rédactionnelle puis **six tests passent dans l'extraction du ZIP définitif**, en 0,02 s pour cette dernière exécution. Ils couvrent les destinations protégées/existantes et les liens symboliques ainsi que la sélection/inspection de l'export.
- **Destinataire sans données :** `python scripts/reproduce.py --output-dir artifacts/runs/missing-input-test` s'arrête avec **code 2**, nomme les deux bases, le CSV codé et `cross_sp_diagnostic.json`, puis renvoie vers le guide des données. Aucun dossier de sortie d'analyse ni `paper/private` n'est créé. Le cache de polices de la session est un intermédiaire distinct.

Le nettoyeur a également consigné une installation neuve depuis son cache de 50 paquets publics, 47 tests complets depuis un paquet extrait et une reproduction du script final. Ce sont **ses exécutions**, décrites dans `docs/CLEANUP.md`, et non des installations complètes répétées par l'auditeur. La présente revue vérifie indépendamment les changements, leurs tests ciblés, les données, les sorties et la provenance pertinente ; elle ne prétend pas avoir installé ce projet sur une autre plateforme.

Le [script de vérification finale](audit_final_candidate.py) utilise le runtime privé déjà vérifié. Commande réellement exécutée depuis ce worktree d'audit :

```bash
PYTHONDONTWRITEBYTECODE=1 work/source_snapshot/paper/private/venv/bin/python docs/audit/audit_final_candidate.py
```

Il crée sa copie du ZIP et une extraction neuve dans `work/`, ouvre les bases de copie en URI `mode=ro` avec `query_only`, et n'importe pas le calcul SNAP pour les comparaisons. L'extraction possède un nom fixe et refuse de réutiliser un dossier existant ; choisir un nouveau nom dans une copie du script pour une nouvelle revue. Les logs et JSON présents sont les résultats de cette exécution, et non des sorties d'exemple.

## 4. Contrôle du paquet remis à un destinataire

**Intégrité.** CRC ZIP valide ; 102 chemins uniques et sûrs ; zéro lien symbolique ; zéro écart de hash dans les 101 fichiers hachés. Le fichier `EXPORT_MANIFEST.json` ne se hache pas lui-même, ce qui est attendu. La copie externe du manifeste et sa copie interne sont identiques. Tous les fichiers sources du ZIP correspondent au worktree auteur.

**Contenu.** Absence des deux bases, du CSV codé, du diagnostic à extraits bruts, de `data/`, des archives méthodologiques non revues, des records privés d'import, des environnements et de l'histoire Git. Les configurations, prompts et rubriques sont inclus volontairement pour décrire la méthode. Zéro correspondance de motif de credential connu et zéro chemin personnel absolu détecté dans le texte accessible, y compris le PDF. Les liens Markdown locaux pointent tous vers des fichiers présents ; ce contrôle de fichiers ne revendique pas la vérification exhaustive de chaque ancre de section ou URL externe.

**Revue textuelle supplémentaire.** L'audit a comparé **24 204 fragments distincts** de 160 caractères (débuts, milieux et fins de réponses/justifications de juges), ainsi que **30 justifications manuelles distinctes** d'au moins 80 caractères. Quatre fichiers ont déclenché ce contrôle élargi : les YAML d'items, les rubriques et le supplément. La vérification de ces correspondances montre qu'elles reprennent toutes du **texte méthodologique déjà présent dans la configuration inchangée**, également stocké dans des justifications historiques. Elles ne révèlent pas de réponse brute additionnelle dans l'export. Le [résultat classifié](evidence/final_text_match_classification.json) conserve les dénominateurs sans reproduire ces textes.

Cette correspondance entre certaines justifications et la rubrique ne permet pas d'établir qui a codé, avec quel outil ou quel degré d'indépendance. La réserve F04 demeure. Les scans exacts ne sont ni une détection sémantique exhaustive ni un avis sur les droits de diffusion.

**PDF.** Les **14 pages** ont été inspectées après rendu Poppler à **110 dpi**, et le hash est celui du PDF inclus dans le ZIP final. Les cinq tableaux, trois figures, huit références et pieds de page sont lisibles ; aucun chevauchement, texte coupé ou glyphe manquant n'a été observé. Les trois PNG du paquet sont les trois figures numériques vues dans le PDF. Les pages 1 et 14 affichent les déclarations encore à compléter, sans faux auteur ni affiliation.

## 5. Ce qui est terminé et ce qui relève encore du propriétaire

**Terminé :** audit des données et des calculs, contrôle des choix et limites, correction des erreurs concrètes, parcours de reproduction protégé, revue du texte et du rendu, export privé vérifié. Ces éléments suffisent pour présenter le projet comme **un pilote documenté qui n'a pas satisfait ses propres critères de stabilité**. Un résultat négatif n'exige pas une nouvelle campagne pour être présenté honnêtement.

**Avant une diffusion publique ou une soumission :** décider du nom d'auteur, de l'affiliation, de la licence et de l'accès/diffusion des matériaux ; établir les faits disponibles concernant le codage/adjudication et les déclarations associées ; choisir le lieu et la version publiée. Si la provenance humaine ne peut pas être attestée, conserver des labels historiques d'origine non vérifiée et renoncer à en tirer une validation humaine. Ces décisions ne peuvent pas être remplacées par une hypothèse de l'agent. La version publique devra être figée avec ses métadonnées réelles et une autorisation de diffusion ; aucune publication n'a été effectuée ici.

L'audit ne conclut pas à un instrument validé de personnalité, un classement stable des six modèles, une absence générale d'effets ou une validation de sûreté. Une revue des items et un suivi expérimental planifié restent des suites facultatives si ces objectifs plus forts sont retenus.

## 6. Livraison de l'audit

Le [rapport principal](RAPPORT_AUDIT.md), cet addendum, le journal [FINDINGS_EN_COURS.md](FINDINGS_EN_COURS.md), les quatre scripts `audit_*.py` et les fichiers d'`evidence/` constituent la livraison d'audit local à conserver ou recopier dans les outputs de coordination. Ils contiennent des identifiants de provenance locale ; ils ne sont pas eux-mêmes un paquet public déjà approuvé.

**Ne pas recopier `work/` pour diffusion** : il contient les snapshots bruts, environnements, rendus intermédiaires et copies temporaires. Le seul paquet de présentation final visé par le présent avis est le ZIP identifié au §1. Aucun dépôt auteur ou original n'a été modifié par l'audit ; aucun appel payant, push, publication ou nouveau codage humain n'a été lancé.
