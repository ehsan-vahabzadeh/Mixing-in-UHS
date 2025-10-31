import os, glob
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from CoolProp.CoolProp import PropsSI
# ---------------- USER SETTINGS ----------------
INPUT_DIR   = r"Y:\Mixing Results\July"
H2_COST_PER_KG = 4.0                   # £/kg (already used in your dataset creation, but we'll recompute safely)
KG_PER_M3_STP  =  PropsSI("D", "P", 1 * 1e5, "T", 293.15, "Hydrogen")
KWH_PER_KG_H2  = 39.41                 # kWh/kg (HHV)
TARGET_TWH  = 200                   # energy target
CL = 360 
r = 0.07
FOLDER = f"optim_dataset_{CL}_H2"
NOC = 1 # number of cycles
OUTPUT_PLAN   = f"optimal_plan_CL{CL}_TWh{TARGET_TWH}.xlsx"
# Optional global limits:
WELL_BUDGET   = None    # e.g., 500   -> limit total wells across UK
ALLOW_CG      = True    # False -> forces CG Ratio == 0 scenarios only
# ------------------------------------------------
keep = [
                "Field Name", "Flow Rate [sm3/d]", "Number of Wells", "CG Ratio",
                "Cum H2 Injected [m3]", "CG injected [m3]", "Cum H2 Produced [m3]", "Net H2 Stored [m3]",
                "Loss Cost [£]", "Porosity [-]", "Permeability [mD]", "Reservoir Pressure[bar]", "Reservoir Temp [K]", "Loss Cost [M$]", 
                "Cum H2 Produced [Twh]","Cum H2 Injected [Twh]", "LCOS"
            ]
H2_COST_PER_M3 = H2_COST_PER_KG * KG_PER_M3_STP
KWH_PER_M3     = KWH_PER_KG_H2 * KG_PER_M3_STP
def twh_to_m3(twh: float) -> float:
    return (twh * 1e9) / KWH_PER_M3
def save_cycles_to_excel(df_long, out_xlsx="rf_by_cycle.xlsx",
                         cycle_col="Cycle_No"):
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        # optional: all data in one sheet
        # df_long.to_excel(writer, sheet_name="all_cycles", index=False)

        for cyc, g in df_long.groupby(cycle_col, sort=True):
            sheet = f"cycle_{int(cyc)}"
            sheet = sheet[:31]  # Excel sheet names max 31 chars
            g.to_excel(writer, sheet_name=sheet, index=False)
