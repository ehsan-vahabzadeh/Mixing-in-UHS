import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.colors import LinearSegmentedColormap, ListedColormap, BoundaryNorm

# =======================
# SETTINGS
# =======================
INPUT_DIR = r"Y:\Mixing Results\July\Two Term Equation\_map_inputs"
SUMMARY_CSV = os.path.join(INPUT_DIR, "per_target_reservoir_summary.csv")

# Different base colour per target (white -> colour)
TARGET_BASE_COLORS = {
    5:   "#24854e",  # green
    15:  "#2b8cbe",  # blue
    50:  "#f28e2b",  # orange
    100: "#7b52ab",  # purple
    150: "#d62728",  # red
    200: "#8c564b",  # brown
}
# TARGET_BASE_COLORS = {
#     5:   "#470000",  # green
#     15:  "#790c01",  # blue
#     50:  "#a03508",  # orange
#     100: "#c9572a",  # purple
#     150: "#f27a4a",  # red
#     200: "#ffad79",  # brown
# }
# Max times a reservoir can be selected for ONE target (e.g. 9 scenarios? 6 scenarios? set it explicitly)
# If you used 9 economic scenarios per target, set MAX_SELECT_PER_TARGET = 9
MAX_SELECT_PER_TARGET = 9  # change to 9 if that's your true max

# 5 size bins for median contribution fraction (already normalised by target)
# Example: 0–1%, 1–3%, 3–6%, 6–10%, 10%+
FRAC_BINS = np.array([0.00, 0.01, 0.03, 0.06, 0.10, np.inf])
SIZE_VALUES = np.array([100, 250, 500, 800, 1200])  # marker areas

ALPHA = 0.8
EDGE_LW = 0.6

# UK-ish extent; expand west for offshore
EXTENT =[-5.5, 4, 52.5, 55]
# EXTENT =[-6.0, 4, 49.5, 60.5]  # expand south and north for offshore fields

# =======================
# HELPERS
# =======================
def make_discrete_white_to_color(base_hex: str, n=9):
    """Return a discrete (ListedColormap) with n steps from white -> base colour."""
    cont = LinearSegmentedColormap.from_list("w2c", [ "#ffffff", base_hex], N=256)
    cols = [cont(i/(n-1)) for i in range(n)]
    cmap = ListedColormap(cols, name=f"w2{base_hex}")
    bounds = np.arange(0.5, n + 1.5, 1.0)   # 0.5..9.5
    norm = BoundaryNorm(bounds, cmap.N)
    return cmap, norm

def count_to_level(count, max_count=6, nlevels=9):
    """Map count in [1..max_count] to discrete level in [1..nlevels]."""
    if count <= 0 or not np.isfinite(count):
        return np.nan
    level = int(np.ceil((count / max_count) * nlevels))
    return int(np.clip(level, 1, nlevels))

def frac_to_size(frac):
    """Map fraction to one of 5 marker sizes."""
    if not np.isfinite(frac):
        return np.nan
    idx = np.digitize([frac], FRAC_BINS, right=False)[0] - 1  # 0..4
    idx = int(np.clip(idx, 0, len(SIZE_VALUES)-1))
    return float(SIZE_VALUES[idx])

