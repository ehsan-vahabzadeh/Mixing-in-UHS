"""
Compute dimensionless numbers (Pe, Ng, Fo, theta) and recovery factor per cycle
from simulation JSON outputs, then export a summary table.

Expected JSON filename format:
<CushionGas>-<FlowRate>-<CycleLength>-<Permeability>-<pressure>-<temperature>-<porosityPercent>-<CG>.json
"""

from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.ndimage import gaussian_filter
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay


# -----------------------------
# Physics helpers
# -----------------------------
def get_molecular_diffusivity(pressure_bar: int, gas_type: str) -> float:
    """Return constant molecular diffusivity [m^2/s] used in this study."""
    if gas_type == "H2":
        return 3.4831e-07
    if gas_type == "CH4":
        return 1.5324e-07
    if gas_type == "CO2":
        return 1.4056e-07
    if gas_type == "N2":
        return 1.6933e-07
    raise ValueError(f"Unknown gas type: {gas_type}")


def isothermal_cf(P: float, T: float, gas: str, dP: float = 1e5) -> Tuple[float, float, float, str]:
    """
    Isothermal compressibility-like factor:
        c_f = (1/rho) * (drho/dP)_T

    Returns:
        (c_f [1/Pa], rho [kg/m3], Z [-], method)
    """
    R = 8.31446261815324  # J/(mol*K)

    gases = {
        "CO2": {"M": 44.0095e-3},
        "H2": {"M": 2.01588e-3},
        "N2": {"M": 28.0134e-3},
        "CH4": {"M": 16.04246e-3},
    }
    if gas not in gases:
        raise ValueError(f"Unsupported gas for isothermal_cf: {gas}")

    rho = PropsSI("D", "P", P, "T", T, gas)
    Pm, Pp = max(P - dP, 100.0), P + dP
    rho_m = PropsSI("D", "P", Pm, "T", T, gas)
    rho_p = PropsSI("D", "P", Pp, "T", T, gas)
    drhodP = (rho_p - rho_m) / (Pp - Pm)

    Z = P * gases[gas]["M"] / (rho * R * T)
    return (drhodP / rho), rho, Z, "CoolProp"


# -----------------------------
# Parsing helpers
# -----------------------------
def extract_simulation_params_from_filename(filename: str) -> Dict[str, Any]:
    """
    Parse parameters from filename:
    CushionGas-FlowRate-CycleLength-Permeability-pressure-temperature-porosityPercent-CG.json
    """
    parts = filename.split("-")
    if len(parts) != 8:
        raise ValueError(f"Filename {filename} doesn't match the expected format")

    cushion_gas_type = parts[0]
    flow_rate = float(parts[1])
    cycle_length_days = int(parts[2])
    permeability_md = float(parts[3])
    pressure_bar = int(parts[4])
    temperature_k = int(parts[5])
    porosity = float(parts[6]) / 100.0
    cg_ratio = float(parts[7].replace(".json", ""))

    injection_duration_dev_days = cg_ratio * cycle_length_days / 2.0
    injection_duration_op_days = cycle_length_days / 2.0
    extraction_duration_op_days = cycle_length_days / 2.0

    return {
        "CushionGasType": cushion_gas_type,
        "FlowRate": flow_rate,
        "CycleLength": cycle_length_days,
        "Permeability": permeability_md,
        "pressure": pressure_bar,
        "temperature": temperature_k,
        "porosity": porosity,
        "CG": cg_ratio,
        "InjectionDurationDev": injection_duration_dev_days,
        "InjectionDurationOp": injection_duration_op_days,
        "ExtractionDurationOp": extraction_duration_op_days,
        "name": filename,
    }


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


@dataclass
class CycleData:
    end_of_withdrawal: List[int]
    end_of_injection: List[int]


def get_cycle_end_indices(params: Dict[str, Any], time_seconds: Sequence[float]) -> CycleData:
    end_of_withdrawal: List[int] = []
    end_of_injection: List[int] = []

    injection_duration_dev = params["InjectionDurationDev"] * 86400.0
    injection_duration_op = params["InjectionDurationOp"] * 86400.0

    qq = 1
    for ii in range(len(time_seconds)):
        if time_seconds[ii] - qq * injection_duration_op - injection_duration_dev >= 0:
            if qq % 2 == 0:
                end_of_withdrawal.append(ii)
            else:
                end_of_injection.append(ii)
            qq += 1

    end_of_withdrawal.append(len(time_seconds))
    return CycleData(end_of_withdrawal, end_of_injection)


