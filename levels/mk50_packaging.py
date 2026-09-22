from __future__ import annotations
import email.parser, json, re, zipfile
from pathlib import Path
from ._mk_common import mkcfg, parse_pinned_requirements, read_json, sha256, target


def run(cfg, report):
    root=target(cfg); expected=mkcfg(cfg)
    # Source manifest
    try:
        manifest=read_json(root/'manifest.json'); bad=[]
        for row in manifest.get('files',[]):
            p=root/row['path']
            if not p.is_file(): bad.append({'path':row['path'],'reason':'missing'}); continue
            actual=sha256(p); size=p.stat().st_size
            if actual!=row.get('sha256') or size!=row.get('bytes'): bad.append({'path':row['path'],'reason':'hash_or_size','sha256':actual,'bytes':size})
        report.add('medikristal.delivery.manifest_hashes','FAIL' if bad else 'PASS','delivery',
                   'Delivery manifest hashes and byte counts match the source tree.' if not bad else 'Delivery manifest contains stale or missing file entries.',
                   evidence=bad[:100] if bad else {'files':len(manifest.get('files',[]))})
    except Exception as exc:
        report.add('medikristal.delivery.manifest_hashes','FAIL','delivery','Delivery manifest could not be verified.',evidence=f'{type(exc).__name__}: {exc}')

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
        sbom=read_json(root/'sbom.cdx.json'); reqs=parse_pinned_requirements(root/'backend/requirements.lock')
        components={(re.sub(r'[-_.]+','-',x.get('name','')).lower(),x.get('version')) for x in sbom.get('components',[])}
        if components!=set(reqs): sbom_errors.append({'requirements':reqs,'sbom':sorted(components)})
        app=sbom.get('metadata',{}).get('component',{})
        if app.get('name')!='medikristal' or app.get('version')!=expected.get('expected_version'): sbom_errors.append({'metadata_component':app})
    except Exception as exc: sbom_errors.append(f'{type(exc).__name__}: {exc}')
    report.add('medikristal.delivery.sbom_lock_alignment','FAIL' if sbom_errors else 'PASS','delivery',
               'CycloneDX direct components exactly match the pinned runtime lock.' if not sbom_errors else 'SBOM and pinned runtime dependency lock differ.',
               evidence=sbom_errors or {'components':len(reqs)})

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
