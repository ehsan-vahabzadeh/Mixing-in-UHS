from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev


SECONDS_PER_DAY = 86400.0
DEFAULT_CYCLES = 15
DEFAULT_COMPONENT = "H2"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = Path(r"Y:\Mixing Results\Revision\15 Cycles")
DEFAULT_OUTPUT_DIR = REPO_ROOT / "Plots" / "rf_15_cycle_behavior_no_cg"
DEFAULT_LEGACY_CASES_FILE = (
    REPO_ROOT
    / "Plots"
    / "rf_15_cycle_behavior"
    / "ch4_legacy_runscript_cases.json"
)
DEFAULT_OPTIMISED_CASES_FILE = (
    REPO_ROOT / "appl" / "1p" / "CH4" / "optimised_validation_cases_ch4.json"
)
DEFAULT_CASES_FILE = (
    DEFAULT_LEGACY_CASES_FILE
    if DEFAULT_LEGACY_CASES_FILE.exists()
    else DEFAULT_OPTIMISED_CASES_FILE
)


@dataclass
class CycleData:
    EndofWithdrawal: list[int]
    EndofInjection: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate RF at each end-of-withdrawal cycle using the same "
            "RF procedure as PostFun/Other/Pe_Ng_sens.py."
        )
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=(
            "Directory containing simulation JSON output files. "
            f"Defaults to '{DEFAULT_INPUT_DIR}'."
        ),
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_FILE,
        help="Validation case JSON containing injection/withdrawal durations.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for CSV and PNG outputs.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=DEFAULT_CYCLES,
        help="Number of withdrawal-cycle RF values to report.",
    )
    parser.add_argument(
        "--component",
        default=DEFAULT_COMPONENT,
        help="Component key under InjectionValues_dt and ProductionValues_dt.",
    )
    parser.add_argument(
        "--pattern",
        default="*.json",
        help="Glob pattern for simulation JSON files.",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Write CSV files only.",
    )
    parser.add_argument(
        "--include-development-injection",
        action="store_true",
        help=(
            "Use the original Pe_Ng_sens denominator, including the development "
            "injection/cushion-gas fill. By default it is excluded."
        ),
    )
    return parser.parse_args()


def load_cases(cases_path: Path) -> dict[str, dict[str, object]]:
    with cases_path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        raise ValueError(f"{cases_path} should contain a list of case dictionaries.")

    case_by_label: dict[str, dict[str, object]] = {}
    for case in cases:
        label = str(case.get("name", "")).strip()
        if label:
            case_by_label[label] = case

    return case_by_label


def cycles(params: dict[str, object], time_seconds: list[float]) -> CycleData:
    """Same end-of-cycle detection used by PostFun/Other/Pe_Ng_sens.py."""
    end_of_withdrawal: list[int] = []
    end_of_injection: list[int] = []
    qq = 1
    injection_duration_dev = float(params["InjectionDurationDev"]) * SECONDS_PER_DAY
    injection_duration_op = float(params["InjectionDurationOp"]) * SECONDS_PER_DAY

    for ii, time_value in enumerate(time_seconds):
        if time_value - qq * injection_duration_op - injection_duration_dev >= 0:
            if qq % 2 == 0:
                end_of_withdrawal.append(ii)
            if qq % 2 == 1:
                end_of_injection.append(ii)
            qq += 1

    end_of_withdrawal.append(len(time_seconds))
    return CycleData(end_of_withdrawal, end_of_injection)


def development_duration_seconds(params: dict[str, object]) -> float:
    cycles_dev = float(params.get("CyclesDev", 1.0))
    injection_duration_dev = float(params["InjectionDurationDev"]) * SECONDS_PER_DAY
    idle_duration_dev = float(params.get("IdleDurationDev", 0.0)) * SECONDS_PER_DAY
    return cycles_dev * (injection_duration_dev + idle_duration_dev)


def first_index_at_or_after(values: list[float], threshold: float) -> int:
    for idx, value in enumerate(values):
        if value >= threshold:
            return idx
    return len(values)


