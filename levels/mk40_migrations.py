from __future__ import annotations
import sqlite3, sys, tempfile
from pathlib import Path
from ._mk_common import python_env, run as run_cmd, target

CRITICAL={'mk_entities','mk_entity_revisions','mk_idempotency','mk_outbox','mk_inbox','mk_reservation_claims','mk_case_access'}

def run(cfg, report):
    root=target(cfg); backend=root/'backend'
    if not (backend/'alembic.ini').is_file():
        report.add('medikristal.migrations.config','FAIL','database','Alembic configuration is missing.'); return
    with tempfile.TemporaryDirectory(prefix='levelupdiag-mk-migrate-') as td:
        db=Path(td)/'migration.db'
        env=python_env(root,{'MEDIKRISTAL_DATABASE_URL':f'sqlite+pysqlite:///{db}','MEDIKRISTAL_ENV':'test','MEDIKRISTAL_AUTH_SECRET':'x'*64})
        steps=[]
        for argv in ([sys.executable,'-m','alembic','-c','alembic.ini','upgrade','head'],[sys.executable,'-m','alembic','-c','alembic.ini','downgrade','base'],[sys.executable,'-m','alembic','-c','alembic.ini','upgrade','head']):
            res=run_cmd(root,list(argv),cwd=backend,timeout=180,env=env); steps.append(res)
            if res['timed_out'] or res['exit_code']!=0: break
        ok=len(steps)==3 and all(x['exit_code']==0 and not x['timed_out'] for x in steps)
        report.add('medikristal.migrations.roundtrip','PASS' if ok else ('INFRA_ERROR' if any(x['timed_out'] for x in steps) else 'FAIL'),'database',
                   'Alembic upgrade -> downgrade base -> upgrade completed on a disposable database.' if ok else 'Alembic migration roundtrip failed.',
                   evidence=[{'argv':x['argv'],'exit_code':x['exit_code'],'timed_out':x['timed_out'],'stderr_tail':x['stderr_tail'][-2000:]} for x in steps])
        if not ok: return
        con=sqlite3.connect(db)
        tables={r[0] for r in con.execute("select name from sqlite_master where type='table'")}; con.close()
        missing=sorted(CRITICAL-tables)
        report.add('medikristal.migrations.integrity_tables','FAIL' if missing else 'PASS','database',
                   'Critical integrity tables exist after migration.' if not missing else 'Critical integrity tables are missing after migration.',
                   evidence={'missing':missing,'tables':sorted(tables)})
        report.metrics['tables_after_upgrade']=len(tables)
