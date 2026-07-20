import glob
import json
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ---------- paths ----------
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = Path(r"Y:\Mixing Results\July")

INPUT_DIR = Path(os.environ.get("MIXING_RESULTS_DIR", DEFAULT_INPUT_DIR))
if not INPUT_DIR.exists():
    fallback_input_dir = REPO_ROOT / "Plots"
    if fallback_input_dir.exists():
        print(f"Input directory not found: {INPUT_DIR}. Falling back to {fallback_input_dir}")
        INPUT_DIR = fallback_input_dir

INPUT_DIR_ALL = Path(os.environ.get("MIXING_OPTIMISED_DIR", str(INPUT_DIR / "Two Term Equation")))
MASTER_CSV = Path(
    os.environ.get("MIXING_MASTER_CSV", str(INPUT_DIR / "consolidated_output - Final.csv"))
)
SCEN_GLOB = os.environ.get(
    "MIXING_SCEN_GLOB", str(INPUT_DIR_ALL / "optimal_plan_CL*_TWh*_*.xlsx")
)

CASE_SAMPLE_N = int(os.environ.get("OPTIMISED_SAMPLE_N", "20"))
CASE_SAMPLE_SEED = int(os.environ.get("OPTIMISED_SAMPLE_SEED", "42"))
CASE_OUTPUT_DIR = REPO_ROOT / "appl" / "1p" / "CH4"
CASE_OUTPUT_JSON = CASE_OUTPUT_DIR / "optimised_validation_cases_ch4.json"
CASE_OUTPUT_CSV = CASE_OUTPUT_DIR / "optimised_validation_cases_ch4.csv"

# Simulation defaults used by appl/1p/CH4/runscript.py.
CUSHION_GAS_TYPE = os.environ.get("CUSHION_GAS_TYPE", "H2")
NUM_OPERATIONAL_CYCLES = int(os.environ.get("NUM_OPERATIONAL_CYCLES", "10"))
VTK_OUTPUT_STEPS = int(os.environ.get("VTK_OUTPUT_STEPS", "2200"))
WELL_HEIGHT_M = float(os.environ.get("WELL_HEIGHT_M", "10"))
WELL_RADIUS_M = float(os.environ.get("WELL_RADIUS_M", "0.2"))
H2_MOLAR_DENSITY_STP = float(os.environ.get("H2_MOLAR_DENSITY_STP", "41.0"))

# ---------- columns in master ----------
COL_FIELD = "Field Name"
COL_PORO = "Porosity [-]"
COL_PERM = "Permeability [mD]"
COL_P_MPA = "Reservoir Pressure[MPa]"
COL_T_C = "Reservoir Temp [C]"

# ---------- columns in scenarios ----------
COL_FLOW = "Flow Rate [sm3/d]"
COL_WELLS = "Number of Wells"
COL_CYCLE = "Cycle Length [d]"
COL_CG = "CG Ratio"
COL_P_BAR = "Reservoir Pressure[bar]"
COL_T_K = "Reservoir Temp [K]"
COL_PRED_RF = "Predicted RF [-]"
COL_PRED_MRF = "Predicted MRf [-]"

# ---------- conversions ----------
MPA_PER_M = 0.010
MD_TO_M2 = 9.869233e-16
SECONDS_PER_DAY = 86400.0


def to_numeric(df: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def format_float(value: float) -> str:
    return format(float(value), ".15g")


def read_master_reservoirs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find master reservoir CSV: {path}. "
            "Set MIXING_MASTER_CSV or MIXING_RESULTS_DIR to the folder containing it."
        )

    dfm = pd.read_csv(path, encoding="cp1252", thousands=",")
    to_numeric(dfm, [COL_PORO, COL_PERM, COL_P_MPA, COL_T_C, COL_WELLS])

    dfm = dfm.dropna(subset=[COL_FIELD, COL_PERM, COL_PORO, COL_P_MPA]).copy()
    dfm["Reservoir Temp [K]"] = dfm[COL_T_C] + 273.15
    dfm["Reservoir Pressure[bar]"] = dfm[COL_P_MPA] * 10.0
    dfm["Depth [m]"] = (dfm[COL_P_MPA] / MPA_PER_M).round(0)
    return dfm


def cycle_length_from_filename(path: Path) -> float | None:
    match = re.search(r"CL(\d+)", path.name)
    if not match:
        return None
    return float(match.group(1))


def scenario_cycle_sheets(xls: pd.ExcelFile) -> list[tuple[int, str]]:
    sheets = []
    for sheet in xls.sheet_names:
        match = re.match(r"^cycle_(\d+)$", sheet)
        if match:
            sheets.append((int(match.group(1)), sheet))
    return sheets


