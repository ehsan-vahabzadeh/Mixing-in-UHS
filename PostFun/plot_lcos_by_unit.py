import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


# DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation Discounted CAPEX")
DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation")
DEFAULT_DISCOUNT_FOLDER = "DR_07"
DEFAULT_YEAR = 30

PSA_ORDER = ["Low", "Med", "High"]
H2_ORDER = [3.0, 4.0, 5.0]
TARGET_ORDER = [5, 15, 50, 100, 150, 200]
BASE_PIE_H2_COST = 4.0
BASE_PIE_PSA_LEVEL = "Low"
COLOR_ALPHA = 0.82
PIE_STARTANGLE = 90

# Costs are grouped by storage-process unit, not by CAPEX/OPEX accounting class.
UNIT_GROUP_MAP = {
    "Compressor": ["Compressor CAPEX", "WG compression OPEX", "WG cooling OPEX"],
    "H2 make-up": ["H2 make-up / replacement", "H2 make-up"],
    "Working gas": ["H2 working gas inventory"],
    "Cushion gas": ["H2 cushion gas inventory/placement"],
    "Purification": ["PSA CAPEX", "PSA OPEX"],
    "Wells": ["Well CAPEX"],
    "Other": ["WG other O&M"],
}

PIE_SEGMENT_MAP = {
    "Compressor": ["Compressor CAPEX", "WG compression OPEX", "WG cooling OPEX"],
    "H2 make-up": ["H2 make-up / replacement", "H2 make-up"],
    "Working gas": ["H2 working gas inventory"],
    "Cushion gas": ["H2 cushion gas inventory/placement"],
    "Purification": ["PSA CAPEX", "PSA OPEX"],
    "Wells": ["Well CAPEX"],
    "Other": ["WG other O&M"],
}

PIE_SEGMENT_COLOR_GROUP = {
    "Compressor": "Compressor",
    "H2 make-up": "H2 make-up",
    "Working gas": "Working gas",
    "Cushion gas": "Cushion gas",
    "Purification": "Purification",
    "Wells": "Wells",
    "Other": "Other",
}

PIE_SEGMENT_LABELS = {}

def colors_from_cmap(cmap_name: str, start: float = 0.35, stop: float = 0.9) -> dict[str, str]:
    cmap = plt.get_cmap(cmap_name)
    positions = np.linspace(start, stop, len(UNIT_GROUP_MAP))
    return {
        unit_group: matplotlib.colors.to_hex(cmap(position))
        for unit_group, position in zip(UNIT_GROUP_MAP, positions)
    }


DEFAULT_COLORS = {
    "Compressor": "#F6C76B",          # warm golden yellow
    "Wells": "#5A2A00",    # dark brown
    "Working gas": "#D95F02",    # burnt orange
    "Cushion gas": "#F28E2B",    # bright orange
    "H2 make-up": "#B30000",    # dark red
    "Purification": "#800000",         # deep red
    "Other": "#ffffff",    # pale cream
}

PLASMA_COLORS = colors_from_cmap("plasma", start=0.12, stop=0.92)
MAGMA_COLORS = colors_from_cmap("magma", start=0.12, stop=0.92)
INFERNO_COLORS = colors_from_cmap("inferno", start=0.12, stop=0.92)
PURPLES_COLORS = colors_from_cmap("Purples")
GREYS_COLORS = colors_from_cmap("Greys", start=0.25, stop=0.85)
BLUES_COLORS = colors_from_cmap("Blues")
GREENS_COLORS = colors_from_cmap("Greens")
REDS_COLORS = colors_from_cmap("Reds")
ORRD_COLORS = colors_from_cmap("OrRd")

# Uncomment one COLORS line to switch the plot palette.
COLORS = DEFAULT_COLORS
# COLORS = PLASMA_COLORS
# COLORS = MAGMA_COLORS
# COLORS = INFERNO_COLORS
# COLORS = PURPLES_COLORS
# COLORS = GREYS_COLORS
# COLORS = BLUES_COLORS
# COLORS = GREENS_COLORS
# COLORS = REDS_COLORS
# COLORS = ORRD_COLORS


def display_unit_label(unit_group: str) -> str:
    return unit_group.replace("H2", r"$H_2$")


