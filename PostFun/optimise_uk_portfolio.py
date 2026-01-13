import glob
import os

import gurobipy as gp
import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI
from gurobipy import GRB


# ---------------- USER SETTINGS ----------------
INPUT_DIR = r"Y:\Mixing Results\July"

H2_COST_PER_KG = 3.0  # $/kg (used earlier; here for consistency)
KG_PER_M3_STP = PropsSI("D", "P", 1 * 1e5, "T", 293.15, "Hydrogen")
KWH_PER_KG_H2 = 39.41  # kWh/kg (HHV)

TARGET_TWH = 150
CL = 360
multiplier = 1
r = 0.07

FOLDER = f"optim_dataset_{CL}_H2_{H2_COST_PER_KG}"  # subfolder in INPUT_DIR
NOC = 1  # number of cycles (currently unused)

if multiplier == 1:
    name1 = "Low"
elif multiplier == 10:
    name1 = "Medium"
else:
    name1 = "High"

OUTPUT_PLAN = f"optimal_plan_CL{CL}_TWh{TARGET_TWH}_ {name1}_H2{H2_COST_PER_KG}.xlsx"

WELL_BUDGET = None  # e.g., 500
ALLOW_CG = True
# ------------------------------------------------


H2_COST_PER_M3 = H2_COST_PER_KG * KG_PER_M3_STP
KWH_PER_M3 = KWH_PER_KG_H2 * KG_PER_M3_STP


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


def load_scenarios(input_dir: str, pattern: str, allow_cg: bool = True, cyc: int = 0) -> pd.DataFrame:
    """
    Loads scenario candidates for a given cycle and computes derived quantities:
    - Lost energy
    - PV CAPEX/OPEX and LCOS proxy
    - Objective column "Loss Cost [M$]"
    Adds res_id and cand_id for MILP grouping/selection.
    """
    if cyc > 9:
        sheet = "cycle_9"
    else:
        sheet = f"cycle_{cyc}"

    paths = glob.glob(os.path.join(input_dir, pattern, sheet + ".csv"))
    df = pd.read_csv(paths[0])

    need = [
        "Field Name",
        "Cum H2 Produced [Twh]",
        "Net H2 Stored [m3]",
        "Cum CG Injected [Twh]",
        "Capital Cost [$]",
        "WG O&M Cost [$]",
        "Number of Wells",
        "Flow Rate [sm3/d]",
        "CG Ratio",
        "Predicted RF [-]",
        "Cum H2 Injected [Twh]",
        "LCOS",
    ]
    df = df.dropna(subset=need).reset_index(drop=True)

    if not allow_cg:
        df = df.loc[(df["CG Ratio"].fillna(0.0) == 0.0)].reset_index(drop=True)

    # Per-cycle injection energy equivalent
    twh_per_cycle = (df["Flow Rate [sm3/d]"] * df["Number of Wells"] * df["Cycle Length [d]"] / 2) * KWH_PER_M3 / 1e9

    df["Net H2 Stored [Twh]"] = df["Net H2 Stored [m3]"] * KWH_PER_M3 / 1e9

    PSA_cap = 10.4702 * np.exp(-60.7137 * df["Predicted RF [-]"]) + 3.1879 * np.exp(-4.8854 * df["Predicted RF [-]"])
    PSA_cap = PSA_cap * multiplier
    df["PSA Cost [$/kg]"] = PSA_cap
    print(np.average(PSA_cap))

    PSA_rec = 0.9
    PSA_opex = PSA_cap / 0.6 * 0.4

    # Cycle extrapolation logic
    if cyc > 9:
        df["Lost [Twh]"] = (
            df["Net H2 Stored [Twh]"]
            + (cyc - 9) * ((1 - PSA_rec * df["Predicted MRf [-]"]) * twh_per_cycle)
            + df["Cum CG Injected [Twh]"]
        )
        df["Cum H2 Produced [Twh]"] = df["Cum H2 Produced [Twh]"] + (cyc - 9) * PSA_rec * (df["Predicted MRf [-]"] * twh_per_cycle)
        df["Cum H2 Injected [Twh]"] = df["Cum H2 Injected [Twh]"] + (cyc - 9) * twh_per_cycle
    else:
        df["Lost [Twh]"] = df["Net H2 Stored [Twh]"] + df["Cum CG Injected [Twh]"]

    # Project horizon (years)
    years = max(1, round((cyc + 1) * CL / 360))

    # Add PSA OPEX and CAPEX to cost fields
    df["WG O&M Cost [$]"] = df["WG O&M Cost [$]"] + ((df["Predicted RF [-]"] * twh_per_cycle) * 1e9 / KWH_PER_KG_H2) * PSA_opex
    annual_opex = df["WG O&M Cost [$]"] * (360.0 / CL)
    pv_opex = sum(annual_opex / ((1 + r) ** y) for y in range(1, years + 1))

    df["Capital Cost [$]"] = df["Capital Cost [$]"] + ((df["Predicted RF [-]"] * twh_per_cycle) * 1e9 / KWH_PER_KG_H2) * PSA_cap
    df["Purification Capital Cost [$]"] = ((df["Predicted RF [-]"] * twh_per_cycle) * 1e9 / KWH_PER_KG_H2) * PSA_cap
    pv_capex = pd.to_numeric(df["Capital Cost [$]"], errors="coerce").fillna(0.0)

    tot_twh = pd.to_numeric(df["Cum H2 Produced [Twh]"], errors="coerce").fillna(0.0)
    annual_twh = tot_twh / years
    pv_energy_twh = sum(annual_twh / ((1 + r) ** y) for y in range(1, years + 1))

    # Note: original code overwrites production with an annualized value
    df["Cum H2 Produced [Twh]"] = tot_twh / (cyc + 1)

    df["LCOS"] = (pv_capex + pv_opex) / pv_energy_twh / 1e6
    df["Loss Cost [M$]"] = (pv_capex + pv_opex) / 1e6

    # IDs for MILP constraints
    df["res_id"] = df["Field Name"].astype("category").cat.codes
    df["cand_id"] = np.arange(len(df), dtype=int)

    return df