def read_optimised_case_rows(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        try:
            xls = pd.ExcelFile(path)
        except Exception as exc:
            print(f"Skipping {path}: {exc}")
            continue

        fallback_cycle_length = cycle_length_from_filename(path)
        for cycle_no, sheet in scenario_cycle_sheets(xls):
            df = pd.read_excel(xls, sheet_name=sheet)
            if df.empty or COL_FIELD not in df.columns:
                continue

            df = df.copy()
            if COL_CYCLE not in df.columns:
                df[COL_CYCLE] = fallback_cycle_length
            if "Cycle_No" not in df.columns:
                df["Cycle_No"] = cycle_no

            df["Source File"] = path.name
            df["Source Path"] = str(path)
            df["Source Sheet"] = sheet
            rows.append(df)

    if not rows:
        return pd.DataFrame()

    cases = pd.concat(rows, ignore_index=True)
    cases[COL_FIELD] = cases[COL_FIELD].astype(str).str.strip()
    return cases


def fill_from_master(cases: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    if cases.empty:
        return cases

    master_cols = [
        COL_FIELD,
        COL_PORO,
        COL_PERM,
        COL_P_BAR,
        COL_T_K,
        COL_WELLS,
        "Depth [m]",
    ]
    available_master_cols = [col for col in master_cols if col in master.columns]
    out = cases.merge(
        master[available_master_cols],
        on=COL_FIELD,
        how="left",
        suffixes=("", "__master"),
    )

    for col in [COL_PORO, COL_PERM, COL_P_BAR, COL_T_K, COL_WELLS, "Depth [m]"]:
        fallback = f"{col}__master"
        if fallback not in out.columns:
            continue
        if col in out.columns:
            out[col] = out[col].combine_first(out[fallback])
        else:
            out[col] = out[fallback]
        out = out.drop(columns=[fallback])

    return out


def pressure_bar(row: pd.Series) -> float:
    value = pd.to_numeric(row.get(COL_P_BAR), errors="coerce")
    if pd.notna(value):
        return float(value)

    value = pd.to_numeric(row.get(COL_P_MPA), errors="coerce")
    if pd.notna(value):
        return float(value) * 10.0

    raise ValueError("Missing reservoir pressure")


def temperature_k(row: pd.Series) -> float:
    value = pd.to_numeric(row.get(COL_T_K), errors="coerce")
    if pd.notna(value):
        return float(value)

    value = pd.to_numeric(row.get(COL_T_C), errors="coerce")
    if pd.notna(value):
        return float(value) + 273.15

    raise ValueError("Missing reservoir temperature")


def porosity_fraction(value: float) -> float:
    value = float(value)
    if value > 1.0:
        return value / 100.0
    return value


def build_case_name(
    flow_rate: float,
    cycle_length: float,
    permeability_md: float,
    p_bar: float,
    temp_k: float,
    porosity: float,
    cg_ratio: float,
) -> str:
    # Keep the 8-token filename convention used by compute_dimensionless_numbers.py.
    return (
        f"{CUSHION_GAS_TYPE}-"
        f"{int(round(flow_rate))}-"
        f"{int(round(cycle_length))}-"
        f"{int(round(permeability_md))}-"
        f"{int(round(p_bar))}-"
        f"{int(round(temp_k))}-"
        f"{int(round(porosity * 100))}-"
        f"{round(cg_ratio, 2)}"
    )


def build_simulation_case(row: pd.Series) -> dict[str, object]:
    flow_rate = float(pd.to_numeric(row.get(COL_FLOW), errors="coerce"))
    cycle_length = float(pd.to_numeric(row.get(COL_CYCLE), errors="coerce"))
    permeability_md = float(pd.to_numeric(row.get(COL_PERM), errors="coerce"))
    porosity = porosity_fraction(pd.to_numeric(row.get(COL_PORO), errors="coerce"))
    p_bar = pressure_bar(row)
    temp_k = temperature_k(row)
    cg_ratio = float(pd.to_numeric(row.get(COL_CG), errors="coerce"))
    number_of_wells = pd.to_numeric(row.get(COL_WELLS), errors="coerce")

    injection_duration_dev = cg_ratio * cycle_length / 2.0
    injection_duration_op = cycle_length / 2.0
    extraction_duration_op = cycle_length / 2.0
    t_end = injection_duration_dev + NUM_OPERATIONAL_CYCLES * cycle_length

    well_circumference = 2.0 * np.pi * WELL_RADIUS_M
    injection_rate = (
        flow_rate
        * H2_MOLAR_DENSITY_STP
        / WELL_HEIGHT_M
        / SECONDS_PER_DAY
        / well_circumference
    )

    case_name = build_case_name(
        flow_rate, cycle_length, permeability_md, p_bar, temp_k, porosity, cg_ratio
    )

    return {
        "name": case_name,
        "FieldName": row.get(COL_FIELD),
        "SourceFile": row.get("Source File"),
        "SourceSheet": row.get("Source Sheet"),
        "Cycle_No": row.get("Cycle_No"),
        "CushionGasType": CUSHION_GAS_TYPE,
        "OperationalCycles": NUM_OPERATIONAL_CYCLES,
        "FlowRate_sm3_d": flow_rate,
        "CycleLength_d": cycle_length,
        "CGRatio": cg_ratio,
        "NumberOfWells": None if pd.isna(number_of_wells) else int(round(number_of_wells)),
        "PredictedRF": pd.to_numeric(row.get(COL_PRED_RF), errors="coerce"),
        "PredictedMRF": pd.to_numeric(row.get(COL_PRED_MRF), errors="coerce"),
        "Permeability_mD": permeability_md,
        "Pressure_bar": p_bar,
        "Temperature_K": temp_k,
        "Porosity": porosity,
        "MaxTimeStepSize": format_float(t_end * SECONDS_PER_DAY / VTK_OUTPUT_STEPS),
        "InjectionRateDev": format_float(-injection_rate),
        "InjectionRateOp": format_float(-injection_rate),
        "ProductionRate": format_float(injection_rate),
        "Well_Height": format_float(WELL_HEIGHT_M),
        "ReferencePorosity": f"{porosity:.6f}",
        "ReferencePermeability": f"{permeability_md * MD_TO_M2:.6e}",
        "Pressure_TOP": format_float(p_bar * 1e5),
        "InitialTemperature": format_float(temp_k),
        "TEnd": format_float(t_end),
        "InjectionDurationDev": format_float(injection_duration_dev),
        "InjectionDurationOp": format_float(injection_duration_op),
        "ExtractionDurationOp": format_float(extraction_duration_op),
    }


def build_simulation_cases(cases: pd.DataFrame) -> pd.DataFrame:
    if COL_CG not in cases.columns:
        cases[COL_CG] = 0.0

    required = [COL_FLOW, COL_CYCLE, COL_PERM, COL_PORO]
    missing = [col for col in required if col not in cases.columns]
    if missing:
        print(f"Cannot build simulation cases; missing columns: {missing}")
        return pd.DataFrame()

    to_numeric(cases, [COL_FLOW, COL_CYCLE, COL_CG, COL_PERM, COL_PORO, COL_P_BAR, COL_T_K])

    records = []
    for _, row in cases.iterrows():
        try:
            records.append(build_simulation_case(row))
        except (TypeError, ValueError):
            continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records).drop_duplicates(subset=["name"]).reset_index(drop=True)


def write_validation_sample(cases: pd.DataFrame) -> pd.DataFrame:
    if cases.empty:
        print("No valid optimised simulation cases were available to sample.")
        return cases

    n = min(CASE_SAMPLE_N, len(cases))
    sampled = cases.sample(n=n, random_state=CASE_SAMPLE_SEED).reset_index(drop=True)

    CASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(CASE_OUTPUT_CSV, index=False)

    with CASE_OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(json.loads(sampled.to_json(orient="records")), f, indent=2)

    print(
        f"Wrote {n} random validation cases "
        f"(seed={CASE_SAMPLE_SEED}) to {CASE_OUTPUT_JSON}"
    )
    print(f"CSV copy written to {CASE_OUTPUT_CSV}")
    return sampled


def stats_series(s: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return dict(n=0, mean=np.nan, std=np.nan, min=np.nan, max=np.nan)
    return dict(n=len(s), mean=s.mean(), std=s.std(ddof=1), min=s.min(), max=s.max())


def summarize_block(df: pd.DataFrame, label: str, flow_samples: pd.Series) -> pd.DataFrame:
    rows = []
    for col, nice in [
        (COL_PERM, "Permeability [mD]"),
        (COL_PORO, "Porosity [-]"),
        (COL_P_MPA, "Pressure [MPa]"),
        ("Reservoir Temp [K]", "Temperature [K]"),
        ("Depth [m]", "Depth [m]"),
    ]:
        if col not in df.columns:
            continue
        st = stats_series(df[col])
        rows.append([nice, st["n"], st["mean"], st["std"], st["min"], st["max"]])

    stf = stats_series(flow_samples)
    rows.append(
        [
            "Flow Rate [sm3/d] (from selections)",
            stf["n"],
            stf["mean"],
            stf["std"],
            stf["min"],
            stf["max"],
        ]
    )
    return pd.DataFrame(
        rows,
        columns=[
            "Parameter",
            "N",
            f"{label} Mean",
            f"{label} Std",
            f"{label} Min",
            f"{label} Max",
        ],
    )


def overlay_horizontal_boxplots(df_all: pd.DataFrame, df_sel: pd.DataFrame, var_name: str) -> None:
    all_vals = pd.to_numeric(df_all[var_name], errors="coerce").dropna()
    sel_vals = pd.to_numeric(df_sel[var_name], errors="coerce").dropna()
    if all_vals.empty or sel_vals.empty:
        print(f"Skipping {var_name} plot because one of the datasets is empty.")
        return

    y0 = 1.0
    offset = 0.10
    pos_all = y0 + offset
    pos_sel = y0 - offset

    fig, ax = plt.subplots(figsize=(15, 5), dpi=140)
    box_kws = dict(
        vert=False,
        widths=0.18,
        patch_artist=True,
        showmeans=True,
        meanline=True,
        showfliers=True,
    )

    ax.boxplot(
        all_vals,
        positions=[pos_all],
        **box_kws,
        boxprops=dict(facecolor="#4C78A8", alpha=0.35, edgecolor="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.6),
        capprops=dict(color="black", linewidth=1.6),
        medianprops=dict(color="black", linewidth=2.2),
        flierprops=dict(
            marker="o",
            markersize=4,
            markerfacecolor="#4C78A8",
            alpha=0.6,
            markeredgecolor="none",
        ),
    )

    ax.boxplot(
        sel_vals,
        positions=[pos_sel],
        **box_kws,
        boxprops=dict(facecolor="#E45756", alpha=0.35, edgecolor="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.6),
        capprops=dict(color="black", linewidth=1.6),
        medianprops=dict(color="black", linewidth=2.2),
        flierprops=dict(
            marker="o",
            markersize=4,
            markerfacecolor="#E45756",
            alpha=0.6,
            markeredgecolor="none",
        ),
    )

    if var_name.lower().startswith("permeability"):
        ax.set_xscale("log")
        ax.set_xlabel(f"{var_name} (log scale)")
    else:
        ax.set_xlabel(var_name)

    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.get_yaxis().set_visible(False)
    plt.show()


def main() -> None:
    dfm = read_master_reservoirs(MASTER_CSV)

    xlsx_paths = [Path(path) for path in sorted(glob.glob(SCEN_GLOB))]
    if not xlsx_paths:
        print(f"No optimised scenario workbooks matched: {SCEN_GLOB}")
        return

    optimised_rows = read_optimised_case_rows(xlsx_paths)
    optimised_rows = fill_from_master(optimised_rows, dfm)

    simulation_cases = build_simulation_cases(optimised_rows)
    write_validation_sample(simulation_cases)

    selected_fields = set()
    if COL_FIELD in optimised_rows.columns:
        selected_fields = set(optimised_rows[COL_FIELD].dropna().astype(str).str.strip())

    dfs = dfm[dfm[COL_FIELD].isin(selected_fields)].copy()
    flow_samples = (
        pd.to_numeric(optimised_rows.get(COL_FLOW, pd.Series(dtype=float)), errors="coerce")
        .dropna()
        .reset_index(drop=True)
    )

    sel_summary = summarize_block(dfs, "Selected", flow_samples)
    all_summary = summarize_block(dfm, "All", flow_samples)
    summary = sel_summary.merge(all_summary, on=["Parameter"], how="outer")
    print("\n=== Summary (Selected across ALL scenarios vs. All reservoirs) ===")
    pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
    print(summary.to_string(index=False))

    if dfs.empty:
        print("No selected reservoirs were found in the master table; skipping plots.")
        return

    plt.rcParams.update(
        {
            "font.size": 20,
            "axes.labelsize": 20,
            "axes.titlesize": 20,
            "xtick.labelsize": 20,
            "ytick.labelsize": 20,
        }
    )

    overlay_horizontal_boxplots(dfm, dfs, "Permeability [mD]")
    overlay_horizontal_boxplots(dfm, dfs, "Porosity [-]")
    overlay_horizontal_boxplots(dfm, dfs, "Reservoir Pressure[MPa]")
    overlay_horizontal_boxplots(dfm, dfs, "Depth [m]")


if __name__ == "__main__":
    main()
