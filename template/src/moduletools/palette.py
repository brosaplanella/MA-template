# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""The module colours from _shared/palette.yml, for use in figures.

    colours["purple"]       "#440379"
    tint("coral", 60)       60% coral mixed with white, as in the PDF/HTML palette
"""

from __future__ import annotations

from pathlib import Path

import yaml

PALETTE = Path(__file__).resolve().parents[2] / "_shared" / "palette.yml"


def _load() -> dict[str, str]:
    data = yaml.safe_load(PALETTE.read_text(encoding="utf-8")) or {}
    out = {}
    for name, entry in (data.get("colours") or {}).items():
        value = (entry or {}).get("hex")
        if value:
            out[name] = "#" + value.lstrip("#").upper()
    return out


colours: dict[str, str] = _load()


def tint(name: str, percent: float) -> str:
    """percent% of a palette colour, the rest white (100 = the colour itself)."""
    h = colours[name].lstrip("#")
    p = percent / 100
    return "#" + "".join(
        f"{round(int(h[i:i + 2], 16) * p + 255 * (1 - p)):02X}" for i in (0, 2, 4)
    )
