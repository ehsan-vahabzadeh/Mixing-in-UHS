from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from CoolProp.CoolProp import PropsSI


SECONDS_PER_DAY = 86400.0
DEFAULT_COMPONENT = "H2"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = Path(r"Y:\Mixing Results\Revision\Testing")
DEFAULT_CASES_FILE = REPO_ROOT / "appl" / "1p" / "CH4" / "optimised_validation_cases_ch4.json"
DEFAULT_MODEL_FILE = REPO_ROOT / "PostFun" / "ann_model_withoutCG_AC.pt"
DEFAULT_SCALERS_FILE = REPO_ROOT / "PostFun" / "scalers_withoutCG_AC.pkl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "Plots" / "testing_rf_surrogate_comparison"
DEFAULT_COMPARISON_CYCLE = 10
DEFAULT_TOP_N = 0


@dataclass
class CycleData:
    end_of_withdrawal: list[int]
    end_of_injection: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare RF from testing reservoir simulations against the ANN "
            "surrogate used by generate_optimisation_scenarios.py."
        )
    )
    parser.add_argument("input_dir", nargs="?", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_FILE)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_FILE)
    parser.add_argument("--scalers", type=Path, default=DEFAULT_SCALERS_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--component", default=DEFAULT_COMPONENT)
    parser.add_argument("--pattern", default="*.json")
    parser.add_argument(
        "--comparison-cycle",
        type=int,
        default=DEFAULT_COMPARISON_CYCLE,
        help="One-based RF cycle to compare. Defaults to the 10th cycle.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Keep only the top N cases ranked by surrogate RF. Defaults to 0, which keeps all cases.",
    )
    parser.add_argument(
        "--include-development-injection",
        action="store_true",
        help=(
            "Include the initial development/cushion-gas injection in the RF "
            "denominator. By default it is excluded, so RF is based on working "
            "gas injection only."
        ),
    )
    return parser.parse_args()


def load_cases(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        raise ValueError(f"{path} must contain a list of case dictionaries.")

    case_by_name: dict[str, dict[str, Any]] = {}
    for case in cases:
        label = str(case.get("name", "")).strip()
        if label:
            case_by_name[label] = case
    return case_by_name


def get_activation(name: str) -> nn.Module:
    if name == "relu":
        return nn.ReLU()
    if name == "tanh":
        return nn.Tanh()
    if name == "sigmoid":
        return nn.Sigmoid()
    raise ValueError(f"Unknown activation function: {name}")


def build_model(input_dim: int, hidden_sizes: list[int], activations: list[str]) -> nn.Sequential:
    layers: list[nn.Module] = []
    in_dim = input_dim
    for out_dim, act_name in zip(hidden_sizes, activations):
        layers.append(nn.Linear(in_dim, out_dim))
        layers.append(get_activation(act_name))
        in_dim = out_dim

    layers.append(nn.Linear(in_dim, 1))
    layers.append(nn.Sigmoid())
    return nn.Sequential(*layers)


def load_surrogate(model_path: Path) -> nn.Module:
    model = build_model(input_dim=9, hidden_sizes=[36, 92, 108], activations=["tanh", "relu", "sigmoid"])
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model


def case_float(case: dict[str, Any], key: str) -> float:
    value = case.get(key)
    if value is None:
        raise KeyError(f"Case {case.get('name', '<unnamed>')} is missing {key}")
    return float(value)


def predict_surrogate_rf(
    case: dict[str, Any],
    model: nn.Module,
    scalers: dict[str, Any],
    model_cycle_index: int,
) -> float:
    pressure_bar = case_float(case, "Pressure_bar")
    temperature_k = case_float(case, "Temperature_K")
    cg_type = str(case.get("CushionGasType", "H2"))

    h2_density = PropsSI("D", "P", pressure_bar * 1e5, "T", temperature_k, "Hydrogen")
    cg_density = PropsSI("D", "P", pressure_bar * 1e5, "T", temperature_k, cg_type)
    delta_rho = cg_density - h2_density

    full_input = np.array(
        [
            [
                case_float(case, "FlowRate_sm3_d"),
                case_float(case, "CycleLength_d"),
                case_float(case, "Permeability_mD"),
                pressure_bar,
                delta_rho,
                case_float(case, "Porosity"),
                temperature_k,
                case_float(case, "CGRatio"),
                float(model_cycle_index),
            ]
        ]
    )
    scaled = scalers["X_scaler"].transform(full_input)
    input_tensor = torch.tensor(scaled, dtype=torch.float32)
    with torch.no_grad():
        rf = float(model(input_tensor).item())
    return rf


def cycles(case: dict[str, Any], time_seconds: list[float]) -> CycleData:
    """Cycle endpoint logic from PostFun/Other/Pe_Ng_sens.py."""
    end_of_withdrawal: list[int] = []
    end_of_injection: list[int] = []
    injection_duration_dev = case_float(case, "InjectionDurationDev") * SECONDS_PER_DAY
    injection_duration_op = case_float(case, "InjectionDurationOp") * SECONDS_PER_DAY

    qq = 1
    for idx, time_value in enumerate(time_seconds):
        if time_value - qq * injection_duration_op - injection_duration_dev >= 0:
            if qq % 2 == 0:
                end_of_withdrawal.append(idx)
            else:
                end_of_injection.append(idx)
            qq += 1

    end_of_withdrawal.append(len(time_seconds))
    return CycleData(end_of_withdrawal=end_of_withdrawal, end_of_injection=end_of_injection)


def development_duration_seconds(case: dict[str, Any]) -> float:
    cycles_dev = float(case.get("CyclesDev", 1.0))
    injection_duration_dev = case_float(case, "InjectionDurationDev") * SECONDS_PER_DAY
    idle_duration_dev = float(case.get("IdleDurationDev", 0.0)) * SECONDS_PER_DAY
    return cycles_dev * (injection_duration_dev + idle_duration_dev)


def first_index_at_or_after(values: list[float], threshold: float) -> int:
    for idx, value in enumerate(values):
        if value >= threshold:
            return idx
    return len(values)


def calculate_rf_values(
    values_inj_dt: list[float],
    values_prod_dt: list[float],
    cycle_data: CycleData,
    exclude_injection_before_idx: int,
) -> tuple[list[float], float]:
    rf_values: list[float] = []
    cumulative_inj = [0.0] * (len(values_inj_dt) + 1)
    cumulative_prod = [0.0] * (len(values_prod_dt) + 1)

    for i in range(1, len(values_inj_dt) + 1):
        cumulative_inj[i] = cumulative_inj[i - 1] + values_inj_dt[i - 1]
        cumulative_prod[i] = cumulative_prod[i - 1] + values_prod_dt[i - 1]

    base_idx = min(exclude_injection_before_idx, len(values_inj_dt))
    excluded_injection = cumulative_inj[base_idx]

    for raw_idx in cycle_data.end_of_withdrawal:
        idx = min(raw_idx, len(values_inj_dt), len(values_prod_dt))
        working_gas_injection = cumulative_inj[idx] - excluded_injection
        if working_gas_injection != 0.0:
            rf_step = abs(cumulative_prod[idx]) / abs(working_gas_injection)
        else:
            rf_step = 0.0
        rf_values.append(rf_step)

    return rf_values, excluded_injection


def load_simulation_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("simulation JSON root is not an object")

    required = {"time", "InjectionValues_dt", "ProductionValues_dt"}
    missing = required - set(data)
    if missing:
        raise KeyError(f"missing required keys: {sorted(missing)}")
    return data


def simulation_rf_values(
    json_path: Path,
    case: dict[str, Any],
    component: str,
    exclude_development_injection: bool,
) -> tuple[list[float], float]:
    data = load_simulation_json(json_path)
    injection_values = data["InjectionValues_dt"]
    production_values = data["ProductionValues_dt"]
    if component not in injection_values or component not in production_values:
        raise KeyError(f"component {component!r} not found in simulation data")

    time_seconds = [float(value) for value in data["time"]]
    values_inj_dt = [float(value) for value in injection_values[component]]
    values_prod_dt = [float(value) for value in production_values[component]]
    n_values = min(len(time_seconds), len(values_inj_dt), len(values_prod_dt))
    if n_values == 0:
        raise ValueError("empty time/injection/production arrays")

    time_seconds = time_seconds[:n_values]
    values_inj_dt = values_inj_dt[:n_values]
    values_prod_dt = values_prod_dt[:n_values]

    cycle_data = cycles(case, time_seconds)
    if exclude_development_injection:
        development_end_idx = first_index_at_or_after(time_seconds, development_duration_seconds(case))
    else:
        development_end_idx = 0

    return calculate_rf_values(
        values_inj_dt,
        values_prod_dt,
        cycle_data,
        exclude_injection_before_idx=development_end_idx,
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def error_summary(df: pd.DataFrame) -> dict[str, float]:
    err = df["RF_simulation"].to_numpy(dtype=float) - df["RF_surrogate"].to_numpy(dtype=float)
    sim = df["RF_simulation"].to_numpy(dtype=float)
    pred = df["RF_surrogate"].to_numpy(dtype=float)
    abs_err = np.abs(err)
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(abs_err))
    bias = float(np.mean(err))
    denom = float(np.sum((sim - np.mean(sim)) ** 2))
    r2 = float(1.0 - np.sum(err**2) / denom) if denom > 0.0 else math.nan
    pearson = float(np.corrcoef(pred, sim)[0, 1]) if len(df) > 1 else math.nan
    return {
        "n": float(len(df)),
        "MAE": mae,
        "RMSE": rmse,
        "Bias_sim_minus_surrogate": bias,
        "MaxAbsError": float(np.max(abs_err)),
        "MeanAbsPercentError": float(np.mean(abs_err / np.maximum(np.abs(sim), 1e-12)) * 100.0),
        "R2": r2,
        "Pearson_r": pearson,
        "RF_surrogate_mean": float(np.mean(pred)),
        "RF_simulation_mean": float(np.mean(sim)),
    }


def plot_pareto_comparison(df: pd.DataFrame, summary: dict[str, float], output_base: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8.5,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    plot_df = df.sort_values("RF_surrogate", ascending=False).reset_index(drop=True)
    plot_df["Pareto_rank"] = np.arange(1, len(plot_df) + 1)

    surrogate = plot_df["RF_surrogate"].to_numpy(float)
    simulation = plot_df["RF_simulation"].to_numpy(float)

    fig, ax_parity = plt.subplots(figsize=(3.75, 3.55), constrained_layout=True)

    scatter = ax_parity.scatter(
        surrogate,
        simulation,
        s=30,
        c=plot_df["abs_error"].to_numpy(float),
        cmap="plasma",
        edgecolors="black",
        linewidths=0.45,
        zorder=3,
    )
    for xi, yi, case_no in zip(surrogate, simulation, plot_df["Pareto_rank"]):
        ax_parity.annotate(
            str(int(case_no)),
            (xi, yi),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=6.5,
            color="0.2",
        )
    lim_min = max(0.0, min(float(np.nanmin(surrogate)), float(np.nanmin(simulation))) - 0.035)
    lim_max = max(float(np.nanmax(surrogate)), float(np.nanmax(simulation))) + 0.035
    ax_parity.plot([lim_min, lim_max], [lim_min, lim_max], color="0.25", linewidth=0.85, linestyle="--")
    ax_parity.set_xlim(lim_min, lim_max)
    ax_parity.set_ylim(lim_min, lim_max)
    ax_parity.set_xlabel("Surrogate RF [-]")
    ax_parity.set_ylabel("Simulation RF [-]")
    ax_parity.set_aspect("equal", adjustable="box")
    ax_parity.grid(True, color="0.88", linewidth=0.65)
    metrics_text = f"RMSE = {summary['RMSE']:.3f}"
    ax_parity.text(
        0.97,
        0.04,
        metrics_text,
        transform=ax_parity.transAxes,
        va="bottom",
        ha="right",
        fontsize=7.4,
        bbox={"facecolor": "white", "edgecolor": "0.75", "linewidth": 0.5, "pad": 2.5},
    )
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    divider = make_axes_locatable(ax_parity)
    cax = divider.append_axes("right", size="4%", pad=0.10)
    cbar = fig.colorbar(scatter, cax=cax)
    cbar.set_label("Absolute error [-]")

    fig.savefig(output_base.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    exclude_development_injection = not args.include_development_injection
    comparison_cycle = int(args.comparison_cycle)
    top_n = int(args.top_n)
    if comparison_cycle < 1 or comparison_cycle > 10:
        raise ValueError("comparison-cycle must be between 1 and 10 for this ANN surrogate.")
    if top_n < 0:
        raise ValueError("top-n must be non-negative.")
    model_cycle_index = comparison_cycle - 1

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not args.cases.exists():
        raise FileNotFoundError(f"Case file does not exist: {args.cases}")
    if not args.model.exists():
        raise FileNotFoundError(f"Model file does not exist: {args.model}")
    if not args.scalers.exists():
        raise FileNotFoundError(f"Scaler file does not exist: {args.scalers}")

    case_by_name = load_cases(args.cases)
    model = load_surrogate(args.model)
    scalers = joblib.load(args.scalers)

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    cycle_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for json_path in sorted(input_dir.glob(args.pattern)):
        label = json_path.stem
        case = case_by_name.get(label)
        if case is None:
            skipped.append({"file": json_path.name, "reason": "no matching validation case"})
            continue

        try:
            rf_values, excluded_injection = simulation_rf_values(
                json_path,
                case,
                args.component,
                exclude_development_injection=exclude_development_injection,
            )
            if len(rf_values) < comparison_cycle:
                raise ValueError(
                    f"only {len(rf_values)} RF endpoints; cycle {comparison_cycle} is required"
                )
            surrogate_rf = predict_surrogate_rf(case, model, scalers, model_cycle_index)
            simulation_rf = float(rf_values[model_cycle_index])
            if not math.isfinite(simulation_rf) or not math.isfinite(surrogate_rf):
                raise ValueError("non-finite RF value")
        except Exception as exc:
            skipped.append({"file": json_path.name, "reason": str(exc)})
            continue

        stored_rf = case.get("PredictedRF")
        stored_rf_float = float(stored_rf) if stored_rf not in (None, "") else math.nan
        error = simulation_rf - surrogate_rf
        row = {
            "label": label,
            "json_file": json_path.name,
            "FieldName": case.get("FieldName", ""),
            "SourceFile": case.get("SourceFile", ""),
            "SourceSheet": case.get("SourceSheet", ""),
            "SourceCycle": case.get("Cycle_No", ""),
            "ModelCycleIndex": model_cycle_index,
            "ComparisonCycle": comparison_cycle,
            "FlowRate_sm3_d": case.get("FlowRate_sm3_d", ""),
            "CycleLength_d": case.get("CycleLength_d", ""),
            "Permeability_mD": case.get("Permeability_mD", ""),
            "Pressure_bar": case.get("Pressure_bar", ""),
            "Temperature_K": case.get("Temperature_K", ""),
            "Porosity": case.get("Porosity", ""),
            "CGRatio": case.get("CGRatio", ""),
            "RF_denominator": (
                "working_gas_injection_only"
                if exclude_development_injection
                else "development_plus_working_gas_injection"
            ),
            f"excluded_development_injection_{args.component}": abs(excluded_injection),
            "RF_simulation": simulation_rf,
            "RF_surrogate": surrogate_rf,
            "RF_surrogate_stored": stored_rf_float,
            "surrogate_minus_stored": surrogate_rf - stored_rf_float if math.isfinite(stored_rf_float) else "",
            "error_sim_minus_surrogate": error,
            "abs_error": abs(error),
            "percent_error_vs_simulation": 100.0 * error / simulation_rf if simulation_rf != 0.0 else "",
            "n_rf_endpoints": len(rf_values),
        }
        rows.append(row)

        for idx, rf_value in enumerate(rf_values[:10], start=1):
            cycle_rows.append({"label": label, "cycle": idx, "RF_simulation": rf_value})

    if not rows:
        for item in skipped:
            warnings.warn(f"{item['file']}: {item['reason']}")
        raise RuntimeError(f"No matched RF rows were calculated from {input_dir}")

    all_df = pd.DataFrame(rows).sort_values("RF_surrogate", ascending=False).reset_index(drop=True)
    all_df.insert(0, "Pareto_rank", np.arange(1, len(all_df) + 1))

    df = all_df.head(top_n).copy() if top_n else all_df.copy()
    df["Pareto_rank"] = np.arange(1, len(df) + 1)
    summary = error_summary(df)
    summary_rows = [{"metric": key, "value": value} for key, value in summary.items()]

    comparison_fields = [
        "Pareto_rank",
        "label",
        "json_file",
        "FieldName",
        "SourceFile",
        "SourceSheet",
        "SourceCycle",
        "ModelCycleIndex",
        "ComparisonCycle",
        "FlowRate_sm3_d",
        "CycleLength_d",
        "Permeability_mD",
        "Pressure_bar",
        "Temperature_K",
        "Porosity",
        "CGRatio",
        "RF_denominator",
        f"excluded_development_injection_{args.component}",
        "RF_simulation",
        "RF_surrogate",
        "RF_surrogate_stored",
        "surrogate_minus_stored",
        "error_sim_minus_surrogate",
        "abs_error",
        "percent_error_vs_simulation",
        "n_rf_endpoints",
    ]
    write_csv(
        output_dir / "testing_rf_surrogate_all_cases.csv",
        all_df.to_dict("records"),
        comparison_fields,
    )
    write_csv(output_dir / "testing_rf_surrogate_comparison.csv", df.to_dict("records"), comparison_fields)
    write_csv(output_dir / "testing_rf_simulation_cycles.csv", cycle_rows, ["label", "cycle", "RF_simulation"])
    write_csv(output_dir / "testing_rf_surrogate_summary.csv", summary_rows, ["metric", "value"])
    write_csv(output_dir / "testing_rf_surrogate_skipped.csv", skipped, ["file", "reason"])

    plot_pareto_comparison(df, summary, output_dir / "testing_rf_surrogate_pareto")

    for item in skipped:
        warnings.warn(f"{item['file']}: {item['reason']}")

    if top_n:
        print(f"Selected top {len(df)} of {len(all_df)} matched simulation cases by surrogate RF.")
    else:
        print(f"Compared {len(df)} simulation cases.")
    print(f"RF denominator: {df['RF_denominator'].iloc[0]}")
    print(f"MAE: {summary['MAE']:.6f}")
    print(f"RMSE: {summary['RMSE']:.6f}")
    print(f"Bias (simulation - surrogate): {summary['Bias_sim_minus_surrogate']:.6f}")
    print(f"Wrote outputs to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
