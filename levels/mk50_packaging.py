from __future__ import annotations
import email.parser, hashlib, json, re, zipfile
from pathlib import Path
from ._mk_common import mkcfg, parse_pinned_requirements, read_json, sha256, target


def verify_delivery_manifest(root: Path, manifest: dict, expected_version: str) -> list[dict]:
    """Check both declared bytes AND full source coverage, without executing target code.

    This mirrors the recorded MediKristal delivery-manifest/2 inclusion policy.
    Snapshot dump metadata and diagnostic output are not product source files.
    """
    excluded_dirs = {'.git', '.levelupdiag', '.pytest_cache', '__pycache__',
                     '.venv', 'venv', 'dist', 'build', 'levelupdiag_zip_runs'}
    excluded_files = {'manifest.json', '.coverage', 'SMARTDUMP_INDEX.txt',
                      'Launch_MULTiSmartDump.lnk'}
    excluded_suffixes = {'.pyc', '.pyo', '.zip', '.whl'}
    expected = set()
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in excluded_dirs or part.endswith('.egg-info') for part in rel.parts[:-1]):
            continue
        if rel.name in excluded_files or rel.suffix in excluded_suffixes:
            continue
        expected.add(rel.as_posix())
    issues = []
    if manifest.get('format') != 'medikristal.delivery-manifest/2':
        issues.append({'path': 'manifest.json', 'reason': 'unsupported_format'})
    if manifest.get('api_version') != expected_version:
        issues.append({'path': 'manifest.json', 'reason': 'wrong_api_version'})
    rows = manifest.get('files')
    if not isinstance(rows, list):
        return issues + [{'path': 'manifest.json', 'reason': 'files_not_an_array'}]
    declared = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            issues.append({'path': 'manifest.json', 'reason': 'invalid_entry'})
            continue
        rel = Path(row['path'])
        key = rel.as_posix()
        if rel.is_absolute() or '..' in rel.parts or not (root / rel).resolve().is_relative_to(root.resolve()):
            issues.append({'path': key, 'reason': 'unsafe_path'})
            continue
        if key in declared:
            issues.append({'path': key, 'reason': 'duplicate_entry'})
            continue
        declared.add(key)
        if key not in expected:
            issues.append({'path': key, 'reason': 'unexpected_entry'})
            continue
        path = root / rel
        if not path.is_file():
            issues.append({'path': key, 'reason': 'missing'})
            continue
        actual = sha256(path)
        size = path.stat().st_size
        if actual != row.get('sha256') or size != row.get('bytes'):
            issues.append({'path': key, 'reason': 'hash_or_size', 'sha256': actual, 'bytes': size})
    for missing in sorted(expected - declared):
        issues.append({'path': missing, 'reason': 'unlisted_source_file'})
    return issues


def verify_sbom_lock(root: Path, sbom: dict) -> list[dict]:
    """Check exact pinned names, extras, versions and lock bytes, not counts only."""
    path = root / 'backend/requirements.lock'
    requirements = parse_pinned_requirements(path)
    components = sbom.get('components', [])
    if not isinstance(components, list):
        return [{'reason': 'invalid_components'}]
    errors = []
    locked = {(name, version) for name, version in requirements}
    from_sbom = {(re.sub(r'[-_.]+', '-', c.get('name', '')).lower(), c.get('version')) for c in components}
    if len(locked) != len(requirements) or from_sbom != locked or len(components) != len(requirements):
        errors.append({'reason': 'lock_component_set_mismatch'})
    prop_list = sbom.get('metadata', {}).get('properties', [])
    props = {x.get('name'): x.get('value') for x in prop_list if isinstance(x, dict)}
    actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if props.get('medikristal:requirements-lock-sha256') != actual_digest:
        errors.append({'reason': 'stale_or_missing_lock_digest'})
    # The lock has one approved optional extra (psycopg[binary]). Flattened
    # name/version equality must not obscure a change in packaging semantics.
    declared_extras = {}
    for c in components:
        properties = c.get('properties', [])
        parsed = {x.get('name'): x.get('value') for x in properties if isinstance(x, dict)}
        if parsed.get('medikristal:extras'):
            declared_extras[re.sub(r'[-_.]+', '-', c['name']).lower()] = parsed['medikristal:extras']
    observed_extras = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[([^]]+)\])?==([^\s;]+)', line)
        if m and m.group(2):
            observed_extras[re.sub(r'[-_.]+', '-', m.group(1)).lower()] = ','.join(sorted(x.strip() for x in m.group(2).split(',')))
    if declared_extras != observed_extras:
        errors.append({'reason': 'extras_mismatch', 'lock': observed_extras, 'sbom': declared_extras})
    return errors


