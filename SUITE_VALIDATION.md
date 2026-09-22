# Validation de LevelUpDiag-MediKristal

Date : 2026-09-22

## Auto-tests de la suite

Commande :

```bash
python -m unittest discover -s tests -v
```

Résultat : **11/11 tests PASS**.

La couverture de ces auto-tests vise le moteur de verdict, la résolution du manifeste, l'exécution de commandes sans shell, le profil MediKristal, la persistance des résultats synthétiques `fail-fast` et la sécurité du lanceur ZIP.

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