def build_and_solve(df: pd.DataFrame, target_twh: float, well_budget=None, logfile=None):
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
    m.Params.OutputFlag = 1

    x = m.addVars(df.index, vtype=GRB.BINARY, name="x")

    m.setObjective(gp.quicksum(x[k] * df.at[k, "Loss Cost [M$]"] for k in df.index), GRB.MINIMIZE)

    m.addConstr(
        gp.quicksum(x[k] * df.at[k, "Cum H2 Produced [Twh]"] for k in df.index) >= target_twh,
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

    chosen_idx = [k for k in df.index if x[k].X > 0.5]
    sol = df.loc[chosen_idx].copy()
    sol["x"] = 1
    return m, sol


if __name__ == "__main__":
    os.chdir(r"Y:\Mixing Results\July")

    years = np.array([1, 5, 10, 15, 20, 25, 30])
    cycles_of_interest = years * 360 / CL
    cycles_of_interest = np.unique(cycles_of_interest).astype(int)

    with pd.ExcelWriter(OUTPUT_PLAN, engine="openpyxl") as writer:
        for cyc in cycles_of_interest:
            df = load_scenarios(INPUT_DIR, FOLDER, allow_cg=ALLOW_CG, cyc=cyc - 1)

            year = round((cyc * CL) / 360)
            pv_mult = sum(1.0 / ((1 + r) ** y) for y in range(1, year + 1))
            target_pv_twh = TARGET_TWH * pv_mult  # computed but not used (kept)

            model, sol = build_and_solve(df, TARGET_TWH, well_budget=WELL_BUDGET)

            total_loss = sol["Loss Cost [M$]"].sum()
            total_prod_twh = sol["Cum H2 Produced [Twh]"].sum()
            total_wells = sol["Number of Wells"].sum()

            print("\n=== Optimal Scenario Selection ===")
            print(f"Delivered: {total_prod_twh:.2f} TWh (target {TARGET_TWH:.2f} TWh)")
            print(f"Total wells used: {int(total_wells)}")
            print(f"Minimum loss cost: Million ${total_loss:,.0f}")

            keep = [
                "Field Name",
                "Flow Rate [sm3/d]",
                "Number of Wells",
                "CG Ratio",
                "Cum H2 Injected [m3]",
                "CG injected [m3]",
                "Cum H2 Produced [m3]",
                "Net H2 Stored [m3]",
                "Loss Cost [£]",
                "Porosity [-]",
                "Permeability [mD]",
                "Reservoir Pressure[bar]",
                "Reservoir Temp [K]",
                "PSA Cost [$/kg]",
                "Purification Capital Cost [$]",
                "Loss Cost [M$]",
                "Cum H2 Produced [Twh]",
                "Cum H2 Injected [Twh]",
                "LCOS",
                "Predicted RF [-]",
            ]

            sol["Cum H2 Injected [Twh]"] = sol["Cum H2 Injected [Twh]"] / (cyc)

            for c in keep:
                if c not in sol.columns:
                    sol[c] = np.nan

            sheet = f"cycle_{int(cyc)}"[:31]
            sol[keep].to_excel(writer, sheet_name=sheet, index=False)
