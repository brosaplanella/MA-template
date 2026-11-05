# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Figure helpers shared by the notes and the sheets.

In any code cell:

    import matplotlib.pyplot as plt
    from moduletools import apply_style, set_zero_axes, colours

    apply_style()                      # module-wide figure style
    fig, ax = plt.subplots()
    ax.plot(x, y, color=colours["purple"])
"""

from .axes import set_zero_axes
from .palette import colours, tint
from .style import apply_style

__all__ = ["apply_style", "colours", "set_zero_axes", "tint"]