def calculate_rf(
    values_inj_dt: list[float],
    values_prod_dt: list[float],
    cycle_data: CycleData,
    exclude_injection_before_idx: int = 0,
) -> tuple[list[float], float]:
    """Pe_Ng_sens RF endpoint logic, optionally excluding development injection."""
    rf_values: list[float] = []
    cumulative_inj = [0.0] * (len(values_inj_dt) + 1)
    cumulative_prod = [0.0] * (len(values_prod_dt) + 1)

    for i in range(1, len(values_inj_dt) + 1):
        cumulative_inj[i] = sum(values_inj_dt[:i])
        cumulative_prod[i] = sum(values_prod_dt[:i])

    base_idx = min(exclude_injection_before_idx, len(values_inj_dt))
    excluded_injection = cumulative_inj[base_idx]

    for raw_idx in cycle_data.EndofWithdrawal:
        idx = min(raw_idx, len(values_inj_dt), len(values_prod_dt))
        operational_injection = cumulative_inj[idx] - excluded_injection
        if operational_injection != 0:
            rf_step = abs(cumulative_prod[idx]) / abs(operational_injection)
        else:
            rf_step = 0.0
        rf_values.append(rf_step)

    return rf_values, excluded_injection


def load_simulation_json(json_path: Path) -> dict[str, object] | None:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return None

    required_keys = {"time", "InjectionValues_dt", "ProductionValues_dt"}
    if not required_keys.issubset(data):
        return None

    return data


def safe_time_days(time_seconds: list[float], idx: int) -> float:
    if not time_seconds:
        return 0.0
    if idx >= len(time_seconds):
        return time_seconds[-1] / SECONDS_PER_DAY
    return time_seconds[idx] / SECONDS_PER_DAY


def process_file(
    json_path: Path,
    case: dict[str, object],
    component: str,
    cycle_count: int,
    exclude_development_injection: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    data = load_simulation_json(json_path)
    if data is None:
        raise ValueError("not a simulation output JSON with time/injection/production data")

    injection_values = data["InjectionValues_dt"]
    production_values = data["ProductionValues_dt"]
    if component not in injection_values or component not in production_values:
        raise KeyError(f"component '{component}' not found in injection/production data")

    time_seconds = [float(value) for value in data["time"]]
    values_inj_dt = [float(value) for value in injection_values[component]]
    values_prod_dt = [float(value) for value in production_values[component]]

    n_values = min(len(time_seconds), len(values_inj_dt), len(values_prod_dt))
    time_seconds = time_seconds[:n_values]
    values_inj_dt = values_inj_dt[:n_values]
    values_prod_dt = values_prod_dt[:n_values]

    cycle_data = cycles(case, time_seconds)
    if exclude_development_injection:
        development_end_idx = first_index_at_or_after(
            time_seconds,
            development_duration_seconds(case),
        )
    else:
        development_end_idx = 0

    rf_values, excluded_injection = calculate_rf(
        values_inj_dt,
        values_prod_dt,
        cycle_data,
        exclude_injection_before_idx=development_end_idx,
    )
    rf_values = rf_values[:cycle_count]
    if len(rf_values) < cycle_count:
        raise ValueError(
            f"only {len(rf_values)} withdrawal-cycle RF values found; "
            f"{cycle_count} required"
        )
    withdrawal_indices = cycle_data.EndofWithdrawal[: len(rf_values)]

    label = str(case["name"])
    wide_row: dict[str, object] = {
        "label": label,
        "json_file": json_path.name,
        "FieldName": case.get("FieldName", ""),
        "CycleLength_d": case.get("CycleLength_d", ""),
        "Permeability_mD": case.get("Permeability_mD", ""),
        "Pressure_bar": case.get("Pressure_bar", ""),
        "PredictedRF": case.get("PredictedRF", ""),
        "n_rf_values": len(rf_values),
        "RF_denominator": (
            "operational_injection_only"
            if exclude_development_injection
            else "development_plus_operational_injection"
        ),
        f"excluded_development_injection_{component}": excluded_injection,
    }

    long_rows: list[dict[str, object]] = []
    for cycle_number in range(1, cycle_count + 1):
        rf_value = rf_values[cycle_number - 1] if cycle_number <= len(rf_values) else ""
        endpoint_idx = (
            withdrawal_indices[cycle_number - 1]
            if cycle_number <= len(withdrawal_indices)
            else ""
        )
        endpoint_days = (
            safe_time_days(time_seconds, int(endpoint_idx))
            if endpoint_idx != ""
            else ""
        )
        wide_row[f"RF_{cycle_number:02d}"] = rf_value
        long_rows.append(
            {
                "label": label,
                "json_file": json_path.name,
                "FieldName": case.get("FieldName", ""),
                "cycle": cycle_number,
                "time_days": endpoint_days,
                "RF": rf_value,
            }
        )

    rf_10 = wide_row.get("RF_10", "")
    rf_15 = wide_row.get("RF_15", "")
    if rf_10 != "" and rf_15 != "":
        wide_row["delta_RF_15_minus_10"] = float(rf_15) - float(rf_10)
    else:
        wide_row["delta_RF_15_minus_10"] = ""

    return wide_row, long_rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict[str, object]], cycle_count: int) -> list[dict[str, object]]:
    summary_rows: list[dict[str, object]] = []
    for cycle_number in range(1, cycle_count + 1):
        values = [
            float(row[f"RF_{cycle_number:02d}"])
            for row in rows
            if row.get(f"RF_{cycle_number:02d}") != ""
        ]
        if not values:
            summary_rows.append(
                {
                    "cycle": cycle_number,
                    "count": 0,
                    "RF_mean": "",
                    "RF_min": "",
                    "RF_max": "",
                    "RF_std": "",
                }
            )
            continue

        summary_rows.append(
            {
                "cycle": cycle_number,
                "count": len(values),
                "RF_mean": mean(values),
                "RF_min": min(values),
                "RF_max": max(values),
                "RF_std": pstdev(values) if len(values) > 1 else 0.0,
            }
        )

    return summary_rows


