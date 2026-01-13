import os

import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from CoolProp.CoolProp import PropsSI
from scipy.stats import qmc
from joblib import load


# ----------------------------
# Constants
# ----------------------------
H2_COST = 3.0
T_STD = 293.15
P_STD_BAR = 1.01325  # bar


# ----------------------------
# Model helpers
# ----------------------------
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


# ----------------------------
# Domain helpers
# ----------------------------
def compute_h2_capacity_m3_std(df: pd.DataFrame) -> list[float]:
    """
    Returns H2 capacity in m3 at standard conditions (as used in the original code).
    """
    rho_h2_std = PropsSI("D", "P", P_STD_BAR * 1e5, "T", T_STD, "Hydrogen")
    rho_ch4_std = PropsSI("D", "P", P_STD_BAR * 1e5, "T", T_STD, "CH4")

    h2_cap = []
    for ii in range(len(df)):
        rho_ch4 = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii], "CH4")
        rho_h2 = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii], "Hydrogen")

        vol = df["RGIIP"].iloc[ii] * 1e6
        m_h2_std = vol * rho_h2 * (rho_ch4_std / rho_ch4)  # m3 at standard conditions (per original comment)
        h2_vol = m_h2_std / rho_h2_std
        h2_cap.append(h2_vol)

    return h2_cap


def optim_data(
    df: pd.DataFrame,
    cycle_length_days: int,
    scalers: dict,
    model: nn.Module,
    clf,
    cg_type: str,
    input_directory: str,
) -> None:
    """
    Generates optimisation dataset CSVs: one file per cycle under optim_dataset_{CL}_{CG_type}_{H2_COST}.
    Behavior matches the original script.
    """
    # Sampling bounds
    fr_min, fr_max = 1e5, 1.5e6
    cg_min, cg_max = 0, 5
    cycles = list(range(10))

    # Costs / constants (as original)
    well_cost = 2.9e5  # $ per well
    compressor_size = 2000  # H2 kg per hour
    compressor_cost = 10200000  # $ per unit
    compressor_power = 2.2  # kWh per kg H2
    cost_of_electricity = 0.14  # $ per kWh
    water_requirment = 50  # L/kg H2
    cooling_cost = 0.0002  # $ per 1 L H2O

    rho_h2_std = PropsSI("D", "P", P_STD_BAR * 1e5, "T", T_STD, "Hydrogen")

    print(f"{len(df)}")

    data = []

    for ii in range(len(df)):
        h2_density = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii], "Hydrogen")
        cg_density = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii], cg_type)

        perm = df["Permeability"].iloc[ii]
        poro = df["Porosity"].iloc[ii]
        pressure = df["Pressure"].iloc[ii]
        temperature = df["Temperature"].iloc[ii]
        delta_rho = cg_density - h2_density

        field_name = df["Field Name"].iloc[ii]
        now = df["Number of Wells"].iloc[ii]
        rgiip = df["RGIIP"].iloc[ii]
        h2_capacity = df["H2 Capacity [m3]"].iloc[ii]

        samples_no = int(now * 300)

        np.random.seed(42)
        sampler = qmc.LatinHypercube(d=3, seed=42)
        lhs_xyz = sampler.random(n=samples_no)

        fr_samples = lhs_xyz[:, 0] * (fr_max - fr_min) + fr_min
        cg_samples = lhs_xyz[:, 1] * (cg_max - cg_min) + cg_min
        now_samples = lhs_xyz[:, 2] * (now - 1) + 1

        for j in range(samples_no):
            flow_rate = fr_samples[j]
            cg_ratio = cg_samples[j]
            if cg_type != "H2":
                cg_ratio = 0.0

            number_of_wells = int(np.round(now_samples[j]))
            if number_of_wells < 1:
                number_of_wells = 1

            scaler = scalers["X_scaler"]
            rf_list = []
            wg_cum_prod_h2 = 0.0

            X = np.array([[flow_rate, perm, pressure, delta_rho]])
            if perm < 8:
                pred = clf.predict(X)
                if pred == 0:
                    continue

            for cl_i in cycles:
                full_input = np.array(
                    [[flow_rate, cycle_length_days, perm, pressure, delta_rho, poro, temperature, cg_ratio, cl_i]]
                )
                scaled = scaler.transform(full_input)
                input_tensor = torch.tensor(scaled, dtype=torch.float32)

                with torch.no_grad():
                    rf = model(input_tensor).item()
                    if rf > 1:
                        print("Warning: RF exceeds 1.0, capping to 1.0")
                        rf = 1.0

                rf_list.append(rf)

                if cl_i > 0:
                    mrf = cl_i * rf - rf_list[cl_i - 1] * (cl_i - 1)
                else:
                    mrf = rf

                PSA_rec = 0.9

                wg_cum_prod_h2 = wg_cum_prod_h2 + (mrf * (cycle_length_days / 2) * flow_rate * number_of_wells) * PSA_rec
                wg_cum_inj_h2 = (cycle_length_days / 2) * flow_rate * number_of_wells
                cg_cum_inj_h2 = cg_ratio * (cycle_length_days / 2) * flow_rate * number_of_wells

                gas_cost = (wg_cum_inj_h2 + cg_cum_inj_h2) * rho_h2_std * H2_COST

                if cg_cum_inj_h2 + wg_cum_inj_h2 > h2_capacity:
                    continue

                total_hours = (cycle_length_days / 2) * 24 + (cycle_length_days / 2) * cg_ratio * 24
                compressor_capital_cost = (
                    ((wg_cum_inj_h2 + cg_cum_inj_h2) * rho_h2_std / (total_hours * compressor_size)) * compressor_cost
                )
                well_capital_cost = well_cost * number_of_wells

                cg_om_cost = cg_cum_inj_h2 * rho_h2_std * (
                    compressor_power * cost_of_electricity + cooling_cost * water_requirment + (0.05 + 0.0045)
                )
                wg_om_cost = wg_cum_inj_h2 * rho_h2_std * (
                    compressor_power * cost_of_electricity + cooling_cost * water_requirment + (0.05 + 0.0045)
                )

                total_capital_cost = compressor_capital_cost + well_capital_cost + gas_cost + cg_om_cost
                CRF = 0.1 * (1 + 0.1) ** 40 / ((1 + 0.1) ** 40 - 1)
                levelised_capital_cost = total_capital_cost * CRF / 0.8

                lcos = (
                    (levelised_capital_cost / (wg_cum_inj_h2 * rho_h2_std * 360 / cycle_length_days))
                    + cost_of_electricity
                    + cooling_cost
                    + 0.05
                    + 0.0045
                )
                if lcos == 0 or wg_cum_inj_h2 == 0 or levelised_capital_cost == 0:
                    check = 1  # kept from original

                wg_inj_twh = wg_cum_inj_h2 * rho_h2_std * 39.41 / 1e9
                wg_prod_twh = wg_cum_prod_h2 * rho_h2_std * 39.41 / 1e9
                cg_twh = cg_cum_inj_h2 * rho_h2_std * 39.41 / 1e9

                data.append(
                    {
                        "Field Name": field_name,
                        "Porosity [-]": poro,
                        "Permeability [mD]": perm,
                        "Reservoir Pressure[bar]": pressure,
                        "Reservoir Temp [K]": temperature,
                        "Density Difference [kg/m3]": delta_rho,
                        "Flow Rate [sm3/d]": flow_rate,
                        "Cycle Length [d]": cycle_length_days,
                        "Cycle_No": cl_i,
                        "CG Ratio": cg_ratio,
                        "Predicted RF [-]": rf,
                        "Predicted MRf [-]": mrf,
                        "Number of Wells": number_of_wells,
                        "RGIIP [1e6 scm]": rgiip,
                        "CG injected [m3]": cg_cum_inj_h2,
                        "Net H2 Stored [m3]": (cl_i + 1) * wg_cum_inj_h2 - wg_cum_prod_h2,
                        "Capital Cost [$]": total_capital_cost,
                        "WG O&M Cost [$]": wg_om_cost,
                        "LCOS": lcos,
                        "Cum CG Injected [Twh]": cg_twh,
                        "Cum H2 Injected [Twh]": (cl_i + 1) * wg_inj_twh,
                        "Cum H2 Produced [Twh]": wg_prod_twh,
                    }
                )

    folder = os.path.join(input_directory, f"optim_dataset_{cycle_length_days}_{cg_type}_{H2_COST}")
    os.makedirs(folder, exist_ok=True)

    data = pd.DataFrame(data)
    for k in range(10):
        kk = data[data["Cycle_No"] == k]
        kk.to_csv(os.path.join(folder, f"cycle_{k}.csv"), index=False)


