#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

FORMAT = "levelupdiag-medikristal.manifest/1"
EXCLUDED_NAMES = {
    "suite-manifest.json",
    "SMARTDUMP_INDEX.txt",
    "CODE_SNAPSHOT_MANIFEST.md",
    "SmartSnap.pyw",
    "GitSink.bat",
}
EXCLUDED_PARTS = {
    ".git",
    ".levelupdiag",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
}


def _suite_version(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\\s*=\\s*["\\\']([^"\\\']+)["\\\']', text, flags=re.MULTILINE)
        if match:
            return match.group(1)
    manifest = root / "suite-manifest.json"
    if manifest.is_file():
        try:
            return str(json.loads(manifest.read_text(encoding="utf-8")).get("suite_version", "unknown"))
        except (OSError, ValueError, TypeError):
            pass
    return "unknown"


def _excluded(rel: Path) -> bool:
    if rel.as_posix() in EXCLUDED_NAMES or rel.name in EXCLUDED_NAMES:
        return True
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return True
    if rel.suffix.lower() in {".pyc", ".pyo"}:
        return True
    return False


def _git_visible_files(root: Path) -> list[Path] | None:
    if not (root / ".git").exists() or shutil.which("git") is None:
        return None
    cp = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        return None
    rows = []
    for raw in cp.stdout.split(b"\0"):
        if not raw:
            continue
        rel = Path(raw.decode("utf-8", "surrogateescape"))
        path = root / rel
        if path.is_file() and not _excluded(rel):
            rows.append(rel)
    return sorted(set(rows), key=lambda p: p.as_posix())


def package_files(root: Path) -> list[Path]:
    git_files = _git_visible_files(root)
    if git_files is not None:
        return git_files
    rows = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _excluded(rel):
            continue
        rows.append(rel)
    return sorted(rows, key=lambda p: p.as_posix())


def build_manifest(root: Path) -> dict:
    files = []
    for rel in package_files(root):
        data = (root / rel).read_bytes()
        files.append({
            "path": rel.as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "format": FORMAT,
        "suite_version": _suite_version(root),
        "files": files,
    }


def _describe_diff(current: dict, expected: dict) -> list[str]:
    current_rows = {x.get("path"): x for x in current.get("files", []) if isinstance(x, dict)}
    expected_rows = {x.get("path"): x for x in expected.get("files", []) if isinstance(x, dict)}
    lines = []
    for path in sorted(set(expected_rows) - set(current_rows)):
        lines.append(f"missing from manifest: {path}")
    for path in sorted(set(current_rows) - set(expected_rows)):
        lines.append(f"no longer present: {path}")
    for path in sorted(set(current_rows) & set(expected_rows)):
        if current_rows[path] != expected_rows[path]:
            lines.append(f"changed: {path}")
    if current.get("suite_version") != expected.get("suite_version"):
        lines.append("suite_version differs")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh or verify LevelUpDiag-MediKristal suite-manifest.json")
    parser.add_argument("--check", action="store_true", help="Do not write; fail if the manifest is stale")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    path = root / "suite-manifest.json"
    expected = build_manifest(root)

    if args.check:
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"suite manifest unreadable: {exc}")
            return 1
        if current == expected:
            print(f"suite manifest OK ({len(expected['files'])} files)")
            return 0
        print("suite manifest is stale")
        for line in _describe_diff(current, expected)[:40]:
            print(f" - {line}")
        print("Run: python tools/refresh_suite_manifest.py")
        return 1

    path.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"refreshed {path.name}: {len(expected['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
