import argparse
import glob
import os
from dataclasses import dataclass
from pathlib import Path

import gurobipy as gp
import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI
from gurobipy import GRB


# ---------------- USER SETTINGS ----------------
INPUT_DIR = Path(r"Y:\Mixing Results\July")
OUTPUT_ROOT = INPUT_DIR / "Two Term Equation Discounted CAPEX"

DISCOUNT_RATES = [0.04, 0.07, 0.10]
H2_COSTS_PER_KG = [3.0, 4.0, 5.0]
PSA_MULTIPLIERS = [1, 10, 100]
CL_TARGETS = {
    14: [5],
    60: [15],
    180: [50],
    360: [100, 150, 200],
}

ALLOW_CG = True
WELL_BUDGET = None  # e.g., 500
NOC = 1  # number of cycles (currently unused)
YEARS_OF_INTEREST = np.array([1, 5, 10, 15, 20, 25, 30])
CAPEX_TREATMENT = "upfront"  # "upfront" keeps the previous behavior.
# ------------------------------------------------


T_STD = 293.15
P_STD_BAR = 1.01325
KG_PER_M3_STP = PropsSI("D", "P", P_STD_BAR * 1e5, "T", T_STD, "Hydrogen")
KWH_PER_KG_H2 = 39.41  # kWh/kg (HHV)
KWH_PER_M3 = KWH_PER_KG_H2 * KG_PER_M3_STP

WELL_COST = 2.9e5  # $ per well
COMPRESSOR_SIZE = 2000  # H2 kg per hour
COMPRESSOR_COST = 10200000  # $ per unit
COMPRESSOR_POWER = 2.2  # kWh per kg H2
COST_OF_ELECTRICITY = 0.14  # $ per kWh
WATER_REQUIREMENT = 50  # L/kg H2
COOLING_COST = 0.0002  # $ per 1 L H2O

PSA_LABELS = {
    1: "Low",
    10: "Med",
    100: "High",
}


@dataclass(frozen=True)
class Scenario:
    cl_days: int
    target_twh: int
    h2_cost_per_kg: float
    psa_multiplier: int

    @property
    def psa_label(self) -> str:
        return PSA_LABELS.get(self.psa_multiplier, f"PSA{self.psa_multiplier:g}")

    @property
    def dataset_folder(self) -> str:
        return f"optim_dataset_{self.cl_days}_H2_{self.h2_cost_per_kg:.1f}"

    @property
    def output_filename(self) -> str:
        return (
            f"optimal_plan_CL{self.cl_days}_TWh{self.target_twh}_"
            f"{self.psa_label}_H2{self.h2_cost_per_kg:.1f}.xlsx"
        )


def discount_folder_name(discount_rate: float) -> str:
    return f"DR_{int(round(discount_rate * 100)):02d}"


def default_output_root(input_dir: Path, capex_treatment: str) -> Path:
    if capex_treatment == "upfront":
        return input_dir / "Two Term Equation"
    if capex_treatment == "discounted_annual":
        return input_dir / "Two Term Equation Discounted CAPEX"
    raise ValueError(f"Unknown capex_treatment: {capex_treatment}")


def scenario_grid() -> list[Scenario]:
    scenarios: list[Scenario] = []
    for cl_days, targets in CL_TARGETS.items():
        for target_twh in targets:
            for h2_cost in H2_COSTS_PER_KG:
                for psa_multiplier in PSA_MULTIPLIERS:
                    scenarios.append(
                        Scenario(
                            cl_days=cl_days,
                            target_twh=target_twh,
                            h2_cost_per_kg=float(h2_cost),
                            psa_multiplier=int(psa_multiplier),
                        )
                    )
    return scenarios


def twh_to_m3(twh: float) -> float:
    return (twh * 1e9) / KWH_PER_M3


def save_cycles_to_excel(df_long: pd.DataFrame, out_xlsx: str = "rf_by_cycle.xlsx", cycle_col: str = "Cycle_No") -> None:
    """
    Utility to save cycle-grouped dataframes to separate Excel sheets.
    Not used in the current main flow, but kept.
    """
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        for cyc, g in df_long.groupby(cycle_col, sort=True):
            sheet = f"cycle_{int(cyc)}"[:31]
            g.to_excel(writer, sheet_name=sheet, index=False)


def find_cycle_csv(input_dir: Path, folder: str, sheet: str) -> Path:
    paths = sorted(glob.glob(str(input_dir / folder / f"{sheet}.csv")))
    if not paths:
        raise FileNotFoundError(f"No input CSV found for {input_dir / folder / f'{sheet}.csv'}")
    return Path(paths[0])


CAPITAL_COMPONENT_COLUMNS = [
    "Compressor Capital Cost [$]",
    "Well Capital Cost [$]",
    "Working Gas Cost [$]",
    "Cushion Gas Cost [$]",
    "Purification Capital Cost [$]",
]

PV_CAPITAL_COMPONENT_COLUMNS = [
    "PV Compressor Capital Cost [$]",
    "PV Well Capital Cost [$]",
    "PV Working Gas Cost [$]",
    "PV Cushion Gas Cost [$]",
    "PV Purification Capital Cost [$]",
]

CAPITAL_COMPONENT_DETAIL = [
    (
        "Compressor",
        "Compressor Capital Cost [$]",
        "PV Compressor Capital Cost [$]",
        "Compressor_Capital_Cost_M$",
        "PV_Compressor_Capital_Cost_M$",
        "Compressor_Capital_Share",
        "PV_Compressor_Capital_Share",
    ),
    (
        "Wells",
        "Well Capital Cost [$]",
        "PV Well Capital Cost [$]",
        "Well_Capital_Cost_M$",
        "PV_Well_Capital_Cost_M$",
        "Well_Capital_Share",
        "PV_Well_Capital_Share",
    ),
    (
        "Working gas",
        "Working Gas Cost [$]",
        "PV Working Gas Cost [$]",
        "Working_Gas_Cost_M$",
        "PV_Working_Gas_Cost_M$",
        "Working_Gas_Share",
        "PV_Working_Gas_Share",
    ),
    (
        "Cushion gas",
        "Cushion Gas Cost [$]",
        "PV Cushion Gas Cost [$]",
        "Cushion_Gas_Cost_M$",
        "PV_Cushion_Gas_Cost_M$",
        "Cushion_Gas_Share",
        "PV_Cushion_Gas_Share",
    ),
    (
        "PSA purification",
        "Purification Capital Cost [$]",
        "PV Purification Capital Cost [$]",
        "Purification_Capital_Cost_M$",
        "PV_Purification_Capital_Cost_M$",
        "Purification_Capital_Share",
        "PV_Purification_Capital_Share",
    ),
]

CAPITAL_COMPONENT_SUMMARY = [
    ("Compressor", "Compressor_Capital_Cost_M$", "Compressor_Capital_Share"),
    ("Wells", "Well_Capital_Cost_M$", "Well_Capital_Share"),
    ("Working gas", "Working_Gas_Cost_M$", "Working_Gas_Share"),
    ("Cushion gas", "Cushion_Gas_Cost_M$", "Cushion_Gas_Share"),
    ("PSA purification", "Purification_Capital_Cost_M$", "Purification_Capital_Share"),
]