def add_basemap(ax):
    ax.add_feature(cfeature.LAND, facecolor="#f3f3f3", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#dbe9ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.6, zorder=1)
    ax.add_feature(cfeature.BORDERS, linewidth=0.4, zorder=1)
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    gl = ax.gridlines(draw_labels=False, linewidth=0.3, color="gray", alpha=0.35, linestyle="--")

    return ax

# =======================
# LOAD SUMMARY
# =======================
df = pd.read_csv(SUMMARY_CSV,  encoding='cp1252' )

# Expected columns (adapt if yours differ)
# reservoir / target_twh / count / frac_median / Latitude / Longitude
# If you used different names, rename them here.
rename_map = {}
for c in df.columns:
    cn = c.strip().lower()
    if cn in ["field", "field name", "field_name", "reservoir", "reservoir_name"]:
        rename_map[c] = "reservoir"
    if cn in ["target", "target_twh", "twh", "target demand", "target demand [twh]"]:
        rename_map[c] = "target_twh"
    if cn in ["count", "n_selected", "times_selected", "n_cases_selected"]:
        rename_map[c] = "count"
    if cn in ["produced_twh_mean"]:
        rename_map[c] = "frac_median"
    if cn == "latitude":
        rename_map[c] = "Latitude"
    if cn == "longitude":
        rename_map[c] = "Longitude"

df = df.rename(columns=rename_map)

needed = ["reservoir", "target_twh", "count", "Latitude", "Longitude"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns in summary CSV: {missing}\nColumns={list(df.columns)}")

# If frac_median is missing, try to build it from something sensible
if "frac_median" not in df.columns:
    # Try common alternatives (median produced TWh)
    candidates = [c for c in df.columns if "produced" in c.lower() and "median" in c.lower()]
    if candidates:
        prod_col = candidates[0]
        df["frac_median"] = pd.to_numeric(df[prod_col], errors="coerce") / pd.to_numeric(df["target_twh"], errors="coerce")
    else:
        raise ValueError("No frac_median column found, and no median produced column to derive it from.")

# Clean numeric
df["target_twh"] = pd.to_numeric(df["target_twh"], errors="coerce")
df["count"] = pd.to_numeric(df["count"], errors="coerce")
df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
df["frac_median"] = pd.to_numeric(df["frac_median"], errors="coerce")

# Keep only selected (count >= 1) and valid coords
df = df.dropna(subset=["target_twh", "count", "Latitude", "Longitude", "frac_median"])
df = df[df["count"] >= 1]

# =======================
# PLOT PER TARGET
# =======================
targets = sorted(df["target_twh"].unique())

for t in targets:
    base_color = TARGET_BASE_COLORS.get(int(t), "#2ca25f")  # default green
    cmap, norm = make_discrete_white_to_color(base_color, n=9)

    dft = df[df["target_twh"] == t].copy()

    # Colour levels 1..9 from count
    dft["level"] = dft["count"].apply(lambda c: count_to_level(c, max_count=MAX_SELECT_PER_TARGET, nlevels=9))

    # 5 marker sizes from frac_median (already normalised by target)
    dft["frac_median"] = dft["frac_median"] / df["target_twh"]
    dft["msize"] = dft["frac_median"].apply(frac_to_size)

    # drop anything that failed mapping
    dft = dft.dropna(subset=["level", "msize"])

    fig = plt.figure(figsize=(15, 5))
    ax = plt.axes(projection=ccrs.Mercator())
    add_basemap(ax)

    sc = ax.scatter(
        dft["Longitude"].values,
        dft["Latitude"].values,
        s=dft["msize"].values,
        c=dft["level"].values,
        cmap=cmap,
        norm=norm,
        alpha=ALPHA,
        edgecolor="k",
        linewidth=EDGE_LW,
        transform=ccrs.PlateCarree(),
        zorder=3
    )

    # Discrete colourbar 1..9
    cbar = plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.025, fraction=0.04, aspect=30, location="top")
    cbar.set_label("Selection frequency [-]", fontsize=18)
    cbar.set_ticks([1, 3, 5, 7, 9])
    cbar.ax.tick_params(labelsize=18) 

    # Size legend (5 bins)
    # Create dummy handles
    import matplotlib.lines as mlines
    labels = ["<1%", "1–3%", "3–6%", "6–10%", ">10%"]
    handles = []
    # for s, lab in zip(SIZE_VALUES, labels):
    #     handles.append(plt.scatter([], [], s=s, edgecolor="k", facecolor="none", linewidth=0.8, label=lab))
    # leg = ax.legend(handles=handles, title="Average contribution\n(% of target)", loc="lower left",
    #                 frameon=True,framealpha=0.5, labelspacing = 1.7, handleheight = 2.1, fontsize=14, title_fontsize=14)
    # leg.get_frame().set_edgecolor("black")

    plt.tight_layout()
    out = os.path.join(INPUT_DIR, f"uk_map_target_{int(t)}TWh.png")
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Saved: {out}")
