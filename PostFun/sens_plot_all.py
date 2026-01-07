import os, re, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
from matplotlib import cm
from scipy.stats import gaussian_kde

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
def parse_TWh(fname):
    m = re.search(r"TWh(\d+)", fname)
    return int(m.group(1)) if m else None

INPUT_DIR    = r"Y:\Mixing Results\July\Two Term Equation"
FILES = []               # not used now
GLOB_PATTERN = "optimal_plan_CL*_TWh*.xlsx"
MASTER_CSV  = os.path.join(INPUT_DIR, "consolidated_output - Final.csv")
YEAR_MARKS = np.array([30], dtype=int)

SCEN_COL_LABEL = "Scenario"
LOSS_LABEL = r"Present-Value Loss Cost [Billion \$]"
LCOS_LABEL     = "LCOS ($\$$/MWh)"
Perm_LABEL     = "Permeability [mD]"
FR_LABEL     = "Flow Rate [sm3/d]"
CG_LABEL     = "Cushion Gas Ratio [-]"
PR_LABEL = "Reservoir Pressure[bar]"
PORO_LABEL = "Porosity [-]"
# ------------------------------------------------

# columns (multi-name tolerant)
COL_INJ_TWH = "Cum H2 Injected [Twh]"
COL_PRO_TWH = "Cum H2 Produced [Twh]"            # nominal
COL_PRO_TWH_PV = "Produced TWh (PV total)"       # preferred if present
COL_LCOS    = "LCOS"
COL_WELLS   = "Number of Wells"
COL_Perm   = "Permeability [mD]"
COL_PORO    = "Porosity [-]"
COL_P_MPA   = "Reservoir Pressure[MPa]"
COL_FR = "Flow Rate [sm3/d]"
COL_CG     = "CG Ratio"
COL_Press = "Reservoir Pressure[bar]"
COL_T_C     = "Reservoir Temp [C]"
LOSS_CANDIDATES = ["Loss Cost [M$]", "Loss Cost [$]", "Loss Cost [£]", "Loss Cost [M£]"]
dfm = pd.read_csv(MASTER_CSV, encoding="cp1252", thousands=",")
for c in [COL_PORO, COL_Perm,COL_PORO, COL_P_MPA, COL_T_C]:
    dfm[c] = pd.to_numeric(dfm[c], errors="coerce")

# drop rows missing the basics
dfm = dfm.dropna(subset=[COL_Perm, COL_PORO, COL_P_MPA]).copy()
dfm["Reservoir Temp [K]"] = dfm[COL_T_C] + 273.15
dfm["Reservoir Pressure[bar]"]      = (dfm[COL_P_MPA] * 10).round(0) 
def parse_CL(fname):
    m = re.search(r"CL(\d+)", fname)
    return int(m.group(1)) if m else None

