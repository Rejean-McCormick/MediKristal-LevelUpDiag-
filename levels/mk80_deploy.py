from __future__ import annotations
import re
from ._mk_common import target


def run(cfg, report):
    root=target(cfg); compose=root/'deploy/docker-compose.yml'; dockerfile=root/'backend/Dockerfile'; envfile=root/'deploy/.env.example'
    if not compose.is_file() or not dockerfile.is_file():
        report.add('medikristal.deploy.files','FAIL','operations','Compose or Dockerfile is missing.'); return
    c=compose.read_text(encoding='utf-8'); d=dockerfile.read_text(encoding='utf-8'); e=envfile.read_text(encoding='utf-8') if envfile.is_file() else ''
    # Deliberately conservative indentation parser: names at 2 spaces beneath services:.
    services=[]; in_services=False
    for line in c.splitlines():
        if line.strip()=='services:': in_services=True; continue
        if in_services and line and not line.startswith(' '): break
        m=re.match(r'^  ([A-Za-z0-9_.-]+):\s*$',line)
        if in_services and m: services.append(m.group(1))
    expected={'db','migrate','api','worker'}
    report.add('medikristal.deploy.compose_topology','PASS' if set(services)==expected else 'FAIL','operations',
               'Compose declares the expected database, migration, API and worker services.' if set(services)==expected else 'Compose service topology differs from the delivery contract.',
               evidence={'expected':sorted(expected),'actual':services})
    hardcoded = bool(re.search(r'POSTGRES_PASSWORD:\s*(?!\$\{)[^\s#]+',c))
    placeholders = '${MEDIKRISTAL_DB_PASSWORD:?set MEDIKRISTAL_DB_PASSWORD}' in c and '${MEDIKRISTAL_AUTH_SECRET:?set MEDIKRISTAL_AUTH_SECRET}' in c
    report.add('medikristal.deploy.secrets_externalized','PASS' if placeholders and not hardcoded else 'FAIL','operations',
               'Compose requires database/auth secrets from the environment and does not hard-code the PostgreSQL password.' if placeholders and not hardcoded else 'Compose secret handling does not satisfy the delivery policy.',
               evidence={'required_placeholders':placeholders,'hardcoded_postgres_password':hardcoded})
    nonroot=bool(re.search(r'^USER\s+(?!root\b)\S+',d,re.M))
    report.add('medikristal.deploy.non_root_runtime','PASS' if nonroot else 'FAIL','operations',
               'Application image declares a non-root runtime user.' if nonroot else 'Application image does not declare a non-root runtime user.')
    production=c.count('MEDIKRISTAL_ENV: production')>=2
    report.add('medikristal.deploy.production_mode','PASS' if production else 'FAIL','operations',
               'API and worker are explicitly configured for production mode.' if production else 'API/worker production-mode configuration is incomplete.')
    example_ok='replace-with-a-long-random-secret-at-least-32-chars' in e and 'replace-with-a-long-random-database-password' in e
    report.add('medikristal.deploy.env_example_placeholders','PASS' if example_ok else 'WARN','operations',
               'Environment example uses explicit replacement placeholders.' if example_ok else 'Environment example should make non-production placeholder values explicit.')
    report.add('medikristal.deploy.runtime_execution_scope','WARN','operations','Static deployment configuration was validated, but Docker/PostgreSQL were not started by this read-only campaign.',recommendation='Run a separate deployment-environment qualification against real Docker/PostgreSQL before production release.')
