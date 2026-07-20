import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


# DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation")
DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation Discounted CAPEX")
DEFAULT_DISCOUNT_FOLDER = "DR_07"
DEFAULT_YEAR = 30

PSA_ORDER = ["Low", "Med", "High"]
H2_ORDER = [3.0, 4.0, 5.0]
TARGET_ORDER = [5, 15, 50, 100, 150, 200]

CAPITAL_COMPONENTS = [
    ("Compressor", "PV_Compressor_Capital_Cost_M$", "Compressor_Capital_Cost_M$"),
    ("Wells", "PV_Well_Capital_Cost_M$", "Well_Capital_Cost_M$"),
    ("Working gas", "PV_Working_Gas_Cost_M$", "Working_Gas_Cost_M$"),
    ("Cushion gas", "PV_Cushion_Gas_Cost_M$", "Cushion_Gas_Cost_M$"),
    ("PSA", "PV_Purification_Capital_Cost_M$", "Purification_Capital_Cost_M$"),
]

OPEX_COMPONENT = ("PV OPEX", "PV_OPEX_Cost_M$")

COLORS = {
    "Compressor": "#4C78A8",
    "Wells": "#72B7B2",
    "Working gas": "#F58518",
    "Cushion gas": "#54A24B",
    "PSA": "#B279A2",
    "PV OPEX": "#9D755D",
}


def existing_component_column(df: pd.DataFrame, pv_col: str, raw_col: str) -> str:
    if pv_col in df.columns and pd.to_numeric(df[pv_col], errors="coerce").notna().any():
        return pv_col
    if raw_col in df.columns:
        return raw_col
    raise KeyError(f"Missing component columns: {pv_col} or {raw_col}")


def load_breakdown(results_root: Path, discount_folder: str, year_pick: int) -> pd.DataFrame:
    path = results_root / discount_folder / "capital_cost_breakdown.csv"
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}")

    df = pd.read_csv(path)
    for col in ["Year", "Target_TWh", "H2_Cost_per_kg", "Weighted_LCOS", "Total_Loss_Cost_M$"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "PSA_Level" not in df.columns:
        raise KeyError("capital_cost_breakdown.csv must contain PSA_Level")

    years = sorted(df["Year"].dropna().unique())
    if year_pick not in years:
        closest = min(years, key=lambda y: abs(y - year_pick))
        print(f"[warn] Year {year_pick} not found. Using closest year {closest}.")
        year_pick = int(closest)

    df = df.loc[df["Year"] == year_pick].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for Year={year_pick}")

    component_cols = []
    for label, pv_col, raw_col in CAPITAL_COMPONENTS:
        col = existing_component_column(df, pv_col, raw_col)
        df[label] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        component_cols.append(label)

    if OPEX_COMPONENT[1] in df.columns:
        df[OPEX_COMPONENT[0]] = pd.to_numeric(df[OPEX_COMPONENT[1]], errors="coerce").fillna(0.0)
    else:
        df[OPEX_COMPONENT[0]] = 0.0

    component_cols_with_opex = component_cols + [OPEX_COMPONENT[0]]
    df["Total_Component_Cost_M$"] = df[component_cols_with_opex].sum(axis=1)

    # This implied denominator makes the component LCOS contributions sum to the reported LCOS.
    df["Implied_PV_Energy_TWh"] = df["Total_Loss_Cost_M$"] / df["Weighted_LCOS"].replace(0, np.nan)
    for col in component_cols_with_opex:
        df[f"{col} LCOS"] = df[col] / df["Implied_PV_Energy_TWh"]
        df[f"{col} Total %"] = 100.0 * df[col] / df["Total_Component_Cost_M$"].replace(0, np.nan)

    capital_total = df[component_cols].sum(axis=1)
    for col in component_cols:
        df[f"{col} Capital %"] = 100.0 * df[col] / capital_total.replace(0, np.nan)

    return df


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
    value_suffix: str,
    components: list[str],
    ylabel: str,
    outfile: Path,
    percent: bool = False,
) -> None:
    targets = ordered_targets(df)
    ncols = 3
    nrows = int(np.ceil(len(targets) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 5.6 * nrows), sharex=True)
    axes = np.asarray(axes).reshape(-1)
    bars, group_centers, group_labels, bar_positions = bar_layout()
    width = 0.78

    for ax, target in zip(axes, targets):
        subset = df.loc[df["Target_TWh"].astype(int) == int(target)].copy()
        bottom = np.zeros(len(bars), dtype=float)

        for component in components:
            values = []
            for psa, h2, _ in bars:
                row = subset.loc[
                    (subset["PSA_Level"].astype(str) == psa)
                    & (np.isclose(subset["H2_Cost_per_kg"].astype(float), h2))
                ]
                values.append(float(row[f"{component}{value_suffix}"].iloc[0]) if not row.empty else 0.0)

            ax.bar(
                bar_positions,
                values,
                width=width,
                bottom=bottom,
                color=COLORS[component],
                edgecolor="white",
                linewidth=0.6,
                label=component,
            )
            bottom += np.asarray(values)

        ax.set_title(f"{target} TWh", fontsize=16)
        ax.set_xticks(bar_positions)
        ax.set_xticklabels([f"{h2:g}" for _, h2, _ in bars], fontsize=11)
        ax.set_xlabel("H2 cost [$ per kg]", fontsize=12)
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
        [Patch(facecolor=COLORS[component], edgecolor="white", label=component) for component in components],
        [component for component in components],
        loc="upper center",
        ncol=len(components),
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=500, bbox_inches="tight")
    plt.close(fig)


def make_plots(results_root: Path, discount_folder: str, year_pick: int, output_dir: Path | None = None) -> None:
    df = load_breakdown(results_root, discount_folder, year_pick)
    output_dir = output_dir or (results_root / "_cost_contribution_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    capital_components = [label for label, _, _ in CAPITAL_COMPONENTS]
    total_components = capital_components + [OPEX_COMPONENT[0]]

    dr_label = discount_folder.lower()
    year_label = int(df["Year"].iloc[0])

    plot_panel(
        df,
        value_suffix=" LCOS",
        components=total_components,
        ylabel="LCOS contribution [$/MWh]",
        outfile=output_dir / f"{dr_label}_year{year_label}_lcos_contribution.png",
    )

    plot_panel(
        df,
        value_suffix=" Total %",
        components=total_components,
        ylabel="Contribution to LCOS / total PV cost [%]",
        outfile=output_dir / f"{dr_label}_year{year_label}_lcos_percent_contribution.png",
        percent=True,
    )

    plot_panel(
        df,
        value_suffix=" Capital %",
        components=capital_components,
        ylabel="Contribution to capital cost [%]",
        outfile=output_dir / f"{dr_label}_year{year_label}_capital_percent_contribution.png",
        percent=True,
    )

    df.to_csv(output_dir / f"{dr_label}_year{year_label}_cost_contribution_plot_data.csv", index=False)
    print(f"Saved plots and plot data to {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot DR_07 stacked cost and LCOS contribution charts.")
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT), help="Root folder containing DR_* outputs.")
    parser.add_argument("--discount-folder", default=DEFAULT_DISCOUNT_FOLDER, help="Discount-rate folder, e.g. DR_07.")
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
