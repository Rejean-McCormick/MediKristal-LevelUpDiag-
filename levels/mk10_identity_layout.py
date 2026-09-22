from __future__ import annotations

import ast
import re
from pathlib import Path

from ._mk_common import mkcfg, parse_pinned_requirements, parse_project, target


def run(cfg, report):
    root = target(cfg)
    expected = mkcfg(cfg)
    required = [
        "backend/pyproject.toml", "backend/requirements.lock", "backend/alembic.ini",
        "backend/medikristal/app.py", "backend/medikristal/api.py", "backend/medikristal/db.py",
        "contracts/openapi.json", "contracts/domain.schema.json", "contracts/traceability.json",
        "frontend/index.html", "frontend/app.js", "frontend/styles.css",
        "deploy/docker-compose.yml", "backend/Dockerfile", "manifest.json", "sbom.cdx.json",
        "validation-report.json", "APP_VALIDATION.md", "VALIDATION.md", "docs/33-acceptance.md",
    ]
    missing = [p for p in required if not (root / p).is_file()]
    report.add("medikristal.layout.required_files", "FAIL" if missing else "PASS", "structure",
               "Required MediKristal delivery surfaces are present." if not missing else "Required MediKristal delivery files are missing.",
               evidence=missing or {"checked": len(required)})

    try:
        project = parse_project(root)
        ok = project.get("name") == expected.get("expected_project_name") and project.get("version") == expected.get("expected_version")
        py = str(project.get("requires-python", ""))
        ok_py = "3.12" in py
        report.add("medikristal.project.identity", "PASS" if ok and ok_py else "FAIL", "structure",
                   "Package identity/version/runtime match the MediKristal contract." if ok and ok_py else "Package metadata does not match expected MediKristal identity.",
                   evidence={"name": project.get("name"), "version": project.get("version"), "requires_python": py})
    except Exception as exc:
        report.add("medikristal.project.identity", "FAIL", "structure", "Unable to parse backend project metadata.", evidence=f"{type(exc).__name__}: {exc}")

    docs = sorted((root / "docs").glob("[0-9][0-9]-*.md"))
    nums = [int(re.match(r"(\d\d)-", p.name).group(1)) for p in docs if re.match(r"(\d\d)-", p.name)]
    exp_chapters = int(expected.get("expected_chapters", 33))
    report.add("medikristal.docs.numbered_chapters", "PASS" if nums == list(range(1, exp_chapters + 1)) else "FAIL", "structure",
               "Numbered documentation chapters are complete and contiguous." if nums == list(range(1, exp_chapters + 1)) else "Numbered documentation chapters are missing, duplicated or out of range.",
               evidence={"expected": exp_chapters, "actual": len(nums), "numbers": nums})

    try:
        reqs = parse_pinned_requirements(root / "backend" / "requirements.lock")
        report.add("medikristal.dependencies.pinned", "PASS" if reqs else "FAIL", "structure",
                   "All direct runtime dependencies are exactly pinned." if reqs else "No pinned runtime dependencies were found.",
                   evidence={"count": len(reqs), "requirements": [f"{n}=={v}" for n, v in reqs]})
    except Exception as exc:
        report.add("medikristal.dependencies.pinned", "FAIL", "structure", "Runtime dependency lock contains an unsupported or unpinned entry.", evidence=str(exc))

    syntax_errors = []
    count = 0
    for base in (root / "backend" / "medikristal", root / "tools", root / "scripts", root / "tests"):
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts or "build" in path.parts:
                continue
            count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as exc:
                syntax_errors.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})
    report.add("medikristal.python.syntax", "FAIL" if syntax_errors else "PASS", "structure",
               "All repository Python sources parse successfully." if not syntax_errors else "One or more Python sources fail to parse.",
               evidence={"files": count, "errors": syntax_errors[:50]})
    report.metrics.update({"required_files": len(required), "python_files_parsed": count, "chapters": len(nums)})
