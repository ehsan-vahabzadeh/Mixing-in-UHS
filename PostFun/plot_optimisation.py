import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- user settings ----------------
INPUT_DIR    = r"Y:\Mixing Results\July"

FILES = [
    "optimal_plan_CL14_TWh5.xlsx",
    "optimal_plan_CL60_TWh15.xlsx",
    "optimal_plan_CL180_TWh50.xlsx",
    "optimal_plan_CL360_TWh100.xlsx",
    "optimal_plan_CL360_TWh150.xlsx",
    "optimal_plan_CL360_TWh200.xlsx",
]
# Or glob:
# GLOB_PATTERN = "optimal_plan_CL*_TWh*.xlsx"
GLOB_PATTERN = None

YEAR_MARKS = np.array([30], dtype=int)

SCEN_COL_LABEL = "Scenario"
LOSS_LABEL = r"Optimal Loss Cost ($\times 10^9$ USD)"
LCOS_LABEL     = "LCOS ($\$$/MWh)"
# ------------------------------------------------

# columns (multi-name tolerant)
COL_INJ_TWH = "Cum H2 Injected [Twh]"
COL_PRO_TWH = "Cum H2 Produced [Twh]"            # nominal
COL_PRO_TWH_PV = "Produced TWh (PV total)"       # preferred if present
COL_LCOS    = "LCOS"
COL_WELLS   = "Number of Wells"

LOSS_CANDIDATES = ["Loss Cost [M$]", "Loss Cost [$]", "Loss Cost [£]", "Loss Cost [M£]"]

def parse_CL(fname):
    m = re.search(r"CL(\d+)", fname)
    return int(m.group(1)) if m else None

def label_from_filename(fname: str) -> str:
    m = re.search(r"CL(\d+)_TWh(\d+)", fname)
    # return f"{m.group(1)} d–{m.group(2)} TWh" if m else os.path.splitext(fname)[0]
    return f"{m.group(2)} TWh" if m else os.path.splitext(fname)[0]
def pick_loss_column(df: pd.DataFrame) -> str:
    for c in LOSS_CANDIDATES:
        if c in df.columns:
            return c
    raise KeyError(f"No loss column found among {LOSS_CANDIDATES}. Got: {list(df.columns)[:10]} ...")

