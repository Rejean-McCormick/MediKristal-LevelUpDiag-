# Result and campaign model

Each level writes:

```text
.levelupdiag/runs/<run-id>/levels/<level-id>/result.json
```

A campaign writes:

```text
.levelupdiag/runs/<run-id>/summary.json
.levelupdiag/runs/<run-id>/summary.txt
```

`latest/` contains convenience copies and does not replace history.

Campaign aggregation rules:

1. diagnostics/config errors cannot become target success;
2. any executed target `FAIL` makes the campaign `FAIL`;
3. required `SKIP`, `BLOCKED`, `PARTIAL`, or `INFRA_ERROR` makes evidence incomplete (`BLOCKED`);
4. equivalent statuses on optional levels degrade to `WARN`;
5. `WARN` remains accepted but visible;
6. missing results are never final evidence.

A level's `required` flag affects completeness, not whether an observed `FAIL` matters. An optional level that actually executes and finds a target failure is still a failure.