def legend_patch(unit_group: str) -> Patch:
    return Patch(
        facecolor=matplotlib.colors.to_rgba(COLORS[unit_group], COLOR_ALPHA),
        edgecolor="black",
        linewidth=0.8,
        label=display_unit_label(unit_group),
    )


META_COLUMNS = [
    "Discount_Rate",
    "Discount_Rate_Percent",
    "CL_days",
    "Target_TWh",
    "H2_Cost_per_kg",
    "PSA_Level",
    "CAPEX_Treatment",
    "Cycle",
    "Year",
    "Selected_Reservoirs",
    "Delivered_TWh",
    "PV_Energy_TWh",
    "Total_Loss_Cost_M$",
    "Weighted_LCOS",
]

LONG_VALUE_COLUMNS = [
    "Component_PV_Cost_M$",
    "Component_LCOS_$/MWh",
    "Component_Share_of_Total_Cost",
]

PLOT_DATA_COLUMNS = META_COLUMNS + [
    "Unit_Group",
    "Unit_PV_Cost_M$",
    "Unit_LCOS_$/MWh",
    "Unit_Share_of_Total_Cost",
]


def component_to_unit_map() -> dict[str, str]:
    return {
        component: unit_group
        for unit_group, components in UNIT_GROUP_MAP.items()
        for component in components
    }


def component_to_pie_segment_map() -> dict[str, str]:
    return {
        component: segment
        for segment, components in PIE_SEGMENT_MAP.items()
        for component in components
    }


def require_columns(df: pd.DataFrame, columns: list[str], path: Path) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"{path} is missing required columns: {missing}")


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def choose_year(df: pd.DataFrame, year_pick: int) -> int:
    years = sorted(df["Year"].dropna().unique())
    if not years:
        raise RuntimeError("No valid Year values were found in the LCOS breakdown data.")
    if year_pick not in years:
        closest = min(years, key=lambda y: abs(y - year_pick))
        print(f"[warn] Year {year_pick} not found. Using closest year {int(closest)}.")
        return int(closest)
    return int(year_pick)


def validate_unit_closure(grouped: pd.DataFrame) -> None:
    case_cols = [col for col in META_COLUMNS if col in grouped.columns]
    for case_key, case in grouped.groupby(case_cols, dropna=False):
        if not isinstance(case_key, tuple):
            case_key = (case_key,)
        meta = dict(zip(case_cols, case_key))

        lcos_sum = float(case["Unit_LCOS_$/MWh"].sum())
        share_sum = float(case["Unit_Share_of_Total_Cost"].sum())
        weighted_lcos = float(case["Weighted_LCOS"].iloc[0])

        target = meta.get("Target_TWh", "unknown")
        psa = meta.get("PSA_Level", "unknown")
        h2_cost = meta.get("H2_Cost_per_kg", "unknown")
        year = meta.get("Year", "unknown")

        if not np.isclose(lcos_sum, weighted_lcos, atol=1e-4, rtol=0):
            print(
                "[warn] Unit LCOS stack does not close: "
                f"target={target}, PSA={psa}, $H_2$={h2_cost}, year={year}, "
                f"sum={lcos_sum:.6f}, reported Weighted_LCOS={weighted_lcos:.6f}"
            )
        if not np.isclose(share_sum, 1.0, atol=1e-4, rtol=0):
            print(
                "[warn] Unit percent stack does not close: "
                f"target={target}, PSA={psa}, $H_2$={h2_cost}, year={year}, "
                f"sum={share_sum:.6f}, reported Weighted_LCOS={weighted_lcos:.6f}"
            )


