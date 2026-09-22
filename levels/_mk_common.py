from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

from levelupdiag_core.commands import run_command


def target(cfg) -> Path:
    return Path(cfg["_target_root"])


def tool(cfg) -> Path:
    return Path(cfg["_tool_root"])


def mkcfg(cfg) -> dict:
    return cfg.get("medikristal", {})


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def python_env(root: Path, extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(root / "backend") + os.pathsep + str(root)
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def operation_map(openapi: dict) -> dict[str, tuple[str, str, dict]]:
    out = {}
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            op_id = op.get("operationId")
            if op_id:
                out[op_id] = (method.upper(), path, op)
    return out


def copy_target_to_temp(root: Path) -> tuple[tempfile.TemporaryDirectory, Path]:
    holder = tempfile.TemporaryDirectory(prefix="levelupdiag-mk-")
    dst = Path(holder.name) / "MediKristal"
    ignore = shutil.ignore_patterns(
        ".git", ".levelupdiag", ".pytest_cache", "__pycache__", ".coverage",
        "*.pyc", "*.pyo", "*.egg-info", "build", "dist"
    )
    shutil.copytree(root, dst, ignore=ignore)
    return holder, dst


def run(root: Path, argv: list[str], *, cwd: Path | None = None, timeout: int = 180, env: dict | None = None):
    return run_command(
        argv,
        cwd=cwd or root,
        timeout_seconds=timeout,
        capture_limit_kb=256,
        env=env or python_env(root),
        redact_output=True,
    )


def parse_project(root: Path) -> dict:
    return tomllib.loads((root / "backend" / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def parse_pinned_requirements(path: Path) -> list[tuple[str, str]]:
    items = []
    rx = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s;]+)$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = rx.fullmatch(line)
        if not m:
            raise ValueError(f"un-pinned or unsupported requirement: {line}")
        items.append((re.sub(r"[-_.]+", "-", m.group(1)).lower(), m.group(2)))
    return items


def text_claims(text: str, pattern: str) -> list[int]:
    return [int(x) for x in re.findall(pattern, text, flags=re.IGNORECASE)]