def compute_recovery_factor(
    values_inj_dt: np.ndarray,
    values_prod_dt: np.ndarray,
    cycle_data: CycleData,
    end_of_cg_index: int,
) -> np.ndarray:
    rf_values: List[float] = []

    cumulative_inj = np.zeros(len(values_inj_dt) + 1)
    cumulative_prod = np.zeros(len(values_prod_dt) + 1)

    for i in range(end_of_cg_index, len(values_inj_dt) + 1):
        cumulative_inj[i] = np.sum(values_inj_dt[end_of_cg_index:i])
        cumulative_prod[i] = np.sum(values_prod_dt[end_of_cg_index:i])

    for i in cycle_data.end_of_withdrawal:
        denom = abs(cumulative_inj[i])
        rf_step = abs(cumulative_prod[i]) / denom if denom != 0 else 0.0
        rf_values.append(rf_step)

    return np.asarray(rf_values)


# -----------------------------
# Velocity metrics reading
# -----------------------------
def read_velocity_metrics(
    json_files: Sequence[str] | str,
    target_label: str,
    input_directory: str,
    cycle_no: int,
) -> Optional[Tuple[Any, ...]]:
    """
    Read cycle-wise velocity/geometry metrics from a separate JSON file like "<folder>.json".
    Returns a tuple of metrics or None if not found.
    """
    if isinstance(json_files, str):
        json_files = [json_files]

    target_label = os.path.splitext(os.path.basename(target_label))[0]

    for jf in json_files:
        json_path = os.path.join(input_directory, jf)
        if not os.path.exists(json_path):
            continue

        with open(json_path, "r") as f:
            data = json.load(f)

        for entry in data:
            if entry.get("label") != target_label:
                continue

            all_cycle_data: List[Tuple[Any, ...]] = []
            for cd in entry.get("injection_end_data", []):
                all_cycle_data.append(
                    (
                        cd.get("avg_vx"),
                        cd.get("max_x_valid"),
                        cd.get("simga_rz"),
                        cd.get("tip_velocity"),
                        cd.get("simga_rr"),
                        cd.get("avg_vx_z"),
                        cd.get("avg_vx_z_rev"),
                        cd.get("avg_vx_x_H2"),
                        cd.get("avg_vx_x_H2_rev"),
                        cd.get("avg_mass_velocity"),
                        cd.get("vx_inlet"),
                        cd.get("height"),
                        cd.get("max_pressure"),
                    )
                )

            if not all_cycle_data:
                return None

            if len(all_cycle_data) < cycle_no:
                return all_cycle_data[-1]
            return all_cycle_data[cycle_no]

    return None


