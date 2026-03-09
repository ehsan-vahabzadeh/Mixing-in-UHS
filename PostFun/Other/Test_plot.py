import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- user settings ----------------
INPUT_DIR = r"Y:\Mixing Results\July"
FILES = [
    "optimal_plan_CL14_TWh5.xlsx",
    "optimal_plan_CL60_TWh15.xlsx",
    "optimal_plan_CL180_TWh50.xlsx",
    "optimal_plan_CL360_TWh100.xlsx",
    "optimal_plan_CL360_TWh150.xlsx",
    "optimal_plan_CL360_TWh200.xlsx"
]
GLOB_PATTERN = None  # or e.g. "optimal_plan_CL*_TWh*.xlsx"

SCEN_COL_LABEL = "Scenario"
LCOS_COL = "LCOS"
LOSS_LABEL = r"Optimal Loss Cost ($\times 10^9$)"
# ------------------------------------------------

# candidate loss columns (the code will pick the first that exists)
LOSS_CANDIDATES = ["Loss Cost [M$]", "Loss Cost [$]", "Loss Cost [£]", "Loss Cost [M£]"]

def label_from_filename(fname: str) -> str:
    m = re.search(r"CL(\d+)_TWh(\d+)", fname)
    return f"CL{m.group(1)}–{m.group(2)} TWh" if m else os.path.splitext(fname)[0]

def pick_loss_column(df: pd.DataFrame) -> str:
    for c in LOSS_CANDIDATES:
        if c in df.columns:
            return c
    raise KeyError(f"No loss column found among {LOSS_CANDIDATES}. Columns: {list(df.columns)[:12]} ...")

def load_all_points(input_dir: str, files: list, glob_pat: str | None):
    """Return dict: scenario -> DataFrame with columns [LOSS_LABEL, LCOS_COL]."""
    if glob_pat:
        file_list = sorted(glob.glob(os.path.join(input_dir, glob_pat)))
    else:
        file_list = [os.path.join(input_dir, f) for f in files]

    scen_points = {}  # scenario -> list of (loss_billion, lcos)

    for path in file_list:
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue

        scen = label_from_filename(os.path.basename(path))
        xls = pd.ExcelFile(path)

        # iterate every sheet: each sheet has multiple reservoirs (rows)
        for sname in xls.sheet_names:
            if not re.match(r"^cycle_\d+$", sname):
                continue
            df = pd.read_excel(xls, sheet_name=sname)

            # get per-row LCOS and Loss
            if LCOS_COL not in df.columns:
                print(f"[warn] {path}:{sname} missing '{LCOS_COL}', skipping those rows.")
                continue
            loss_col = pick_loss_column(df)

            lcos = pd.to_numeric(df[LCOS_COL], errors="coerce")
            loss = pd.to_numeric(df[loss_col], errors="coerce")

            # Convert loss to billions if the column is in millions (M$ or M£)
            if "[M$]" in loss_col or "[M£]" in loss_col:
                loss = loss / 1e3  # millions -> billions

            # keep only finite pairs
            mask = lcos.notna() & loss.notna() & np.isfinite(lcos) & np.isfinite(loss)
            pts = list(zip(loss[mask].values, lcos[mask].values))

            if pts:
                scen_points.setdefault(scen, []).extend(pts)

    # convert lists to DataFrames
    scen_dfs = {
        scen: pd.DataFrame(pts, columns=[LOSS_LABEL, LCOS_COL])
        for scen, pts in scen_points.items()
        if len(pts) > 0
    }
    return scen_dfs

# ----------- collect per-reservoir points -----------
scenario_dfs = load_all_points(INPUT_DIR, FILES, GLOB_PATTERN)

# Optional: concatenate to one CSV for record
if scenario_dfs:
    all_df = pd.concat(
        [df.assign(**{SCEN_COL_LABEL: scen}) for scen, df in scenario_dfs.items()],
        ignore_index=True
    )
    all_df.to_csv("all_points_lcos_vs_loss.csv", index=False)

# ----------- plot: all points, coloured by scenario -----------
plt.rcParams.update({
    "font.size": 15,
    "axes.labelsize": 15,
    "axes.titlesize": 16,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
})

fig, ax = plt.subplots(figsize=(10, 6))

markers = ["o","s","^","D","P","X","v","<",">"]  # optional variety
for (scen, df), mk in zip(scenario_dfs.items(), markers * 5):
    ax.scatter(df[LOSS_LABEL], df[LCOS_COL], s=35, alpha=0.85, label=scen, marker=mk)

ax.set_title("LCOS vs Total Loss Cost — all reservoirs, all cycles")
ax.set_xlabel(LOSS_LABEL)
ax.set_ylabel("LCOS (USD/MWh)")
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(title=SCEN_COL_LABEL, frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("scatter_lcos_vs_loss_all_points.png", dpi=300, bbox_inches="tight")
plt.show()
