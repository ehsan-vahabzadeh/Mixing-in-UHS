import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def make_size_legend_horizontal(
    SIZE_VALUES,
    labels,
    title="Average contribution (% of target)",
    outfile=None,
    dpi=300,
):
    """
    Standalone horizontal legend for marker sizes.
    SIZE_VALUES: list of marker areas (same 's=' units you used in scatter)
    labels:      list of strings (same length as SIZE_VALUES)
    """
    fig, ax = plt.subplots(figsize=(10, 1.4))
    ax.axis("off")

    # Empty scatter handles (facecolor none so it looks like outline circles)
    handles = [
        ax.scatter([], [], s=s, edgecolor="k", facecolor="none", linewidth=1.2)
        for s in SIZE_VALUES
    ]

    leg = ax.legend(
        handles, labels,
        title=title,
        loc="center",
        ncol=len(labels),
        frameon=False,
        framealpha=0.5,
        # spacing controls (these are the ones you want)
        columnspacing=2.0,
        labelspacing=1.2,
        handletextpad=0.8,
        borderpad=0.8,
        scatterpoints=1,
        fontsize=16,
    )

    # Optional: make title a bit smaller/cleaner
    leg.get_title().set_fontsize(16)

    if outfile:
        fig.savefig(outfile, dpi=dpi, bbox_inches="tight")
    return fig


def make_target_color_legend_horizontal_long(
    TARGET_LABELS,
    TARGET_COLORS,
    title="Annual delivery target",
    outfile=None,
    dpi=300,
):
    """
    Standalone horizontal legend with long colour rectangles.
    """
    # Wide + short figure for a horizontal legend strip
    fig, ax = plt.subplots(figsize=(12, 1.4))
    ax.axis("off")

    handles = [
        Patch(facecolor=TARGET_COLORS[l], edgecolor="k", alpha=0.7, label=l)
        for l in TARGET_LABELS
    ]

    leg = ax.legend(
        handles=handles,
        title=title,
        loc="center",
        ncol=len(TARGET_LABELS),
        frameon=False,
        framealpha=0.5,
        edgecolor="black",
        borderpad=0.8,
        columnspacing=1.6,
        labelspacing=1.0,
        handletextpad=0.7,
        # THESE control rectangle size
        handlelength=3.2,   # make rectangles longer
        handleheight=1.4,   # make rectangles taller
        fontsize=14,
    )
    leg.get_title().set_fontsize(16)

    if outfile:
        fig.savefig(outfile, dpi=dpi, bbox_inches="tight")
    return fig

# ------------------ Example usage ------------------

# 1) Size legend (use YOUR actual marker areas)
labels = ["<1%", "1–3%", "3–6%", "6–10%", ">10%"]
SIZE_VALUES = [100, 250, 500, 800, 1200]  # marker areas

make_size_legend_horizontal(
    SIZE_VALUES, labels,
    title="Average contribution [% of target]",
    outfile="legend_size_horizontal.png"
)

# 2) Target colour legend (rectangles)
TARGET_LABELS = ["5 TWh", "15 TWh", "50 TWh", "100 TWh", "150 TWh", "200 TWh"]
TARGET_COLORS = {
    "5 TWh":   "#24854e",  # green
    "15 TWh":  "#2b8cbe",  # blue
    "50 TWh":  "#f28e2b",  # orange
    "100 TWh": "#7b52ab",  # purple
    "150 TWh": "#d62728",  # red
    "200 TWh": "#8c564b",  # brown
}

make_target_color_legend_horizontal_long(
    TARGET_LABELS, TARGET_COLORS,
    title="Annual delivery target [Twh]",
    outfile="legend_targets_horizontal.png"
)

plt.show()
