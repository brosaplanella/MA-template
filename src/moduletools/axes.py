# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Axes helpers."""

from __future__ import annotations

import matplotlib as mpl


def set_zero_axes(ax, xlabel=None, ylabel=None):
    """
    Move the left and bottom spines to x=0 and y=0 (blackboard style),
    hide the top and right spines, and optionally add axis labels near
    the ends of the spines.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    xlabel : str, optional
        Label placed at the right end of the horizontal axis.
    ylabel : str, optional
        Label placed at the top end of the vertical axis.
    """
    ax.spines["left"].set_position("zero")
    ax.spines["bottom"].set_position("zero")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Hide the zero tick on both axes — its position is obvious from the spines
    ax.set_xticks([t for t in ax.get_xticks() if t != 0])
    ax.set_yticks([t for t in ax.get_yticks() if t != 0])

    # Re-place axis labels at the end of each spine instead of the edge
    if xlabel is not None:
        ax.set_xlabel("")   # clear the default label
        xmin, xmax = ax.get_xlim()
        ymin, _    = ax.get_ylim()
        ax.annotate(
            xlabel,
            xy=(xmax, 0), xycoords="data",
            xytext=(6, 0), textcoords="offset points",
            ha="left", va="center", fontsize=mpl.rcParams["axes.labelsize"],
        )

    if ylabel is not None:
        ax.set_ylabel("")   # clear the default label
        _, ymax = ax.get_ylim()
        ax.annotate(
            ylabel,
            xy=(0, ymax), xycoords="data",
            xytext=(0, 6), textcoords="offset points",
            ha="center", va="bottom", fontsize=mpl.rcParams["axes.labelsize"],
        )
