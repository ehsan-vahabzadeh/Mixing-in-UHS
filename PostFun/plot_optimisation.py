import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- user settings ----------------
INPUT_DIR    = r"Y:\Mixing Results\July"

# EITHER: list files explicitly
FILES = [
    "optimal_plan_CL14_TWh5.xlsx",
    "optimal_plan_CL60_TWh15.xlsx",
    "optimal_plan_CL180_TWh50.xlsx",
    "optimal_plan_CL360_TWh100.xlsx",
    "optimal_plan_CL360_TWh200.xlsx",
]

# OR: glob everything that matches
# GLOB_PATTERN = "optimal_plan_CL*_TWh*.xlsx"
GLOB_PATTERN = None
# ------------------------------------------------

# column names
COL_INJ_TWH = "Cum H2 Injected [Twh]"
COL_PRO_TWH = "Cum H2 Produced [Twh]"
COL_INJ_M3  = "Cum H2 Injected [m3]"
COL_PRO_M3  = "Cum H2 Produced [m3]"
COL_NET_M3  = "Net H2 Stored [m3]"
COL_LCOS    = "LCOS"
COL_PERM    = "Permeability [mD]"
COL_WELLS   = "Number of Wells"
COL_CG      = "CG Ratio"

KWH_PER_M3  = 39.41 * 0.08988  # kWh per m3 at STP

def m3_to_TWh(m3):
    return m3 * KWH_PER_M3 / 1e9

def label_from_filename(fname: str) -> str:
    """Make a short legend label like 'CL180–50TWh'."""
    m = re.search(r"CL(\d+)_TWh(\d+)", fname)
    return f"CL{m.group(1)}–{m.group(2)} TWh" if m else os.path.splitext(fname)[0]

def aggregate_one_file(path: str) -> pd.DataFrame:
    """Return a tidy dataframe with one row per cycle for this scenario."""
    xls = pd.ExcelFile(path)
    # collect only sheets called cycle_<int>
    cyc_sheets = sorted(
        (int(m.group(1)), s)
        for s in xls.sheet_names
        for m in [re.match(r"^cycle_(\d+)$", s)]
        if m
    )
    rows = []
    for cyc, sname in cyc_sheets:
        df = pd.read_excel(xls, sheet_name=sname)

        # totals (robust even if TWh cols missing)
        inj_twh = pd.to_numeric(df.get(COL_INJ_TWH), errors="coerce").sum(min_count=1)
        pro_twh = pd.to_numeric(df.get(COL_PRO_TWH), errors="coerce").sum(min_count=1)
        if not np.isfinite(inj_twh) or not np.isfinite(pro_twh):
            inj_twh = m3_to_TWh(pd.to_numeric(df[COL_INJ_M3], errors="coerce").sum())
            pro_twh = m3_to_TWh(pd.to_numeric(df[COL_PRO_M3], errors="coerce").sum())

        # weights for energy-weighted stats
        w = pd.to_numeric(df.get(COL_PRO_TWH), errors="coerce").fillna(0.0)
        if w.sum() == 0:
            # fall back to equal weights if produced energy missing/zero
            w = pd.Series(np.ones(len(df)), index=df.index)

        # energy-weighted LCOS / permeability / CG
        lcos = pd.to_numeric(df[COL_LCOS], errors="coerce")
        perm = pd.to_numeric(df[COL_PERM], errors="coerce")
        cg   = pd.to_numeric(df[COL_CG],   errors="coerce")

        lcos_w  = (lcos * w).sum() / w.sum()
        perm_w  = (perm * w).sum() / w.sum()
        cg_w    = (cg   * w).sum() / w.sum()

        wells_sum = pd.to_numeric(df[COL_WELLS], errors="coerce").sum()

        rows.append(dict(
            cycle=cyc,
            inj_twh=inj_twh,
            pro_twh=pro_twh,
            eff=pro_twh / inj_twh if inj_twh > 0 else np.nan,  # efficiency
            lcos=lcos_w,
            wells=wells_sum,
            perm=perm_w,
            cg=cg_w,
        ))

    out = pd.DataFrame(rows).sort_values("cycle").reset_index(drop=True)
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
    agg = aggregate_one_file(f)
    agg["scenario"] = label_from_filename(os.path.basename(f))
    scenarios.append(agg)

if not scenarios:
    raise RuntimeError("No scenarios loaded. Check FILES/GLOB_PATTERN and paths.")

# ----------- plotting style -----------
plt.rcParams.update({
    "font.size": 18,
    "axes.labelsize": 18,
    "axes.titlesize": 18,
    "legend.fontsize": 14,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "lines.linewidth": 3,
    "lines.markersize": 7,
})

def plot_one(metric_key, ylabel, title, yfmt=None):
    plt.figure(figsize=(9.5, 6.5))
    for df in scenarios:
        s = df["scenario"].iloc[0]
        plt.plot(df["cycle"], df[metric_key], marker="o", label=s)
    plt.xlabel("Cycle number [-]")
    plt.ylabel(ylabel)
    if yfmt:
        ax = plt.gca()
        ax.yaxis.set_major_formatter(yfmt)
    plt.title(title)
    plt.grid(alpha=0.35)
    plt.legend(frameon=True, ncol=1)
    plt.tight_layout()
    plt.show()

# ========== Figures ==========
# 1) Efficiency = Produced / Injected (TWh)
plot_one("eff", "Efficiency (Produced / Injected) [-]",
         "Scenario efficiency vs. cycle")

# 2) LCOS (weighted by produced TWh)
plot_one("lcos", "LCOS [$/MWh]", "LCOS vs. cycle (energy-weighted)")

# 3) Total number of wells selected
plot_one("wells", "Total wells selected [-]", "Wells vs. cycle")

# 4) Average permeability (energy-weighted)
plot_one("perm", "Average permeability [mD]", "Permeability vs. cycle")

# 5) Average CG ratio (energy-weighted)
plot_one("cg", "Average cushion-gas ratio [-]", "Cushion-gas ratio vs. cycle")
