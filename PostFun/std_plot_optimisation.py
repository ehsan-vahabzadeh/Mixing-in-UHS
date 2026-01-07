import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ---------- paths ----------
INPUT_DIR   = r"Y:\Mixing Results\July"
INPUT_DIR_all   = r"Y:\Mixing Results\July\Two Term Equation"
MASTER_CSV  = os.path.join(INPUT_DIR, "consolidated_output - Final.csv")
SCEN_GLOB   = os.path.join(INPUT_DIR_all, "optimal_plan_CL*_TWh*_Low_H24.0.xlsx")

# ---------- columns in master ----------
COL_FIELD   = "Field Name"
COL_PORO    = "Porosity [-]"
COL_PERM    = "Permeability [mD]"
COL_P_MPA   = "Reservoir Pressure[MPa]"
COL_T_C     = "Reservoir Temp [C]"

# ---------- columns in scenarios ----------
COL_FLOW    = "Flow Rate [sm3/d]"   # from the optimized sheets
COL_WELLS   = "Number of Wells"

# ---------- depth estimate (very rough) ----------
# hydrostatic ~ 0.010 MPa/m (10 MPa per km). Adjust if you prefer.
MPA_PER_M   = 0.010

# =========================================================
# 1) Load master reservoir attributes
# =========================================================
dfm = pd.read_csv(MASTER_CSV, encoding="cp1252", thousands=",")
for c in [COL_PORO, COL_PERM, COL_P_MPA, COL_T_C]:
    dfm[c] = pd.to_numeric(dfm[c], errors="coerce")

# drop rows missing the basics
dfm = dfm.dropna(subset=[COL_FIELD, COL_PERM, COL_PORO, COL_P_MPA]).copy()
dfm["Reservoir Temp [K]"] = dfm[COL_T_C] + 273.15
dfm["Depth [m]"]      = (dfm[COL_P_MPA] / MPA_PER_M).round(0)

# =========================================================
# 2) Union of selected fields across all scenarios & cycles
# =========================================================
selected_fields = set()
flow_samples    = []

xlsx_paths = sorted(glob.glob(SCEN_GLOB))
for path in xlsx_paths:
    xls = pd.ExcelFile(path)
    cyc_sheets = [s for s in xls.sheet_names if re.match(r"^cycle_\d+$", s)]
    for s in cyc_sheets:
        df = pd.read_excel(xls, sheet_name=s)
        if COL_FIELD in df.columns:
            selected_fields.update(df[COL_FIELD].dropna().astype(str).tolist())
        # store flow rates from chosen rows (if present)
        if COL_FLOW in df.columns:
            flow_samples.extend(pd.to_numeric(df[COL_FLOW], errors="coerce").dropna().tolist())

selected_fields = {f.strip() for f in selected_fields if f and f == f}  # clean

# subset master to selected
dfs = dfm[dfm[COL_FIELD].isin(selected_fields)].copy()

# =========================================================
# 3) Stats helper
# =========================================================
def stats_series(s: pd.Series):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return dict(n=0, mean=np.nan, std=np.nan, min=np.nan, max=np.nan)
    return dict(n=len(s), mean=s.mean(), std=s.std(ddof=1), min=s.min(), max=s.max())
def compare_box_violin(df_all, df_sel, col, ylabel, title, show_violin=False):
    a = pd.to_numeric(df_all[col], errors="coerce").dropna()
    s = pd.to_numeric(df_sel[col], errors="coerce").dropna()

    fig, ax = plt.subplots(figsize=(7.8, 7.8))

    # --- side-by-side boxplots ---
    bp = ax.boxplot(
        [a, s], positions=[1, 2], widths=0.55, showmeans=True, meanline=True, vert=False, orientation="horizontal",
        boxprops=dict(linewidth=2), whiskerprops=dict(linewidth=2),
        capprops=dict(linewidth=2), medianprops=dict(linewidth=2),
        meanprops=dict(linewidth=2, color="C1"),
        labels=["All reservoirs", "Selected"],
    )

    # --- optional translucent violins for distribution shape ---
    if show_violin:
        parts = ax.violinplot(
            [a, s], positions=[1, 2], widths=0.7, showmeans=False, showmedians=False
        )
        # color the violins (light)
        for i, body in enumerate(parts['bodies'], start=1):
            body.set_facecolor("C0" if i == 1 else "C3")
            body.set_alpha(0.25)
            body.set_edgecolor("none")

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.show()
def summarize_block(df: pd.DataFrame, label: str):
    rows = []
    for col, nice in [
        (COL_PERM, "Permeability [mD]"),
        (COL_PORO, "Porosity [-]"),
        (COL_P_MPA, "Pressure [MPa]"),
        ("Reservoir Temp [K]", "Temperature [K]"),
        ("Depth [m]", "Depth [m]"),
    ]:
        st = stats_series(df[col])
        rows.append([nice, st["n"], st["mean"], st["std"], st["min"], st["max"]])
    # flows (from scenarios)
    stf = stats_series(pd.Series(flow_samples))
    rows.append(["Flow Rate [sm3/d] (from selections)", stf["n"], stf["mean"], stf["std"], stf["min"], stf["max"]])
    out = pd.DataFrame(rows, columns=["Parameter", "N", f"{label} Mean", f"{label} Std", f"{label} Min", f"{label} Max"])
    return out