def build_percent_variation_rows(
    rows: list[dict[str, object]],
    start_cycle: int = 10,
    end_cycle: int = 15,
) -> list[dict[str, object]]:
    percent_rows: list[dict[str, object]] = []
    baseline_key = f"RF_{start_cycle:02d}"

    for row in rows:
        baseline_value = row.get(baseline_key)
        if baseline_value in ("", None):
            continue

        baseline_rf = float(baseline_value)
        if baseline_rf == 0.0:
            continue

        for cycle_number in range(start_cycle, end_cycle + 1):
            cycle_key = f"RF_{cycle_number:02d}"
            rf_value = row.get(cycle_key)
            if rf_value in ("", None):
                continue

            rf = float(rf_value)
            delta_rf = rf - baseline_rf
            percent_rows.append(
                {
                    "label": row["label"],
                    "json_file": row["json_file"],
                    "FieldName": row.get("FieldName", ""),
                    "cycle": cycle_number,
                    "baseline_cycle": start_cycle,
                    "RF_baseline": baseline_rf,
                    "RF": rf,
                    "delta_RF": delta_rf,
                    "delta_RF_percent": 100.0 * delta_rf / baseline_rf,
                }
            )

    return percent_rows


def short_label(label: object) -> str:
    text = str(label)
    if text.startswith("H2-"):
        text = text[3:]
    return text


def rf_cycle_values(row: dict[str, object]) -> tuple[list[int], list[float]]:
    cycles_x: list[int] = []
    rf_y: list[float] = []
    for key, value in row.items():
        if not key.startswith("RF_") or not key[3:].isdigit() or value == "":
            continue
        cycles_x.append(int(key.split("_")[1]))
        rf_y.append(float(value))

    paired = sorted(zip(cycles_x, rf_y))
    return [cycle for cycle, _ in paired], [rf for _, rf in paired]


def percent_deviation_values(
    row: dict[str, object],
    start_cycle: int = 10,
    end_cycle: int = 15,
) -> tuple[list[int], list[float]]:
    baseline = row.get(f"RF_{start_cycle:02d}")
    if baseline in ("", None):
        return [], []

    baseline_rf = float(baseline)
    if baseline_rf == 0.0:
        return [], []

    cycles_x: list[int] = []
    deviation_y: list[float] = []
    for cycle_number in range(start_cycle, end_cycle + 1):
        rf_value = row.get(f"RF_{cycle_number:02d}")
        if rf_value in ("", None):
            continue
        cycles_x.append(cycle_number)
        deviation_y.append(100.0 * (float(rf_value) - baseline_rf) / baseline_rf)

    return cycles_x, deviation_y


