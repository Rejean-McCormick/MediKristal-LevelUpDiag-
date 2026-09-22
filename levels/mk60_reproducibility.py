from __future__ import annotations
import sys
from pathlib import Path
from ._mk_common import copy_target_to_temp, read_json, run as run_cmd, sha256, target

GENERATED=[
 'contracts/domain.schema.json','contracts/openapi.json','contracts/traceability.json',
 'backend/medikristal/_assets/contracts/domain.schema.json','backend/medikristal/_assets/contracts/openapi.json','backend/medikristal/_assets/contracts/traceability.json',
 'backend/medikristal/_assets/frontend/index.html','backend/medikristal/_assets/frontend/app.js','backend/medikristal/_assets/frontend/styles.css',
 'sbom.cdx.json','validation-report.json','VALIDATION.md','manifest.json'
]

def run(cfg, report):
    root=target(cfg); holder,tmp=copy_target_to_temp(root)
    try:
        steps=[]
        for script in ('build_contracts.py','validate_reference.py','sync_runtime_assets.py','build_sbom.py','build_manifest.py'):
            res=run_cmd(tmp,[sys.executable,str(tmp/'tools'/script)],cwd=tmp,timeout=240)
            steps.append((script,res))
            if res['timed_out'] or res['exit_code']!=0: break
        # Canonical compileall proof is run only in the disposable copy.
        if len(steps)==5 and all(x[1]['exit_code']==0 for x in steps):
            comp=run_cmd(tmp,[sys.executable,'-m','compileall','-q','backend/medikristal','tools','scripts','tests'],cwd=tmp,timeout=180)
            steps.append(('compileall',comp))
        ok=all(r['exit_code']==0 and not r['timed_out'] for _,r in steps) and len(steps)==6
        report.add('medikristal.reproducibility.generators_execute','PASS' if ok else ('INFRA_ERROR' if any(r['timed_out'] for _,r in steps) else 'FAIL'),'reproducibility',
                   'Canonical generators and compileall execute successfully in a disposable repository copy.' if ok else 'A canonical generator or compile step failed in the disposable repository copy.',
                   evidence=[{'step':n,'exit_code':r['exit_code'],'timed_out':r['timed_out'],'stdout_tail':r['stdout_tail'][-1200:],'stderr_tail':r['stderr_tail'][-1200:]} for n,r in steps])
        if not ok: return
        drift=[]
        for rel in GENERATED:
            a=root/rel; b=tmp/rel
            if not a.is_file() or not b.is_file(): drift.append({'path':rel,'reason':'missing'}); continue
            if a.read_bytes()!=b.read_bytes(): drift.append({'path':rel,'checked_in_sha256':sha256(a),'regenerated_sha256':sha256(b)})
        fresh=read_json(tmp/'validation-report.json').get('counts',{})
        report.add('medikristal.reproducibility.generated_files','FAIL' if drift else 'PASS','reproducibility',
                   'Checked-in generated artifacts exactly match a fresh local regeneration.' if not drift else 'One or more checked-in generated artifacts are stale relative to canonical generators.',
                   evidence={'drift':drift,'fresh_validation_counts':fresh},
                   recommendation='Regenerate the delivery evidence and manifest together, then rerun the release campaign.' if drift else None)
        report.metrics.update({'generated_files_checked':len(GENERATED),'drifted_generated_files':len(drift),'fresh_documentary_pass':fresh.get('pass'),'fresh_documentary_fail':fresh.get('fail')})
    finally:
        holder.cleanup()
