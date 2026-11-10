# Validation de LevelUpDiag-MediKristal

## Current branch 09 evidence — 2026-11-09

- **22/22 diagnostic self-tests PASS**, including seven independent negative-case tests for manifest omission/path traversal, exact lock/SBOM/extras and prohibited clinical-capability claims.
- MediKristal owner source: **73/73 synthetic API tests PASS**, current documentary validation **208 PASS / 0 FAIL**, and code coverage **87.24% global / 86.25% API** in the local Python 3.13.5 test environment.
- The reconstructed 142-byte `backend/requirements.lock` matches the *original* MediKristal manifest SHA-256. The owner source manifest and CycloneDX SBOM currently agree.
- Diagnostic `baseline`: `WARN` overall (7 `PASS` plus one expected context `WARN` because extracted ZIP has no Git metadata). `MK30`: `PASS` (isolated runtime smoke and engineering-only capability guard). `MK50`: **FAIL** for missing release wheel and `dist/SHA256SUMS`; its source-manifest and SBOM/lock subchecks **PASS**.
- The **90% minimum release coverage gate is NOT MET**. No release, patient-care or regulatory qualification is asserted. The current source snapshot also lacks the binary wheel, real Docker/PostgreSQL environment and partner validation.

The September 2026 sample reports below describe an earlier source snapshot and must not be substituted for this branch's current qualification status.

Date : 2026-09-22

## Auto-tests de la suite

Commande :

```bash
python -m unittest discover -s tests -v
```

Résultat : **15/15 tests PASS**.

La couverture de ces auto-tests vise le moteur de verdict, la résolution du manifeste, l'exécution de commandes sans shell, le profil MediKristal, la persistance des résultats synthétiques `fail-fast` et la sécurité du lanceur ZIP, ainsi que les helpers de l'interface graphique `.pyw`.

## Validation fonctionnelle contre MediKristal

La campagne `software` a été exécutée sur une extraction fraîche de `MediKristal_final_complete.zip` :

- N00 PASS
- N01 WARN : absence de dépôt Git dans le snapshot extrait
- N02 PASS
- N03 PASS
- N04 PASS
- N05 PASS : tests applicatifs + syntaxe JavaScript
- N06 PASS
- MK10 PASS
- MK20 PASS
- MK30 PASS
- MK40 PASS

Les niveaux release ont ensuite été exécutés individuellement pour conserver toute la preuve même après un FAIL :

- MK50 WARN : packaging/wheel/SBOM conformes ; archives sources originales non présentes pour revalider leurs hashes
- MK60 FAIL : `validation-report.json`, `VALIDATION.md` et `manifest.json` ne sont pas reproductibles à l'identique ; validation documentaire fraîche = 208 PASS au lieu de 211
- MK70 FAIL : 73 tests collectés, mais couverture fraîche 87,24 % (API 86,25 %) contre 91 % global documenté ; compte documentaire frais 208 contre 211 documenté
- MK80 WARN : configuration de déploiement statiquement conforme, Docker/PostgreSQL non démarrés

Le chemin `release --fail-fast` a aussi été exercé après correction du runner : verdict **FAIL**, code de sortie **10**, et un `result.json` est présent pour chaque niveau, y compris ceux bloqués par fail-fast.

Voir `SAMPLE_VALIDATION_MEDIKRISTAL_FINAL.md` et `sample-results/` pour les preuves d'exemple.

## Validation de l'interface graphique

- `levelupdiag_ui.py` et `LevelUpDiag-MediKristal.pyw` passent `py_compile`.
- Le runner a été exercé avec le callback UI sur une vraie campagne `baseline` : 8 événements `level_started`, 8 `level_finished`, puis `campaign_finished`.
- Le démarrage visuel n'est pas automatisé dans cet environnement sans bureau graphique ; le code cible Tkinter 8.6 / Python 3.10+.