def group_long_lcos_breakdown(path: Path, year_pick: int) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, META_COLUMNS + ["Component"] + LONG_VALUE_COLUMNS, path)
    coerce_numeric(
        df,
        [
            "Discount_Rate",
            "Discount_Rate_Percent",
            "CL_days",
            "Target_TWh",
            "H2_Cost_per_kg",
            "Cycle",
            "Year",
            "Selected_Reservoirs",
            "Delivered_TWh",
            "PV_Energy_TWh",
            "Total_Loss_Cost_M$",
            "Weighted_LCOS",
            *LONG_VALUE_COLUMNS,
        ],
    )

    year_pick = choose_year(df, year_pick)
    df = df.loc[df["Year"] == year_pick].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for Year={year_pick} in {path}")

    inverse_map = component_to_unit_map()
    df["Unit_Group"] = df["Component"].map(inverse_map)
    unknown = sorted(df.loc[df["Unit_Group"].isna(), "Component"].dropna().unique())
    if unknown:
        raise ValueError(
            f"{path} contains components that are not mapped to storage-process units: {unknown}"
        )

    grouped = (
        df.groupby(META_COLUMNS + ["Unit_Group"], dropna=False, as_index=False)
        .agg(
            **{
                "Unit_PV_Cost_M$": ("Component_PV_Cost_M$", "sum"),
                # Unit contribution = unit PV cost divided by PV delivered energy.
                # The stacked LCOS bars therefore sum to the reported portfolio LCOS.
                "Unit_LCOS_$/MWh": ("Component_LCOS_$/MWh", "sum"),
                # Percent bars show each unit's share of total PV system cost.
                "Unit_Share_of_Total_Cost": ("Component_Share_of_Total_Cost", "sum"),
            }
        )
        .sort_values(["Target_TWh", "PSA_Level", "H2_Cost_per_kg", "Unit_Group"])
    )
    validate_unit_closure(grouped)
    return grouped[PLOT_DATA_COLUMNS]


def load_grouped_unit_breakdown(path: Path, year_pick: int) -> pd.DataFrame:
    df = pd.read_csv(path)
    group_col = "Unit_Group" if "Unit_Group" in df.columns else "Component_Group"
    require_columns(df, META_COLUMNS + [group_col], path)
    coerce_numeric(
        df,
        [
            "Discount_Rate",
            "Discount_Rate_Percent",
            "CL_days",
            "Target_TWh",
            "H2_Cost_per_kg",
            "Cycle",
            "Year",
            "Selected_Reservoirs",
            "Delivered_TWh",
            "PV_Energy_TWh",
            "Total_Loss_Cost_M$",
            "Weighted_LCOS",
        ],
    )

    unit_groups = set(UNIT_GROUP_MAP)
    observed_groups = set(df[group_col].dropna().astype(str).unique())
    if not observed_groups or not observed_groups.issubset(unit_groups):
        raise RuntimeError(
            f"{path} does not contain storage-process unit groups. "
            "Rerun the updated optimisation to generate lcos_breakdown_long.csv."
        )

    rename_map = {group_col: "Unit_Group"}
    value_candidates = {
        "Unit_PV_Cost_M$": ["Unit_PV_Cost_M$", "Group_PV_Cost_M$"],
        "Unit_LCOS_$/MWh": ["Unit_LCOS_$/MWh", "Group_LCOS_$/MWh"],
        "Unit_Share_of_Total_Cost": [
            "Unit_Share_of_Total_Cost",
            "Group_Share_of_Total_Cost",
        ],
    }
    for target_col, candidates in value_candidates.items():
        source_col = next((col for col in candidates if col in df.columns), None)
        if source_col is None:
            raise KeyError(f"{path} is missing a column for {target_col}: {candidates}")
        rename_map[source_col] = target_col

    df = df.rename(columns=rename_map)
    coerce_numeric(df, list(value_candidates))
    year_pick = choose_year(df, year_pick)
    df = df.loc[df["Year"] == year_pick].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for Year={year_pick} in {path}")

    validate_unit_closure(df)
    return df[PLOT_DATA_COLUMNS]


def load_unit_breakdown(results_root: Path, discount_folder: str, year_pick: int) -> pd.DataFrame:
    dr_dir = results_root / discount_folder
    long_path = dr_dir / "lcos_breakdown_long.csv"
    if long_path.exists():
        return group_long_lcos_breakdown(long_path, year_pick)

    grouped_path = dr_dir / "lcos_breakdown_grouped.csv"
    if grouped_path.exists():
        return load_grouped_unit_breakdown(grouped_path, year_pick)

    raise FileNotFoundError(
        f"Could not find {long_path} or {grouped_path}. "
        "Rerun the updated optimisation to generate component-level LCOS breakdowns."
    )