def plot_behavior(rows: list[dict[str, object]], summary_rows: list[dict[str, object]], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    for row in rows:
        cycles_x, rf_y = rf_cycle_values(row)
        ax.plot(cycles_x, rf_y, color="0.72", linewidth=0.9, alpha=0.85)

    cycles_x = [int(row["cycle"]) for row in summary_rows if row["RF_mean"] != ""]
    mean_y = [float(row["RF_mean"]) for row in summary_rows if row["RF_mean"] != ""]
    min_y = [float(row["RF_min"]) for row in summary_rows if row["RF_min"] != ""]
    max_y = [float(row["RF_max"]) for row in summary_rows if row["RF_max"] != ""]

    ax.fill_between(cycles_x, min_y, max_y, color="0.88", alpha=0.75, linewidth=0)
    ax.plot(cycles_x, mean_y, color="#111111", linewidth=2.2, label="Mean RF")
    ax.set_xlabel("Withdrawal cycle number [-]")
    ax.set_ylabel("Recovery factor [-]")
    max_cycle = max(cycles_x) if cycles_x else DEFAULT_CYCLES
    ax.set_xlim(0, max_cycle)
    ax.set_ylim(0.7, 1.0)
    ax.set_xticks([0, 5, 10, 15])
    ax.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax.set_box_aspect(1)
    ax.grid(True, color="0.88", linewidth=0.8)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def plot_cycle_10_to_15_variation(rows: list[dict[str, object]], path: Path) -> None:
    import matplotlib.pyplot as plt

    complete_rows = [
        row
        for row in rows
        if row.get("RF_10") != ""
        and row.get("RF_15") != ""
        and row.get("delta_RF_15_minus_10") != ""
    ]
    complete_rows.sort(key=lambda row: float(row["delta_RF_15_minus_10"]))

    labels = [short_label(row["label"]) for row in complete_rows]
    deltas = [float(row["delta_RF_15_minus_10"]) for row in complete_rows]
    rf_10 = [float(row["RF_10"]) for row in complete_rows]
    rf_15 = [float(row["RF_15"]) for row in complete_rows]
    positions = list(range(len(complete_rows)))

    fig, (ax_delta, ax_pair) = plt.subplots(
        1,
        2,
        figsize=(12.0, 6.2),
        gridspec_kw={"width_ratios": [1.0, 1.15]},
        sharey=True,
    )

    ax_delta.barh(positions, deltas, color="#4477aa", height=0.64)
    ax_delta.axvline(0.0, color="0.25", linewidth=0.8)
    ax_delta.set_xlabel(r"$RF_{15} - RF_{10}$ [-]")
    ax_delta.set_ylabel("Simulation label")
    ax_delta.set_yticks(positions)
    ax_delta.set_yticklabels(labels, fontsize=8)
    ax_delta.grid(True, axis="x", color="0.88", linewidth=0.8)

    for pos, x10, x15 in zip(positions, rf_10, rf_15):
        ax_pair.plot([x10, x15], [pos, pos], color="0.55", linewidth=1.2)
    ax_pair.scatter(rf_10, positions, color="#cc6677", label="Cycle 10", zorder=3)
    ax_pair.scatter(rf_15, positions, color="#117733", label="Cycle 15", zorder=3)
    ax_pair.set_xlabel("Recovery factor [-]")
    ax_pair.grid(True, axis="x", color="0.88", linewidth=0.8)
    ax_pair.legend(frameon=False, loc="lower right")

    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def plot_percent_variation_from_cycle_10(
    rows: list[dict[str, object]],
    path: Path,
    start_cycle: int = 10,
    end_cycle: int = 15,
) -> None:
    import matplotlib.pyplot as plt

    complete_rows = [
        row
        for row in rows
        if all(row.get(f"RF_{cycle_number:02d}") not in ("", None)
               for cycle_number in range(start_cycle, end_cycle + 1))
    ]

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    cycle_numbers = list(range(start_cycle, end_cycle + 1))
    all_percent_values: list[list[float]] = []

    for row in complete_rows:
        cycles_x, percent_values = percent_deviation_values(row, start_cycle, end_cycle)
        if len(percent_values) != len(cycle_numbers):
            continue
        all_percent_values.append(percent_values)
        ax.plot(cycles_x, percent_values, color="0.72", linewidth=0.9, alpha=0.85)

    if all_percent_values:
        mean_values = [
            mean(values[cycle_idx] for values in all_percent_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        min_values = [
            min(values[cycle_idx] for values in all_percent_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        max_values = [
            max(values[cycle_idx] for values in all_percent_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        ax.fill_between(
            cycle_numbers,
            min_values,
            max_values,
            color="0.88",
            alpha=0.75,
            linewidth=0,
        )
        ax.plot(
            cycle_numbers,
            mean_values,
            color="#111111",
            linewidth=2.2,
            label="Mean deviation",
        )

    ax.axhline(0.0, color="0.25", linewidth=0.8)
    ax.set_xlabel("Withdrawal cycle number [-]")
    ax.set_ylabel("Deviation from RF at cycle 10 [%]")
    ax.set_xlim(start_cycle, end_cycle)
    ax.set_xticks(cycle_numbers)
    ax.set_box_aspect(1)
    ax.grid(True, color="0.88", linewidth=0.8)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def plot_paper_combined(
    rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
    path: Path,
    start_cycle: int = 10,
    end_cycle: int = 15,
) -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
        }
    )

    fig, (ax_rf, ax_dev) = plt.subplots(1, 2, figsize=(7.2, 3.7))

    for row in rows:
        cycles_x, rf_y = rf_cycle_values(row)
        ax_rf.plot(cycles_x, rf_y, color="0.68", linewidth=0.8, alpha=0.85)

    cycles_x = [int(row["cycle"]) for row in summary_rows if row["RF_mean"] != ""]
    mean_y = [float(row["RF_mean"]) for row in summary_rows if row["RF_mean"] != ""]
    min_y = [float(row["RF_min"]) for row in summary_rows if row["RF_min"] != ""]
    max_y = [float(row["RF_max"]) for row in summary_rows if row["RF_max"] != ""]

    ax_rf.fill_between(cycles_x, min_y, max_y, color="0.88", alpha=0.8, linewidth=0)
    ax_rf.plot(cycles_x, mean_y, color="0.0", linewidth=1.8, label="Mean")
    ax_rf.set_xlim(0, 15)
    ax_rf.set_ylim(0.7, 1.0)
    ax_rf.set_xticks([0, 5, 10, 15])
    ax_rf.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax_rf.set_xlabel("Withdrawal cycle number [-]")
    ax_rf.set_ylabel("Recovery factor [-]")
    ax_rf.set_title("(a) Recovery factor")
    ax_rf.grid(True, color="0.88", linewidth=0.7)
    ax_rf.legend(frameon=False, loc="lower right")
    ax_rf.set_box_aspect(1)

    cycle_numbers = list(range(start_cycle, end_cycle + 1))
    all_deviation_values: list[list[float]] = []
    for row in rows:
        cycles_dev, deviation_y = percent_deviation_values(row, start_cycle, end_cycle)
        if len(deviation_y) != len(cycle_numbers):
            continue
        all_deviation_values.append(deviation_y)
        ax_dev.plot(cycles_dev, deviation_y, color="0.68", linewidth=0.8, alpha=0.85)

    if all_deviation_values:
        mean_dev = [
            mean(values[cycle_idx] for values in all_deviation_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        min_dev = [
            min(values[cycle_idx] for values in all_deviation_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        max_dev = [
            max(values[cycle_idx] for values in all_deviation_values)
            for cycle_idx in range(len(cycle_numbers))
        ]
        ax_dev.fill_between(
            cycle_numbers,
            min_dev,
            max_dev,
            color="0.88",
            alpha=0.8,
            linewidth=0,
        )
        ax_dev.plot(cycle_numbers, mean_dev, color="0.0", linewidth=1.8, label="Mean")

    ax_dev.axhline(0.0, color="0.25", linewidth=0.8)
    ax_dev.set_xlim(start_cycle, end_cycle)
    ax_dev.set_xticks(cycle_numbers)
    ax_dev.set_xlabel("Withdrawal cycle number [-]")
    ax_dev.set_ylabel("Deviation from RF at cycle 10 [%]")
    ax_dev.set_title("(b) Deviation from 10th-cycle RF")
    ax_dev.grid(True, color="0.88", linewidth=0.7)
    ax_dev.legend(frameon=False, loc="lower left")
    ax_dev.set_box_aspect(1)

    fig.tight_layout(w_pad=2.0)
    fig.savefig(path, dpi=600, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    cases_path = args.cases
    output_dir = args.output_dir
    cycle_count = args.cycles
    exclude_development_injection = not args.include_development_injection

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not cases_path.exists():
        raise FileNotFoundError(f"Case file does not exist: {cases_path}")

    case_by_label = load_cases(cases_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    wide_rows: list[dict[str, object]] = []
    long_rows: list[dict[str, object]] = []
    skipped: list[str] = []

    for json_path in sorted(input_dir.glob(args.pattern)):
        label = json_path.stem
        case = case_by_label.get(label)
        if case is None:
            skipped.append(f"{json_path.name}: no matching case label")
            continue

        try:
            wide_row, case_long_rows = process_file(
                json_path,
                case,
                args.component,
                cycle_count,
                exclude_development_injection,
            )
        except Exception as exc:
            skipped.append(f"{json_path.name}: {exc}")
            continue

        wide_rows.append(wide_row)
        long_rows.extend(case_long_rows)

    if not wide_rows:
        for item in skipped:
            warnings.warn(item)
        raise RuntimeError(f"No RF rows were calculated from {input_dir}")

    wide_rows.sort(key=lambda row: str(row["label"]))
    long_rows.sort(key=lambda row: (str(row["label"]), int(row["cycle"])))
    summary_rows = build_summary(wide_rows, cycle_count)
    percent_variation_rows = build_percent_variation_rows(wide_rows)

    wide_fields = [
        "label",
        "json_file",
        "FieldName",
        "CycleLength_d",
        "Permeability_mD",
        "Pressure_bar",
        "PredictedRF",
        "n_rf_values",
        "RF_denominator",
        f"excluded_development_injection_{args.component}",
    ]
    wide_fields.extend(f"RF_{cycle_number:02d}" for cycle_number in range(1, cycle_count + 1))
    wide_fields.append("delta_RF_15_minus_10")

    write_csv(output_dir / "rf_15_cycle_values.csv", wide_rows, wide_fields)
    write_csv(
        output_dir / "rf_15_cycle_long.csv",
        long_rows,
        ["label", "json_file", "FieldName", "cycle", "time_days", "RF"],
    )
    write_csv(
        output_dir / "rf_15_cycle_summary.csv",
        summary_rows,
        ["cycle", "count", "RF_mean", "RF_min", "RF_max", "RF_std"],
    )
    write_csv(
        output_dir / "rf_percent_variation_cycle_10_to_15.csv",
        percent_variation_rows,
        [
            "label",
            "json_file",
            "FieldName",
            "cycle",
            "baseline_cycle",
            "RF_baseline",
            "RF",
            "delta_RF",
            "delta_RF_percent",
        ],
    )

    if not args.no_plot:
        plot_behavior(wide_rows, summary_rows, output_dir / "rf_15_cycle_behavior.png")
        plot_behavior(wide_rows, summary_rows, output_dir / "rf_values_cycle_1_to_15.png")
        plot_percent_variation_from_cycle_10(
            wide_rows,
            output_dir / "rf_percent_variation_cycle_10_to_15.png",
        )
        plot_paper_combined(
            wide_rows,
            summary_rows,
            output_dir / "rf_paper_combined.png",
        )

    for item in skipped:
        warnings.warn(item)

    print(f"Calculated RF for {len(wide_rows)} simulations.")
    print(f"Wrote outputs to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
