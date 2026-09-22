from __future__ import annotations

import re
from pathlib import Path

from ._mk_common import mkcfg, operation_map, parse_project, read_json, target


def run(cfg, report):
    root = target(cfg); expected = mkcfg(cfg)
    try:
        api = read_json(root / "contracts/openapi.json")
        schema = read_json(root / "contracts/domain.schema.json")
        trace = read_json(root / "contracts/traceability.json")
        index = read_json(root / "examples/index.json")
    except Exception as exc:
        report.add("medikristal.contracts.parse", "FAIL", "contracts", "A core JSON contract cannot be parsed.", evidence=f"{type(exc).__name__}: {exc}")
        return
    report.add("medikristal.contracts.parse", "PASS", "contracts", "Core JSON contracts parse successfully.")

    ops = operation_map(api)
    operation_occurrences = []
    for path, methods in api.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() in {"get","post","put","patch","delete"}:
                operation_occurrences.append(op.get("operationId"))
    op_expected = int(expected.get("expected_operations", 80))
    dupes = sorted({x for x in operation_occurrences if x and operation_occurrences.count(x) > 1})
    op_ok = len(operation_occurrences) == op_expected and len(ops) == op_expected and not dupes
    report.add("medikristal.openapi.operation_set", "PASS" if op_ok else "FAIL", "contracts",
               "OpenAPI declares the expected unique operation set." if op_ok else "OpenAPI operation count or uniqueness differs from the delivery contract.",
               evidence={"expected": op_expected, "actual": len(operation_occurrences), "unique": len(ops), "duplicates": dupes})

    schema_count = len(schema.get("$defs", {})); schema_expected = int(expected.get("expected_schemas", 107))
    report.add("medikristal.schema.definition_count", "PASS" if schema_count == schema_expected else "FAIL", "contracts",
               "Domain schema definition count matches the declared contract." if schema_count == schema_expected else "Domain schema definition count drifted.",
               evidence={"expected": schema_expected, "actual": schema_count})

    project = parse_project(root)
    version_ok = api.get("info",{}).get("version") == project.get("version") == expected.get("expected_version")
    report.add("medikristal.contracts.version_alignment", "PASS" if version_ok else "FAIL", "contracts",
               "API and package versions are aligned." if version_ok else "API/package version mismatch.",
               evidence={"openapi": api.get("info",{}).get("version"), "package": project.get("version"), "expected": expected.get("expected_version")})

    bad_security=[]
    for op_id, (_method, path, op) in ops.items():
        if not op.get("x-permission") or not op.get("security"):
            bad_security.append({"operation": op_id, "path": path})
    report.add("medikristal.openapi.permission_metadata", "FAIL" if bad_security else "PASS", "contracts",
               "Every API operation declares permission and security metadata." if not bad_security else "One or more API operations lack permission/security metadata.",
               evidence=bad_security[:100] if bad_security else {"operations": len(ops)})

    entries = trace.get("entries", [])
    req_expected = int(expected.get("expected_requirements", 32))
    expected_req_ids = {f"MK-{i:03d}" for i in range(1, req_expected + 1)}
    actual_req_ids = {x.get("requirement") for x in entries}
    trace_errors=[]
    defs=set(schema.get("$defs",{})); op_ids=set(ops)
    acceptance_doc=(root/"docs/33-acceptance.md").read_text(encoding="utf-8")
    for row in entries:
        rid=row.get("requirement")
        if row.get("status") != "specified": trace_errors.append(f"{rid}: status={row.get('status')}")
        for chapter in row.get("chapters",[]):
            if not (root/chapter).is_file(): trace_errors.append(f"{rid}: missing chapter {chapter}")
        for name in row.get("schemas",[]):
            if name not in defs: trace_errors.append(f"{rid}: unknown schema {name}")
        for name in row.get("operations",[]):
            if name not in op_ids: trace_errors.append(f"{rid}: unknown operation {name}")
        ats=row.get("acceptance_tests",[])
        if not ats: trace_errors.append(f"{rid}: no acceptance test")
        for at in ats:
            if not re.fullmatch(r"AT-\d{3}", str(at)) or at not in acceptance_doc:
                trace_errors.append(f"{rid}: acceptance reference {at} missing")
    if actual_req_ids != expected_req_ids:
        trace_errors.append(f"requirement set mismatch: missing={sorted(expected_req_ids-actual_req_ids)} extra={sorted(actual_req_ids-expected_req_ids)}")
    report.add("medikristal.traceability.matrix", "FAIL" if trace_errors else "PASS", "traceability",
               "Traceability covers every MK requirement with resolvable chapters, schemas, operations and acceptance tests." if not trace_errors else "Traceability matrix contains unresolved or incomplete references.",
               evidence=trace_errors[:200] if trace_errors else {"requirements": len(entries)})

    examples = index if isinstance(index, list) else index.get("examples", [])
    example_count = len(examples); exp_examples=int(expected.get("expected_examples",12))
    report.add("medikristal.examples.count", "PASS" if example_count == exp_examples else "FAIL", "contracts",
               "Example inventory count matches the contract." if example_count == exp_examples else "Example inventory count drifted.",
               evidence={"expected": exp_examples, "actual": example_count})

    asset_errors=[]
    for name in ("openapi.json","domain.schema.json","traceability.json"):
        src=root/"contracts"/name; dst=root/"backend/medikristal/_assets/contracts"/name
        if not dst.is_file() or src.read_bytes()!=dst.read_bytes(): asset_errors.append(f"contracts/{name}")
    for name in ("index.html","app.js","styles.css"):
        src=root/"frontend"/name; dst=root/"backend/medikristal/_assets/frontend"/name
        if not dst.is_file() or src.read_bytes()!=dst.read_bytes(): asset_errors.append(f"frontend/{name}")
    report.add("medikristal.runtime_assets.parity", "FAIL" if asset_errors else "PASS", "contracts",
               "Packaged runtime source assets match repository contracts and frontend." if not asset_errors else "Runtime source assets are stale or missing.",
               evidence=asset_errors or {"files": 6})
    report.metrics.update({"operations":len(ops),"schemas":schema_count,"requirements":len(entries),"examples":example_count})
