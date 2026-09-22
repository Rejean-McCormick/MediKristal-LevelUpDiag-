# Security and non-mutation model

LevelUpDiag is diagnostic tooling, not a sandbox.

This MediKristal-specific suite reduces risk by:

- not auto-executing discovered project commands;
- using `shell=False`;
- bounding external commands with timeouts;
- blocking declarations marked mutating or networked unless explicitly enabled;
- excluding diagnostic source/evidence from target scans;
- redacting common credential assignments in command output;
- never recording the matched secret value in security-hygiene findings;
- checking target-relative working directories;
- sampling tracked Git state before/after a campaign.

The generic security level is a **hygiene heuristic**, not proof that the repository is secure. Findings are warnings because generic pattern matching can produce false positives.