def load_scenarios(input_dir, pattern, allow_cg=True, cyc = 0):
    
    if cyc > 9:
        sheet = f"cycle_{9}"
    else:  
        sheet = f"cycle_{cyc}"
    paths = glob.glob(os.path.join(input_dir, pattern, sheet + ".csv"))
    df = pd.read_csv(paths[0])
    # df = pd.concat(df, ignore_index=True)

    # # Clean numeric columns (commas)
    # num_cols = ["Cum H2 Injected [Twh]", "Cum CG injected [Twh]", "Cum H2 Produced [Twh]", "Net H2 Stored [m3]",
    #             "Flow Rate [sm3/d]", "Number of Wells", "CG Ratio"]
    # for c in num_cols:
    #     if c in df.columns and df[c].dtype == "object":
    #         df[c] = df[c].str.replace(",", "", regex=False)
    #     if c in df.columns:
    #         df[c] = pd.to_numeric(df[c], errors="coerce")

    # Basic sanity
    need = ["Field Name", "Cum H2 Produced [Twh]", "Net H2 Stored [m3]", "Cum CG Injected [Twh]","Capital Cost [$]", "WG O&M Cost [$]",
            "Number of Wells", "Flow Rate [sm3/d]", "CG Ratio", "Predicted RF [-]", "Cum H2 Injected [Twh]", "LCOS"]
    df = df.dropna(subset=need).reset_index(drop=True)

    # Filter CG policy (if not allowed, keep only CG Ratio == 0)
    if not allow_cg:
        df = df.loc[(df["CG Ratio"].fillna(0.0) == 0.0)].reset_index(drop=True)
    Twh_per_cycle = (df["Flow Rate [sm3/d]"]* df["Number of Wells"] * df["Cycle Length [d]"] / 2) * KWH_PER_M3 / 1e9
    df["Net H2 Stored [Twh]"] = df["Net H2 Stored [m3]"] * KWH_PER_M3 / 1e9
    # Compute loss cost from data only (no ML)
    if cyc > 9:
        # check1 =  (cyc - 9) * ((1 - df["Predicted MRf [-]"][0]) * Twh_per_cycle[0])
        # check2 = df["Net H2 Stored [Twh]"][0] 
        # check3 = df["Cum H2 Produced [Twh]"][0]
        # check4 = (cyc - 9) * (df["Predicted MRf [-]"][0] * Twh_per_cycle[0])
        df["Lost [Twh]"]       = (df["Net H2 Stored [Twh]"] + (cyc - 9) * ((1 - df["Predicted MRf [-]"]) * Twh_per_cycle) + df["Cum CG Injected [Twh]"])
        df["Cum H2 Produced [Twh]"] = df["Cum H2 Produced [Twh]"] + (cyc - 9) * (df["Predicted MRf [-]"] * Twh_per_cycle)
        df["Cum H2 Injected [Twh]"] = df["Cum H2 Injected [Twh]"] + (cyc - 9) * Twh_per_cycle
    else:
         df["Lost [Twh]"]       = (df["Net H2 Stored [Twh]"] + df["Cum CG Injected [Twh]"])
    
    # df["Loss Cost [M$]"] = df["Lost [Twh]"] *1e9 / KWH_PER_KG_H2 * H2_COST_PER_KG / 1e6 # in million $
    # df["Loss Cost [M$]"] = (df["Capital Cost [$]"] + df["WG O&M Cost [$]"] * (cyc+1)) / 1e6 # in million $
    
    
    years = max(1, round((cyc+1) * CL / 360))  # project horizon in years

    # Annual OPEX approximation ($/yr): scale per-cycle O&M to per-year
    annual_opex = df["WG O&M Cost [$]"] * (360.0 / CL)

    # PV(OPEX)
    pv_opex = sum(annual_opex / ((1 + r) ** y) for y in range(1, years + 1))

    # CAPEX at t=0 (if your CAPEX is staged, discount each stage instead)
    pv_capex = pd.to_numeric(df["Capital Cost [$]"], errors="coerce").fillna(0.0)

    # Delivered energy over the horizon (TWh total, from your sheet)
    tot_twh = pd.to_numeric(df["Cum H2 Produced [Twh]"], errors="coerce").fillna(0.0)

    # Approximate uniform annual energy (TWh/yr)
    annual_twh = tot_twh / years

    # PV(energy) (TWh)
    pv_energy_twh = sum(annual_twh / ((1 + r) ** y) for y in range(1, years + 1))
    df["Cum H2 Produced [Twh]"] = tot_twh / (cyc+1)
    # LCOS = PV(cost)/PV(energy)
    df["LCOS"] = (pv_capex + pv_opex) / pv_energy_twh/1e6 

    # Objective number to minimize = PV(cost) directly
    df["Loss Cost [M$]"] = (pv_capex + pv_opex) / 1e6  # in million $

    
    
    # Tot_time = round((cyc+1) * CL / 360)
    # if Tot_time == 0:
    #     Tot_time = 1
    # CAPEX = pd.to_numeric(df["Capital Cost [$]"], errors="coerce").fillna(0.0)
    # df["OPEX"] = df["WG O&M Cost [$]"] * 0
    # df["Met_demand"] = df["WG O&M Cost [$]"] * 0
    # for ii in range(Tot_time):
    #     df["OPEX"] = df["OPEX"] + (df["WG O&M Cost [$]"] * (360 / CL)) / ((1+0.1)**ii)
    #     df["Met_demand"] = df["Met_demand"] +  ( ((df["Cum H2 Produced [Twh]"] * 1e6)) / (((cyc+1) * CL)/360) ) / ((1+0.1)**ii)
    # df["LCOS"] = (df["Capital Cost [$]"] + df["OPEX"]) / (df["Met_demand"])
    # df["Loss Cost [M$]"] = df["LCOS"] * df["Cum H2 Produced [Twh]"] * 1e6 / (cyc+1) / 1e6 # in million $
    # IDs
    df["res_id"]  = df["Field Name"].astype("category").cat.codes
    df["cand_id"] = np.arange(len(df), dtype=int)
    return df

