# Architecture

LevelUpDiag-MediKristal is a standalone adaptation of the LevelUpDiag process-isolated diagnostics frame.

```text
CLI / ZIP launcher
      ↓
manifest + MediKristal profile config
      ↓
campaign scheduler
      ↓  fresh process per level
N* universal levels + MK* target levels
      ↓
read-only target observation / explicit validators / disposable-copy generators
```

The target is normally selected explicitly with `--target`, or extracted temporarily by `run_medikristal_zip.py`. Evidence is written under the target `.levelupdiag/` directory for an extracted repository; ZIP runs copy the finished run outside the temporary extraction.

`N05` executes only declared read-oriented validators. Target-mutating canonical generators are not run in-place: `MK60` copies the repository and regenerates contracts, validation evidence, runtime assets, SBOM and manifest in that disposable copy.

`parallel_safe: false` levels run exclusively. Synthetic blocked results are persisted to `result.json`, including fail-fast paths, so campaign summaries and `latest/` remain complete.
