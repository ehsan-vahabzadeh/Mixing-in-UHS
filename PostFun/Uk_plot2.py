import os
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

# Master list containing *all* reservoirs (selected + not selected)
ALL_FIELDS_CSV = r"Y:\Mixing Results\July\consolidated_output - Final.csv"  # <-- change if needed

TARGET_BASE_COLORS = {
    5:   "#24854e",
    15:  "#2b8cbe",
    50:  "#f28e2b",
    100: "#7b52ab",
    150: "#d62728",
    200: "#8c564b",
}

MAX_SELECT_PER_TARGET = 6  # adjust if your true max differs

FRAC_BINS = np.array([0.00, 0.01, 0.03, 0.06, 0.10, np.inf])
SIZE_VALUES = np.array([100, 250, 500, 800, 1200])

ALPHA_SEL = 0.85
ALPHA_ALL = 0.35
EDGE_LW = 0.6

EXTENT =[-5.5, 4, 52.5, 55]

# =======================
# HELPERS
# =======================
def norm_name(x: str) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip().lower()

def make_discrete_white_to_color(base_hex: str, n=9):
    cont = LinearSegmentedColormap.from_list("w2c", ["#ffffff", base_hex], N=256)
    cols = [cont(i/(n-1)) for i in range(n)]
    cmap = ListedColormap(cols, name=f"w2{base_hex}")
    bounds = np.arange(0.5, n + 1.5, 1.0)
    norm = BoundaryNorm(bounds, cmap.N)
    return cmap, norm

def count_to_level(count, max_count=6, nlevels=9):
    if count <= 0 or not np.isfinite(count):
        return np.nan
    level = int(np.ceil((count / max_count) * nlevels))
    return int(np.clip(level, 1, nlevels))

def frac_to_size(frac):
    if not np.isfinite(frac):
        return np.nan
    idx = np.digitize([frac], FRAC_BINS, right=False)[0] - 1
    idx = int(np.clip(idx, 0, len(SIZE_VALUES)-1))
    return float(SIZE_VALUES[idx])