# -----------------------------
# Main extraction routine
# -----------------------------
def extract_metrics_for_directory(input_directory: str, cycle_numbers: Sequence[int]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    json_files = [f for f in os.listdir(input_directory) if f.endswith(".json")]
    for json_file in json_files:
        try:
            params = extract_simulation_params_from_filename(json_file)
            data = load_json(os.path.join(input_directory, json_file))

            time_seconds = data["time"]
            values_inj_dt = np.asarray(data["InjectionValues_dt"]["H2"])
            values_prod_dt = np.asarray(data["ProductionValues_dt"]["H2"])

            end_of_cg = 0
            if params["CG"] > 0.0:
                cg_end_time = params["InjectionDurationDev"] * 86400.0
                for ii, t in enumerate(time_seconds):
                    if t > cg_end_time:
                        end_of_cg = ii
                        break

            cycle_data = get_cycle_end_indices(params, time_seconds)
            rf = compute_recovery_factor(values_inj_dt, values_prod_dt, cycle_data, end_of_cg)

            # Thermophysical properties
            P = params["pressure"] * 1e5
            T = params["temperature"]

            # Note: you use "Hydrogen" here and "H2" elsewhere. Kept as-is.
            h2_density = PropsSI("D", "P", P, "T", T, "Hydrogen")
            h2_visc = PropsSI("VISCOSITY", "P", P, "T", T, "Hydrogen")

            cg_type = params["CushionGasType"]
            cg_density = PropsSI("D", "P", P, "T", T, cg_type)
            cg_visc = PropsSI("VISCOSITY", "P", P, "T", T, cg_type)

            cf_h2 = isothermal_cf(P, T, "H2")[0]
            cf_cg = isothermal_cf(P, T, cg_type)[0]

            if cg_type == "H2":
                cg_density = h2_density
                cg_visc = h2_visc

            porosity = params["porosity"]
            perm = params["Permeability"] * 9.869233e-16  # m^2
            folder_tag = os.path.basename(input_directory)
            velocity_db_filename = f"{folder_tag}.json"

            for cj in cycle_numbers:
                vel_tuple = read_velocity_metrics(velocity_db_filename, json_file, input_directory, cj)
                if vel_tuple is None:
                    warnings.warn(f"Missing velocity metrics for {json_file} (cycle {cj}). Skipping.")
                    continue

                (
                    velocity,
                    length,
                    sigma_rz,
                    tip_velocity,
                    sigma_rr,
                    avg_vx_z,
                    avg_vx_z_rev,
                    avg_vx_x_h2,
                    avg_vx_x_h2_rev,
                    avg_mass_velocity,
                    vx_inlet,
                    height,
                    max_pressure,
                ) = vel_tuple

                # Guardrails (kept logic)
                if len(rf) < 10:
                    warnings.warn("RF too short, skipping: " + json_file)
                    rf_safe = np.zeros(10)
                    results.append(
                        {
                            "label": params["name"],
                            "FlowRate": params["FlowRate"],
                            "CycleLength": params["CycleLength"],
                            "Permeability": params["Permeability"],
                            "porosity": porosity,
                            "Pressure": params["pressure"],
                            "Temperature": params["temperature"],
                            "Pe": 0.0,
                            "Ng": 0.0,
                            "theta": 0.0,
                            "Fo": 0.0,
                            "Cycle_No": cj,
                            "rf": rf_safe[cj],
                            "delta_rho": cg_density - h2_density,
                            "max_pressure": max_pressure,
                        }
                    )
                    continue

                if max_pressure / 1e5 > 1.5 * params["pressure"]:
                    warnings.warn("Overpressure threshold hit, skipping: " + json_file)
                    results.append(
                        {
                            "label": params["name"],
                            "FlowRate": params["FlowRate"],
                            "CycleLength": params["CycleLength"],
                            "Permeability": params["Permeability"],
                            "porosity": porosity,
                            "Pressure": params["pressure"],
                            "Temperature": params["temperature"],
                            "Pe": 0.0,
                            "Ng": 0.0,
                            "theta": 0.0,
                            "Fo": 0.0,
                            "Cycle_No": cj,
                            "rf": rf[cj],
                            "delta_rho": cg_density - h2_density,
                            "max_pressure": max_pressure,
                        }
                    )
                    continue

                pore_velocity = velocity / porosity

                diffusion = get_molecular_diffusivity(params["pressure"], params["CushionGasType"])

                pe = (pore_velocity * length) / (diffusion + 0.5 * sigma_rr / (params["CycleLength"] * 86400.0 / 2.0))
                fo = (pore_velocity * params["CycleLength"] * 86400.0 / 2.0) / length
                theta = (h2_density / cg_density) * (cf_h2 / cf_cg)

                ng = ((perm / 10.0) * (cg_density - h2_density) * 9.81 * length) / (h2_visc * pore_velocity * height * porosity)

                results.append(
                    {
                        "label": params["name"],
                        "FlowRate": params["FlowRate"],
                        "CycleLength": params["CycleLength"],
                        "Permeability": params["Permeability"],
                        "porosity": porosity,
                        "Pressure": params["pressure"],
                        "Temperature": params["temperature"],
                        "delta_rho": cg_density - h2_density,
                        "theta": theta,
                        "Fo": fo,
                        "Cycle_No": cj,
                        "rf": rf[cj],
                        "CG Ratio": params["CG"],
                        "Pe": pe,
                        "Ng": ng,
                        "max_pressure": max_pressure,
                    }
                )

        except Exception as e:
            warnings.warn(f"Skipping {json_file} due to error: {e}")
            continue

    results.sort(key=lambda x: x["rf"])
    return results


def save_results_to_excel(results: Sequence[Dict[str, Any]], output_path: str) -> None:
    rows = []
    for res in results:
        row = dict(res)
        row["CushionGas"] = row["label"].split("-")[0]
        rows.append(row)

    df = pd.DataFrame(rows)
    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name="AllResults", index=False)

    print(f"Results saved to: {output_path}")