def load_pie_segment_breakdown(
    results_root: Path,
    discount_folder: str,
    year_pick: int,
    unit_df: pd.DataFrame,
) -> pd.DataFrame:
    long_path = results_root / discount_folder / "lcos_breakdown_long.csv"
    if not long_path.exists():
        fallback = unit_df.rename(
            columns={
                "Unit_Group": "Pie_Segment",
                "Unit_PV_Cost_M$": "Segment_PV_Cost_M$",
                "Unit_LCOS_$/MWh": "Segment_LCOS_$/MWh",
                "Unit_Share_of_Total_Cost": "Segment_Share_of_Total_Cost",
            }
        )
        return fallback[
            META_COLUMNS
            + [
                "Pie_Segment",
                "Segment_PV_Cost_M$",
                "Segment_LCOS_$/MWh",
                "Segment_Share_of_Total_Cost",
            ]
        ]

    df = pd.read_csv(long_path)
    require_columns(df, META_COLUMNS + ["Component"] + LONG_VALUE_COLUMNS, long_path)
    coerce_numeric(
        df,
        [
            "Discount_Rate",
            "Discount_Rate_Percent",
            "CL_days",
            "Target_TWh",
            "H2_Cost_per_kg",
            "Cycle",
            "Year",
            "Selected_Reservoirs",
            "Delivered_TWh",
            "PV_Energy_TWh",
            "Total_Loss_Cost_M$",
            "Weighted_LCOS",
            *LONG_VALUE_COLUMNS,
        ],
    )

    year_pick = choose_year(df, year_pick)
    df = df.loc[df["Year"] == year_pick].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for Year={year_pick} in {long_path}")

    inverse_map = component_to_pie_segment_map()
    df["Pie_Segment"] = df["Component"].map(inverse_map)
    unknown = sorted(df.loc[df["Pie_Segment"].isna(), "Component"].dropna().unique())
    if unknown:
        raise ValueError(f"{long_path} contains components that are not mapped to pie segments: {unknown}")

    grouped = (
        df.groupby(META_COLUMNS + ["Pie_Segment"], dropna=False, as_index=False)
        .agg(
            **{
                "Segment_PV_Cost_M$": ("Component_PV_Cost_M$", "sum"),
                "Segment_LCOS_$/MWh": ("Component_LCOS_$/MWh", "sum"),
                "Segment_Share_of_Total_Cost": ("Component_Share_of_Total_Cost", "sum"),
            }
        )
        .sort_values(["Target_TWh", "PSA_Level", "H2_Cost_per_kg", "Pie_Segment"])
    )
    return grouped[
        META_COLUMNS
        + [
            "Pie_Segment",
            "Segment_PV_Cost_M$",
            "Segment_LCOS_$/MWh",
            "Segment_Share_of_Total_Cost",
        ]
    ]


def ordered_targets(df: pd.DataFrame) -> list[int]:
    available = set(pd.to_numeric(df["Target_TWh"], errors="coerce").dropna().astype(int))
    ordered = [target for target in TARGET_ORDER if target in available]
    ordered.extend(sorted(available - set(ordered)))
    return ordered


def bar_layout() -> tuple[list[tuple[str, float, float]], list[float], list[str], list[float]]:
    bars = []
    centers = []
    center_labels = []
    x = 0.0
    gap = 0.9
    for psa in PSA_ORDER:
        group_x = []
        for h2 in H2_ORDER:
            bars.append((psa, h2, x))
            group_x.append(x)
            x += 1.0
        centers.append(float(np.mean(group_x)))
        center_labels.append(f"{psa} PSA")
        x += gap
    return bars, centers, center_labels, [b[2] for b in bars]


