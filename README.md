# LevelUpDiag-MediKristal

**Version :** 1.1.0  
**Cible :** MediKristal 0.2.0  
**Mode :** suite de diagnostic autonome, lecture seule par défaut  
**Dépendances propres :** Python 3.10+ standard library uniquement

LevelUpDiag-MediKristal adapte le cadre LevelUpDiag au dépôt MediKristal. Son but n'est pas de remplacer `pytest` ou les validateurs du projet : il orchestre les validateurs canoniques et ajoute des contrôles indépendants de contrat, runtime, migration, packaging, provenance, reproductibilité et cohérence des preuves de livraison.

La suite ne prétend **pas** valider cliniquement MediKristal. Les données et parcours exercés sont ceux de l'implémentation d'ingénierie/synthétique.

## Interface graphique Windows (`.pyw`)

Double-cliquer sur `LevelUpDiag-MediKristal.pyw`, ou lancer `RUN_LEVELUPDIAG_UI.bat`. L'interface permet de :

- choisir un dépôt MediKristal extrait ou une archive ZIP ;
- choisir `baseline`, `software`, `delivery`, `release` ou `deep` ;
- régler le parallélisme (`jobs`) et `fail-fast` ;
- suivre chaque niveau en temps réel ;
- consulter les verdicts et les findings ;
- ouvrir le dossier de preuves et `summary.json` ;
- copier un résumé texte dans le presse-papiers.

L'UI utilise uniquement Tkinter/stdlib. Pour un ZIP, l'extraction est temporaire et protégée contre les chemins de type `../`; les preuves sont copiées sous `levelupdiag_zip_runs/` par défaut.

## Utilisation rapide

Sur un dépôt extrait :

```bash
python levelupdiag.py --target /chemin/vers/MediKristal doctor
python levelupdiag.py --target /chemin/vers/MediKristal run baseline
python levelupdiag.py --target /chemin/vers/MediKristal run software
python levelupdiag.py --target /chemin/vers/MediKristal run delivery
python levelupdiag.py --target /chemin/vers/MediKristal run release
```

Sur un ZIP de livraison, sans modifier l'archive :

```bash
python run_medikristal_zip.py /chemin/MediKristal_final_complete.zip release
```

Les rapports sont structurés en JSON sous `.levelupdiag/runs/<run-id>/` pour un dépôt extrait, ou sous `levelupdiag_zip_runs/` avec le lanceur ZIP.

## Campagnes

| Campagne | Portée |
|---|---|
| `baseline` | intégrité du diagnostic, contexte, inventaire, hygiène, identité MediKristal, contrats/traçabilité |
| `software` | baseline + 73 tests applicatifs déclarés, syntaxe JS, smoke FastAPI, migrations |
| `delivery` | software + hashes du manifeste, wheel, SBOM, provenance, Compose/Dockerfile |
| `release` | delivery + régénération complète dans une copie jetable, cohérence des chiffres documentés, re-mesure de couverture |
| `deep` | alias de `release` |

## Niveaux spécifiques MediKristal

- **MK10 — Identity and Layout** : identité du package, fichiers attendus, 33 chapitres, dépendances pinées, parsing Python.
- **MK20 — Contract and Traceability Integrity** : OpenAPI, 107 schémas, 80 opérations, 32 exigences MK, AT-001..AT-032, parité des assets runtime.
- **MK30 — Runtime API Smoke** : application FastAPI sur SQLite jetable, `/healthz`, `/readyz`, OpenAPI servi, UI, Problem JSON, headers de sécurité et états honnêtes des capacités externes.
- **MK40 — Migration Cycle** : `upgrade head -> downgrade base -> upgrade head` sur SQLite jetable et présence des tables d'intégrité.
- **MK50 — Packaging and Provenance** : `manifest.json`, SHA-256 du wheel, metadata/assets du wheel, SBOM ↔ lockfile, attestation des snapshots source.
- **MK60 — Generated Artifact Reproducibility** : copie temporaire du dépôt, régénération des contrats/validation/assets/SBOM/manifeste et détection de dérive.
- **MK70 — Delivery Claims Consistency** : collecte fraîche des tests, cohérence des compteurs documentaires et re-mesure Coverage.py.
- **MK80 — Deployment Configuration** : topologie Compose, secrets externalisés, mode production, utilisateur non-root; aucun démarrage Docker implicite.

## Principes de verdict

`PASS`, `WARN`, `FAIL`, `SKIP`, `BLOCKED`, `PARTIAL`, `ERROR`, `INFRA_ERROR`, `CONFIG_ERROR` conservent leur sens LevelUpDiag. Un niveau requis bloqué ou incomplet n'est jamais converti en succès. Un `WARN` est accepté mais visible; un `FAIL` fait échouer la campagne.

Quelques avertissements sont volontairement distincts d'un échec logiciel : par exemple, les hashes de snapshots sources ne peuvent pas être revalidés si les archives originales ne sont pas présentes, et la configuration Docker peut être contrôlée statiquement sans prétendre avoir démarré PostgreSQL.

## Sécurité d'exécution

- réseau désactivé par défaut ;
- aucune installation de dépendances ;
- aucune mutation volontaire du dépôt cible ;
- tests Python lancés avec `PYTHONDONTWRITEBYTECODE=1` et cache pytest désactivé ;
- migrations et runtime utilisent des bases SQLite jetables ;
- les générateurs qui modifient des fichiers sont lancés dans une **copie temporaire** du dépôt ;
- sortie bornée et redaction LevelUpDiag ;
- extraction ZIP protégée contre les chemins `../`.

## Limites

Cette suite ne remplace pas une qualification PostgreSQL multi-processus, un test Docker/Compose réel, un audit de sécurité complet, une qualification Kristal/FHIR partenaire, des essais de charge, ni une validation clinique/réglementaire. Ces preuves nécessitent les environnements et profils externes correspondants.
