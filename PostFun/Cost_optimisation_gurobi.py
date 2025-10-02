import os, glob
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

# ---------------- USER SETTINGS ----------------
INPUT_DIR   = r"Y:\Mixing Results\July"
PATTERN     = "optim_dataset_180_H2.csv"    # files from your optim_data() writer
TARGET_TWH  = 100.0                    # energy target
H2_COST_PER_KG = 4.0                   # £/kg (already used in your dataset creation, but we'll recompute safely)
KG_PER_M3_STP  = 0.08988               # kg/m3 at STP
KWH_PER_KG_H2  = 39.41                 # kWh/kg (HHV)
OUTPUT_PLAN   = "optimal_plan.csv"
# Optional global limits:
WELL_BUDGET   = None    # e.g., 500   -> limit total wells across UK
ALLOW_CG      = True    # False -> forces CG Ratio == 0 scenarios only
# ------------------------------------------------

H2_COST_PER_M3 = H2_COST_PER_KG * KG_PER_M3_STP
KWH_PER_M3     = KWH_PER_KG_H2 * KG_PER_M3_STP

def twh_to_m3(twh: float) -> float:
    return (twh * 1e9) / KWH_PER_M3

def load_scenarios(input_dir, pattern, allow_cg=True):
    paths = glob.glob(os.path.join(input_dir, pattern))
    if not paths:
        raise FileNotFoundError("No candidate CSVs found. Check INPUT_DIR and PATTERN.")
    df = pd.concat([pd.read_csv(p, encoding="cp1252") for p in paths], ignore_index=True)

    # Clean numeric columns (commas)
    num_cols = ["Cum H2 Injected [m3]", "CG injected [m3]", "Cum H2 Produced [m3]", "Net H2 Stored [m3]",
                "Flow Rate [sm3/d]", "Number of Wells", "CG Ratio"]
    for c in num_cols:
        if c in df.columns and df[c].dtype == "object":
            df[c] = df[c].str.replace(",", "", regex=False)
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Basic sanity
    need = ["Field Name", "Cum H2 Produced [m3]", "Net H2 Stored [m3]", "CG injected [m3]",
            "Number of Wells", "Flow Rate [sm3/d]", "CG Ratio"]
    df = df.dropna(subset=need).reset_index(drop=True)

    # Filter CG policy (if not allowed, keep only CG Ratio == 0)
    if not allow_cg:
        df = df.loc[(df["CG Ratio"].fillna(0.0) == 0.0)].reset_index(drop=True)

    # Compute loss cost from data only (no ML)
    NOC = 40 # number of cycles
    df["Lost m3"]       = (df["Net H2 Stored [m3]"] * NOC + df["CG injected [m3]"])
    df ["Cum H2 Produced [Twh]"] = df["Cum H2 Produced [m3]"] * KWH_PER_M3 / 1e9
    # df["Loss Cost [M$]"] = (df["Capital Cost [$]"] + df["WG O&M Cost [$]"] * NOC) / 1e6 # in million $
    df["Loss Cost [M$]"] = df["Lost m3"] * H2_COST_PER_M3 / 1e6 # in million $

    # IDs
    df["res_id"]  = df["Field Name"].astype("category").cat.codes
    df["cand_id"] = np.arange(len(df), dtype=int)
    return df

def build_and_solve(df: pd.DataFrame, target_twh: float, well_budget=None, logfile=None):
    target_m3 = twh_to_m3(target_twh)

    m = gp.Model("UK_H2_MinLoss")
    if logfile:
        m.Params.LogFile = logfile
    m.Params.OutputFlag = 1

    # Decision: select scenario k
    x = m.addVars(df.index, vtype=GRB.BINARY, name="x")

    # Objective: minimize total loss cost
    # m.setObjective(gp.quicksum(x[k] * df.at[k, "Lost"] for k in df.index), GRB.MINIMIZE)
    m.setObjective(gp.quicksum(x[k] * df.at[k, "Loss Cost [M$]"] for k in df.index), GRB.MINIMIZE)
    # Target (delivered H2 >= target)
    m.addConstr(gp.quicksum(x[k] * df.at[k, "Cum H2 Produced [Twh]"] for k in df.index) >= target_twh,
                name="energy_target")

    # At most one scenario per reservoir
    for r, idx in df.groupby("res_id").groups.items():
        m.addConstr(gp.quicksum(x[k] for k in idx) <= 1, name=f"one_scenario_per_res_{int(r)}")

    # Optional: total wells budget
    if well_budget is not None and "Number of Wells" in df.columns:
        m.addConstr(gp.quicksum(x[k] * df.at[k, "Number of Wells"] for k in df.index) <= well_budget,
                    name="well_budget")

    m.optimize()

    chosen_idx = [k for k in df.index if x[k].X > 0.5]
    sol = df.loc[chosen_idx].copy()
    sol["x"] = 1
    return m, sol

if __name__ == "__main__":
    df = load_scenarios(INPUT_DIR, PATTERN, allow_cg=ALLOW_CG)

    model, sol = build_and_solve(df, TARGET_TWH, well_budget=WELL_BUDGET)

    # Summaries
    # total_loss = sol["Lost"].sum()
    total_loss = sol["Loss Cost [M$]"].sum()
    total_prod_TWh = sol["Cum H2 Produced [Twh]"].sum()
    total_wells = sol["Number of Wells"].sum()

    print("\n=== Optimal Scenario Selection ===")
    print(f"Delivered: {total_prod_TWh:.2f} TWh (target {TARGET_TWH:.2f} TWh)")
    print(f"Total wells used: {int(total_wells)}")
    print(f"Minimum loss cost: Million ${total_loss:,.0f}")

    keep = [
        "Field Name", "Flow Rate [sm3/d]", "Number of Wells", "CG Ratio",
        "Cum H2 Injected [m3]", "CG injected [m3]", "Cum H2 Produced [m3]", "Net H2 Stored [m3]",
        "Loss Cost [£]", "Porosity [-]", "Permeability [mD]", "Reservoir Pressure[bar]", "Reservoir Temp [K]", 
        "Cum H2 Produced [Twh]"
    ]
        
    for c in keep:
        if c not in sol.columns: 
            sol[c] = np.nan

    out_path = os.path.join(INPUT_DIR, OUTPUT_PLAN)
    sol[keep].to_csv(out_path, index=False)
    print(f"Saved plan: {out_path}")
