# Exemple de validation — MediKristal_final_complete.zip

Date d'exécution : 2026-09-22  
SHA-256 de l'archive testée : `648a05e57328233028e4c0afe466478f060c58ea49ed16a67eeaf990c0c320a4`

Ce rapport est un **exemple réel d'utilisation** de LevelUpDiag-MediKristal sur l'archive MediKristal disponible pendant la construction de la suite. Il ne remplace pas une exécution sur une archive ultérieure.

## Résultat logiciel

La campagne `software` s'exécute avec succès sur les contrôles logiciels requis :

- suite applicative : **73 tests collectés et passants** ;
- contrats : **80 opérations**, **107 définitions de schéma**, **32 exigences MK**, **12 exemples**, **33 chapitres** ;
- smoke FastAPI isolé : PASS ;
- parité `/openapi.json` : PASS ;
- états des capacités externes : PASS (aucun succès fictif) ;
- cycle Alembic `upgrade -> downgrade base -> upgrade` : PASS ;
- syntaxe JavaScript : PASS.

La campagne peut conserver un WARN de contexte si le snapshot n'est pas un dépôt Git, ce qui limite la preuve VCS sans constituer un échec du logiciel.

## Résultat livraison

Les contrôles de packaging ont confirmé :

- `manifest.json` valide contre les bytes livrés : PASS ;
- SHA-256 du wheel : PASS ;
- metadata et assets embarqués du wheel : PASS ;
- SBOM CycloneDX ↔ `requirements.lock` : PASS ;
- configuration Compose : services `db/migrate/api/worker`, secrets externalisés, mode production, utilisateur non-root : PASS.

La provenance des cinq snapshots sources reste **WARN** : les descripteurs sont bien formés mais les archives originales correspondantes ne sont pas incluses dans la livraison à revalider.

## Écarts détectés par la gate release

### 1. Preuves documentaires périmées — FAIL

Une régénération dans une copie jetable produit **208 PASS / 0 FAIL**, alors que les fichiers livrés annoncent **211 PASS / 0 FAIL**. Les fichiers qui divergent après régénération sont :

- `validation-report.json` ;
- `VALIDATION.md` ;
- `manifest.json` (par conséquence des changements de preuves).

LevelUpDiag-MediKristal ne modifie pas l'archive pour corriger ce point ; il le signale comme dérive de preuve.

### 2. Couverture documentée non reproductible — FAIL

Re-mesure avec le même type de surface `pytest --cov=medikristal` :

- couverture globale fraîche : **87,24 %** (arrondi 87 %) ;
- couverture de `medikristal/api.py` : **86,25 %** (arrondi 86 %) ;
- documentation livrée : **91 % global / 86 % API**.

La cible du profil LevelUpDiag-MediKristal est de 90 % global minimum ; la mesure fraîche ne l'atteint pas et ne correspond pas au chiffre de 91 % annoncé.

## Verdict

La couche logicielle principale est verte, mais la **gate release est FAIL** tant que les preuves générées et les affirmations de couverture ne sont pas remises en cohérence avec une exécution fraîche.

Ce verdict ne constitue aucune validation clinique, réglementaire, PostgreSQL multi-processus, Docker réel ou partenaire Kristal/FHIR.