def label_from_filename(fname: str) -> str:
    m = re.search(r"CL(\d+)_TWh(\d+)", fname)
    # return f"{m.group(1)} d–{m.group(2)} TWh" if m else os.path.splitext(fname)[0]
    return f"{m.group(2)}" if m else os.path.splitext(fname)[0]
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
    perm_vals = pd.to_numeric(df_sheet.get(COL_Perm), errors="coerce")
    fr_vals = pd.to_numeric(df_sheet.get(COL_FR), errors="coerce")
    cg_vals = pd.to_numeric(df_sheet.get(COL_CG), errors="coerce")
    pr_vals = pd.to_numeric(df_sheet.get(COL_Press), errors="coerce")
    poro_vals = pd.to_numeric(df_sheet.get(COL_PORO), errors="coerce")
    if (w > 0).any() and lcos_vals.notna().any():
        plan_lcos = (lcos_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
        plan_perm = (perm_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
        plan_fr = (fr_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
        plan_cg = (cg_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
        plan_pr = (pr_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
        plan_poro = (poro_vals.fillna(0.0) * w).sum() / max(w.sum(), 1e-12)
    else:
        plan_lcos = lcos_vals.mean() if lcos_vals.notna().any() else np.nan
        plan_perm = perm_vals.mean() if perm_vals.notna().any() else np.nan
        plan_fr = fr_vals.mean() if fr_vals.notna().any() else np.nan
        plan_cg = cg_vals.mean() if cg_vals.notna().any() else np.nan
        plan_pr = pr_vals.mean() if pr_vals.notna().any() else np.nan
        plan_poro = poro_vals.mean() if poro_vals.notna().any() else np.nan

    return {
        LOSS_LABEL: total_loss,
        LCOS_LABEL: plan_lcos,
        Perm_LABEL: plan_perm,
        FR_LABEL: plan_fr,
        CG_LABEL: plan_cg,
        PR_LABEL: plan_pr,
        PORO_LABEL: plan_poro,
        "wells": pd.to_numeric(df_sheet.get(COL_WELLS), errors="coerce").sum(min_count=1)
    }

def snap_cycle_to_year(cycle: int, cl_days: int, year_marks: np.ndarray) -> int:
    year_raw = cycle * (cl_days / 360.0)
    return int(year_marks[np.abs(year_marks - year_raw).argmin()])


def collect_long_dataframe(input_dir: str,
                           files: list,
                           glob_pat: str | None) -> pd.DataFrame:
    # build file list
    if glob_pat:
        file_list = sorted(glob.glob(os.path.join(input_dir, glob_pat)))
    else:
        file_list = [os.path.join(input_dir, f) for f in files]

    records = []
    for path in file_list:
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue

        fname = os.path.basename(path)
        cl   = parse_CL(fname)        # e.g. 14, 60, 180, 360
        twh  = parse_TWh(fname)       # e.g. 5, 15, 50, 100, 150, 200

        xls = pd.ExcelFile(path)

        # sheets named cycle_X
        cyc_sheets = sorted(
            (int(m.group(1)), s)
            for s in xls.sheet_names
            for m in [re.match(r"^cycle_(\d+)$", s)]
            if m
        )

        for cyc, sname in cyc_sheets:
            df_sheet = pd.read_excel(xls, sheet_name=sname)
            agg = aggregate_plan_rows(df_sheet)

            year_raw = cyc * (cl / 360.0)  # keep if you need it later

            rec = {
                "Target_TWh": twh,
                "CL_days": cl,
                "cycle": cyc,
                "year_raw": year_raw,
                **agg,
            }
            records.append(rec)

    if not records:
        raise RuntimeError("No scenarios loaded/aggregated.")

    return pd.DataFrame.from_records(records)
def ecdf_with_depth(real_values, df_long, value_col, xlabel, outfile=None):
    """
    ECDF plot for pressure with dual x-axis:
    - Top: Pressure [bar]
    - Bottom: Depth [m] = Pressure / 0.1
    """

    import matplotlib.pyplot as plt
    import numpy as np

    # -----------------------------
    # Extract scenario groups
    # -----------------------------
    twh_values = sorted(df_long["Target_TWh"].unique())
    scenario_ecdfs = {
        twh : df_long.loc[df_long["Target_TWh"] == twh, value_col].dropna().values
        for twh in twh_values
    }

    # -----------------------------
    # Plot setup
    # -----------------------------
    fig, ax = plt.subplots(figsize=(6,7))

    # -----------------------------
    # 1. ECDF for real reservoir data
    # -----------------------------
    r_sorted = np.sort(real_values)
    r_y = np.linspace(0, 1, len(r_sorted))
    ax.step(r_sorted, r_y, where="post",
            color="black", linewidth=3, label="Reservoirs")

    # Shaded IQR for real reservoirs
    q25, q75 = np.percentile(real_values, [25, 75])
    ax.axvspan(q25, q75, color="gray", alpha=0.10)

    # -----------------------------
    # 2. ECDFs for each scenario
    # -----------------------------
    colors = ["#4d0000", "#660000", "#800000", "#b30000",
              "#e60000", "#ff704d", "#ff9966"]

    for (twh, col) in zip(twh_values, colors):
        vals = scenario_ecdfs[twh]
        xs = np.sort(vals)
        ys = np.linspace(0, 1, len(xs))
        ax.step(xs, ys, where="post",
                color=col, lw=2.2, label=f"{twh} TWh")

    # -----------------------------
    # MAIN X-AXIS: Pressure
    # -----------------------------
    ax.set_xlabel("Reservoir Pressure [bar]", fontsize=18)
    ax.set_ylabel("Cumulative Probability [-]", fontsize=18)
    ax.set_ylim(0, 1)
    # ax.grid(True, linestyle="--", alpha=0.3)

    # -----------------------------
    # SECONDARY AXIS: Depth
    # Depth [m] = Pressure / 0.1
    # -----------------------------
    def P_to_depth(P):
        return P / 0.1

    def depth_to_P(D):
        return D * 0.1

    ax_bottom = ax.secondary_xaxis(
        -0.18,      # distance below main x-axis
        functions=(P_to_depth, depth_to_P)
    )

    ax_bottom.set_xlabel("Depth [m]", fontsize=18)

    # -----------------------------
    # Legend & layout
    # -----------------------------
    # ax.legend(frameon=False, fontsize=12,
    #           bbox_to_anchor=(1.02, 1), loc="upper left")

    plt.tight_layout()

    if outfile:
        fig.savefig(outfile, dpi=500, bbox_inches="tight")

    plt.show()


# def ridge_facetplot(real_values, df_long, value_col, xlabel, outfile=None):
#     """
#     Plots stacked KDE curves for Reservoirs + each TWh group.
#     Ensures all subplots share the same x-axis range.
#     """
#     import matplotlib.gridspec as grid_spec
#     # ---------------------------
#     # 1) Define groups
#     # ---------------------------
#     order = sorted(df_long["Target_TWh"].unique())
#     labels = ["Reservoirs"] + [f"{t} TWh" for t in order]

#     # ---------------------------
#     # 2) Build dataset list
#     # ---------------------------
#     datasets = [np.asarray(real_values)]
#     for t in order:
#         vals = df_long[df_long["Target_TWh"] == t][value_col].dropna().values
#         datasets.append(vals)

#     # ---------------------------
#     # 3) Determine GLOBAL x-range
#     # ---------------------------
#     full_data = np.concatenate(datasets)
#     full_data = full_data[full_data > 0]  # remove zeros for log-scale

#     if xlabel.startswith("Permeability"):
#         x_min = full_data.min()
#         x_max = full_data.max()
#     else:
#         x_min = np.percentile(full_data, 0.1)
#         x_max = np.percentile(full_data, 99.9)

#     # ---------------------------
#     # 4) Create subplot grid
#     # ---------------------------
#     gs = grid_spec.GridSpec(len(labels), 1)
#     fig = plt.figure(figsize=(9, 10))

#     ax_objs = []
#     colors = sns.cubehelix_palette(len(labels), rot=-0.25, light=.7)

#     # ---------------------------
#     # 5) Plot each KDE in its own row
#     # ---------------------------
#     for i, (vals, label) in enumerate(zip(datasets, labels)):

#         ax = fig.add_subplot(gs[i:i+1, 0:])
#         ax_objs.append(ax)

#         # KDE Plot
#         plot = sns.kdeplot(vals, ax=ax, color="black", lw=1.2)
#         x = plot.get_lines()[-1].get_xdata()
#         y = plot.get_lines()[-1].get_ydata()

#         # Fill area
#         ax.fill_between(x, y, color=colors[i], alpha=0.8)

#         # Consistent x-range for ALL plots
#         ax.set_xlim(x_min, x_max)

#         # Log-scale if permeability
#         if xlabel.startswith("Permeability"):
#             ax.set_xscale("log")

#         # Label
#         # ax.text(x_min, max(y)*0.6, label, fontsize=12,
#         #         ha='left', va='center')

#         # Clean look
#         ax.set_yticks([])
#         ax.set_ylabel("")
#         # ax.set_xlim(1, 100)
#         # ax.grid(axis='x', linestyle=':', alpha=0.3)
#     gs.update(hspace= -0.1)
#     # Global x-label
#     # fig.text(0.5, 0.04, xlabel, ha='center', fontsize=14)
#     plt.tight_layout()
#     plt.show()


def ecdf_comparison(real_values, df_long, value_col, xlabel, outfile=None):
    """
    ECDF plot comparing:
    - Real reservoir distribution
    - All TWh groups (5, 15, 50, 100, 150, 200)
    """

    order = sorted(df_long["Target_TWh"].unique())   # [5,15,50,100,150,200]

    plt.figure(figsize=(6, 6))

    # ---- Real reservoirs ----
    sns.ecdfplot(real_values, label="Reservoirs", linewidth=3, color = 'black')
    q25, q75 = np.percentile(real_values, [25, 75])
    plt.axvspan(q25, q75, color="gray", alpha=0.1)
    colors = ['#810000', '#af0000', '#df0000', '#fc4227', '#ff7e54', '#ffac7c']
    # ---- ECDF for each TWh group ----
    for t in order:
        vals = df_long.loc[df_long["Target_TWh"] == t, value_col].dropna()
        sns.ecdfplot(vals, label=f"{t} TWh", linewidth=2.2, color=colors[order.index(t)])

    # ---- Axis formatting ----
    if xlabel.startswith("Permeability"):
        plt.xscale("log")

    plt.xlabel(xlabel, fontsize=18)
    plt.ylabel("Cumulative Probability [-]", fontsize=18)
    # plt.grid(True, linestyle=":", alpha=0.4)
    plt.legend(frameon=False, fontsize=12)
    # plt.ylim([-0.01 , 1.01])
    plt.tight_layout()
    if outfile:
        plt.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.show()


dfL = collect_long_dataframe(INPUT_DIR, FILES, GLOB_PATTERN)
def box_by_twh(df, value_col, title, xlabel, outfile=None):
    # order TWh groups numerically
    order = sorted(df["Target_TWh"].unique())
    data = [df.loc[df["Target_TWh"] == t, value_col].dropna().values for t in order]

    fig, ax = plt.subplots(figsize=(8, 6))
    bp = ax.boxplot(
        data,
        vert=False,
        labels=[f"{t} TWh" for t in order],
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 2},
        boxprops={"facecolor": "gray", "edgecolor": "black", "linewidth": 2},
        whiskerprops={"color": "black", "linewidth": 1.2},
        capprops={"color": "black", "linewidth": 1.2},
    )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Target Demand")
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)

    fig.tight_layout()
    if outfile:
        fig.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.show()
    
def plot_ecdf_legend_only(real_values, df_long, value_col, xlabel, outfile=None):
    """
    Creates a standalone horizontal legend using the same df_long input
    as the main ECDF plots. The legend is shown using rectangular patches.
    """

    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # --------------------------------------------
    # Extract the TWh groups exactly as ECDF code
    # --------------------------------------------
    twh_values = sorted(df_long["Target_TWh"].unique())
    labels = [f"{t} TWh" for t in twh_values]
    labels.insert(0, "Reservoirs")
    # SAME COLOR SEQUENCE as ECDF
    colors = ["black","#4d0000", "#660000", "#800000", "#b30000",
              "#e60000", "#ff704d", "#ff9966"]

    # Build legend handles (rectangular patches)
    handles = [
        Patch(facecolor=c, edgecolor="black", label=l)
        for c, l in zip(colors[:len(labels)], labels)
    ]

    # --------------------------------------------
    # Create legend-only figure
    # --------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 1))

    ax.legend(
        handles=handles,
        loc="center",
        frameon=True,
        edgecolor="black",
        ncol=len(handles),
        fontsize=20,
        handlelength=3,
        handleheight=1.5
    )

    ax.set_axis_off()  # remove axes

    plt.tight_layout()

    if outfile:
        fig.savefig(outfile, dpi=400, bbox_inches="tight")

    plt.show()
plot_ecdf_legend_only(
    real_values=dfm[COL_Perm], 
    df_long=dfL,
    value_col="Permeability [mD]", 
    xlabel="Permeability [mD]",
    outfile="legend_only.png"
)
    
ecdf_comparison(
    real_values=dfm[COL_Perm],
    df_long=dfL,
    value_col=Perm_LABEL,
    xlabel="Permeability [mD]",
    outfile="ecdf_perm_double.png"
)
ecdf_comparison(
    real_values=dfm[COL_PORO],
    df_long=dfL,
    value_col=PORO_LABEL,       # or your renamed label
    xlabel="Porosity [-]",
    outfile="box_poro_double.png"
)
ecdf_with_depth(
    real_values=dfm[COL_Press],
    df_long=dfL,
    value_col = PR_LABEL,
    xlabel=PR_LABEL,
    outfile="box_pressure_by_TWh.png",
)



