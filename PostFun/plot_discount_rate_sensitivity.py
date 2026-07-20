import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation")
# DEFAULT_RESULTS_ROOT = Path(r"Y:\Mixing Results\July\Two Term Equation Discounted CAPEX")
DEFAULT_YEAR = 30
DEFAULT_CAPEX_TREATMENT = "auto"
DEFAULT_BASELINE_H2_COST = 4.0
DEFAULT_BASELINE_PSA = "Low"
DEFAULT_COLORMAP = "coolwarm"

DISCOUNT_RATES = [4.0, 7.0, 10.0]
TARGET_ORDER = [5, 15, 50, 100, 150, 200]
H2_ORDER = [3.0, 4.0, 5.0]
PSA_ORDER = ["Low", "Med", "High"]

COLORMAP_CHOICES = [
    "blue_yellow",
    "blue_yellow_r",
    "coolwarm",
    "RdBu_r",
    "seismic",
    "inferno",
    "magma",
    "plasma",
    "viridis",
    "cividis",
    "Reds",
    "OrRd",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot LCOS sensitivity to discount rate from UK portfolio optimisation outputs."
    )
    parser.add_argument(
        "--results-root",
        default=str(DEFAULT_RESULTS_ROOT),
        help="Root folder containing discount_rate_summary_all.csv or DR_* subfolders.",
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Project horizon year to plot.")
    parser.add_argument(
        "--capex-treatment",
        default=DEFAULT_CAPEX_TREATMENT,
        choices=["auto", "upfront", "discounted_annual"],
        help=(
            "CAPEX treatment to filter. Use auto to prefer upfront when available, "
            "or discounted_annual when the selected folder only contains discounted CAPEX outputs."
        ),
    )
    parser.add_argument(
        "--baseline-h2-cost",
        type=float,
        default=DEFAULT_BASELINE_H2_COST,
        help="H2 cost used for the main line plot.",
    )
    parser.add_argument(
        "--baseline-psa",
        default=DEFAULT_BASELINE_PSA,
        choices=PSA_ORDER,
        help="PSA level used for the main line plot.",
    )
    parser.add_argument(
        "--colormap",
        default=DEFAULT_COLORMAP,
        choices=COLORMAP_CHOICES,
        help="Matplotlib colormap for heatmaps. Line colours are sampled from the same colormap.",
    )
    parser.add_argument("--output-dir", default=None, help="Optional output folder for plots and CSV files.")
    return parser.parse_args()


def get_colormap(colormap: str) -> matplotlib.colors.Colormap:
    if colormap == "blue_yellow":
        return matplotlib.colors.LinearSegmentedColormap.from_list(
            "blue_yellow",
            ["#2166AC", "#F7F7F7", "#FDD835"],
        )
    if colormap == "blue_yellow_r":
        return matplotlib.colors.LinearSegmentedColormap.from_list(
            "blue_yellow_r",
            ["#FDD835", "#F7F7F7", "#2166AC"],
        )
    return plt.get_cmap(colormap)


def line_colors_from_colormap(colormap: str) -> dict[float, str]:
    cmap = get_colormap(colormap)
    reference_colour = matplotlib.colors.to_hex(cmap(0.50))
    reference_rgb = matplotlib.colors.to_rgb(reference_colour)
    reference_luminance = (
        0.2126 * reference_rgb[0]
        + 0.7152 * reference_rgb[1]
        + 0.0722 * reference_rgb[2]
    )
    if reference_luminance > 0.78:
        reference_colour = "#4D4D4D"

    return {
        4.0: matplotlib.colors.to_hex(cmap(0.08)),
        7.0: reference_colour,
        10.0: matplotlib.colors.to_hex(cmap(0.92)),
    }


def read_summary(results_root: Path) -> pd.DataFrame:
    combined = results_root / "discount_rate_summary_all.csv"
    if combined.exists():
        return pd.read_csv(combined)

    frames = []
    for dr in ["DR_04", "DR_07", "DR_10"]:
        path = results_root / dr / "discount_rate_summary.csv"
        if not path.exists():
            print(f"[warn] Missing summary file: {path}")
            continue
        frame = pd.read_csv(path)
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(
            f"Could not find {combined} or any DR_*/discount_rate_summary.csv files under {results_root}"
        )
    return pd.concat(frames, ignore_index=True)


def prepare_summary(df: pd.DataFrame) -> pd.DataFrame:
    required = ["Target_TWh", "H2_Cost_per_kg", "PSA_Level", "Year"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Summary data is missing required columns: {missing}")

    if "Discount_Rate_Percent" not in df.columns:
        if "Discount_Rate" not in df.columns:
            raise KeyError("Summary data must contain Discount_Rate_Percent or Discount_Rate.")
        df["Discount_Rate_Percent"] = pd.to_numeric(df["Discount_Rate"], errors="coerce") * 100.0

    numeric_cols = [
        "Discount_Rate",
        "Discount_Rate_Percent",
        "Target_TWh",
        "H2_Cost_per_kg",
        "Year",
        "Weighted_LCOS",
        "Total_Loss_Cost_M$",
        "PV_Energy_TWh",
        "Selected_Reservoirs",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Discount_Rate_Percent"] = df["Discount_Rate_Percent"].round(6)
    df["H2_Cost_per_kg"] = df["H2_Cost_per_kg"].round(6)

    if "Weighted_LCOS" not in df.columns:
        if {"Total_Loss_Cost_M$", "PV_Energy_TWh"}.issubset(df.columns):
            df["Weighted_LCOS"] = df["Total_Loss_Cost_M$"] / df["PV_Energy_TWh"]
        else:
            raise KeyError(
                "Summary data must contain Weighted_LCOS or both Total_Loss_Cost_M$ and PV_Energy_TWh."
            )
    else:
        missing_lcos = df["Weighted_LCOS"].isna()
        if missing_lcos.any() and {"Total_Loss_Cost_M$", "PV_Energy_TWh"}.issubset(df.columns):
            df.loc[missing_lcos, "Weighted_LCOS"] = (
                df.loc[missing_lcos, "Total_Loss_Cost_M$"]
                / df.loc[missing_lcos, "PV_Energy_TWh"]
            )

    if "CAPEX_Treatment" not in df.columns:
        print("[warn] CAPEX_Treatment column not found. Treating all rows as upfront.")
        df["CAPEX_Treatment"] = "upfront"

    invalid_lcos = df["Weighted_LCOS"].notna() & (df["Weighted_LCOS"] <= 0)
    if invalid_lcos.any():
        print(f"[warn] Found {int(invalid_lcos.sum())} non-positive LCOS rows. They will be ignored.")
        df = df.loc[~invalid_lcos].copy()

    df["PSA_Level"] = df["PSA_Level"].astype(str)
    df["CAPEX_Treatment"] = df["CAPEX_Treatment"].astype(str)
    return df


def ordered_capex_treatments(values: pd.Series) -> list[str]:
    preferred = ["upfront", "discounted_annual"]
    present = [str(value) for value in values.dropna().unique()]
    ordered = [value for value in preferred if value in present]
    ordered.extend(sorted(set(present) - set(ordered)))
    return ordered


def resolve_capex_treatment(df: pd.DataFrame, year: int, requested: str) -> str:
    year_rows = df.loc[df["Year"].astype(int) == int(year)]
    available = ordered_capex_treatments(year_rows["CAPEX_Treatment"])
    if not available:
        raise RuntimeError(f"No CAPEX_Treatment values found for Year={year}.")

    if requested == "auto":
        selected = "upfront" if "upfront" in available else available[0]
        print(f"Using CAPEX_Treatment={selected} for Year={year}. Available: {available}")
        return selected

    if requested in available:
        return requested

    if len(available) == 1:
        selected = available[0]
        print(
            f"[warn] Requested CAPEX_Treatment={requested}, but only {selected} is "
            f"available for Year={year}. Using {selected}."
        )
        return selected

    raise RuntimeError(
        f"Requested CAPEX_Treatment={requested} is not available for Year={year}. "
        f"Available treatments: {available}"
    )


def filter_year_capex(df: pd.DataFrame, year: int, capex_treatment: str) -> pd.DataFrame:
    filtered = df.loc[
        (df["Year"].astype(int) == int(year))
        & (df["CAPEX_Treatment"].astype(str) == capex_treatment)
    ].copy()
    if filtered.empty:
        available = (
            df[["Year", "CAPEX_Treatment"]]
            .drop_duplicates()
            .sort_values(["Year", "CAPEX_Treatment"])
            .to_string(index=False)
        )
        raise RuntimeError(
            f"No rows found for Year={year} and CAPEX_Treatment={capex_treatment}.\n"
            f"Available year/CAPEX combinations:\n{available}"
        )
    return filtered


def lcos_lookup(df: pd.DataFrame) -> dict[tuple[float, int, float, str], float]:
    lookup = {}
    group_cols = ["Discount_Rate_Percent", "Target_TWh", "H2_Cost_per_kg", "PSA_Level"]
    for key, group in df.groupby(group_cols, dropna=False):
        value = group["Weighted_LCOS"].dropna()
        if value.empty:
            continue
        if len(value) > 1:
            print(f"[warn] Duplicate LCOS rows for {key}; using the first value.")
        dr, target, h2_cost, psa = key
        lookup[(round(float(dr), 6), int(target), round(float(h2_cost), 6), str(psa))] = float(value.iloc[0])
    return lookup


def warn_missing(
    lookup: dict[tuple[float, int, float, str], float],
    targets: list[int],
    h2_costs: list[float],
    psa_levels: list[str],
    discount_rates: list[float],
    year: int,
    capex_treatment: str,
) -> None:
    for dr in discount_rates:
        for target in targets:
            for h2_cost in h2_costs:
                for psa in psa_levels:
                    key = (round(float(dr), 6), int(target), round(float(h2_cost), 6), str(psa))
                    if key not in lookup:
                        print(
                            "[warn] Missing LCOS combination: "
                            f"target={target}, H2 cost={h2_cost:g}, PSA={psa}, "
                            f"discount rate={dr:g}%, year={year}, CAPEX={capex_treatment}"
                        )


def ordered_present(values: pd.Series, preferred: list) -> list:
    present = set(values.dropna().tolist())
    ordered = [value for value in preferred if value in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def plot_baseline_line(
    df: pd.DataFrame,
    output_dir: Path,
    year: int,
    capex_treatment: str,
    baseline_h2_cost: float,
    baseline_psa: str,
    line_colors: dict[float, str],
) -> pd.DataFrame:
    baseline = df.loc[
        (np.isclose(df["H2_Cost_per_kg"].astype(float), baseline_h2_cost))
        & (df["PSA_Level"].astype(str) == baseline_psa)
    ].copy()

    lookup = lcos_lookup(baseline)
    warn_missing(
        lookup,
        TARGET_ORDER,
        [baseline_h2_cost],
        [baseline_psa],
        DISCOUNT_RATES,
        year,
        capex_treatment,
    )

    rows = []
    for dr in DISCOUNT_RATES:
        for target in TARGET_ORDER:
            lcos = lookup.get((round(dr, 6), target, round(baseline_h2_cost, 6), baseline_psa), np.nan)
            rows.append(
                {
                    "Discount_Rate_Percent": dr,
                    "Target_TWh": target,
                    "H2_Cost_per_kg": baseline_h2_cost,
                    "PSA_Level": baseline_psa,
                    "Year": year,
                    "CAPEX_Treatment": capex_treatment,
                    "Weighted_LCOS": lcos,
                }
            )
    plot_data = pd.DataFrame(rows)
    plot_data.to_csv(output_dir / "discount_rate_lcos_baseline_data.csv", index=False)

    plotted = plot_data["Weighted_LCOS"].dropna()
    if not plotted.empty:
        print(
            "Baseline LCOS range: "
            f"{plotted.min():.3f} to {plotted.max():.3f} USD/MWh"
        )

    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    for dr in DISCOUNT_RATES:
        line = plot_data.loc[plot_data["Discount_Rate_Percent"] == dr]
        ax.plot(
            line["Target_TWh"],
            line["Weighted_LCOS"],
            marker="o",
            linewidth=2.4,
            markersize=7,
            color=line_colors[dr],
            label=f"{dr:g}%",
        )

    ax.set_xlabel("Delivery target [TWh]", fontsize=14)
    ax.set_ylabel(r"LCOS [\$/MWh]", fontsize=14)
    ax.set_xticks(TARGET_ORDER)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, alpha=0.28)
    ax.legend(frameon=False, fontsize=12, title="Discount rate", title_fontsize=12)
    fig.tight_layout()
    fig.savefig(output_dir / "discount_rate_lcos_baseline.png", dpi=500, bbox_inches="tight")
    fig.savefig(output_dir / "discount_rate_lcos_baseline.pdf", bbox_inches="tight")
    plt.close(fig)

    return plot_data


def build_sensitivity_summary(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["Target_TWh", "H2_Cost_per_kg", "PSA_Level", "Year", "CAPEX_Treatment"]
    work = df.loc[df["Discount_Rate_Percent"].isin(DISCOUNT_RATES)].copy()
    pivot = (
        work.pivot_table(
            index=group_cols,
            columns="Discount_Rate_Percent",
            values="Weighted_LCOS",
            aggfunc="first",
        )
        .rename(columns={4.0: "LCOS_4", 7.0: "LCOS_7", 10.0: "LCOS_10"})
        .reset_index()
    )
    for col in ["LCOS_4", "LCOS_7", "LCOS_10"]:
        if col not in pivot.columns:
            pivot[col] = np.nan

    pivot["Delta_10_vs_7_percent"] = 100.0 * (pivot["LCOS_10"] - pivot["LCOS_7"]) / pivot["LCOS_7"]
    pivot["Delta_4_vs_7_percent"] = 100.0 * (pivot["LCOS_4"] - pivot["LCOS_7"]) / pivot["LCOS_7"]
    pivot["LCOS_range_percent"] = 100.0 * (pivot["LCOS_10"] - pivot["LCOS_4"]) / pivot["LCOS_7"]
    return pivot[
        group_cols
        + [
            "LCOS_4",
            "LCOS_7",
            "LCOS_10",
            "Delta_10_vs_7_percent",
            "Delta_4_vs_7_percent",
            "LCOS_range_percent",
        ]
    ].sort_values(["PSA_Level", "H2_Cost_per_kg", "Target_TWh"])


def heatmap_rows(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        for compare_dr, delta_col in [
            (10.0, "Delta_10_vs_7_percent"),
            (4.0, "Delta_4_vs_7_percent"),
        ]:
            compare_lcos_col = "LCOS_10" if compare_dr == 10.0 else "LCOS_4"
            rows.append(
                {
                    "Compare_Discount_Rate_Percent": compare_dr,
                    "Reference_Discount_Rate_Percent": 7.0,
                    "Target_TWh": row["Target_TWh"],
                    "H2_Cost_per_kg": row["H2_Cost_per_kg"],
                    "PSA_Level": row["PSA_Level"],
                    "Year": row["Year"],
                    "CAPEX_Treatment": row["CAPEX_Treatment"],
                    "LCOS_compare": row[compare_lcos_col],
                    "LCOS_7": row["LCOS_7"],
                    "Delta_percent": row[delta_col],
                }
            )
    return pd.DataFrame(rows)


def plot_heatmap(
    heatmap_data: pd.DataFrame,
    output_dir: Path,
    compare_dr: float,
    year: int,
    capex_treatment: str,
) -> None:
    subset = heatmap_data.loc[heatmap_data["Compare_Discount_Rate_Percent"] == compare_dr].copy()
    valid = subset["Delta_percent"].dropna()
    if valid.empty:
        print(f"[warn] No valid heatmap values for {compare_dr:g}% versus 7%.")
        vmax = 1.0
    else:
        print(
            f"{compare_dr:g}% vs 7% LCOS change range: "
            f"{valid.min():.3f}% to {valid.max():.3f}%"
        )
        vmax = float(np.nanmax(np.abs(valid)))
        if vmax == 0:
            vmax = 1.0

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), sharex=True, sharey=True)
    image = None
    for ax, psa in zip(axes, PSA_ORDER):
        panel = subset.loc[subset["PSA_Level"].astype(str) == psa]
        matrix = np.full((len(H2_ORDER), len(TARGET_ORDER)), np.nan)
        for y_idx, h2_cost in enumerate(H2_ORDER):
            for x_idx, target in enumerate(TARGET_ORDER):
                row = panel.loc[
                    (np.isclose(panel["H2_Cost_per_kg"].astype(float), h2_cost))
                    & (panel["Target_TWh"].astype(int) == int(target))
                ]
                if not row.empty:
                    matrix[y_idx, x_idx] = float(row["Delta_percent"].iloc[0])

        image = ax.imshow(matrix, cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_title(f"{psa} PSA", fontsize=14)
        ax.set_xticks(np.arange(len(TARGET_ORDER)))
        ax.set_xticklabels([str(target) for target in TARGET_ORDER], fontsize=11)
        ax.set_yticks(np.arange(len(H2_ORDER)))
        ax.set_yticklabels([f"{h2:g}" for h2 in H2_ORDER], fontsize=11)
        ax.set_xlabel("Delivery target [TWh]", fontsize=12)

        for y_idx in range(len(H2_ORDER)):
            for x_idx in range(len(TARGET_ORDER)):
                value = matrix[y_idx, x_idx]
                if np.isnan(value):
                    label = ""
                else:
                    label = f"{value:.1f}"
                ax.text(x_idx, y_idx, label, ha="center", va="center", fontsize=10, color="black")

    axes[0].set_ylabel(r"$H_2$ cost [\$/kg]", fontsize=12)
    cbar = fig.colorbar(image, ax=axes, shrink=0.88, pad=0.025)
    cbar.set_label("Change in LCOS relative to 7% [%]", fontsize=12)
    cbar.ax.tick_params(labelsize=11)
    fig.savefig(
        output_dir / f"discount_rate_heatmap_{int(compare_dr)}_vs_7.png",
        dpi=500,
        bbox_inches="tight",
    )
    fig.savefig(output_dir / f"discount_rate_heatmap_{int(compare_dr)}_vs_7.pdf", bbox_inches="tight")
    plt.close(fig)


def heatmap_matrix(panel: pd.DataFrame) -> np.ndarray:
    matrix = np.full((len(H2_ORDER), len(TARGET_ORDER)), np.nan)
    for y_idx, h2_cost in enumerate(H2_ORDER):
        for x_idx, target in enumerate(TARGET_ORDER):
            row = panel.loc[
                (np.isclose(panel["H2_Cost_per_kg"].astype(float), h2_cost))
                & (panel["Target_TWh"].astype(int) == int(target))
            ]
            if not row.empty:
                matrix[y_idx, x_idx] = float(row["Delta_percent"].iloc[0])
    return matrix


def annotation_color(
    value: float,
    cmap: matplotlib.colors.Colormap,
    vmin: float,
    vmax: float,
) -> str:
    if np.isnan(value):
        return "black"
    rgba = cmap((value - vmin) / (vmax - vmin))
    luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
    return "white" if luminance < 0.45 else "black"


def plot_combined_heatmaps(
    heatmap_data: pd.DataFrame,
    output_dir: Path,
    year: int,
    capex_treatment: str,
    colormap: str,
) -> None:
    compare_rates = [4.0, 10.0]
    valid = heatmap_data.loc[
        heatmap_data["Compare_Discount_Rate_Percent"].isin(compare_rates),
        "Delta_percent",
    ].dropna()
    if valid.empty:
        print("[warn] No valid heatmap values for combined discount-rate heatmap.")
        vmax = 1.0
    else:
        print(
            "Combined heatmap LCOS change range: "
            f"{valid.min():.3f}% to {valid.max():.3f}%"
        )
        vmax = float(np.nanmax(np.abs(valid)))
        if vmax == 0:
            vmax = 1.0
    vmin = -vmax
    cmap = get_colormap(colormap)

    fig, axes = plt.subplots(
        len(PSA_ORDER),
        len(compare_rates),
        figsize=(11.8, 10.2),
        sharex=True,
        sharey=True,
    )
    image = None
    for row_idx, psa in enumerate(PSA_ORDER):
        for col_idx, compare_dr in enumerate(compare_rates):
            ax = axes[row_idx, col_idx]
            panel = heatmap_data.loc[
                (heatmap_data["Compare_Discount_Rate_Percent"] == compare_dr)
                & (heatmap_data["PSA_Level"].astype(str) == psa)
            ]
            matrix = heatmap_matrix(panel)
            image = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")

            if row_idx == 0:
                ax.set_title(f"{compare_dr:g}% vs 7%", fontsize=15)
            if col_idx == 0:
                ax.set_ylabel(rf"{psa} PSA" + "\n" + r"$H_2$ cost [\$/kg]", fontsize=12)

            ax.set_xticks(np.arange(len(TARGET_ORDER)))
            ax.set_xticklabels([str(target) for target in TARGET_ORDER], fontsize=11)
            ax.set_yticks(np.arange(len(H2_ORDER)))
            ax.set_yticklabels([f"{h2:g}" for h2 in H2_ORDER], fontsize=11)
            ax.tick_params(axis="x", labelbottom=True)

            if row_idx == len(PSA_ORDER) - 1:
                ax.set_xlabel("Delivery target [TWh]", fontsize=12)

            for y_idx in range(len(H2_ORDER)):
                for x_idx in range(len(TARGET_ORDER)):
                    value = matrix[y_idx, x_idx]
                    label = "" if np.isnan(value) else f"{value:.1f}"
                    ax.text(
                        x_idx,
                        y_idx,
                        label,
                        ha="center",
                        va="center",
                        fontsize=10,
                        color=annotation_color(value, cmap, vmin, vmax),
                    )

    cbar = fig.colorbar(image, ax=axes, shrink=0.92, pad=0.025)
    cbar.set_label("Change in LCOS relative to 7% [%]", fontsize=12)
    cbar.ax.tick_params(labelsize=11)
    fig.savefig(
        output_dir / "discount_rate_heatmap_combined.png",
        dpi=500,
        bbox_inches="tight",
    )
    fig.savefig(output_dir / "discount_rate_heatmap_combined.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    results_root = Path(args.results_root)
    output_dir = Path(args.output_dir) if args.output_dir else results_root / "_discount_rate_sensitivity_plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    line_colors = line_colors_from_colormap(args.colormap)
    print(f"Using colormap={args.colormap}")

    df = prepare_summary(read_summary(results_root))
    capex_treatment = resolve_capex_treatment(df, args.year, args.capex_treatment)
    filtered = filter_year_capex(df, args.year, capex_treatment)
    lookup = lcos_lookup(filtered)
    warn_missing(
        lookup,
        TARGET_ORDER,
        H2_ORDER,
        PSA_ORDER,
        DISCOUNT_RATES,
        args.year,
        capex_treatment,
    )

    plotted_lcos = filtered.loc[filtered["Discount_Rate_Percent"].isin(DISCOUNT_RATES), "Weighted_LCOS"].dropna()
    if not plotted_lcos.empty:
        print(
            "All filtered LCOS range: "
            f"{plotted_lcos.min():.3f} to {plotted_lcos.max():.3f} USD/MWh"
        )

    plot_baseline_line(
        filtered,
        output_dir,
        args.year,
        capex_treatment,
        args.baseline_h2_cost,
        args.baseline_psa,
        line_colors,
    )

    summary = build_sensitivity_summary(filtered)
    summary.to_csv(output_dir / "discount_rate_sensitivity_summary.csv", index=False)

    heatmap_data = heatmap_rows(summary)
    heatmap_data.to_csv(output_dir / "discount_rate_heatmap_data.csv", index=False)
    all_changes = heatmap_data["Delta_percent"].dropna()
    if not all_changes.empty:
        print(
            "All percentage changes relative to 7% range: "
            f"{all_changes.min():.3f}% to {all_changes.max():.3f}%"
        )

    plot_combined_heatmaps(heatmap_data, output_dir, args.year, capex_treatment, args.colormap)
    print(f"Saved discount-rate sensitivity plots and data to {output_dir}")


if __name__ == "__main__":
    main()
