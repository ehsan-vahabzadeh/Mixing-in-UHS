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
]
greens = ["black", "peru", "darkseagreen", "mediumblue", "crimson"]
# Or glob:
# GLOB_PATTERN = "optimal_plan_CL*_TWh*.xlsx"
GLOB_PATTERN = None

YEAR_MARKS = np.array([1, 5, 10, 15, 20, 25, 30], dtype=int)
# ------------------------------------------------

# column names
COL_INJ_TWH = "Cum H2 Injected [Twh]"
COL_PRO_TWH = "Cum H2 Produced [Twh]"
COL_INJ_M3  = "Cum H2 Injected [m3]"
COL_PRO_M3  = "Cum H2 Produced [m3]"
COL_LCOS    = "LCOS"
COL_PERM    = "Permeability [mD]"
COL_WELLS   = "Number of Wells"
COL_CG      = "CG Ratio"
KWH_PER_M3  = 39.41 * 0.08988  # kWh per m3 at STP

def m3_to_TWh(m3):
    return m3 * KWH_PER_M3 / 1e9

def parse_CL(fname):
    m = re.search(r"CL(\d+)", fname)
    return int(m.group(1)) if m else None

def label_from_filename(fname: str) -> str:
    m = re.search(r"CL(\d+)_TWh(\d+)", fname)
    return f"CL{m.group(1)}–{m.group(2)} TWh" if m else os.path.splitext(fname)[0]

def aggregate_one_file(path: str) -> pd.DataFrame:
    """Return per-cycle aggregates for this scenario."""
    xls = pd.ExcelFile(path)
    cyc_sheets = sorted(
        (int(m.group(1)), s)
        for s in xls.sheet_names
        for m in [re.match(r"^cycle_(\d+)$", s)]
        if m
    )
    rows = []
    for cyc, sname in cyc_sheets:
        df = pd.read_excel(xls, sheet_name=sname)

        inj_twh = pd.to_numeric(df.get(COL_INJ_TWH), errors="coerce").sum(min_count=1)
        pro_twh = pd.to_numeric(df.get(COL_PRO_TWH), errors="coerce").sum(min_count=1)
        if not np.isfinite(inj_twh) or not np.isfinite(pro_twh):
            inj_twh = m3_to_TWh(pd.to_numeric(df[COL_INJ_M3], errors="coerce").sum())
            pro_twh = m3_to_TWh(pd.to_numeric(df[COL_PRO_M3], errors="coerce").sum())

        w = pd.to_numeric(df.get(COL_PRO_TWH), errors="coerce").fillna(0.0)
        if w.sum() == 0:
            w = pd.Series(np.ones(len(df)), index=df.index)

        lcos = pd.to_numeric(df[COL_LCOS], errors="coerce")
        perm = pd.to_numeric(df[COL_PERM], errors="coerce")
        cg   = pd.to_numeric(df[COL_CG],   errors="coerce")

        rows.append(dict(
            cycle=cyc,
            inj_twh=inj_twh,
            pro_twh=pro_twh,
            eff=(pro_twh / inj_twh) if inj_twh > 0 else np.nan,
            lcos=(lcos * w).sum() / w.sum(),
            wells=pd.to_numeric(df[COL_WELLS], errors="coerce").sum(),
            perm=(perm * w).sum() / w.sum(),
            cg=(cg * w).sum() / w.sum(),
        ))
    return pd.DataFrame(rows).sort_values("cycle").reset_index(drop=True)

def snap_cycles_to_years(df_cycles: pd.DataFrame, cl_days: int, year_marks: np.ndarray) -> pd.DataFrame:
    """
    Add 'year_raw' = cycle*CL/360 and 'year' = nearest YEAR_MARK.
    For each target year, keep the row whose cycle is closest to that year.
    """
    df = df_cycles.copy()
    df["year_raw"] = df["cycle"] * (cl_days / 360.0)
    # snap to nearest mark
    df["year"] = year_marks[np.abs(df["year_raw"].values[:, None] - year_marks).argmin(axis=1)]
    # choose closest row per snapped year
    df["dist"] = np.abs(df["year_raw"] - df["year"])
    idx = df.groupby("year")["dist"].idxmin()   # indices of closest cycles
    out = df.loc[idx].sort_values("year").drop(columns=["dist"]).reset_index(drop=True)
    return out

# ------------- collect scenarios -------------
if GLOB_PATTERN:
    file_list = sorted(glob.glob(os.path.join(INPUT_DIR, GLOB_PATTERN)))
else:
    file_list = [os.path.join(INPUT_DIR, f) for f in FILES]

scenarios = []
for f in file_list:
    if not os.path.exists(f):
        print(f"[skip] {f} not found")
        continue
    agg_cyc = aggregate_one_file(f)
    cl = parse_CL(os.path.basename(f))
    agg_year = snap_cycles_to_years(agg_cyc, cl, YEAR_MARKS)
    agg_year["scenario"] = label_from_filename(os.path.basename(f))
    scenarios.append(agg_year)

if not scenarios:
    raise RuntimeError("No scenarios loaded.")

# ----------- plotting style -----------
plt.rcParams.update({
    "font.size": 20,
    "axes.labelsize": 20,
    "axes.titlesize": 20,
    "legend.fontsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "lines.linewidth": 3,
    "lines.markersize": 7,
})

def plot_one(metric_key, ylabel, title):
    plt.figure(figsize=(9.5, 6.2))
    for i, df in enumerate(scenarios):
        s = df["scenario"].iloc[0]
        plt.plot(df["year"], df[metric_key], marker="o", label=s,color = greens[i])
    plt.xlabel("Years")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(YEAR_MARKS)
    plt.grid(alpha=0.35)
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.show()

# ========== Figures (vs. years) ==========
plot_one("eff",   "Efficiency (Produced / Injected) [-]", "Scenario efficiency vs. years")
plot_one("lcos",  "LCOS [$/MWh]",                         "LCOS vs. years (energy-weighted)")
plot_one("wells", "Total wells selected [-]",             "Wells vs. years")
plot_one("perm",  "Average permeability [mD]",            "Permeability vs. years")
plot_one("cg",    "Average cushion-gas ratio [-]",        "Cushion-gas ratio vs. years")
