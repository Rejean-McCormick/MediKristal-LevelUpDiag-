#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

from levelupdiag_core.runner import run_campaign


def safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            candidate = (destination / member.filename).resolve(strict=False)
            if not candidate.is_relative_to(root):
                raise SystemExit(f"Unsafe ZIP path: {member.filename}")
        zf.extractall(destination)


def find_target(extracted: Path) -> Path:
    candidates = []
    for path in [extracted, *[p for p in extracted.rglob('*') if p.is_dir()]]:
        if (path / 'backend/pyproject.toml').is_file() and (path / 'contracts/openapi.json').is_file():
            candidates.append(path)
    if len(candidates) != 1:
        raise SystemExit(f"Expected one MediKristal repository in ZIP; found {len(candidates)}")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description='Run LevelUpDiag-MediKristal against a delivery ZIP without modifying the archive.')
    parser.add_argument('archive', type=Path)
    parser.add_argument('campaign', nargs='?', default='release', choices=['baseline','software','delivery','release','deep'])
    parser.add_argument('--output', type=Path, default=Path('levelupdiag_zip_runs'))
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--fail-fast', action='store_true')
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise SystemExit(f"Archive not found: {archive}")
    tool_root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='levelupdiag-mk-zip-') as td:
        extracted = Path(td) / 'extracted'; extracted.mkdir()
        safe_extract(archive, extracted)
        target = find_target(extracted)
        summary, code, run_root = run_campaign(tool_root, args.campaign, target_override=str(target), jobs=args.jobs, fail_fast=args.fail_fast)
        out = args.output.resolve() / f"{archive.stem}-{summary['run_id']}"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(run_root, out)
        print(f"LevelUpDiag-MediKristal {args.campaign}: {summary['verdict']}")
        print(f"Evidence: {out / 'summary.json'}")
        return code


if __name__ == '__main__':
    raise SystemExit(main())
