from __future__ import annotations
import json, os, sys
from pathlib import Path

root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/'backend'))
os.environ.setdefault('MEDIKRISTAL_ENV','test')
os.environ.setdefault('MEDIKRISTAL_ALLOW_TEST_TOKEN','1')
os.environ.setdefault('MEDIKRISTAL_AUTH_SECRET','x'*64)
os.environ.setdefault('MEDIKRISTAL_CONTRACT_DIR',str(root/'contracts'))
os.environ.setdefault('MEDIKRISTAL_FRONTEND_DIR',str(root/'frontend'))
os.environ.setdefault('MEDIKRISTAL_AUTO_CREATE_SCHEMA','1')

from fastapi.testclient import TestClient
from medikristal.app import app

out={'checks':{},'details':{}}
with TestClient(app) as client:
    health=client.get('/healthz'); ready=client.get('/readyz')
    served=client.get('/openapi.json')
    root_contract=json.loads((root/'contracts/openapi.json').read_text(encoding='utf-8'))
    ui=client.get('/'); js=client.get('/app.js'); css=client.get('/styles.css')
    caps=client.get('/api/v1/capabilities',headers={'Authorization':'Bearer test-all'})
    missing=client.get('/api/v1/cases/00000000-0000-4000-8000-000000000404',headers={'Authorization':'Bearer test-all'})
    out['checks']={
      'health': health.status_code==200 and health.json()=={'status':'ok'},
      'ready': ready.status_code==200 and ready.json()=={'status':'ready'},
      'openapi_exact': served.status_code==200 and served.json()==root_contract,
      'ui': ui.status_code==200 and js.status_code==200 and css.status_code==200,
      'capabilities': caps.status_code==200,
      'problem_json': missing.status_code==404 and missing.headers.get('content-type','').startswith('application/problem+json'),
      'security_headers': caps.headers.get('cache-control')=='no-store' and caps.headers.get('x-content-type-options')=='nosniff' and 'frame-ancestors' in caps.headers.get('content-security-policy',''),
    }
    if caps.status_code==200:
      out['details']['capabilities']={x['name']:x['state'] for x in caps.json().get('capabilities',[])}
    out['details']['runtime_api_routes']=sum(1 for r in app.routes if r.path.startswith('/api/v1') for m in (r.methods or set()) if m in {'GET','POST','PUT','PATCH','DELETE'})
print(json.dumps(out,ensure_ascii=False))
raise SystemExit(0 if all(out['checks'].values()) else 1)