def plot_panel(
    df: pd.DataFrame,
    value_col: str,
    ylabel: str,
    outfile: Path,
    percent: bool = False,
) -> None:
    targets = ordered_targets(df)
    unit_groups = list(UNIT_GROUP_MAP)
    ncols = 3
    nrows = int(np.ceil(len(targets) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 5.6 * nrows), sharex=True)
    axes = np.asarray(axes).reshape(-1)
    bars, group_centers, group_labels, bar_positions = bar_layout()
    width = 0.78

    for ax, target in zip(axes, targets):
        subset = df.loc[df["Target_TWh"].astype(int) == int(target)].copy()
        bottom = np.zeros(len(bars), dtype=float)

        for unit_group in unit_groups:
            values = []
            for psa, h2, _ in bars:
                row = subset.loc[
                    (subset["PSA_Level"].astype(str) == psa)
                    & (np.isclose(subset["H2_Cost_per_kg"].astype(float), h2))
                    & (subset["Unit_Group"].astype(str) == unit_group)
                ]
                value = float(row[value_col].sum()) if not row.empty else 0.0
                values.append(100.0 * value if percent else value)

            ax.bar(
                bar_positions,
                values,
                width=width,
                bottom=bottom,
                color=COLORS[unit_group],
                alpha=COLOR_ALPHA,
                edgecolor="white",
                linewidth=0.6,
                label=unit_group,
            )
            bottom += np.asarray(values)

        ax.set_title(f"{target} TWh", fontsize=16)
        ax.set_xticks(bar_positions)
        ax.set_xticklabels([f"{h2:g}" for _, h2, _ in bars], fontsize=14)
        ax.set_xlabel(r"$H_2$ cost [\$ per kg]", fontsize=14)
        ax.tick_params(axis="x", labelbottom=True, labelsize=14)
        ax.tick_params(axis="y", labelsize=13)
        ax.grid(axis="y", alpha=0.25)
        if percent:
            ax.set_ylim(0, 100)

        for center, label in zip(group_centers, group_labels):
            ax.text(
                center,
                -0.16,
                label,
                ha="center",
                va="top",
                transform=ax.get_xaxis_transform(),
                fontsize=12,
            )

        for boundary in [2.95, 6.85]:
            ax.axvline(boundary, color="0.75", linewidth=0.8)

    for ax in axes[len(targets) :]:
        ax.set_axis_off()

    for row in range(nrows):
        axes[row * ncols].set_ylabel(ylabel, fontsize=13)

    fig.legend(
        [legend_patch(unit_group) for unit_group in unit_groups],
        [display_unit_label(unit_group) for unit_group in unit_groups],
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=14,
        bbox_to_anchor=(0.5, 1.01),
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.close(fig)


def pct_label(pct: float) -> str:
    return f"{pct:.0f}%" if pct >= 3.0 else ""


def plot_base_case_pies(
    df: pd.DataFrame,
    outfile: Path,
    h2_cost: float = BASE_PIE_H2_COST,
    psa_level: str = BASE_PIE_PSA_LEVEL,
) -> None:
    base = df.loc[
        (df["PSA_Level"].astype(str) == psa_level)
        & (np.isclose(df["H2_Cost_per_kg"].astype(float), h2_cost))
    ].copy()
    if base.empty:
        raise RuntimeError(f"No rows found for base pie case: PSA={psa_level}, $H_2$ cost={h2_cost}")

    targets = ordered_targets(base)
    unit_groups = list(UNIT_GROUP_MAP)
    pie_segments = list(PIE_SEGMENT_MAP)
    colors = [COLORS[PIE_SEGMENT_COLOR_GROUP[segment]] for segment in pie_segments]
    fig, axes = plt.subplots(2, 3, figsize=(11.8, 7.8))
    axes = np.asarray(axes).reshape(-1)

    for ax, target in zip(axes, targets):
        subset = base.loc[base["Target_TWh"].astype(int) == int(target)].copy()
        values = []
        for segment in pie_segments:
            row = subset.loc[subset["Pie_Segment"].astype(str) == segment]
            values.append(float(row["Segment_Share_of_Total_Cost"].sum()) if not row.empty else 0.0)

        values = np.asarray(values, dtype=float)
        if values.sum() <= 0:
            ax.set_axis_off()
            continue
        labels = [
            PIE_SEGMENT_LABELS.get(segment, "") if value >= 0.015 else ""
            for segment, value in zip(pie_segments, values)
        ]

        ax.pie(
            values,
            colors=colors,
            labels=labels,
            startangle=PIE_STARTANGLE,
            counterclock=False,
            radius=1.08,
            autopct=pct_label,
            labeldistance=0.45,
            pctdistance=0.72,
            textprops={"fontsize": 10, "color": "black"},
            wedgeprops={"edgecolor": "black", "linewidth": 0.8, "alpha": COLOR_ALPHA},
        )
        weighted_lcos = float(subset["Weighted_LCOS"].iloc[0]) if not subset.empty else np.nan
        ax.set_title(f"{target} TWh\nLCOS {weighted_lcos:.1f} $/MWh", fontsize=13, pad=1)

    for ax in axes[len(targets) :]:
        ax.set_axis_off()

    fig.legend(
        [legend_patch(unit_group) for unit_group in unit_groups],
        [display_unit_label(unit_group) for unit_group in unit_groups],
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.13, wspace=-0.18, hspace=0.28)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.close(fig)


def plot_base_case_nested_donut(
    df: pd.DataFrame,
    outfile: Path,
    h2_cost: float = BASE_PIE_H2_COST,
    psa_level: str = BASE_PIE_PSA_LEVEL,
) -> None:
    base = df.loc[
        (df["PSA_Level"].astype(str) == psa_level)
        & (np.isclose(df["H2_Cost_per_kg"].astype(float), h2_cost))
    ].copy()
    if base.empty:
        raise RuntimeError(f"No rows found for nested donut case: PSA={psa_level}, $H_2$ cost={h2_cost}")

    targets = ordered_targets(base)
    unit_groups = list(UNIT_GROUP_MAP)
    pie_segments = list(PIE_SEGMENT_MAP)
    colors = [COLORS[PIE_SEGMENT_COLOR_GROUP[segment]] for segment in pie_segments]
    outer_radius = 1.0
    ring_width = outer_radius / len(targets)

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    ax.set_aspect("equal")

    for ring_index, target in enumerate(targets):
        subset = base.loc[base["Target_TWh"].astype(int) == int(target)].copy()
        values = []
        for segment in pie_segments:
            row = subset.loc[subset["Pie_Segment"].astype(str) == segment]
            values.append(float(row["Segment_Share_of_Total_Cost"].sum()) if not row.empty else 0.0)

        values = np.asarray(values, dtype=float)
        if values.sum() <= 0:
            continue

        radius = outer_radius - ring_index * ring_width
        ax.pie(
            values,
            radius=radius,
            colors=colors,
            startangle=PIE_STARTANGLE,
            counterclock=False,
            labels=None,
            autopct=pct_label,
            pctdistance=1.0 - (ring_width / radius) * 0.52,
            textprops={"fontsize": 8, "color": "black"},
            wedgeprops={
                "width": ring_width,
                "edgecolor": "black",
                "linewidth": 0.7,
                "alpha": COLOR_ALPHA,
            },
        )

    ax.set_axis_off()
    fig.legend(
        [legend_patch(unit_group) for unit_group in unit_groups],
        [display_unit_label(unit_group) for unit_group in unit_groups],
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.15)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.close(fig)


def make_plots(
    results_root: Path,
    discount_folder: str,
    year_pick: int,
    output_dir: Path | None = None,
) -> None:
    df = load_unit_breakdown(results_root, discount_folder, year_pick)
    pie_df = load_pie_segment_breakdown(results_root, discount_folder, year_pick, df)
    output_dir = output_dir or (results_root / "_unit_lcos_contribution_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    dr_label = discount_folder.lower()
    year_label = int(df["Year"].iloc[0])

    plot_panel(
        df,
        value_col="Unit_LCOS_$/MWh",
        ylabel="LCOS contribution [$/MWh]",
        outfile=output_dir / f"{dr_label}_year{year_label}_lcos_by_storage_unit.png",
    )

    plot_panel(
        df,
        value_col="Unit_Share_of_Total_Cost",
        ylabel="Contribution to total PV cost [%]",
        outfile=output_dir / f"{dr_label}_year{year_label}_lcos_by_storage_unit_percent.png",
        percent=True,
    )

    plot_base_case_pies(
        pie_df,
        outfile=(
            output_dir
            / f"{dr_label}_year{year_label}_storage_unit_pies_h2_4_low_psa.png"
        ),
    )

    plot_base_case_nested_donut(
        pie_df,
        outfile=(
            output_dir
            / f"{dr_label}_year{year_label}_storage_unit_nested_donut_h2_4_low_psa.png"
        ),
    )

    df.to_csv(
        output_dir / f"{dr_label}_year{year_label}_lcos_by_storage_unit_plot_data.csv",
        index=False,
    )
    pie_df.to_csv(
        output_dir / f"{dr_label}_year{year_label}_storage_unit_pie_segment_data.csv",
        index=False,
    )
    print(f"Saved plots and plot data to {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot stacked LCOS contributions by storage-process unit."
    )
    parser.add_argument(
        "--results-root",
        default=str(DEFAULT_RESULTS_ROOT),
        help="Root folder containing DR_* outputs.",
    )
    parser.add_argument(
        "--discount-folder",
        default=DEFAULT_DISCOUNT_FOLDER,
        help="Discount-rate folder, e.g. DR_07.",
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Project horizon year to plot.")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for plots.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    make_plots(
        results_root=Path(args.results_root),
        discount_folder=args.discount_folder,
        year_pick=args.year,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
