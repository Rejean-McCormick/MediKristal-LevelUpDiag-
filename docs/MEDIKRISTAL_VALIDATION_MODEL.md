# Modèle de validation MediKristal

## Séparation des preuves

LevelUpDiag-MediKristal sépare cinq familles de preuve afin qu'un compteur ne masque pas une autre catégorie :

1. **Logiciel** — tests applicatifs, parsing/syntaxe, runtime HTTP et migrations.
2. **Contrats** — OpenAPI, JSON Schema, traçabilité MK/AT et parité des assets.
3. **Livraison** — manifeste SHA-256, wheel, SBOM, provenance et configuration de déploiement.
4. **Reproductibilité** — régénération dans une copie jetable et comparaison octet pour octet.
5. **Affirmations** — les nombres annoncés dans la documentation doivent correspondre à une mesure fraîche.

Un PASS d'une famille ne compense jamais un FAIL d'une autre. En particulier, une suite `pytest` verte ne prouve pas la fraîcheur d'un manifeste de livraison, et un validateur documentaire vert ne prouve pas le comportement runtime.

## Contrats attendus pour MediKristal 0.2.0

Le profil livré avec cette suite attend : 80 opérations API, 107 définitions de schéma, 12 exemples, 33 chapitres numérotés, 32 exigences `MK-001` à `MK-032`, 73 tests applicatifs collectés et une couverture globale documentée d'au moins 90 %. Ces valeurs sont des attentes de cette livraison cible; elles doivent être révisées explicitement lors d'une nouvelle version de MediKristal.

## Reproductibilité

`MK60` copie le dépôt vers un répertoire temporaire, puis exécute les générateurs canoniques dans l'ordre :

```text
build_contracts.py
validate_reference.py
sync_runtime_assets.py
build_sbom.py
build_manifest.py
compileall
```

Les fichiers régénérés sont comparés à ceux du dépôt d'origine. La cible n'est pas modifiée.

## Capacités externes

`MK30` exige que `provider_network`, `fhir_partner` et `kristal_export` ne soient pas annoncés `available` dans la distribution autonome. Un connecteur absent doit rester indisponible/non configuré plutôt que de produire un succès fictif.

## Déploiement

`MK80` valide statiquement le contrat de déploiement. Il ne démarre pas Docker. Une vraie gate de production doit ajouter un environnement PostgreSQL/Docker et des tests de concurrence multi-processus.
