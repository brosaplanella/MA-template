# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Generate the colour files from _shared/palette.yml.

    uv run scripts/palette.py

Writes _shared/generated/:
    palette.tex         \\definecolor for every colour and tint, plus the roles (accent, alert)
    theme-light.scss    HTML light theme (on top of Bootswatch flatly)
    theme-dark.scss     HTML dark theme (on top of Bootswatch darkly)

Runs before every render (Quarto pre-render hook) and only rewrites files that changed.
The generated files are committed, so a render works even without this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import moduleconf  # noqa: E402  (also makes sure PyYAML is available)
import yaml  # noqa: E402

SOURCE = moduleconf.ROOT / "_shared" / "palette.yml"
OUT = moduleconf.ROOT / "_shared" / "generated"
TINTS = (80, 60, 40, 20)
WHITE = "#FFFFFF"
DARK_BG = "#222222"  # body background of Bootswatch darkly
HEADER = "Generated from _shared/palette.yml by scripts/palette.py: do not edit."


def rgb(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"not a #RRGGBB colour: {hex_colour!r}")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def to_hex(channels) -> str:
    return "#" + "".join(f"{round(c):02X}" for c in channels)


def mix(colour: str, other: str, percent: float) -> str:
    """percent% of colour, the rest of other (like LaTeX colour!percent!other)."""
    p = percent / 100
    return to_hex(a * p + b * (1 - p) for a, b in zip(rgb(colour), rgb(other)))


def contrast(a: str, b: str) -> float:
    def lum(h):
        c = [v / 255 for v in rgb(h)]
        c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def load() -> tuple[dict[str, str], dict[str, str]]:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8")) or {}
    colours = {}
    for name, entry in (data.get("colours") or {}).items():
        value = (entry or {}).get("hex")
        if value:
            rgb(value)  # validate
            colours[name] = "#" + value.lstrip("#").upper()
    roles = {}
    for role, value in (data.get("roles") or {}).items():
        value = str(value)
        if value.startswith("#"):
            rgb(value)
            roles[role] = value.upper()
        elif value in colours:
            roles[role] = colours[value]
        else:
            sys.exit(f"palette.yml: role {role} uses unknown colour {value!r}")
    for role in ("accent", "accent-dark", "alert", "alert-dark"):
        if role not in roles:
            sys.exit(f"palette.yml: role {role} is missing")
    return colours, roles


def shades(colours: dict[str, str]) -> list[tuple[str, str]]:
    """(name, hex) for every colour and its tints: brand-purple, brand-purple-80, ..."""
    out = []
    for name, value in colours.items():
        out.append((f"brand-{name}", value))
        out += [(f"brand-{name}-{t}", mix(value, WHITE, t)) for t in TINTS]
    return out


def latex(colours, roles) -> str:
    lines = [f"% {HEADER}"]
    lines += [f"\\definecolor{{{n}}}{{HTML}}{{{h[1:]}}}" for n, h in shades(colours)]
    lines.append("% Roles")
    lines += [f"\\definecolor{{{r}}}{{HTML}}{{{roles[r][1:]}}}" for r in ("accent", "alert")]
    return "\n".join(lines) + "\n"


def scss(colours, roles, dark: bool) -> str:
    accent = roles["accent-dark" if dark else "accent"]
    alert = roles["alert-dark" if dark else "alert"]
    background = DARK_BG if dark else WHITE
    base = "darkly" if dark else "flatly"
    lines = [
        "/*-- scss:defaults --*/",
        f"// {HEADER}",
        f"// {'Dark' if dark else 'Light'} theme, on top of Bootswatch {base}.",
        f"$accent: {accent};",
        # Navbar and buttons keep the light accent in both modes (white text on it)
        f"$primary: {roles['accent']};",
        "$link-color: $accent;",
        "$headings-color: $accent;",
        "",
        "/*-- scss:rules --*/",
        ":root {",
    ]
    lines += [f"  --{n}: {h};" for n, h in shades(colours)]
    lines += [
        f"  --accent: {accent};",
        f"  --accent-soft: {mix(accent, background, 12)};",
        f"  --accent-border: {mix(accent, background, 50)};",
        f"  --alert: {alert};",
        "}",
    ]
    return "\n".join(lines) + "\n"


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    colours, roles = load()
    for role, background, label in (
        ("accent", WHITE, "white"),
        ("accent-dark", DARK_BG, "the dark background"),
        ("alert", WHITE, "white"),
        ("alert-dark", DARK_BG, "the dark background"),
    ):
        ratio = contrast(roles[role], background)
        if ratio < 4.5:
            print(
                f"WARNING palette.yml: {role} has contrast {ratio:.1f} on {label} "
                "(text needs at least 4.5)"
            )
    files = {
        "palette.tex": latex(colours, roles),
        "theme-light.scss": scss(colours, roles, dark=False),
        "theme-dark.scss": scss(colours, roles, dark=True),
    }
    for name, text in files.items():
        if write_if_changed(OUT / name, text):
            print(f"Colours updated: _shared/generated/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