def aggregate_plan_rows(df_sheet: pd.DataFrame) -> dict:
    """Aggregate one sheet (one year for a scenario) to plan-level totals."""
    # loss cost (sum across selected assets)
    loss_col = pick_loss_column(df_sheet)
    loss_vals = pd.to_numeric(df_sheet[loss_col], errors="coerce")/1e3
    total_loss = loss_vals.sum(min_count=1)

    # energy weights (prefer PV energy if present)
    if COL_PRO_TWH_PV in df_sheet.columns:
        w = pd.to_numeric(df_sheet[COL_PRO_TWH_PV], errors="coerce").fillna(0.0)
    else:
        w = pd.to_numeric(df_sheet.get(COL_PRO_TWH), errors="coerce").fillna(0.0)

    # plan LCOS: energy-weighted mean (fallback to simple mean if all weights are zero)
    lcos_vals = pd.to_numeric(df_sheet.get(COL_LCOS), errors="coerce")
    if (w > 0).any() and lcos_vals.notna().any():
        plan_lcos = (lcos_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
    else:
        plan_lcos = lcos_vals.mean() if lcos_vals.notna().any() else np.nan

    return {
        LOSS_LABEL: total_loss,
        LCOS_LABEL: plan_lcos,
        "wells": pd.to_numeric(df_sheet.get(COL_WELLS), errors="coerce").sum(min_count=1)
    }

def snap_cycle_to_year(cycle: int, cl_days: int, year_marks: np.ndarray) -> int:
    year_raw = cycle * (cl_days / 360.0)
    return int(year_marks[np.abs(year_marks - year_raw).argmin()])

def collect_long_dataframe(input_dir: str, files: list, glob_pat: str | None) -> pd.DataFrame:
    if glob_pat:
        file_list = sorted(glob.glob(os.path.join(input_dir, glob_pat)))
    else:
        file_list = [os.path.join(input_dir, f) for f in files]

    records = []
    for path in file_list:
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue

        xls = pd.ExcelFile(path)
        cl = parse_CL(os.path.basename(path))
        scen_label = label_from_filename(os.path.basename(path))

        # sheets are named "cycle_<n>"
        cyc_sheets = sorted(
            (int(m.group(1)), s)
            for s in xls.sheet_names
            for m in [re.match(r"^cycle_(\d+)$", s)]
            if m
        )

        for cyc, sname in cyc_sheets:
            df_sheet = pd.read_excel(xls, sheet_name=sname)
            agg = aggregate_plan_rows(df_sheet)
            year = snap_cycle_to_year(cyc, cl, YEAR_MARKS)

            rec = {
                SCEN_COL_LABEL: scen_label,
                "CL_days": cl,
                "cycle": cyc,
                "year": year,
                **agg
            }
            records.append(rec)

    if not records:
        raise RuntimeError("No scenarios loaded/aggregated.")

    df_long = pd.DataFrame.from_records(records)
    # keep only requested year marks (in case a sheet doesn’t align)
    df_long = df_long[df_long["year"].isin(YEAR_MARKS)].reset_index(drop=True)
    return df_long

# ----------- collect -----------
def collect_long_dataframe(input_dir: str, files: list, glob_pat: str | None) -> pd.DataFrame:
    if glob_pat:
        file_list = sorted(glob.glob(os.path.join(input_dir, glob_pat)))
    else:
        file_list = [os.path.join(input_dir, f) for f in files]

    records = []
    for path in file_list:
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue

        xls = pd.ExcelFile(path)
        cl = parse_CL(os.path.basename(path))
        scen_label = label_from_filename(os.path.basename(path))

        cyc_sheets = sorted(
            (int(m.group(1)), s)
            for s in xls.sheet_names
            for m in [re.match(r"^cycle_(\d+)$", s)]
            if m
        )

        for cyc, sname in cyc_sheets:
            df_sheet = pd.read_excel(xls, sheet_name=sname)
            agg = aggregate_plan_rows(df_sheet)

            year_raw = cyc * (cl / 360.0)  # no snapping
            rec = {
                SCEN_COL_LABEL: scen_label,
                "CL_days": cl,
                "cycle": cyc,
                "year_raw": year_raw,   # keep actual year value
                **agg
            }
            records.append(rec)

    if not records:
        raise RuntimeError("No scenarios loaded/aggregated.")

    df_long = pd.DataFrame.from_records(records)
    return df_long

# ----------- collect -----------
dfL = collect_long_dataframe(INPUT_DIR, FILES, GLOB_PATTERN)

# ----------- SCATTER: ALL points from ALL years & scenarios -----------
fig, ax = plt.subplots(figsize=(10, 6))
for scen, g in dfL.groupby(SCEN_COL_LABEL):
    ax.scatter(g[LOSS_LABEL], g[LCOS_LABEL], s=45, alpha=0.9, label=scen)

ax.set_title("LCOS vs Total Loss Cost — all years, coloured by Scenario")
ax.set_xlabel(LOSS_LABEL)
ax.set_ylabel(LCOS_LABEL)
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(title=SCEN_COL_LABEL, frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("scatter_loss_vs_lcos_all_years.png", dpi=300, bbox_inches="tight")
plt.show()

# ----------- plotting style -----------
plt.rcParams.update({
    "font.size": 20,
    "axes.labelsize": 20,
    "axes.titlesize": 20,
    "legend.fontsize": 18,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "lines.linewidth": 2.5,
    "lines.markersize": 6,
})

# ----------- 1) BOX: Total Loss Cost by Scenario -----------
def horizontal_boxplot(df, value_col, group_col, title, xlabel, outfile=None):
    order = (df.groupby(group_col)[value_col]
               .median()
               .sort_values(ascending=True)
               .index.tolist())
    data = [df.loc[df[group_col]==g, value_col].values for g in order]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(
        data, vert=False, labels=order, patch_artist=True,showfliers=False,
        medianprops={"color":"red", "linewidth":2},
        boxprops={"facecolor":"none", "edgecolor":"blue", "linewidth":2},
        whiskerprops={"color":"black", "linewidth":1.2},
        capprops={"color":"black", "linewidth":1.2},
        # flierprops={"marker":"o", "markersize":3, "markerfacecolor":"none", "markeredgecolor":"blue"}
    )
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Demand")
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    if outfile:
        fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.show()

horizontal_boxplot(
    dfL, LOSS_LABEL, SCEN_COL_LABEL,
    title="Distribution of Optimal Total Loss Cost by Scenario",
    xlabel=f"{LOSS_LABEL}",
    outfile="box_total_loss_by_scenario.png"
)

# ----------- 2) BOX: LCOS by Scenario -----------
horizontal_boxplot(
    dfL, LCOS_LABEL, SCEN_COL_LABEL,
    title="Distribution of LCOS by Scenario",
    xlabel=f"{LCOS_LABEL}",
    outfile="box_lcos_by_scenario.png"
)

# ----------- 3) SCATTER: Total Loss vs LCOS (coloured by Scenario) -----------
fig, ax = plt.subplots(figsize=(10, 6))
scenarios = dfL[SCEN_COL_LABEL].unique()
for scen in scenarios:
    g = dfL[dfL[SCEN_COL_LABEL]==scen]
    ax.scatter(g[LOSS_LABEL], g[LCOS_LABEL], s=45, alpha=0.9, label=scen)

ax.set_title("LCOS vs Total Loss Cost (coloured by Scenario)")
ax.set_xlabel(LOSS_LABEL)
ax.set_ylabel(f"{LCOS_LABEL} ($/MWh)")
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(title=SCEN_COL_LABEL, frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("scatter_loss_vs_lcos_by_scenario.png", dpi=300, bbox_inches="tight")
plt.show()
