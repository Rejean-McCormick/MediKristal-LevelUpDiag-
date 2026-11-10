from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
from ._mk_common import mkcfg, python_env, run as run_cmd, target, tool


def assess_engineering_only_capabilities(capabilities: dict, required_states: dict) -> list[dict]:
    """Independent no-clinical-claim gate for the synthetic 0.2.0 software profile."""
    errors = []
    if not isinstance(capabilities, dict) or not capabilities:
        return [{'reason': 'missing_capability_evidence'}]
    for name, capability in capabilities.items():
        if not isinstance(capability, dict):
            errors.append({'name': name, 'reason': 'invalid_capability_shape'})
            continue
        uses = capability.get('supported_uses')
        limitations = capability.get('limitations')
        if uses != ['engineering']:
            errors.append({'name': name, 'reason': 'unqualified_supported_use', 'value': uses})
        if not isinstance(limitations, list) or not limitations or not all(isinstance(x, str) and x.strip() for x in limitations):
            errors.append({'name': name, 'reason': 'missing_limitations'})
    for name, states in required_states.items():
        record = capabilities.get(name)
        state = record.get('state') if isinstance(record, dict) else None
        if state not in states:
            errors.append({'name': name, 'reason': 'unauthorized_external_state', 'state': state, 'allowed': states})
    return errors


def run(cfg, report):
    root=target(cfg); expected=mkcfg(cfg)
    with tempfile.TemporaryDirectory(prefix='levelupdiag-mk-runtime-') as td:
        db=Path(td)/'runtime.db'; blobs=Path(td)/'blobs'; blobs.mkdir()
        env=python_env(root,{
            'MEDIKRISTAL_DATABASE_URL':f'sqlite+pysqlite:///{db}',
            'MEDIKRISTAL_ENV':'test','MEDIKRISTAL_ALLOW_TEST_TOKEN':'1','MEDIKRISTAL_AUTH_SECRET':'x'*64,
            'MEDIKRISTAL_AUTO_CREATE_SCHEMA':'1','MEDIKRISTAL_CONTRACT_DIR':str(root/'contracts'),
            'MEDIKRISTAL_FRONTEND_DIR':str(root/'frontend'),'MEDIKRISTAL_BLOB_DIR':str(blobs),
        })
        result=run_cmd(root,[sys.executable,str(tool(cfg)/'probes/runtime_smoke.py'),str(root)],timeout=180,env=env)
    payload=None
    try:
        payload=json.loads((result.get('stdout_tail') or '').strip().splitlines()[-1])
    except Exception:
        pass
    ok=result['exit_code']==0 and not result['timed_out'] and isinstance(payload,dict)
    report.add('medikristal.runtime.smoke','PASS' if ok else ('INFRA_ERROR' if result['timed_out'] else 'FAIL'),'runtime',
               'Isolated FastAPI runtime smoke passed.' if ok else 'Isolated FastAPI runtime smoke failed.', evidence=payload or result,
               recommendation=None if ok else 'Inspect runtime import/startup, database readiness and HTTP contract behavior.')
    if not payload: return
    caps=payload.get('details',{}).get('capabilities',{})
    bad=assess_engineering_only_capabilities(caps, expected.get('required_external_capability_states',{}))
    report.add('medikristal.runtime.external_capabilities_honest','FAIL' if bad else 'PASS','runtime',
               'Every reported capability is engineering-only with explicit limitations; disabled external integrations remain unavailable.' if not bad else
               'A runtime capability advertises an unqualified use, lacks limitations or exposes an unauthorized external state.',
               evidence=bad or {'capabilities_checked':len(caps), 'external_names':sorted(expected.get('required_external_capability_states',{}))})
    route_count=payload.get('details',{}).get('runtime_api_routes')
    exp=int(expected.get('expected_operations',80))
    report.add('medikristal.runtime.route_count','PASS' if route_count==exp else 'FAIL','runtime',
               'Runtime route count matches the OpenAPI operation contract.' if route_count==exp else 'Runtime route count differs from the expected API surface.',
               evidence={'expected':exp,'actual':route_count})
