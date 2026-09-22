# Configuration reference

`levelupdiag.config.json` is the committed MediKristal profile. `levelupdiag.config.local.json` may override it recursively.

Core execution keys keep their LevelUpDiag meaning: parallelism, timeouts, output limits, target mutation/network policy, scanning bounds, validators, security patterns and redaction.

Validator declarations may additionally contain an `env` object. Environment entries are merged into the child process environment; this profile uses it to set `PYTHONDONTWRITEBYTECODE=1` for pytest.

The `medikristal` object pins the target profile:

- `expected_project_name` / `expected_version`;
- expected operation/schema/example/chapter/requirement/test counts;
- minimum re-measured global coverage;
- allowed states for external capabilities that must not fabricate availability.

These values are release-profile expectations, not universal LevelUpDiag constants. Update them only with an intentional MediKristal contract/version change.
