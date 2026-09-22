from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
from ._mk_common import mkcfg, python_env, run as run_cmd, target, tool


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
    bad=[]
    for name, allowed in expected.get('required_external_capability_states',{}).items():
        if caps.get(name) not in allowed: bad.append({'name':name,'state':caps.get(name),'allowed':allowed})
    report.add('medikristal.runtime.external_capabilities_honest','FAIL' if bad else 'PASS','runtime',
               'External/partner capabilities are not advertised as available without configuration.' if not bad else 'An external capability is advertised in a state forbidden by the delivery policy.',
               evidence=bad or {k:caps.get(k) for k in expected.get('required_external_capability_states',{})})
    route_count=payload.get('details',{}).get('runtime_api_routes')
    exp=int(expected.get('expected_operations',80))
    report.add('medikristal.runtime.route_count','PASS' if route_count==exp else 'FAIL','runtime',
               'Runtime route count matches the OpenAPI operation contract.' if route_count==exp else 'Runtime route count differs from the expected API surface.',
               evidence={'expected':exp,'actual':route_count})
