# LevelUpDiag for MediKristal

**Version:** `1.1.2` | **Target:** MediKristal `0.2.0` | **Runtime dependency:** Python `3.10+` standard library | **Default mode:** read-only diagnostics.

This standalone diagnostic suite orchestrates MediKristal's own validators and provides additional independent checks for contracts, runtime behavior, migrations, packaging, provenance, reproducibility and delivery claims. It does **not** certify clinical validity or regulatory readiness; the exercised medical data and pathways are synthetic engineering fixtures.

## Windows application and target selection

Double-click `LevelUpDiag-MediKristal.pyw` or open `RUN_LEVELUPDIAG_UI.bat`. The GUI accepts an extracted checkout or a ZIP archive and offers `baseline`, `software`, `delivery`, `release` and `deep` campaigns, progress, findings and evidence browsing. The default GUI target is `C:\mycode\MediKristal\MediKristal` but can be changed.

The Tkinter interface uses Python's standard library. ZIP extraction is temporary and validates traversal paths; evidence is copied to `levelupdiag_zip_runs/`.

## Command-line usage

```bash
python levelupdiag.py --target /path/to/MediKristal doctor
python levelupdiag.py --target /path/to/MediKristal run baseline
python levelupdiag.py --target /path/to/MediKristal run software
python levelupdiag.py --target /path/to/MediKristal run delivery
python levelupdiag.py --target /path/to/MediKristal run release
python run_medikristal_zip.py /path/to/MediKristal.zip release
```

Reports are stored in `.levelupdiag/runs/<run-id>/` for checkouts or under `levelupdiag_zip_runs/` for ZIP runs.

## Campaign boundaries

| Campaign | Additional checks |
| --- | --- |
| `baseline` | Diagnostic integrity, repo/contract identity and hygiene |
| `software` | Application tests, JavaScript syntax, FastAPI smoke, migrations |
| `delivery` | Manifest, wheel, SBOM, provenance and deployment structure |
| `release` | Regeneration in an isolated copy and current delivery-claims coherence |
| `deep` | Alias for `release` |

Dedicated MediKristal levels cover: identity/layout (MK10), contracts/traceability (MK20), API smoke (MK30), migration cycles (MK40), packaging/provenance (MK50), regeneration (MK60), delivery claims (MK70) and static deployment configuration (MK80).

## Verdict and safety

`PASS`, `WARN`, `FAIL`, `SKIP`, `BLOCKED`, `PARTIAL`, `ERROR`, `INFRA_ERROR` and `CONFIG_ERROR` retain their distinct meanings. Missing required evidence must never be promoted to success.

No network calls or dependency installation occur by default, and the target checkout is not intentionally modified. Python runs disable bytecode/cache writes, migrations use disposable SQLite files, and generators execute on temporary copies. Docker is not implicitly launched by a static deployment check.

**Out of scope:** live multi-process PostgreSQL qualification, a real Docker deployment, exhaustive security testing, partner FHIR/Kristal qualification, load testing, clinical validation and medical regulatory approval.