LCOS_COMPONENT_DETAIL = [
    ("Compressor CAPEX", "PV_Compressor_Capital_Cost_M$"),
    ("Well CAPEX", "PV_Well_Capital_Cost_M$"),
    ("H2 working gas inventory", "PV_Working_Gas_Cost_M$"),
    ("H2 cushion gas inventory/placement", "PV_Cushion_Gas_Cost_M$"),
    ("H2 make-up / replacement", "PV_H2_Make_up_Cost_M$"),
    ("PSA CAPEX", "PV_Purification_Capital_Cost_M$"),
    ("WG compression OPEX", "PV_WG_Compression_OPEX_M$"),
    ("WG cooling OPEX", "PV_WG_Cooling_OPEX_M$"),
    ("WG other O&M", "PV_WG_Other_OM_M$"),
    ("PSA OPEX", "PV_PSA_OPEX_M$"),
]

LCOS_COMPONENT_GROUPS = [
    (
        "Compression system",
        ["PV_Compressor_Capital_Cost_M$", "PV_WG_Compression_OPEX_M$", "PV_WG_Cooling_OPEX_M$"],
    ),
    ("Wells / reservoir access", ["PV_Well_Capital_Cost_M$"]),
    ("H2 inventory", ["PV_Working_Gas_Cost_M$", "PV_Cushion_Gas_Cost_M$"]),
    ("H2 make-up / replacement", ["PV_H2_Make_up_Cost_M$"]),
    ("Purification system", ["PV_Purification_Capital_Cost_M$", "PV_PSA_OPEX_M$"]),
    ("Other operating services", ["PV_WG_Other_OM_M$"]),
]