def add_basemap(ax):
    ax.add_feature(cfeature.LAND, facecolor="#f3f3f3", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#dbe9ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.6, zorder=1)
    ax.add_feature(cfeature.BORDERS, linewidth=0.4, zorder=1)
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    ax.gridlines(draw_labels=False, linewidth=0.3, color="gray", alpha=0.35, linestyle="--")
    return ax

# =======================
# LOAD DATA
# =======================
df_sum = pd.read_csv(SUMMARY_CSV, encoding="cp1252")
df_all = pd.read_csv(ALL_FIELDS_CSV, encoding="cp1252")

# --- normalize columns in df_sum ---
rename_map = {}
for c in df_sum.columns:
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

df_sum = df_sum.rename(columns=rename_map)

# --- normalize columns in df_all ---
rename_all = {}
for c in df_all.columns:
    cn = c.strip().lower()
    if cn in ["field", "field name", "field_name", "reservoir", "reservoir_name"]:
        rename_all[c] = "reservoir"
    if cn == "latitude":
        rename_all[c] = "Latitude"
    if cn == "longitude":
        rename_all[c] = "Longitude"

df_all = df_all.rename(columns=rename_all)

# Keep only what we need
df_all = df_all[["reservoir", "Latitude", "Longitude"]].copy()

# Clean numeric
for col in ["Latitude", "Longitude"]:
    df_all[col] = pd.to_numeric(df_all[col], errors="coerce")
df_all = df_all.dropna(subset=["Latitude", "Longitude"])

df_sum["target_twh"] = pd.to_numeric(df_sum["target_twh"], errors="coerce")
df_sum["count"] = pd.to_numeric(df_sum["count"], errors="coerce")
df_sum["Latitude"] = pd.to_numeric(df_sum.get("Latitude"), errors="coerce")
df_sum["Longitude"] = pd.to_numeric(df_sum.get("Longitude"), errors="coerce")
df_sum["frac_median"] = pd.to_numeric(df_sum.get("frac_median"), errors="coerce")

# If summary doesn't have coords, merge from df_all
df_sum["reservoir_norm"] = df_sum["reservoir"].apply(norm_name)
df_all["reservoir_norm"] = df_all["reservoir"].apply(norm_name)

df_sum = df_sum.merge(
    df_all[["reservoir_norm", "Latitude", "Longitude"]],
    on="reservoir_norm",
    how="left",
    suffixes=("", "_all")
)

# Fill coords if missing
df_sum["Latitude"] = df_sum["Latitude"].fillna(df_sum["Latitude_all"])
df_sum["Longitude"] = df_sum["Longitude"].fillna(df_sum["Longitude_all"])
df_sum = df_sum.drop(columns=[c for c in df_sum.columns if c.endswith("_all")])

df_sum = df_sum.dropna(subset=["target_twh", "count", "Latitude", "Longitude"])

targets = sorted(df_sum["target_twh"].dropna().unique())

# =======================
# PLOT PER TARGET
# =======================
for t in targets:
    t_int = int(t)
    base_color = TARGET_BASE_COLORS.get(t_int, "#2ca25f")
    cmap, norm = make_discrete_white_to_color(base_color, n=9)

    # Build per-target selection table
    sel = df_sum[df_sum["target_twh"] == t].copy()
    sel = sel[sel["count"] >= 1].copy()

    # IMPORTANT: frac_median should already be "fraction of target"
    # If yours is median produced TWh, then uncomment this line:
    # sel["frac_median"] = sel["frac_median"] / float(t)

    # Create a per-target dataframe that includes ALL reservoirs:
    all_t = df_all.copy()
    all_t = all_t.merge(
        sel[["reservoir_norm", "count", "frac_median"]],
        on="reservoir_norm",
        how="left"
    )
    all_t["count"] = all_t["count"].fillna(0)
    all_t["frac_median"] = all_t["frac_median"].fillna(0.0)

    # Separate selected vs not selected
    not_sel = all_t[all_t["count"] <= 0].copy()
    dft = all_t[all_t["count"] >= 1].copy()

    # Map colour level and marker size for selected
    dft["level"] = dft["count"].apply(lambda c: count_to_level(c, max_count=MAX_SELECT_PER_TARGET, nlevels=9))
    dft["frac_median"] = (dft["frac_median"] / t) 
    dft["msize"] = dft["frac_median"].apply(frac_to_size)
    dft = dft.dropna(subset=["level", "msize"])
    
    # Rank top 5 by "combined frequency and median value"
    # Simple, transparent: score = count * frac_median
    dft["score"] = dft["count"] * dft["frac_median"]
    dft["reservoir_plot"] = (
    dft["reservoir"]
      .astype(str)
      .str.replace(r"\bgas\s*field\b", "", regex=True)
      .str.replace(r"\s+", " ", regex=True)
      .str.strip(" ,-_")
)
    top5 = dft.sort_values("score", ascending=False).head(5)

    fig = plt.figure(figsize=(20, 5))
    ax = plt.axes(projection=ccrs.Mercator())
    add_basemap(ax)

    # 1) Plot ALL reservoirs as grey dots (unselected)
    ax.scatter(
        not_sel["Longitude"].values,
        not_sel["Latitude"].values,
        s=18,
        color="#666666",
        alpha=ALPHA_ALL,
        edgecolor="none",
        transform=ccrs.PlateCarree(),
        zorder=2
    )

    # 2) Plot selected reservoirs as colored bubbles
    sc = ax.scatter(
        dft["Longitude"].values,
        dft["Latitude"].values,
        s=dft["msize"].values,
        c=dft["level"].values,
        cmap=cmap,
        norm=norm,
        alpha=ALPHA_SEL,
        edgecolor="k",
        linewidth=EDGE_LW,
        transform=ccrs.PlateCarree(),
        zorder=3
    )
    ax.scatter(
    top5["Longitude"].values,
    top5["Latitude"].values,
    s=top5["msize"].values * 1.15,      # tiny bump so ring sits outside
    facecolors="none",                  # ring only
    edgecolors="k",
    linewidths=1.5,                     # <-- bold outline
    alpha=1.0,
    transform=ccrs.PlateCarree(),
    zorder=4
    )
    # 3) Annotate top 5
    # Small offsets so text doesn't sit on the marker
    for _, r in top5.iterrows():
        ax.text(
        r["Longitude"] + 0.11, r["Latitude"] + 0.07,  # small offset
        str(r["reservoir_plot"]),
        transform=ccrs.PlateCarree(),
        fontsize=16,
        zorder=5
    )

    # Discrete colourbar
    cbar = plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.025,
                        fraction=0.04, aspect=30, location="top")
    cbar.set_label("Selection frequency [-]", fontsize=18)
    cbar.set_ticks([1, 3, 5, 7, 9])
    cbar.ax.tick_params(labelsize=18)

    # plt.title(f"UK reservoirs selected under {t_int} TWh target (top 5 annotated)", fontsize=14, pad=10)
    plt.tight_layout()

    out = os.path.join(INPUT_DIR, f"uk_map_target_{t_int}TWh_with_all_and_top5.png")
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.show()
    print(f"Saved: {out}")
