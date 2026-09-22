# Evolution guide — LevelUpDiag-MediKristal

This repository is no longer the neutral frame: it is the MediKristal-specific adaptation.

When MediKristal changes version, re-inventory the target before updating expectations. Prefer canonical target validators over duplicated logic, keep generated-file checks non-mutating by running generators in a disposable copy, and update `levelupdiag_manifest.json`, `levelupdiag.config.json`, the specific `MK*` levels and `docs/MEDIKRISTAL_VALIDATION_MODEL.md` together.

Do not change expected counts merely to make a release pass. A change from 80 API operations, 107 schemas, 32 requirements, 73 tests or any other pinned profile value must be justified by a corresponding MediKristal contract/version change.

External integrations, Docker/PostgreSQL qualification, load testing, partner conformance and clinical/regulatory validation remain separate evidence domains and must never be inferred from local synthetic PASS results.
