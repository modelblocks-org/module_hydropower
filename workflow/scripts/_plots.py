"""Reusable collection of plot functions."""

def draw_empty(ax, title, message="No data available"):
    """Helper to render an empty-data placeholder."""
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, alpha=0.7)
    ax.set_title(title)
    ax.set_axis_off()