sel_summary = summarize_block(dfs, "Selected")
all_summary = summarize_block(dfm, "All")

# merge for a neat side-by-side table
summary = sel_summary.merge(all_summary, on=["Parameter","N"], how="outer", suffixes=("",""))
print("\n=== Summary (Selected across ALL scenarios vs. All reservoirs) ===")
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
print(summary.to_string(index=False))

# =========================================================
# 4) Boxplots (presentation ready) over SELECTED reservoirs
# =========================================================
plt.rcParams.update({
    "font.size": 20, "axes.labelsize": 20, "axes.titlesize": 20,
    "xtick.labelsize": 20, "ytick.labelsize": 20
})
def overlay_horizontal_boxplots(df_all, df_sel, var_name="Porosity [-]"):
    # y positions so the boxes are "on top of each other"
    all_vals = pd.to_numeric(df_all[var_name], errors="coerce").dropna()
    sel_vals = pd.to_numeric(df_sel[var_name], errors="coerce").dropna()
    y0 = 1.0
    offset = 0.10
    pos_all = y0 + offset
    pos_sel = y0 - offset

    fig, ax = plt.subplots(figsize=(15, 5), dpi=140)

    # Common styling
    box_kws = dict(vert=False, widths=0.18, patch_artist=True,
                   showmeans=True, meanline=True, showfliers=True)

    # All reservoirs (blue, with dashed mean)
    b1 = ax.boxplot(all_vals, positions=[pos_all], **box_kws,
                    boxprops=dict(facecolor="#4C78A8", alpha=0.35, edgecolor="black", linewidth=1.8),
                    whiskerprops=dict(color="black", linewidth=1.6),
                    capprops=dict(color="black", linewidth=1.6),
                    medianprops=dict(color="black", linewidth=2.2),          # solid median line
                    # meanprops=dict(color="#1f3a93", linestyle="--", linewidth=2.0),  # dashed mean line
                    flierprops=dict(marker="o", markersize=4, markerfacecolor="#4C78A8", alpha=0.6, markeredgecolor="none"))

    # Selected (red, with dashed mean)
    b2 = ax.boxplot(sel_vals, positions=[pos_sel], **box_kws,
                    boxprops=dict(facecolor="#E45756", alpha=0.35, edgecolor="black", linewidth=1.8),
                    whiskerprops=dict(color="black", linewidth=1.6),
                    capprops=dict(color="black", linewidth=1.6),
                    medianprops=dict(color="black", linewidth=2.2),
                    # meanprops=dict(color="#9b1c1c", linestyle="--", linewidth=2.0),
                    flierprops=dict(marker="o", markersize=4, markerfacecolor="#E45756", alpha=0.6, markeredgecolor="none"))

    # Y axis: a single tick label for the variable
    # ax.set_yticks([y0])
    # ax.set_yticklabels([var_name])
    if var_name.lower().startswith("permeability"):
        ax.set_xscale("log")
        ax.set_xlabel(f"{var_name} (log scale)")
    # X label, limits, grid, legend
    ax.set_xlabel(var_name)
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True) 
    ax.get_yaxis().set_visible(False)
    # Legend
    # handles = [Patch(facecolor="#4C78A8", alpha=0.35, edgecolor="black", label="All reservoirs"),
    #            Patch(facecolor="#E45756", alpha=0.35, edgecolor="black", label="Selected")]
    # ax.legend(handles=handles, loc="lower right", frameon=True)

    # plt.tight_layout()
    plt.show()
# # ==== make the comparison plots you asked for ====
# compare_box_violin(dfm, dfs, "Permeability [mD]",
#                    "Permeability [mD]", "Permeability: All vs Selected")
overlay_horizontal_boxplots(dfm, dfs, "Permeability [mD]")
overlay_horizontal_boxplots(dfm, dfs, "Porosity [-]")
overlay_horizontal_boxplots(dfm, dfs, "Reservoir Pressure[MPa]")
overlay_horizontal_boxplots(dfm, dfs, "Depth [m]")
# compare_box_violin(dfm, dfs, "Porosity [-]",
#                    "Porosity [-]", "Porosity: All vs Selected")

# compare_box_violin(dfm, dfs, "Reservoir Pressure[MPa]",
#                    "Pressure [MPa]", "Pressure: All vs Selected")

# compare_box_violin(dfm, dfs, "Depth_est [m]",
#                    "Depth (estimated) [m]", "Depth: All vs Selected")