# -----------------------------
# Plotting (kept as script-style)
# -----------------------------
def plot_pe_ng_rf(pe: np.ndarray, ng: np.ndarray, rf: np.ndarray) -> None:
    x, y, z = pe, ng, np.clip(rf, 0.0, 1.0)

    xi = np.linspace(x.min(), x.max(), 200)
    yi = np.linspace(y.min(), y.max(), 200)
    Xi, Yi = np.meshgrid(xi, yi)

    tri = Delaunay(np.column_stack([x, y]))
    lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
    Zi = lin(Xi, Yi)

    mask = np.isnan(Zi)
    Zi_smooth = Zi.copy()
    Zi_smooth[~mask] = gaussian_filter(Zi[~mask], sigma=1)

    fig, ax = plt.subplots(1, 3, figsize=(12, 6))
    fig.subplots_adjust(wspace=0.1)

    ax[0].contourf(Xi, Yi, Zi_smooth, cmap="plasma")
    ax[0].set_xlabel("Pe [-]", fontsize=18)
    ax[0].set_ylabel("Ng [-]", fontsize=18)
    ax[0].tick_params(axis="both", labelsize=18)

    sc1 = ax[1].scatter(pe, rf, c=rf, cmap="plasma", edgecolor="k")
    ax[1].set_xlabel("Pe [-]", fontsize=18)
    ax[1].set_ylabel("RF [-]", fontsize=18)
    ax[1].tick_params(axis="both", labelsize=18)

    sc2 = ax[2].scatter(ng, rf, c=rf, cmap="plasma", edgecolor="k")
    ax[2].set_xlabel("Ng [-]", fontsize=18)
    ax[2].set_ylabel("RF [-]", fontsize=18)
    ax[2].tick_params(axis="both", labelsize=18)

    cbar = plt.colorbar(sc2, ax=ax[2])
    cbar.ax.tick_params(labelsize=18)
    cbar.set_label("Recovery Factor [-]", fontsize=18)

    plt.tight_layout()
    plt.show()


def main() -> None:
    base_input_dir = r"Y:\Mixing Results\July"
    gas_types = ["H2", "CO2", "CH4", "N2"]
    cycle_numbers = list(range(10))

    all_results: List[Dict[str, Any]] = []
    for gas in gas_types:
        gas_dir = os.path.join(base_input_dir, gas)
        if not os.path.exists(gas_dir):
            print(f"Skipping missing folder: {gas_dir}")
            continue
        all_results.extend(extract_metrics_for_directory(gas_dir, cycle_numbers))

    all_results.sort(key=lambda x: x["rf"])

    out_xlsx = os.path.join(base_input_dir, "mixing_results_withoutCG_allcycles.xlsx")
    save_results_to_excel(all_results, out_xlsx)

    # Prepare arrays for plotting (this uses the keys actually written above)
    rf_vals = np.asarray([d["rf"] for d in all_results if d["rf"] > 0 and d["Pe"] > 0 and not np.isnan(d["Pe"])])
    pe_vals = np.asarray([d["Pe"] for d in all_results if d["rf"] > 0 and d["Pe"] > 0 and not np.isnan(d["Pe"])])
    ng_vals = np.asarray([d["Ng"] for d in all_results if d["rf"] > 0 and d["Pe"] > 0 and not np.isnan(d["Pe"])])

    if len(rf_vals) > 0:
        plot_pe_ng_rf(pe_vals, ng_vals, rf_vals)


if __name__ == "__main__":
    main()
