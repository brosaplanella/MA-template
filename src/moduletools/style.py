# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Consistent figure style for the notes and the sheets."""

from __future__ import annotations

import matplotlib as mpl
from cycler import cycler

from .palette import colours

# Text in the figures matches the PDF: a Palatino-like serif with Computer Modern maths.
# The first font found is used; DejaVu Serif ships with matplotlib, so there is always one.
SERIF = ["TeX Gyre Pagella", "Palatino Linotype", "Palatino", "Book Antiqua", "DejaVu Serif"]


def apply_style(brand_cycle: bool = False) -> None:
    """Apply the module figure style.

    brand_cycle=True draws lines in the brand colours (purple first). Most brand colours
    are light, so check that lines stay visible; the default keeps matplotlib's colours.
    """
    mpl.rcParams.update({
        "font.family":        "serif",
        "font.serif":         SERIF,
        "mathtext.fontset":   "cm",
        "font.size":          12,
        "axes.labelsize":     13,
        "axes.titlesize":     13,
        "xtick.labelsize":    11,
        "ytick.labelsize":    11,
        "lines.linewidth":    2.0,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
    })
    if brand_cycle:
        names = ["purple", "coral", "blue", "green", "lavender", "yellow"]
        mpl.rcParams["axes.prop_cycle"] = cycler(
            color=[colours[n] for n in names if n in colours]
        )
