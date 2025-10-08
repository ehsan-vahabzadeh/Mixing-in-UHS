import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- paths ----------
INPUT_DIR   = r"Y:\Mixing Results\July"
MASTER_CSV  = os.path.join(INPUT_DIR, "consolidated_output - Final.csv")
SCEN_GLOB   = os.path.join(INPUT_DIR, "optimal_plan_CL*_TWh*.xlsx")

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
dfm["Depth_est [m]"]      = (dfm[COL_P_MPA] / MPA_PER_M).round(0)

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
def compare_box_violin(df_all, df_sel, col, ylabel, title, show_violin=True):
    a = pd.to_numeric(df_all[col], errors="coerce").dropna()
    s = pd.to_numeric(df_sel[col], errors="coerce").dropna()

    fig, ax = plt.subplots(figsize=(7.8, 7.8))

    # --- side-by-side boxplots ---
    bp = ax.boxplot(
        [a, s], positions=[1, 2], widths=0.55, showmeans=True, meanline=True,
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
        ("Depth_est [m]", "Depth (est) [m]"),
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
    "font.size": 18, "axes.labelsize": 18, "axes.titlesize": 18,
    "xtick.labelsize": 16, "ytick.labelsize": 16
})

def boxplot_param(series, ylabel, title, fname):
    s = pd.to_numeric(series, errors="coerce").dropna()
    plt.figure(figsize=(6.8, 7.2))
    plt.boxplot(s, vert=True, showmeans=True, meanline=True,
                boxprops=dict(linewidth=2), whiskerprops=dict(linewidth=2),
                capprops=dict(linewidth=2), medianprops=dict(linewidth=2),
                meanprops=dict(linewidth=2, color="C1"))
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    # plt.savefig(os.path.join(INPUT_DIR, fname), dpi=300)
    plt.show()

# boxplot_param(dfs[COL_PERM], "Permeability [mD]", "Selected reservoirs – Permeability", "box_perm.png")
# boxplot_param(dfs[COL_PORO], "Porosity [-]", "Selected reservoirs – Porosity", "box_poro.png")
# boxplot_param(dfs[COL_P_MPA], "Pressure [MPa]", "Selected reservoirs – Pressure", "box_pressure.png")
# boxplot_param(dfs["Depth_est [m]"], "Depth (estimated) [m]", "Selected reservoirs – Depth (est.)", "box_depth.png")
# # ==== make the comparison plots you asked for ====
# compare_box_violin(dfm, dfs, "Permeability [mD]",
#                    "Permeability [mD]", "Permeability: All vs Selected")

# compare_box_violin(dfm, dfs, "Porosity [-]",
#                    "Porosity [-]", "Porosity: All vs Selected")

# compare_box_violin(dfm, dfs, "Reservoir Pressure[MPa]",
#                    "Pressure [MPa]", "Pressure: All vs Selected")

# compare_box_violin(dfm, dfs, "Depth_est [m]",
#                    "Depth (estimated) [m]", "Depth: All vs Selected")

cols = {
    "Permeability [mD]": "Permeability [mD]",
    "Porosity [-]": "Porosity [-]",
    "Reservoir Pressure[MPa]": "Pressure [MPa]",
    "Depth_est [m]": "Depth (estimated) [m]",
}

# compute stats
summary = []
for c in cols.keys():
    all_vals = pd.to_numeric(dfm[c], errors="coerce").dropna()
    sel_vals = pd.to_numeric(dfs[c], errors="coerce").dropna()
    summary.append({
        "Parameter": cols[c],
        "All_mean": all_vals.mean(),
        "All_std": all_vals.std(),
        "Sel_mean": sel_vals.mean(),
        "Sel_std": sel_vals.std(),
    })
summary = pd.DataFrame(summary)

# plotting style
plt.rcParams.update({
    "font.size": 18,
    "axes.labelsize": 18,
    "axes.titlesize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 15,
})

# plot each parameter separately
for i, row in summary.iterrows():
    fig, ax = plt.subplots(figsize=(9, 3.5))

    # horizontal bars
    ax.barh(0, row["All_mean"], xerr=row["All_std"],
            color="lightgray", edgecolor="black",
            height=0.35, label="All reservoirs", capsize=5)
    ax.barh(1, row["Sel_mean"], xerr=row["Sel_std"],
            color="#1f77b4", edgecolor="black",
            height=0.35, label="Selected reservoirs", capsize=5)

    # labels and formatting
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["All", "Selected"])
    ax.set_xlabel(row["Parameter"])
    ax.set_title(f"{row['Parameter']} – Comparison")
    ax.grid(axis="x", alpha=0.3)

    # numeric labels
    ax.text(row["All_mean"] * 1.02, 0, f"{row['All_mean']:.2f}", va="center", fontsize=14)
    ax.text(row["Sel_mean"] * 1.02, 1, f"{row['Sel_mean']:.2f}", va="center", fontsize=14)

    plt.tight_layout()
    plt.show()