def build_and_solve(df: pd.DataFrame, target_twh: float, well_budget=None, logfile=None):
    m = gp.Model("UK_H2_MinLoss")
    if logfile:
        m.Params.LogFile = logfile
    m.Params.OutputFlag = 1

    # ---- Solution pool settings ----
    m.Params.PoolSearchMode = 1     # near-optimal distinct plans
    m.Params.PoolGap        = 1  # within 5% of best cost
    m.Params.PoolSolutions  = 50    # up to 50 alternatives

    # Decision vars
    x = m.addVars(df.index, vtype=GRB.BINARY, name="x")

    # Objective: minimize PV(cost)
    m.setObjective(gp.quicksum(x[k] * df.at[k, "Loss Cost [M$]"] for k in df.index), GRB.MINIMIZE)

    # Meet energy target (NB: you're using raw TWh here; if you meant PV energy, pass that in)
    m.addConstr(gp.quicksum(x[k] * df.at[k, "Cum H2 Produced [Twh]"] for k in df.index) >= target_twh,
                name="energy_target")

    # At most one scenario per reservoir
    for r, idx in df.groupby("res_id").groups.items():
        m.addConstr(gp.quicksum(x[k] for k in idx) <= 1, name=f"one_scenario_per_res_{int(r)}")

    # Well budget (optional)
    if well_budget is not None and "Number of Wells" in df.columns:
        m.addConstr(gp.quicksum(x[k] * df.at[k, "Number of Wells"] for k in df.index) <= well_budget,
                    name="well_budget")

    m.optimize()

    # Best solution (for backward compatibility)
    chosen_idx = [k for k in df.index if x[k].X > 0.5]
    sol_best = df.loc[chosen_idx].copy()
    sol_best["x"] = 1

    # ---- Collect all pool solutions ----
    all_solutions = []
    nSolutions = m.SolCount

    for i in range(nSolutions):
        m.Params.SolutionNumber = i
        chosen_idx_i = [k for k in df.index if x[k].Xn > 0.5]
        sol_i = df.loc[chosen_idx_i].copy()
        sol_i["x"] = 1

        cost_i   = sol_i["Loss Cost [M$]"].sum()
        energy_i = sol_i["Cum H2 Produced [Twh]"].sum()
        wells_i  = sol_i["Number of Wells"].sum()

        all_solutions.append({
            "pool_id": i,
            "cost_M$": float(cost_i),
            "delivered_TWh": float(energy_i),
            "total_wells": int(wells_i),
            "fields": list(sol_i["Field Name"].astype(str).unique()),
            "df": sol_i,
        })

    return m, sol_best, all_solutions


if __name__ == "__main__":
    os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
    Years = np.array([10])
    cycles_of_interest = Years * 360 / CL
    cycles_of_interest = np.unique(cycles_of_interest).astype(int)
    # cycles_of_interest = [9,19,29,39,49,59,69,79,89,99]  # e.g., range(0, 10) for cycles 0 to 9  
    with pd.ExcelWriter(OUTPUT_PLAN, engine="openpyxl") as writer:
        for cyc in cycles_of_interest:
            df = load_scenarios(INPUT_DIR, FOLDER, allow_cg=ALLOW_CG, cyc=cyc - 1)
            year = round((cyc * CL) / 360)
            pv_mult = sum(1.0/((1+r)**y) for y in range(1, year+1))
            target_pv_twh = TARGET_TWH * pv_mult         # if TARGET_TWH is annual demand
            # target_pv_twh = TARGET_TWH                  # if TARGET_TWH is a fixed total for the horizon
            model, sol, all_solutions = build_and_solve(df, TARGET_TWH, well_budget=WELL_BUDGET)
            # Print the best, as before
            total_loss = sol["Loss Cost [M$]"].sum()
            total_prod_TWh = sol["Cum H2 Produced [Twh]"].sum()
            total_wells = sol["Number of Wells"].sum()

            print("\n=== Optimal Scenario Selection ===")
            print(f"Delivered: {total_prod_TWh:.2f} TWh (target {TARGET_TWH:.2f} TWh)")
            print(f"Total wells used: {int(total_wells)}")
            print(f"Minimum loss cost: Million ${total_loss:,.0f}")

            # Save best plan (your existing 'keep' subset)
            sheet = f"cycle_{int(cyc)}"[:31]
            for c in keep:
                if c not in sol.columns:
                    sol[c] = np.nan
            sol[keep].to_excel(writer, sheet_name=sheet, index=False)

            # Save the option set (summary + optional detail sheets)
            summary_rows = []
            for s in all_solutions:
                summary_rows.append({
                    "Pool ID": s["pool_id"],
                    "Total Cost [M$]": s["cost_M$"],
                    "Delivered [TWh]": s["delivered_TWh"],
                    "Total Wells": s["total_wells"],
                    "Fields": ", ".join(s["fields"]),
                })
            summary_df = pd.DataFrame(summary_rows).sort_values("Total Cost [M$]")

            sheet_summary = f"{sheet}_options"[:31]
            summary_df.to_excel(writer, sheet_name=sheet_summary, index=False)

            max_plans_to_write = min(10, len(all_solutions))
            for s in all_solutions[:max_plans_to_write]:
                plan_sheet = f"{sheet}_opt{s['pool_id']}"[:31]
                df_plan = s["df"].copy()
                for c in keep:
                    if c not in df_plan.columns:
                        df_plan[c] = np.nan
                df_plan[keep].to_excel(writer, sheet_name=plan_sheet, index=False)

            
