from __future__ import annotations
import json, os, re, sys, tempfile
from pathlib import Path
from ._mk_common import copy_target_to_temp, mkcfg, python_env, read_json, run as run_cmd, target


def _one(pattern,text):
    m=re.search(pattern,text,re.I|re.S); return int(m.group(1)) if m else None


def run(cfg, report):
    root=target(cfg); expected=mkcfg(cfg)
    env=python_env(root)
    collected=run_cmd(root,[sys.executable,'-m','pytest','--collect-only','-q','-p','no:cacheprovider'],cwd=root/'backend',timeout=240,env=env)
    text=(collected.get('stdout_tail') or '')+'\n'+(collected.get('stderr_tail') or '')
    m=re.search(r'(\d+) tests? collected',text)
    count=int(m.group(1)) if m else None
    if count is None and collected['exit_code']==0:
        # pytest -q on some versions prints one nodeid per line and no summary when quiet plugins differ.
        
        compact=[re.fullmatch(r'[^:]+\.py:\s*(\d+)', line.strip()) for line in text.splitlines()]
        compact_counts=[int(m.group(1)) for m in compact if m]
        count=sum(compact_counts) if compact_counts else sum(1 for line in text.splitlines() if '::test_' in line)
    exp_tests=int(expected.get('expected_tests',73))
    report.add('medikristal.evidence.test_collection','PASS' if collected['exit_code']==0 and count==exp_tests else 'FAIL','evidence',
               'Fresh pytest collection matches the declared application test count.' if collected['exit_code']==0 and count==exp_tests else 'Fresh pytest collection differs from the declared application test count.',
               evidence={'expected':exp_tests,'actual':count,'exit_code':collected['exit_code'],'tail':text[-1800:]})

    current=read_json(root/'validation-report.json').get('counts',{})
    # Recompute the documentary validator in a disposable copy so stale checked-in
    # evidence cannot validate its own claims.
    holder,tmp=copy_target_to_temp(root)
    try:
        fresh_doc_run=run_cmd(tmp,[sys.executable,str(tmp/'tools/validate_reference.py')],cwd=tmp,timeout=180)
        fresh_doc=read_json(tmp/'validation-report.json').get('counts',{}) if fresh_doc_run['exit_code']==0 else {}
    finally:
        holder.cleanup()
    app=(root/'APP_VALIDATION.md').read_text(encoding='utf-8')
    impl=(root/'IMPLEMENTATION.md').read_text(encoding='utf-8') if (root/'IMPLEMENTATION.md').exists() else ''
    changelog=(root/'CHANGELOG.md').read_text(encoding='utf-8') if (root/'CHANGELOG.md').exists() else ''
    validation=(root/'VALIDATION.md').read_text(encoding='utf-8')
    claims=[]
    patterns=[
        ('APP_VALIDATION tests',app,r'PASS\s*[—-]\s*(\d+)\s+tests'),
        ('IMPLEMENTATION tests',impl,r'tests applicatifs\s*:\s*\*\*(\d+)/\d+'),
        ('APP_VALIDATION documentary',app,r'PASS\s*[—-]\s*(\d+)\s+contr[oô]les'),
        ('IMPLEMENTATION documentary',impl,r'contr[oô]les documentaires/contractuels[^\d]*(\d+)/\d+'),
        ('VALIDATION documentary',validation,r'R[ée]sultat\s*:\s*(\d+)\s+PASS'),
    ]
    for label,src,pat in patterns:
        val=_one(pat,src)
        if val is not None: claims.append((label,val))
    mismatches=[]
    for label,val in claims:
        if 'tests' in label and count is not None and val!=count: mismatches.append({'claim':label,'documented':val,'fresh':count})
        if 'documentary' in label and fresh_doc.get('pass') is not None and val!=fresh_doc.get('pass'): mismatches.append({'claim':label,'documented':val,'fresh':fresh_doc.get('pass')})
    report.add('medikristal.evidence.documented_counts_consistent','FAIL' if mismatches else 'PASS','evidence',
               'Documented validation counts are internally consistent with fresh/current evidence.' if not mismatches else 'One or more delivery documents contain stale validation counts.',
               evidence={'claims':claims,'checked_in_validation_report':current,'fresh_validation_report':fresh_doc,'mismatches':mismatches},
               recommendation='Update validation prose only after regenerating and rerunning the corresponding evidence.' if mismatches else None)

    # Re-measure code coverage with the same pytest-cov surface documented by MediKristal,
    # while writing the JSON report outside the target repository.
    with tempfile.TemporaryDirectory(prefix='levelupdiag-mk-cov-') as td:
        covjson=Path(td)/'coverage.json'
        cenv=python_env(root,{'COVERAGE_FILE':str(Path(td)/'.coverage')})
        cov=run_cmd(root,[sys.executable,'-m','pytest','--cov=medikristal',f'--cov-report=json:{covjson}','-q','-p','no:cacheprovider'],cwd=root/'backend',timeout=600,env=cenv)
        if cov['exit_code']!=0 or cov['timed_out'] or not covjson.is_file():
            blocked='unrecognized arguments' in ((cov.get('stdout_tail') or '')+(cov.get('stderr_tail') or '')).lower()
            report.add('medikristal.evidence.coverage_remeasure','BLOCKED' if blocked else 'FAIL','evidence','Coverage could not be independently remeasured in this environment.',evidence=cov,recommendation='Install pytest-cov/coverage.py and the locked MediKristal test dependencies to qualify the documented coverage claim.')
        else:
            data=json.loads(covjson.read_text(encoding='utf-8')); pct=float(data['totals']['percent_covered']); rounded=round(pct)
            api_file=next((v for k,v in data.get('files',{}).items() if k.replace('\\','/').endswith('medikristal/api.py')),None)
            api_pct=float(api_file['summary']['percent_covered']) if api_file else None
            documented=_one(r'couverture globale\s+(\d+)\s*%',app)
            documented_api=_one(r'API\s+(\d+)\s*%',app)
            min_pct=float(expected.get('minimum_global_coverage_percent',90))
            coverage_mismatch=(documented is not None and documented!=rounded) or (documented_api is not None and api_pct is not None and documented_api!=round(api_pct))
            verdict='FAIL' if pct<min_pct or coverage_mismatch else 'PASS'
            report.add('medikristal.evidence.coverage_remeasure',verdict,'evidence',
                       'Coverage was independently remeasured and matches documented rounded values/minimum.' if verdict=='PASS' else 'Fresh coverage differs from the documented value or required minimum.',
                       evidence={'global_percent':pct,'global_rounded':rounded,'api_percent':api_pct,'api_rounded':round(api_pct) if api_pct is not None else None,'documented_global':documented,'documented_api':documented_api,'minimum':min_pct})
            report.metrics.update({'tests_collected':count,'coverage_percent':round(pct,2),'api_coverage_percent':round(api_pct,2) if api_pct is not None else None})
