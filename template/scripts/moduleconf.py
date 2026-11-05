# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Module settings and sheet layout, shared by the build scripts.

Reads _module.yml, then _local.yml on top (if present). Mirrors the rules in
_shared/common.lua (used by the Quarto filter); keep the two in sync:

    sheets/<kind>/<id>/<id>.qmd            questions
    sheets/<kind>/<id>/<id>-solutions.qmd  solutions

A setting is looked up in the sheet's own entry, then in the kind's `defaults`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the environment
    # Quarto may run the hooks with another Python (e.g. `py` on Windows): rerun
    # the same script with the project's environment if there is one.
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv.exists() and Path(sys.executable).resolve() != venv.resolve():
        sys.exit(subprocess.run([str(venv), *sys.argv]).returncode)
    sys.exit(
        "PyYAML is missing. Run `uv sync` once in the repository, then build with "
        "`uv run scripts/build.py`."
    )

KINDS = ("problem-sheets", "assignments")
BUILD = ROOT / "_build"

# Written by template.lua into every sheet: <meta name="ma-template"> in HTML,
# a MATemplate entry in the PDF info.
MARKER_RE = re.compile(
    rb"ma-template-doc kind=([\w-]+) id=([\w.-]+) role=(\w+) build=(\w+)"
)


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _merge(base: dict, top: dict) -> dict:
    for key, value in top.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load() -> dict:
    """The module settings: _module.yml with _local.yml merged on top."""
    return _merge(_read(ROOT / "_module.yml"), _read(ROOT / "_local.yml"))


def setting(conf: dict, kind: str, sheet_id: str, key: str):
    section = conf.get(kind) or {}
    entry = section.get(sheet_id) or {}
    if key in entry:
        return entry[key]
    return (section.get("defaults") or {}).get(key)


def is_released(conf: dict, kind: str, sheet_id: str) -> bool:
    return setting(conf, kind, sheet_id, "solutions-released") is True