def main(input_directory: str) -> None:
    clf = load("rf_validity.joblib")

    # Field data CSV
    csv_path = r"Y:\Mixing Results\July\consolidated_output - Final.csv"
    df = pd.read_csv(csv_path, encoding="cp1252", thousands=",")

    # Column handling
    columns = [
        "Field Name",
        "Porosity [-]",
        "Permeability [mD]",
        "Reservoir Pressure[MPa]",
        "Reservoir Temp [C]",
        "Number of Wells",
        "Pore Volume",
        "RGIIP",
        "Cum",
        "Gas Saturation [-]",
    ]
    df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors="coerce")

    df_clean = df.dropna(subset=["Number of Wells"]).reset_index(drop=True)
    df_clean["Reservoir Pressure[MPa]"] = df_clean["Reservoir Pressure[MPa]"] * 10
    df_clean["Reservoir Temp [C]"] = df_clean["Reservoir Temp [C]"] + 273.15

    df_clean = df_clean.rename(
        columns={
            "Reservoir Pressure[MPa]": "Pressure",
            "Reservoir Temp [C]": "Temperature",
            "Porosity [-]": "Porosity",
            "Permeability [mD]": "Permeability",
        }
    )

    df["RGIIP"] = df["RGIIP"].replace({",": ""}, regex=True).astype(float)

    df_clean["H2 Capacity [m3]"] = compute_h2_capacity_m3_std(df_clean)

    # Load ANN + scalers
    activation = ["tanh", "relu", "sigmoid"]
    model = build_model(input_dim=9, hidden_sizes=[36, 92, 108], activations=activation)
    model.load_state_dict(torch.load("ann_model_withoutCG_AC.pt"))
    model.eval()

    scalers = joblib.load("scalers_withoutCG_AC.pkl")

    # Run
    cg_type = "H2"
    cycle_length_days = 14
    optim_data(df_clean, cycle_length_days, scalers, model, clf, cg_type, input_directory)


if __name__ == "__main__":
    os.chdir(r"Y:\Mixing Results\July")
    input_directory = os.getcwd()
    main(input_directory)
