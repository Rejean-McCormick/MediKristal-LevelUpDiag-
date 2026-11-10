# Final-system evidence boundary for MediKristal software diagnostics

**Status:** `TARGET_DESIGN` + independently executable **synthetic software checks**. **Owner:** LevelUpDiag-MediKristal. **Target version:** MediKristal `0.2.0`. **Functional chains:** FC-18 (diagnostics), FC-20 (medical domain), and FC-14 (effect-point security).

## Intent and non-authority

This tool evaluates the engineering behavior and delivery package of an exact MediKristal source checkout or ZIP; it does not own patient data, medical reasoning, production policies, regulatory decisions, deployment permissions or clinical validation. The target remains a separate application and its author remains responsible for its software contracts and authorized use.

A result of `PASS` means only that **the specifically named check** ran successfully against a pinned input. `WARN`, `BLOCKED`, `SKIP`, `ERROR` and `INFRA_ERROR` must remain distinguishable; a healthy source manifest or API smoke test never grants clinical readiness.

## Enhanced two-sided checks

| Evidence boundary | MediKristal owner artifact | Independent diagnostic condition |
|---|---|---|
| Runtime dependencies | `backend/requirements.lock`, `sbom.cdx.json` | All direct pins, optional extras **and exact SHA-256 of lock bytes** match the declared SBOM. |
| Source delivery | `manifest.json` and on-disk source files | **Full enumerated source set** matches manifest, not just hashes for entries retained in an incomplete list. Unsafe, duplicate and missing paths are rejected. |
| Isolated runtime | `/api/v1/capabilities` and core health/contract endpoints | All returned capability `supported_uses` are exactly `['engineering']`; limitations are explicit; externally unconfigured adapters are not `available`. |
| Synthetic tests | MediKristal's isolated application suite | Exact commands, actual results and environment stored in report; no extrapolation to real partners. |
| Deployment | Owner's Docker/DB plan | Static check can show configuration coherence, **not** a working production deployment. |

`levels/mk50_packaging.py` checks source completeness and pinned SBOM; `levels/mk30_runtime_smoke.py` checks runtime capability and external-adapter honesty with evidence emitted by `probes/runtime_smoke.py`. `tests/test_cross_owner_integrity.py` exercises positive and tampered synthetic cases without needing the product's application dependencies.

## Source archive qualification

The supplied MediKristal snapshot lacked `backend/requirements.lock`. The MediKristal branch reconstruction matched the original owner's 142-byte manifest entry and SBOM SHA-256 exactly. Independent validations must run against the **patched branch archive**, not against a partially supplied dump, before claiming the lock and source manifest agree.

The original LevelUpDiag snapshot's `suite-manifest.json` was also stale against several source files. Regenerate it with `python tools/refresh_suite_manifest.py` after editing and run `python tools/refresh_suite_manifest.py --check`; preserve the generated SHA-256 entries in the delivered archive.

## Remaining gates

1. Execute `baseline`, `software`, `delivery` and `release` campaigns with declared dependencies and a pinned target. A missing `pytest-cov` or PostgreSQL/psycopg is an infrastructure limitation, **not a reason to report PASS**.
2. Run multi-process PostgreSQL, real Docker and actual partner contracts in their authorized environments before claiming anything about production behavior.
3. Obtain separate clinical-domain governance for intended patient use, clinical evidence, privacy and any regulatory approvals. **No software-only diagnostic can issue these approvals.**
4. Where an external MediKristal↔Kristal/FHIR/Koali integration is not adopted by both owners, leave it `TBD` and report `capability_unavailable` or `not_configured` instead of inventing endpoints.

## Current branch 09 software evidence (2026-11-09)

MediKristal: **73/73 synthetic application tests PASS**, fresh **87.24% global / 86.25% API** coverage, **208/208 documentary checks PASS**, exact dependency lock restored, and the source delivery manifest/SBOM integrity check passes after owner regeneration. The **90% release coverage criterion remains unmet**. A selected or baseline diagnostic pass is not a release qualification.

For reproducibility, the MediKristal suite disables ambient pytest plugin autoload when it invokes the target. It explicitly loads `pytest_cov` only for a coverage campaign; absence of pytest-cov blocks that measurement rather than fabricating a percentage.