def numeric_column(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def present_value_annuity_factor(discount_rate: float, years: int) -> float:
    return sum(1.0 / ((1.0 + discount_rate) ** y) for y in range(1, years + 1))


def capex_pv_factor(discount_rate: float, years: int, capex_treatment: str) -> float:
    """
    "upfront": previous behavior; CAPEX occurs at year 0, so PV factor is 1.
    "discounted_annual": spreads CAPEX evenly across the active horizon and
    discounts those annual capital tranches to present value.
    """
    if capex_treatment == "upfront":
        return 1.0
    if capex_treatment == "discounted_annual":
        return present_value_annuity_factor(discount_rate, years) / max(years, 1)
    raise ValueError(f"Unknown capex_treatment: {capex_treatment}")


def ensure_capital_breakdown(df: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """
    Preserve capital-cost components from generated datasets, or reconstruct them
    for legacy CSVs that only contain total Capital Cost [$].

    The cushion-gas bucket includes the CG inventory cost plus the upfront CG
    handling cost that the original generator included in Capital Cost [$].
    """
    wg_m3 = (
        numeric_column(df, "Flow Rate [sm3/d]")
        * numeric_column(df, "Number of Wells")
        * numeric_column(df, "Cycle Length [d]")
        / 2.0
    )
    cg_m3 = numeric_column(df, "CG injected [m3]", default=np.nan)
    cg_m3 = cg_m3.where(cg_m3.notna(), numeric_column(df, "CG Ratio") * wg_m3).fillna(0.0)

    total_hours = (
        numeric_column(df, "Cycle Length [d]") / 2.0 * 24.0
        + numeric_column(df, "Cycle Length [d]") / 2.0 * numeric_column(df, "CG Ratio") * 24.0
    )
    total_hours = total_hours.replace(0.0, np.nan)

    if "Compressor Capital Cost [$]" not in df.columns:
        df["Compressor Capital Cost [$]"] = (
            (wg_m3 + cg_m3) * KG_PER_M3_STP / (total_hours * COMPRESSOR_SIZE) * COMPRESSOR_COST
        ).fillna(0.0)
    else:
        df["Compressor Capital Cost [$]"] = numeric_column(df, "Compressor Capital Cost [$]")

    if "Well Capital Cost [$]" not in df.columns:
        df["Well Capital Cost [$]"] = numeric_column(df, "Number of Wells") * WELL_COST
    else:
        df["Well Capital Cost [$]"] = numeric_column(df, "Well Capital Cost [$]")

    if "Working Gas Cost [$]" not in df.columns:
        df["Working Gas Cost [$]"] = wg_m3 * KG_PER_M3_STP * scenario.h2_cost_per_kg
    else:
        df["Working Gas Cost [$]"] = numeric_column(df, "Working Gas Cost [$]")

    if "Cushion Gas Cost [$]" not in df.columns:
        cg_inventory_cost = cg_m3 * KG_PER_M3_STP * scenario.h2_cost_per_kg
        cg_handling_cost = cg_m3 * KG_PER_M3_STP * (
            COMPRESSOR_POWER * COST_OF_ELECTRICITY
            + COOLING_COST * WATER_REQUIREMENT
            + (0.05 + 0.0045)
        )
        df["Cushion Gas Cost [$]"] = cg_inventory_cost + cg_handling_cost
    else:
        df["Cushion Gas Cost [$]"] = numeric_column(df, "Cushion Gas Cost [$]")

    df["Capital Breakdown Total [$]"] = sum(numeric_column(df, col) for col in CAPITAL_COMPONENT_COLUMNS[:-1])
    base_capital = numeric_column(df, "Base Capital Cost [$]", default=np.nan)
    original_capital = numeric_column(df, "Capital Cost [$]", default=np.nan)
    df["Base Capital Cost [$]"] = base_capital.where(base_capital.notna(), original_capital)
    df["Base Capital Cost [$]"] = df["Base Capital Cost [$]"].where(
        df["Base Capital Cost [$]"].notna(), df["Capital Breakdown Total [$]"]
    )
    return df


def ensure_working_gas_opex_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct non-PSA working-gas OPEX components from existing scenario CSV
    columns using the same formulas as the scenario-generation code. Future CSVs
    may already contain these columns; when they do, preserve and numeric-clean
    them rather than overwriting.
    """
    wg_m3_per_cycle = (
        numeric_column(df, "Flow Rate [sm3/d]")
        * numeric_column(df, "Number of Wells")
        * numeric_column(df, "Cycle Length [d]")
        / 2.0
    )
    wg_kg_per_cycle = wg_m3_per_cycle * KG_PER_M3_STP

    if "WG Compression OPEX [$]" not in df.columns:
        df["WG Compression OPEX [$]"] = wg_kg_per_cycle * COMPRESSOR_POWER * COST_OF_ELECTRICITY
    else:
        df["WG Compression OPEX [$]"] = numeric_column(df, "WG Compression OPEX [$]")

    if "WG Cooling OPEX [$]" not in df.columns:
        df["WG Cooling OPEX [$]"] = wg_kg_per_cycle * WATER_REQUIREMENT * COOLING_COST
    else:
        df["WG Cooling OPEX [$]"] = numeric_column(df, "WG Cooling OPEX [$]")

    if "WG Other O&M [$]" not in df.columns:
        df["WG Other O&M [$]"] = wg_kg_per_cycle * (0.05 + 0.0045)
    else:
        df["WG Other O&M [$]"] = numeric_column(df, "WG Other O&M [$]")

    df["WG O&M Cost [$]"] = (
        df["WG Compression OPEX [$]"]
        + df["WG Cooling OPEX [$]"]
        + df["WG Other O&M [$]"]
    )
    return df


def load_scenarios(
    input_dir: Path,
    scenario: Scenario,
    discount_rate: float,
    capex_treatment: str = CAPEX_TREATMENT,
    allow_cg: bool = True,
    cyc: int = 0,
) -> pd.DataFrame:
    """
    Loads scenario candidates for a given cycle and computes derived quantities:
    - Lost energy
    - PV OPEX and upfront CAPEX
    - LCOS proxy
    - Objective column "Objective Cost [M$]"
    Adds res_id and cand_id for MILP grouping/selection.
    """
    sheet = "cycle_9" if cyc > 9 else f"cycle_{cyc}"
    csv_path = find_cycle_csv(input_dir, scenario.dataset_folder, sheet)
    df = pd.read_csv(csv_path)

    need = [
        "Field Name",
        "Cum H2 Produced [Twh]",
        "Net H2 Stored [m3]",
        "Cum CG Injected [Twh]",
        "Capital Cost [$]",
        "Number of Wells",
        "Flow Rate [sm3/d]",
        "Cycle Length [d]",
        "CG Ratio",
        "Predicted RF [-]",
        "Cum H2 Injected [Twh]",
        "LCOS",
    ]
    df = df.dropna(subset=need).reset_index(drop=True)

    if not allow_cg:
        df = df.loc[(df["CG Ratio"].fillna(0.0) == 0.0)].reset_index(drop=True)

    df = ensure_capital_breakdown(df, scenario)
    df = ensure_working_gas_opex_breakdown(df)

    # Per-cycle injection energy equivalent
    twh_per_cycle = (
        df["Flow Rate [sm3/d]"]
        * df["Number of Wells"]
        * df["Cycle Length [d]"]
        / 2
        * KWH_PER_M3
        / 1e9
    )

    df["Net H2 Stored [Twh]"] = df["Net H2 Stored [m3]"] * KWH_PER_M3 / 1e9

    psa_cap = 10.4702 * np.exp(-60.7137 * df["Predicted RF [-]"]) + 3.1879 * np.exp(
        -4.8854 * df["Predicted RF [-]"]
    )
    psa_cap = psa_cap * scenario.psa_multiplier
    df["PSA Cost [$/kg]"] = psa_cap

    psa_rec = 0.9
    psa_opex = psa_cap / 0.6 * 0.4

    # Cycle extrapolation logic
    if cyc > 9:
        df["Lost [Twh]"] = (
            df["Net H2 Stored [Twh]"]
            + (cyc - 9) * ((1 - psa_rec * df["Predicted MRf [-]"]) * twh_per_cycle)
            + df["Cum CG Injected [Twh]"]
        )
        df["Cum H2 Produced [Twh]"] = df["Cum H2 Produced [Twh]"] + (cyc - 9) * psa_rec * (
            df["Predicted MRf [-]"] * twh_per_cycle
        )
        df["Cum H2 Injected [Twh]"] = df["Cum H2 Injected [Twh]"] + (cyc - 9) * twh_per_cycle
    else:
        df["Lost [Twh]"] = df["Net H2 Stored [Twh]"] + df["Cum CG Injected [Twh]"]

    # Project horizon (years)
    years = max(1, round((cyc + 1) * scenario.cl_days / 360))
    pv_factor = present_value_annuity_factor(discount_rate, years)
    capex_factor = capex_pv_factor(discount_rate, years, capex_treatment)

    annual_factor = 360.0 / scenario.cl_days

    # Initial working-gas cost is the initial system fill. Cushion-gas cost is
    # retained inventory/placement. Full working gas is not charged every year;
    # only the shortfall between injected H2 and saleable delivered H2 is
    # charged as recurring make-up to avoid double counting the initial fill.
    injected_h2_kg_per_cycle = twh_per_cycle * 1e9 / KWH_PER_KG_H2
    delivered_h2_kg_per_cycle = (
        df["Predicted RF [-]"] * psa_rec * twh_per_cycle
    ) * 1e9 / KWH_PER_KG_H2
    makeup_h2_kg_per_cycle = (injected_h2_kg_per_cycle - delivered_h2_kg_per_cycle).clip(lower=0.0)
    df["H2 Make-up Mass [kg/cycle]"] = makeup_h2_kg_per_cycle
    df["H2 Make-up Cost [$]"] = makeup_h2_kg_per_cycle * scenario.h2_cost_per_kg
    df["PV H2 Make-up Cost [$]"] = df["H2 Make-up Cost [$]"] * annual_factor * pv_factor

    # PSA CAPEX/OPEX are applied to the H2 stream withdrawn from the reservoir
    # before PSA tail losses. Saleable delivered H2 after PSA is tracked below.
    produced_h2_kg_per_cycle = (df["Predicted RF [-]"] * twh_per_cycle) * 1e9 / KWH_PER_KG_H2
    df["PSA OPEX Cost [$]"] = produced_h2_kg_per_cycle * psa_opex

    df["PV WG Compression OPEX [$]"] = df["WG Compression OPEX [$]"] * annual_factor * pv_factor
    df["PV WG Cooling OPEX [$]"] = df["WG Cooling OPEX [$]"] * annual_factor * pv_factor
    df["PV WG Other O&M [$]"] = df["WG Other O&M [$]"] * annual_factor * pv_factor
    df["PV Non-PSA OPEX [$]"] = (
        df["PV WG Compression OPEX [$]"]
        + df["PV WG Cooling OPEX [$]"]
        + df["PV WG Other O&M [$]"]
    )
    df["PV PSA OPEX [$]"] = df["PSA OPEX Cost [$]"] * annual_factor * pv_factor
    df["PV OPEX Cost [$]"] = (
        df["PV Non-PSA OPEX [$]"]
        + df["PV PSA OPEX [$]"]
        + df["PV H2 Make-up Cost [$]"]
    )

    df["Purification Capital Cost [$]"] = (
        produced_h2_kg_per_cycle * psa_cap
    )
    base_capex = pd.to_numeric(df["Base Capital Cost [$]"], errors="coerce").fillna(0.0)
    df["Capital Cost [$]"] = base_capex + df["Purification Capital Cost [$]"]
    df["Total Capital Cost [$]"] = df["Capital Cost [$]"]
    df["Capital Breakdown Total [$]"] = (
        pd.to_numeric(df["Compressor Capital Cost [$]"], errors="coerce").fillna(0.0)
        + pd.to_numeric(df["Well Capital Cost [$]"], errors="coerce").fillna(0.0)
        + pd.to_numeric(df["Working Gas Cost [$]"], errors="coerce").fillna(0.0)
        + pd.to_numeric(df["Cushion Gas Cost [$]"], errors="coerce").fillna(0.0)
        + pd.to_numeric(df["Purification Capital Cost [$]"], errors="coerce").fillna(0.0)
    )
    # CAPEX components are converted to PV using the active CAPEX treatment.
    for raw_col, pv_col in zip(CAPITAL_COMPONENT_COLUMNS, PV_CAPITAL_COMPONENT_COLUMNS, strict=True):
        df[pv_col] = pd.to_numeric(df[raw_col], errors="coerce").fillna(0.0) * capex_factor

    df["PV Capital Breakdown Total [$]"] = sum(
        pd.to_numeric(df[col], errors="coerce").fillna(0.0) for col in PV_CAPITAL_COMPONENT_COLUMNS
    )
    df["PV CAPEX Cost [$]"] = df["PV Capital Breakdown Total [$]"]
    df["Capital Cost Used [$]"] = df["PV CAPEX Cost [$]"]
    df["Capital PV Factor [-]"] = capex_factor

    delivered_after_psa_twh = pd.to_numeric(df["Cum H2 Produced [Twh]"], errors="coerce").fillna(0.0)
    # The generated scenario CSVs already apply PSA recovery to Cum H2
    # Produced [Twh]. Keep that column as cumulative delivered H2 after PSA for
    # compatibility, and add explicit before/after-PSA columns for clarity.
    df["Produced H2 Before PSA [TWh]"] = delivered_after_psa_twh / psa_rec
    df["Delivered H2 After PSA [TWh]"] = delivered_after_psa_twh
    df["Annual Produced H2 Before PSA [TWh/y]"] = df["Produced H2 Before PSA [TWh]"] / years
    df["Annual Delivered H2 After PSA [TWh/y]"] = df["Delivered H2 After PSA [TWh]"] / years
    df["Legacy Average Delivered H2 After PSA [TWh/cycle]"] = delivered_after_psa_twh / (cyc + 1)
    df["PV Delivered Energy [TWh]"] = df["Annual Delivered H2 After PSA [TWh/y]"] * pv_factor

    df["PV Total Component Cost [$]"] = (
        df["PV Compressor Capital Cost [$]"]
        + df["PV Well Capital Cost [$]"]
        + df["PV Working Gas Cost [$]"]
        + df["PV Cushion Gas Cost [$]"]
        + df["PV Purification Capital Cost [$]"]
        + df["PV WG Compression OPEX [$]"]
        + df["PV WG Cooling OPEX [$]"]
        + df["PV WG Other O&M [$]"]
        + df["PV PSA OPEX [$]"]
        + df["PV H2 Make-up Cost [$]"]
    )
    total_cost = df["Capital Cost Used [$]"] + df["PV OPEX Cost [$]"]
    df["PV Total Cost [$]"] = total_cost
    df["PV Total Cost [M$]"] = total_cost / 1e6
    df["Cost Closure Error [%]"] = 100.0 * (
        df["PV Total Component Cost [$]"] - total_cost
    ) / total_cost.replace(0.0, np.nan)

    # LCOS component contribution is PV component cost divided by PV delivered energy.
    df["LCOS"] = total_cost / df["PV Delivered Energy [TWh]"] / 1e6
    # Kept for backward compatibility. This is the MILP total PV objective cost,
    # not a hydrogen-loss-only cost.
    df["Loss Cost [M$]"] = total_cost / 1e6
    df["Objective Cost [M$]"] = df["Loss Cost [M$]"]

    # Metadata useful when workbooks are combined later.
    df["CAPEX Treatment"] = capex_treatment
    df["Discount Rate [-]"] = discount_rate
    df["Discount Rate [%]"] = discount_rate * 100.0
    df["H2 Cost [$/kg]"] = scenario.h2_cost_per_kg
    df["PSA Multiplier"] = scenario.psa_multiplier
    df["PSA Level"] = scenario.psa_label
    df["Target TWh"] = scenario.target_twh

    # IDs for MILP constraints
    df["res_id"] = df["Field Name"].astype("category").cat.codes
    df["cand_id"] = np.arange(len(df), dtype=int)

    return df


def build_and_solve(df: pd.DataFrame, target_twh: float, well_budget=None, logfile=None, verbose: bool = False):
    """
    MILP:
    - Decision x_k in {0,1}: choose scenario k
    - Minimize sum(cost_k * x_k)
    - Meet delivered energy target
    - Choose at most one scenario per reservoir (res_id)
    - Optional total wells budget
    """
    m = gp.Model("UK_H2_MinLoss")
    if logfile:
        m.Params.LogFile = logfile
    m.Params.OutputFlag = 1 if verbose else 0

    x = m.addVars(df.index, vtype=GRB.BINARY, name="x")

    m.setObjective(gp.quicksum(x[k] * df.at[k, "Objective Cost [M$]"] for k in df.index), GRB.MINIMIZE)

    m.addConstr(
        gp.quicksum(x[k] * df.at[k, "Annual Delivered H2 After PSA [TWh/y]"] for k in df.index) >= target_twh,
        name="energy_target",
    )

    for res_id, idx in df.groupby("res_id").groups.items():
        m.addConstr(gp.quicksum(x[k] for k in idx) <= 1, name=f"one_scenario_per_res_{int(res_id)}")

    if well_budget is not None and "Number of Wells" in df.columns:
        m.addConstr(
            gp.quicksum(x[k] * df.at[k, "Number of Wells"] for k in df.index) <= well_budget,
            name="well_budget",
        )

    m.optimize()

    if m.SolCount == 0:
        return m, pd.DataFrame(columns=df.columns)

    chosen_idx = [k for k in df.index if x[k].X > 0.5]
    sol = df.loc[chosen_idx].copy()
    sol["x"] = 1
    return m, sol


def cycles_for_cl(cl_days: int) -> np.ndarray:
    cycles = YEARS_OF_INTEREST * 360 / cl_days
    return np.unique(cycles).astype(int)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce")
    weights = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    mask = values.notna() & weights.notna()
    if not mask.any():
        return np.nan
    if weights.loc[mask].sum() <= 0:
        return float(values.loc[mask].mean())
    return float((values.loc[mask] * weights.loc[mask]).sum() / weights.loc[mask].sum())


def sum_currency(df: pd.DataFrame, column: str) -> float:
    if df.empty or column not in df.columns:
        return np.nan
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0.0).sum())


def sum_million(df: pd.DataFrame, column: str) -> float:
    value = sum_currency(df, column)
    if np.isnan(value):
        return np.nan
    return value / 1e6


def capital_share(df: pd.DataFrame, column: str, total_column: str = "Capital Breakdown Total [$]") -> float:
    component = sum_currency(df, column)
    total = sum_currency(df, total_column)
    if np.isnan(component) or np.isnan(total) or total <= 0:
        return np.nan
    return component / total


def cost_closure_error_percent(df: pd.DataFrame) -> float:
    component_total = sum_currency(df, "PV Total Component Cost [$]")
    objective_total = sum_currency(df, "PV Total Cost [$]")
    if np.isnan(objective_total):
        objective_total = sum_currency(df, "Capital Cost Used [$]") + sum_currency(df, "PV OPEX Cost [$]")
    if np.isnan(component_total) or np.isnan(objective_total) or objective_total == 0:
        return np.nan
    return 100.0 * (component_total - objective_total) / objective_total


def summarize_solution(
    scenario: Scenario,
    discount_rate: float,
    capex_treatment: str,
    cycle: int,
    model: gp.Model,
    sol: pd.DataFrame,
    output_file: Path,
) -> dict[str, object]:
    if sol.empty:
        return {
            "Discount_Rate": discount_rate,
            "Discount_Rate_Percent": discount_rate * 100.0,
            "CL_days": scenario.cl_days,
            "Target_TWh": scenario.target_twh,
            "H2_Cost_per_kg": scenario.h2_cost_per_kg,
            "PSA_Multiplier": scenario.psa_multiplier,
            "PSA_Level": scenario.psa_label,
            "CAPEX_Treatment": capex_treatment,
            "Cycle": cycle,
            "Year": round(cycle * scenario.cl_days / 360),
            "Status": model.Status,
            "Selected_Reservoirs": 0,
            "Delivered_TWh": np.nan,
            "PV_Energy_TWh": np.nan,
            "Total_Wells": np.nan,
            "Total_Loss_Cost_M$": np.nan,
            "Weighted_LCOS": np.nan,
            "H2_Make_up_Mass_kg_per_cycle": np.nan,
            "H2_Make_up_Cost_M$": np.nan,
            "PV_H2_Make_up_Cost_M$": np.nan,
            "Produced_H2_Before_PSA_TWh": np.nan,
            "Delivered_H2_After_PSA_TWh": np.nan,
            "Annual_Delivered_H2_After_PSA_TWh_per_y": np.nan,
            "PV_Total_Cost_M$": np.nan,
            "Objective_Cost_M$": np.nan,
            "PV_WG_Compression_OPEX_M$": np.nan,
            "PV_WG_Cooling_OPEX_M$": np.nan,
            "PV_WG_Other_OM_M$": np.nan,
            "PV_Non_PSA_OPEX_M$": np.nan,
            "PV_PSA_OPEX_M$": np.nan,
            "PV_OPEX_Cost_M$": np.nan,
            "Compressor_Capital_Cost_M$": np.nan,
            "Well_Capital_Cost_M$": np.nan,
            "Working_Gas_Cost_M$": np.nan,
            "Cushion_Gas_Cost_M$": np.nan,
            "Purification_Capital_Cost_M$": np.nan,
            "PV_Compressor_Capital_Cost_M$": np.nan,
            "PV_Well_Capital_Cost_M$": np.nan,
            "PV_Working_Gas_Cost_M$": np.nan,
            "PV_Cushion_Gas_Cost_M$": np.nan,
            "PV_Purification_Capital_Cost_M$": np.nan,
            "Base_Capital_Cost_M$": np.nan,
            "Total_Capital_Cost_M$": np.nan,
            "Capital_Breakdown_Total_M$": np.nan,
            "PV_CAPEX_Cost_M$": np.nan,
            "Capital_Cost_Used_M$": np.nan,
            "PV_Capital_Breakdown_Total_M$": np.nan,
            "PV_Total_Component_Cost_M$": np.nan,
            "Cost_Closure_Error_Percent": np.nan,
            "Mean_Capital_PV_Factor": np.nan,
            "Compressor_Capital_Share": np.nan,
            "Well_Capital_Share": np.nan,
            "Working_Gas_Share": np.nan,
            "Cushion_Gas_Share": np.nan,
            "Purification_Capital_Share": np.nan,
            "PV_Compressor_Capital_Share": np.nan,
            "PV_Well_Capital_Share": np.nan,
            "PV_Working_Gas_Share": np.nan,
            "PV_Cushion_Gas_Share": np.nan,
            "PV_Purification_Capital_Share": np.nan,
            "Output_File": str(output_file),
        }

    weights = pd.to_numeric(sol["Annual Delivered H2 After PSA [TWh/y]"], errors="coerce").fillna(0.0)
    pv_energy_twh = sum_currency(sol, "PV Delivered Energy [TWh]")
    if "Objective Cost [M$]" in sol.columns:
        total_loss_cost_m = float(pd.to_numeric(sol["Objective Cost [M$]"], errors="coerce").fillna(0.0).sum())
    elif "Loss Cost [M$]" in sol.columns:
        total_loss_cost_m = float(pd.to_numeric(sol["Loss Cost [M$]"], errors="coerce").fillna(0.0).sum())
    else:
        total_loss_cost_m = np.nan
    weighted_lcos = total_loss_cost_m / pv_energy_twh if pv_energy_twh and pv_energy_twh > 0 else np.nan
    return {
        "Discount_Rate": discount_rate,
        "Discount_Rate_Percent": discount_rate * 100.0,
        "CL_days": scenario.cl_days,
        "Target_TWh": scenario.target_twh,
        "H2_Cost_per_kg": scenario.h2_cost_per_kg,
        "PSA_Multiplier": scenario.psa_multiplier,
        "PSA_Level": scenario.psa_label,
        "CAPEX_Treatment": capex_treatment,
        "Cycle": cycle,
        "Year": round(cycle * scenario.cl_days / 360),
        "Status": model.Status,
        "Selected_Reservoirs": int(len(sol)),
        "Delivered_TWh": float(weights.sum()),
        "PV_Energy_TWh": pv_energy_twh,
        "Total_Wells": float(pd.to_numeric(sol["Number of Wells"], errors="coerce").sum()),
        "Total_Loss_Cost_M$": total_loss_cost_m,
        "Weighted_LCOS": weighted_lcos,
        "H2_Make_up_Mass_kg_per_cycle": sum_currency(sol, "H2 Make-up Mass [kg/cycle]"),
        "H2_Make_up_Cost_M$": sum_million(sol, "H2 Make-up Cost [$]"),
        "PV_H2_Make_up_Cost_M$": sum_million(sol, "PV H2 Make-up Cost [$]"),
        "Produced_H2_Before_PSA_TWh": sum_currency(sol, "Produced H2 Before PSA [TWh]"),
        "Delivered_H2_After_PSA_TWh": sum_currency(sol, "Delivered H2 After PSA [TWh]"),
        "Annual_Delivered_H2_After_PSA_TWh_per_y": sum_currency(
            sol, "Annual Delivered H2 After PSA [TWh/y]"
        ),
        "PV_Total_Cost_M$": sum_million(sol, "PV Total Cost [$]"),
        "Objective_Cost_M$": sum_currency(sol, "Objective Cost [M$]")
        if "Objective Cost [M$]" in sol.columns
        else total_loss_cost_m,
        "PV_WG_Compression_OPEX_M$": sum_million(sol, "PV WG Compression OPEX [$]"),
        "PV_WG_Cooling_OPEX_M$": sum_million(sol, "PV WG Cooling OPEX [$]"),
        "PV_WG_Other_OM_M$": sum_million(sol, "PV WG Other O&M [$]"),
        "PV_Non_PSA_OPEX_M$": sum_million(sol, "PV Non-PSA OPEX [$]"),
        "PV_PSA_OPEX_M$": sum_million(sol, "PV PSA OPEX [$]"),
        "PV_OPEX_Cost_M$": sum_million(sol, "PV OPEX Cost [$]"),
        "Compressor_Capital_Cost_M$": sum_million(sol, "Compressor Capital Cost [$]"),
        "Well_Capital_Cost_M$": sum_million(sol, "Well Capital Cost [$]"),
        "Working_Gas_Cost_M$": sum_million(sol, "Working Gas Cost [$]"),
        "Cushion_Gas_Cost_M$": sum_million(sol, "Cushion Gas Cost [$]"),
        "Purification_Capital_Cost_M$": sum_million(sol, "Purification Capital Cost [$]"),
        "PV_Compressor_Capital_Cost_M$": sum_million(sol, "PV Compressor Capital Cost [$]"),
        "PV_Well_Capital_Cost_M$": sum_million(sol, "PV Well Capital Cost [$]"),
        "PV_Working_Gas_Cost_M$": sum_million(sol, "PV Working Gas Cost [$]"),
        "PV_Cushion_Gas_Cost_M$": sum_million(sol, "PV Cushion Gas Cost [$]"),
        "PV_Purification_Capital_Cost_M$": sum_million(sol, "PV Purification Capital Cost [$]"),
        "Base_Capital_Cost_M$": sum_million(sol, "Base Capital Cost [$]"),
        "Total_Capital_Cost_M$": sum_million(sol, "Total Capital Cost [$]"),
        "Capital_Breakdown_Total_M$": sum_million(sol, "Capital Breakdown Total [$]"),
        "PV_CAPEX_Cost_M$": sum_million(sol, "PV CAPEX Cost [$]"),
        "Capital_Cost_Used_M$": sum_million(sol, "Capital Cost Used [$]"),
        "PV_Capital_Breakdown_Total_M$": sum_million(sol, "PV Capital Breakdown Total [$]"),
        "PV_Total_Component_Cost_M$": sum_million(sol, "PV Total Component Cost [$]"),
        "Cost_Closure_Error_Percent": cost_closure_error_percent(sol),
        "Mean_Capital_PV_Factor": weighted_mean(sol["Capital PV Factor [-]"], weights),
        "Compressor_Capital_Share": capital_share(sol, "Compressor Capital Cost [$]"),
        "Well_Capital_Share": capital_share(sol, "Well Capital Cost [$]"),
        "Working_Gas_Share": capital_share(sol, "Working Gas Cost [$]"),
        "Cushion_Gas_Share": capital_share(sol, "Cushion Gas Cost [$]"),
        "Purification_Capital_Share": capital_share(sol, "Purification Capital Cost [$]"),
        "PV_Compressor_Capital_Share": capital_share(
            sol, "PV Compressor Capital Cost [$]", "PV Capital Breakdown Total [$]"
        ),
        "PV_Well_Capital_Share": capital_share(sol, "PV Well Capital Cost [$]", "PV Capital Breakdown Total [$]"),
        "PV_Working_Gas_Share": capital_share(sol, "PV Working Gas Cost [$]", "PV Capital Breakdown Total [$]"),
        "PV_Cushion_Gas_Share": capital_share(sol, "PV Cushion Gas Cost [$]", "PV Capital Breakdown Total [$]"),
        "PV_Purification_Capital_Share": capital_share(
            sol, "PV Purification Capital Cost [$]", "PV Capital Breakdown Total [$]"
        ),
        "Output_File": str(output_file),
    }


def keep_columns() -> list[str]:
    return [
        "Field Name",
        "Flow Rate [sm3/d]",
        "Cycle Length [d]",
        "Number of Wells",
        "CG Ratio",
        "Cum H2 Injected [m3]",
        "CG injected [m3]",
        "Cum H2 Produced [m3]",
        "Net H2 Stored [m3]",
        "Loss Cost [£]",
        "Loss Cost [Â£]",
        "Compressor Capital Cost [$]",
        "Well Capital Cost [$]",
        "Working Gas Cost [$]",
        "Cushion Gas Cost [$]",
        "Base Capital Cost [$]",
        "Purification Capital Cost [$]",
        "Total Capital Cost [$]",
        "Capital Breakdown Total [$]",
        "PV Compressor Capital Cost [$]",
        "PV Well Capital Cost [$]",
        "PV Working Gas Cost [$]",
        "PV Cushion Gas Cost [$]",
        "PV Purification Capital Cost [$]",
        "PV CAPEX Cost [$]",
        "Capital Cost Used [$]",
        "PV Capital Breakdown Total [$]",
        "Capital PV Factor [-]",
        "WG O&M Cost [$]",
        "WG Compression OPEX [$]",
        "WG Cooling OPEX [$]",
        "WG Other O&M [$]",
        "PSA OPEX Cost [$]",
        "PV WG Compression OPEX [$]",
        "PV WG Cooling OPEX [$]",
        "PV WG Other O&M [$]",
        "PV Non-PSA OPEX [$]",
        "PV PSA OPEX [$]",
        "H2 Make-up Mass [kg/cycle]",
        "H2 Make-up Cost [$]",
        "PV H2 Make-up Cost [$]",
        "PV OPEX Cost [$]",
        "Produced H2 Before PSA [TWh]",
        "Delivered H2 After PSA [TWh]",
        "Annual Produced H2 Before PSA [TWh/y]",
        "Annual Delivered H2 After PSA [TWh/y]",
        "Legacy Average Delivered H2 After PSA [TWh/cycle]",
        "PV Delivered Energy [TWh]",
        "PV Total Component Cost [$]",
        "PV Total Cost [$]",
        "PV Total Cost [M$]",
        "Cost Closure Error [%]",
        "Porosity [-]",
        "Permeability [mD]",
        "Reservoir Pressure[bar]",
        "Reservoir Temp [K]",
        "Discount Rate [-]",
        "Discount Rate [%]",
        "H2 Cost [$/kg]",
        "PSA Multiplier",
        "PSA Level",
        "Target TWh",
        "CAPEX Treatment",
        "PSA Cost [$/kg]",
        "Loss Cost [M$]",
        "Objective Cost [M$]",
        "Cum H2 Produced [Twh]",
        "Cum H2 Injected [Twh]",
        "LCOS",
        "Predicted RF [-]",
    ]


def cost_breakdown_columns() -> list[str]:
    return [
        "Discount_Rate",
        "Discount_Rate_Percent",
        "CL_days",
        "Target_TWh",
        "H2_Cost_per_kg",
        "PSA_Multiplier",
        "PSA_Level",
        "CAPEX_Treatment",
        "Cycle",
        "Year",
        "Status",
        "Selected_Reservoirs",
        "Delivered_TWh",
        "PV_Energy_TWh",
        "Total_Loss_Cost_M$",
        "Weighted_LCOS",
        "H2_Make_up_Mass_kg_per_cycle",
        "H2_Make_up_Cost_M$",
        "PV_H2_Make_up_Cost_M$",
        "Produced_H2_Before_PSA_TWh",
        "Delivered_H2_After_PSA_TWh",
        "Annual_Delivered_H2_After_PSA_TWh_per_y",
        "PV_Total_Cost_M$",
        "Objective_Cost_M$",
        "PV_WG_Compression_OPEX_M$",
        "PV_WG_Cooling_OPEX_M$",
        "PV_WG_Other_OM_M$",
        "PV_Non_PSA_OPEX_M$",
        "PV_PSA_OPEX_M$",
        "PV_OPEX_Cost_M$",
        "Compressor_Capital_Cost_M$",
        "Well_Capital_Cost_M$",
        "Working_Gas_Cost_M$",
        "Cushion_Gas_Cost_M$",
        "Purification_Capital_Cost_M$",
        "PV_Compressor_Capital_Cost_M$",
        "PV_Well_Capital_Cost_M$",
        "PV_Working_Gas_Cost_M$",
        "PV_Cushion_Gas_Cost_M$",
        "PV_Purification_Capital_Cost_M$",
        "Base_Capital_Cost_M$",
        "Total_Capital_Cost_M$",
        "Capital_Breakdown_Total_M$",
        "PV_CAPEX_Cost_M$",
        "Capital_Cost_Used_M$",
        "PV_Capital_Breakdown_Total_M$",
        "PV_Total_Component_Cost_M$",
        "Cost_Closure_Error_Percent",
        "Mean_Capital_PV_Factor",
        "Compressor_Capital_Share",
        "Well_Capital_Share",
        "Working_Gas_Share",
        "Cushion_Gas_Share",
        "Purification_Capital_Share",
        "PV_Compressor_Capital_Share",
        "PV_Well_Capital_Share",
        "PV_Working_Gas_Share",
        "PV_Cushion_Gas_Share",
        "PV_Purification_Capital_Share",
    ]


def build_capital_breakdown_long(summary: pd.DataFrame) -> pd.DataFrame:
    metadata_cols = [
        "Discount_Rate",
        "Discount_Rate_Percent",
        "CL_days",
        "Target_TWh",
        "H2_Cost_per_kg",
        "PSA_Multiplier",
        "PSA_Level",
        "CAPEX_Treatment",
        "Cycle",
        "Year",
        "Status",
        "Selected_Reservoirs",
        "Delivered_TWh",
        "Total_Loss_Cost_M$",
        "PV_OPEX_Cost_M$",
        "Total_Capital_Cost_M$",
        "Capital_Breakdown_Total_M$",
        "PV_CAPEX_Cost_M$",
        "Capital_Cost_Used_M$",
        "PV_Capital_Breakdown_Total_M$",
        "Mean_Capital_PV_Factor",
    ]

    records: list[dict[str, object]] = []
    for _, row in summary.iterrows():
        for component, raw_col, pv_col, raw_summary_col, pv_summary_col, raw_share_col, pv_share_col in (
            CAPITAL_COMPONENT_DETAIL
        ):
            raw_cost = pd.to_numeric(row.get(raw_summary_col), errors="coerce")
            pv_cost = pd.to_numeric(row.get(pv_summary_col), errors="coerce")
            raw_share = pd.to_numeric(row.get(raw_share_col), errors="coerce")
            pv_share = pd.to_numeric(row.get(pv_share_col), errors="coerce")

            rec = {col: row.get(col, np.nan) for col in metadata_cols}
            rec.update(
                {
                    "Component": component,
                    "Component_Cost_M$": pv_cost,
                    "Share_of_Capital": pv_share,
                    "Raw_Component_Cost_M$": raw_cost,
                    "PV_Component_Cost_M$": pv_cost,
                    "Raw_Share_of_Capital": raw_share,
                    "PV_Share_of_Capital": pv_share,
                    "Raw_Component_Column": raw_col,
                    "PV_Component_Column": pv_col,
                }
            )
            records.append(rec)

    return pd.DataFrame.from_records(records)


def lcos_breakdown_metadata_columns() -> list[str]:
    return [
        "Discount_Rate",
        "Discount_Rate_Percent",
        "CL_days",
        "Target_TWh",
        "H2_Cost_per_kg",
        "PSA_Multiplier",
        "PSA_Level",
        "CAPEX_Treatment",
        "Cycle",
        "Year",
        "Status",
        "Selected_Reservoirs",
        "Delivered_TWh",
        "PV_Energy_TWh",
        "Total_Loss_Cost_M$",
        "PV_Total_Cost_M$",
        "Objective_Cost_M$",
        "Weighted_LCOS",
        "Cost_Closure_Error_Percent",
    ]


def build_lcos_breakdown_long(summary: pd.DataFrame) -> pd.DataFrame:
    # LCOS component contribution is calculated as PV component cost divided by
    # PV delivered energy. The component shares use the total PV system cost.
    records: list[dict[str, object]] = []
    metadata_cols = lcos_breakdown_metadata_columns()

    for _, row in summary.iterrows():
        pv_energy_twh = pd.to_numeric(row.get("PV_Energy_TWh"), errors="coerce")
        total_loss_cost_m = pd.to_numeric(row.get("Total_Loss_Cost_M$"), errors="coerce")

        for component, cost_col in LCOS_COMPONENT_DETAIL:
            component_cost_m = pd.to_numeric(row.get(cost_col), errors="coerce")
            component_lcos = (
                component_cost_m / pv_energy_twh
                if pd.notna(component_cost_m) and pd.notna(pv_energy_twh) and pv_energy_twh > 0
                else np.nan
            )
            component_share = (
                component_cost_m / total_loss_cost_m
                if pd.notna(component_cost_m) and pd.notna(total_loss_cost_m) and total_loss_cost_m > 0
                else np.nan
            )

            rec = {col: row.get(col, np.nan) for col in metadata_cols}
            rec.update(
                {
                    "Component": component,
                    "Component_PV_Cost_M$": component_cost_m,
                    "Component_LCOS_$/MWh": component_lcos,
                    "Component_Share_of_Total_Cost": component_share,
                }
            )
            records.append(rec)

    return pd.DataFrame.from_records(records)


def build_lcos_breakdown_grouped(summary: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    metadata_cols = lcos_breakdown_metadata_columns()

    for _, row in summary.iterrows():
        pv_energy_twh = pd.to_numeric(row.get("PV_Energy_TWh"), errors="coerce")
        total_loss_cost_m = pd.to_numeric(row.get("Total_Loss_Cost_M$"), errors="coerce")

        for component_group, cost_cols in LCOS_COMPONENT_GROUPS:
            component_cost_m = sum(
                pd.to_numeric(row.get(cost_col), errors="coerce")
                for cost_col in cost_cols
                if pd.notna(pd.to_numeric(row.get(cost_col), errors="coerce"))
            )
            component_lcos = (
                component_cost_m / pv_energy_twh
                if pd.notna(component_cost_m) and pd.notna(pv_energy_twh) and pv_energy_twh > 0
                else np.nan
            )
            component_share = (
                component_cost_m / total_loss_cost_m
                if pd.notna(component_cost_m) and pd.notna(total_loss_cost_m) and total_loss_cost_m > 0
                else np.nan
            )

            rec = {col: row.get(col, np.nan) for col in metadata_cols}
            rec.update(
                {
                    "Component_Group": component_group,
                    "Component_PV_Cost_M$": component_cost_m,
                    "Component_LCOS_$/MWh": component_lcos,
                    "Component_Share_of_Total_Cost": component_share,
                }
            )
            records.append(rec)

    return pd.DataFrame.from_records(records)


def print_batch_validations(summary: pd.DataFrame) -> None:
    max_abs_closure = pd.to_numeric(summary.get("Cost_Closure_Error_Percent"), errors="coerce").abs().max()
    print(f"Maximum absolute cost-closure error across solved cases: {max_abs_closure:.6g}%")
    if pd.notna(max_abs_closure) and max_abs_closure > 0.01:
        print("WARNING: Maximum absolute cost-closure error exceeds 0.01%.")

    lcos_long = build_lcos_breakdown_long(summary)
    if not lcos_long.empty:
        metadata_cols = lcos_breakdown_metadata_columns()
        component_sum = (
            lcos_long.groupby(metadata_cols, dropna=False)["Component_LCOS_$/MWh"]
            .sum(min_count=1)
            .reset_index(name="Component_LCOS_Sum")
        )
        component_sum["LCOS_Closure_Error"] = (
            component_sum["Component_LCOS_Sum"]
            - pd.to_numeric(component_sum["Weighted_LCOS"], errors="coerce")
        )
        max_lcos_diff = component_sum["LCOS_Closure_Error"].abs().max()
        print(f"Maximum absolute component-LCOS closure error: {max_lcos_diff:.6g} $/MWh")
        if pd.notna(max_lcos_diff) and max_lcos_diff > 1e-4:
            print("WARNING: Component LCOS sum differs from Weighted_LCOS by more than 1e-4 $/MWh.")

    solved = summary.loc[pd.to_numeric(summary.get("Selected_Reservoirs"), errors="coerce").fillna(0.0) > 0].copy()
    if solved.empty:
        return

    makeup_cost = pd.to_numeric(solved.get("PV_H2_Make_up_Cost_M$"), errors="coerce").fillna(0.0)
    total_cost = pd.to_numeric(solved.get("Total_Loss_Cost_M$"), errors="coerce").replace(0.0, np.nan)
    solved["PV_H2_Make_up_Cost_Share"] = makeup_cost / total_cost

    representative = solved.copy()
    if (pd.to_numeric(representative.get("Year"), errors="coerce") == 30).any():
        representative = representative.loc[pd.to_numeric(representative.get("Year"), errors="coerce") == 30]
    representative = representative.sort_values(["Discount_Rate_Percent", "Target_TWh", "H2_Cost_per_kg", "PSA_Level"])
    print("Representative PV H2 make-up cost shares:")
    for _, row in representative.head(6).iterrows():
        share = pd.to_numeric(row.get("PV_H2_Make_up_Cost_Share"), errors="coerce")
        print(
            "  "
            f"DR={row.get('Discount_Rate_Percent', np.nan):g}%, "
            f"target={row.get('Target_TWh', np.nan):g} TWh, "
            f"H2={row.get('H2_Cost_per_kg', np.nan):g} $/kg, "
            f"PSA={row.get('PSA_Level', 'NA')}: "
            f"{100.0 * share:.2f}%"
        )

    zero_makeup = solved.loc[makeup_cost <= 1e-9]
    if not zero_makeup.empty:
        print(
            "WARNING: PV H2 make-up cost is zero for "
            f"{len(zero_makeup)} solved cases even though PSA recovery is below 1."
        )


def write_metadata_sheet(
    writer: pd.ExcelWriter,
    scenario: Scenario,
    discount_rate: float,
    capex_treatment: str,
) -> None:
    metadata = pd.DataFrame(
        [
            {
                "Discount_Rate": discount_rate,
                "Discount_Rate_Percent": discount_rate * 100.0,
                "CL_days": scenario.cl_days,
                "Target_TWh": scenario.target_twh,
                "H2_Cost_per_kg": scenario.h2_cost_per_kg,
                "PSA_Multiplier": scenario.psa_multiplier,
                "PSA_Level": scenario.psa_label,
                "CAPEX_Treatment": capex_treatment,
                "Input_Dataset": scenario.dataset_folder,
            }
        ]
    )
    metadata.to_excel(writer, sheet_name="metadata", index=False)


def run_scenario(
    input_dir: Path,
    output_dir: Path,
    scenario: Scenario,
    discount_rate: float,
    capex_treatment: str = CAPEX_TREATMENT,
    well_budget=None,
    allow_cg: bool = True,
    verbose: bool = False,
) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / scenario.output_filename
    summaries: list[dict[str, object]] = []
    cols = keep_columns()

    print(
        f"[DR {discount_rate:.0%}, CAPEX={capex_treatment}] CL={scenario.cl_days}, target={scenario.target_twh} TWh, "
        f"H2={scenario.h2_cost_per_kg:.1f}, PSA={scenario.psa_label}"
    )

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        write_metadata_sheet(writer, scenario, discount_rate, capex_treatment)

        for cycle in cycles_for_cl(scenario.cl_days):
            df = load_scenarios(
                input_dir,
                scenario,
                discount_rate,
                capex_treatment=capex_treatment,
                allow_cg=allow_cg,
                cyc=cycle - 1,
            )
            model, sol = build_and_solve(df, scenario.target_twh, well_budget=well_budget, verbose=verbose)

            if not sol.empty:
                sol["Cum H2 Injected [Twh]"] = sol["Cum H2 Injected [Twh]"] / cycle

                for col in cols:
                    if col not in sol.columns:
                        sol[col] = np.nan

                sheet = f"cycle_{int(cycle)}"[:31]
                sol[cols].to_excel(writer, sheet_name=sheet, index=False)
            else:
                pd.DataFrame(columns=cols).to_excel(writer, sheet_name=f"cycle_{int(cycle)}"[:31], index=False)

            summaries.append(
                summarize_solution(scenario, discount_rate, capex_treatment, int(cycle), model, sol, output_file)
            )

        summary_df = pd.DataFrame(summaries)
        summary_df[cost_breakdown_columns()].to_excel(writer, sheet_name="cost_breakdown", index=False)
        build_capital_breakdown_long(summary_df).to_excel(writer, sheet_name="capital_breakdown_long", index=False)
        build_lcos_breakdown_long(summary_df).to_excel(writer, sheet_name="lcos_breakdown_long", index=False)
        build_lcos_breakdown_grouped(summary_df).to_excel(writer, sheet_name="lcos_breakdown_group", index=False)

    return summaries


def run_batch(
    input_dir: Path,
    output_root: Path,
    discount_rates: list[float],
    scenarios: list[Scenario],
    capex_treatment: str = CAPEX_TREATMENT,
    well_budget=None,
    allow_cg: bool = True,
    verbose: bool = False,
) -> pd.DataFrame:
    all_summaries: list[dict[str, object]] = []

    for discount_rate in discount_rates:
        output_dir = output_root / discount_folder_name(discount_rate)
        dr_summaries: list[dict[str, object]] = []

        for scenario in scenarios:
            try:
                dr_summaries.extend(
                    run_scenario(
                        input_dir=input_dir,
                        output_dir=output_dir,
                        scenario=scenario,
                        discount_rate=discount_rate,
                        capex_treatment=capex_treatment,
                        well_budget=well_budget,
                        allow_cg=allow_cg,
                        verbose=verbose,
                    )
                )
            except FileNotFoundError as exc:
                print(f"[skip] {exc}")
                dr_summaries.append(
                    {
                        "Discount_Rate": discount_rate,
                        "Discount_Rate_Percent": discount_rate * 100.0,
                        "CL_days": scenario.cl_days,
                        "Target_TWh": scenario.target_twh,
                        "H2_Cost_per_kg": scenario.h2_cost_per_kg,
                        "PSA_Multiplier": scenario.psa_multiplier,
                        "PSA_Level": scenario.psa_label,
                        "CAPEX_Treatment": capex_treatment,
                        "Cycle": np.nan,
                        "Year": np.nan,
                        "Status": "missing_input",
                        "Selected_Reservoirs": np.nan,
                        "Delivered_TWh": np.nan,
                        "Total_Wells": np.nan,
                        "Total_Loss_Cost_M$": np.nan,
                        "Weighted_LCOS": np.nan,
                        "Output_File": str(output_dir / scenario.output_filename),
                    }
                )

        dr_summary = pd.DataFrame(dr_summaries)
        for col in cost_breakdown_columns():
            if col not in dr_summary.columns:
                dr_summary[col] = np.nan
        dr_summary.to_csv(output_dir / "discount_rate_summary.csv", index=False)
        dr_summary[cost_breakdown_columns()].to_csv(output_dir / "capital_cost_breakdown.csv", index=False)
        build_capital_breakdown_long(dr_summary).to_csv(output_dir / "capital_cost_breakdown_long.csv", index=False)
        build_lcos_breakdown_long(dr_summary).to_csv(output_dir / "lcos_breakdown_long.csv", index=False)
        build_lcos_breakdown_grouped(dr_summary).to_csv(output_dir / "lcos_breakdown_grouped.csv", index=False)
        all_summaries.extend(dr_summaries)

    summary = pd.DataFrame(all_summaries)
    for col in cost_breakdown_columns():
        if col not in summary.columns:
            summary[col] = np.nan
    output_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_root / "discount_rate_summary_all.csv", index=False)
    summary[cost_breakdown_columns()].to_csv(output_root / "capital_cost_breakdown_all.csv", index=False)
    build_capital_breakdown_long(summary).to_csv(output_root / "capital_cost_breakdown_long_all.csv", index=False)
    build_lcos_breakdown_long(summary).to_csv(output_root / "lcos_breakdown_long_all.csv", index=False)
    build_lcos_breakdown_grouped(summary).to_csv(output_root / "lcos_breakdown_grouped_all.csv", index=False)
    print_batch_validations(summary)
    return summary


def parse_float_list(value: str) -> list[float]:
    return [float(v.strip()) for v in value.split(",") if v.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run UK portfolio optimisation for 4%, 7%, and 10% discount-rate sensitivity."
    )
    parser.add_argument("--input-dir", default=str(INPUT_DIR), help="Folder containing optim_dataset_* inputs.")
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Folder where DR_04, DR_07, and DR_10 output folders are written. "
            "Default depends on --capex-treatment."
        ),
    )
    parser.add_argument(
        "--discount-rates",
        default=",".join(str(r) for r in DISCOUNT_RATES),
        help="Comma-separated discount rates, e.g. 0.04,0.07,0.10.",
    )
    parser.add_argument(
        "--capex-treatment",
        choices=["upfront", "discounted_annual"],
        default=CAPEX_TREATMENT,
        help=(
            "'upfront' keeps previous behavior. 'discounted_annual' spreads CAPEX evenly over the "
            "active horizon and discounts those annual capital tranches."
        ),
    )
    parser.add_argument("--verbose-gurobi", action="store_true", help="Show Gurobi logs.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_root = Path(args.output_root) if args.output_root else default_output_root(input_dir, args.capex_treatment)
    summary_df = run_batch(
        input_dir=input_dir,
        output_root=output_root,
        discount_rates=parse_float_list(args.discount_rates),
        scenarios=scenario_grid(),
        capex_treatment=args.capex_treatment,
        well_budget=WELL_BUDGET,
        allow_cg=ALLOW_CG,
        verbose=args.verbose_gurobi,
    )
    print(f"Finished {len(summary_df)} cycle-level optimisation summaries.")