def run(cfg, report):
    root=target(cfg); expected=mkcfg(cfg)
    # Verify declared entries and independently enumerate required source files.
    # A truncated manifest must never get a false PASS merely because each
    # remaining listed hash is accurate.
    try:
        manifest = read_json(root / 'manifest.json')
        bad = verify_delivery_manifest(root, manifest, str(expected.get('expected_version', '')))
        report.add('medikristal.delivery.manifest_hashes', 'FAIL' if bad else 'PASS', 'delivery',
                   'Source manifest hashes, declared members and complete source inventory agree.' if not bad else
                   'Source manifest has missing, unlisted, duplicate, unsafe or stale entries.',
                   evidence=bad[:100] if bad else {'files': len(manifest['files'])})
    except Exception as exc:
        report.add('medikristal.delivery.manifest_hashes', 'FAIL', 'delivery',
                   'Delivery manifest could not be verified.', evidence=f'{type(exc).__name__}: {exc}')

    sums=root/'dist/SHA256SUMS'; wheels=list((root/'dist').glob('medikristal-*.whl')) if (root/'dist').exists() else []
    wheel=wheels[0] if len(wheels)==1 else None
    sum_ok=False; declared=None
    if wheel and sums.is_file():
        for line in sums.read_text(encoding='utf-8').splitlines():
            parts=line.split()
            if len(parts)>=2 and Path(parts[-1]).name==wheel.name: declared=parts[0]; break
        sum_ok=declared==sha256(wheel)
    report.add('medikristal.delivery.wheel_checksum','PASS' if sum_ok else 'FAIL','delivery',
               'Wheel checksum matches dist/SHA256SUMS.' if sum_ok else 'Wheel or matching SHA256SUMS entry is missing/stale.',
               evidence={'wheel':wheel.name if wheel else None,'declared':declared,'actual':sha256(wheel) if wheel else None})

    wheel_errors=[]; metadata={}
    if wheel:
        try:
            with zipfile.ZipFile(wheel) as z:
                names=set(z.namelist())
                meta_names=[x for x in names if x.endswith('.dist-info/METADATA')]
                if len(meta_names)!=1: wheel_errors.append('METADATA missing/ambiguous')
                else:
                    text=z.read(meta_names[0]).decode('utf-8','replace')
                    msg=email.parser.Parser().parsestr(text); metadata={'Name':msg.get('Name'),'Version':msg.get('Version')}
                    if msg.get('Name')!='medikristal' or msg.get('Version')!=expected.get('expected_version'): wheel_errors.append('package identity/version mismatch')
                for name in ('openapi.json','domain.schema.json','traceability.json'):
                    member=f'medikristal/_assets/contracts/{name}'
                    if member not in names or z.read(member)!=(root/'contracts'/name).read_bytes(): wheel_errors.append(member)
                for name in ('index.html','app.js','styles.css'):
                    member=f'medikristal/_assets/frontend/{name}'
                    if member not in names or z.read(member)!=(root/'frontend'/name).read_bytes(): wheel_errors.append(member)
        except Exception as exc: wheel_errors.append(f'{type(exc).__name__}: {exc}')
    else: wheel_errors.append('wheel missing')
    report.add('medikristal.delivery.wheel_contents','FAIL' if wheel_errors else 'PASS','delivery',
               'Wheel metadata and embedded runtime assets match repository sources.' if not wheel_errors else 'Wheel contents are stale or incomplete.',
               evidence=wheel_errors or metadata)

    sbom_errors=[]
    try:
        sbom=read_json(root/'sbom.cdx.json')
        sbom_errors.extend(verify_sbom_lock(root, sbom))
        app=sbom.get('metadata',{}).get('component',{})
        if app.get('name')!='medikristal' or app.get('version')!=expected.get('expected_version'):
            sbom_errors.append({'reason':'metadata_component_mismatch','component':app})
    except Exception as exc:
        sbom_errors.append(f'{type(exc).__name__}: {exc}')
    report.add('medikristal.delivery.sbom_lock_alignment','FAIL' if sbom_errors else 'PASS','delivery',
               'SBOM direct components, optional extras and exact lock SHA-256 agree.' if not sbom_errors else
               'SBOM and pinned runtime lock differ or evidence is incomplete.',
               evidence=sbom_errors or {'components':len(sbom['components'])})

    try:
        snaps=read_json(root/'source-snapshots.json').get('snapshots',[]); malformed=[]
        for row in snaps:
            if not re.fullmatch(r'[a-f0-9]{64}',str(row.get('sha256',''))) or int(row.get('size_bytes',0))<=0 or int(row.get('entries',0))<=0: malformed.append(row.get('filename'))
        verdict='WARN' if snaps else 'FAIL'
        message='Source snapshot descriptors are well-formed, but original archives are not part of this target so their hashes cannot be independently reverified.' if snaps and not malformed else 'Source snapshot provenance descriptors are missing or malformed.'
        if malformed: verdict='FAIL'
        report.add('medikristal.delivery.source_snapshot_attestation',verdict,'delivery',message,evidence={'snapshots':len(snaps),'malformed':malformed},recommendation='Reverify these hashes against the original source archives during provenance attestation.' if verdict=='WARN' else None)
    except Exception as exc:
        report.add('medikristal.delivery.source_snapshot_attestation','FAIL','delivery','Source snapshot provenance descriptor could not be parsed.',evidence=str(exc))
