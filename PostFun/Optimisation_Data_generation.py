import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from CoolProp.CoolProp import PropsSI
from pyswarm import pso
import torch
import joblib
from joblib import dump, load
import torch.nn as nn
from pyDOE2 import lhs

T_std = 293.15
P_std = 1.01325
def get_activation(name):
    if name == "relu":
        return nn.ReLU()
    elif name == "tanh":
        return nn.Tanh()
    elif name == "sigmoid":
        return nn.Sigmoid()
    else:
        raise ValueError(f"Unknown activation function: {name}")  
def build_model(input_dim, hidden_sizes, activations):
    layers = []
    in_dim = input_dim

    for out_dim, act_name in zip(hidden_sizes, activations):
        layers.append(nn.Linear(in_dim, out_dim))
        layers.append(get_activation(act_name))
        # layers.append(nn.Dropout(0.2))  # Add dropout for regularization
        in_dim = out_dim
    layers += [nn.Linear(in_dim, 1)]   # <- bound to (0,1)
    layers.append(nn.Sigmoid())  # Output layer
    return nn.Sequential(*layers)
def H2_capacity(df):
    swr = 0.423
    rho_h2_std = PropsSI("D", "P", P_std * 1e5, "T", T_std, "Hydrogen")
    rho_CH4_std = PropsSI("D", "P", P_std * 1e5, "T", T_std,  "CH4")
    H2_cap = []
    for ii in range(len(df)):
        rho_CH4 = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii],  "CH4")
        rho_H2 = PropsSI("D", "P", df["Pressure"].iloc[ii] * 1e5, "T", df["Temperature"].iloc[ii], "Hydrogen")
        vol = df["RGIIP"].iloc[ii] * 1e6
        m_H2_std = vol * rho_H2 * (rho_CH4_std / rho_CH4)   # m3 at standard conditions
        H2_HHV = m_H2_std * 39.41 / 1e9 # Twh
        H2_vol = m_H2_std / rho_h2_std  # m3 at standard conditions
        H2_cap.append(H2_vol) 
    return H2_cap
def optim_data(df, CL, scalers, model, clf,CG_type):
    
    FR_min, FR_max = 1e5, 1.5e6
    CG_min, CG_max = 0, 5
    data = []
    cycles = list(range(10))
    well_cost = 2.9e5 # $ per well
    compressor_size = 2000 #H2 kg per hour
    compressor_cost = 10200000 # $ per unit
    compressor_power = 2.2 #Kwh per kg H2
    cost_of_electricity = 0.14 # $ per kwh
    water_requirment = 50 # L/kg H2
    cooling_cost = 0.0002 # $ per 1 L H2O
    rho_h2_std = PropsSI("D", "P", P_std * 1e5, "T", T_std, "Hydrogen")
    print(f"{len(df)}")
    for ii in range(len(df)):
        H2_density = PropsSI("D", "P", df['Pressure'].iloc[ii] * 1e5, "T", df['Temperature'].iloc[ii], "Hydrogen")
        CG_density = PropsSI("D", "P", df['Pressure'].iloc[ii] * 1e5, "T", df['Temperature'].iloc[ii] , CG_type)
        perm = df['Permeability'].iloc[ii]
        poro = df['Porosity'].iloc[ii]
        pressure = df['Pressure'].iloc[ii]
        temperature = df['Temperature'].iloc[ii]
        delta_rho = CG_density - H2_density
        Field_name = df['Field Name'].iloc[ii]
        NOW = df['Number of Wells'].iloc[ii]
        RGIIP = df['RGIIP'].iloc[ii]
        H2_capacity = df['H2 Capacity [m3]'].iloc[ii]
        samples_NO = 5000  # set how many you want
        if NOW > 10:
            samples_NO = 7000  # set how many you want
        np.random.seed(42)
        # lhs_xyz = lhs(3, samples = samples_NO )
        from scipy.stats import qmc
        sampler = qmc.LatinHypercube(d=3, seed=42)
        lhs_xyz = sampler.random(n=samples_NO)
        FR_samples     = lhs_xyz[:,0] * (FR_max - FR_min) + FR_min
        CG_samples = lhs_xyz[:,1] * (CG_max - CG_min) + CG_min
        NOW_samples      = lhs_xyz[:,2] * (NOW - 1) + 1
        for j in range(samples_NO):   
            Flow_rate = FR_samples[j]
            CG_ratio = CG_samples[j]
            if CG_type != 'H2':
                CG_ratio = 0.0
            Number_of_wells = int(np.round(NOW_samples[j]))  
            if Number_of_wells < 1:
                Number_of_wells = 1      
            scaler = scalers["X_scaler"] 
            rf_list=[] 
            WG_cum_prod_H2 = 0.0 
            X = np.array([[Flow_rate, perm, pressure, delta_rho]])
            if perm < 8:
                pred = clf.predict(X)
                if pred == 0:
                    continue
            for cl_i in cycles: 
                full_input = np.array([[Flow_rate, CL, perm, pressure, delta_rho, poro, temperature, CG_ratio, cl_i]])
                scaled = scaler.transform(full_input)
                input_tensor = torch.tensor(scaled, dtype=torch.float32)  
                with torch.no_grad():
                    rf = model(input_tensor).item()
                    if rf > 1:
                        print("Warning: RF exceeds 1.0, capping to 1.0")
                        rf = 1.0  # Cap RF at 1.0
                rf_list.append(rf)
                if cl_i > 0:
                    mrf = cl_i * rf  - rf_list[cl_i - 1] * (cl_i - 1)
                else:
                    mrf = rf
                WG_cum_prod_H2 = WG_cum_prod_H2 + mrf * (CL / 2) * Flow_rate * Number_of_wells
                WG_cum_inj_H2 = (CL / 2) * Flow_rate * Number_of_wells
                CG_cum_inj_H2 = CG_ratio * (CL / 2) * Flow_rate * Number_of_wells
                gas_cost = (WG_cum_inj_H2 + CG_cum_inj_H2) * rho_h2_std * 4.0 # $
                if CG_cum_inj_H2 + WG_cum_inj_H2 > H2_capacity:
                    continue
                total_hours = (CL/2) * 24 + (CL / 2) * CG_ratio * 24
                compressor_capital_cost = ((WG_cum_inj_H2 + CG_cum_inj_H2) * rho_h2_std / (total_hours * compressor_size)) * compressor_cost
                well_capital_cost = well_cost * Number_of_wells
                CG_OM_cost = CG_cum_inj_H2 * rho_h2_std * ( compressor_power * cost_of_electricity + cooling_cost * water_requirment + (0.05 + 0.0045))
                WG_OM_cost = WG_cum_inj_H2 * rho_h2_std * ( compressor_power * cost_of_electricity + cooling_cost * water_requirment + (0.05 + 0.0045))
                Total_capital_cost = compressor_capital_cost + well_capital_cost + gas_cost + CG_OM_cost
                CRF = 0.1*(1+0.1)**40 / ((1+0.1)**40 - 1)
                Levelised_capital_cost = Total_capital_cost * CRF / 0.8
                LCOS = (Levelised_capital_cost / ( WG_cum_inj_H2 * rho_h2_std * 360/CL )) + cost_of_electricity + cooling_cost + 0.05 + 0.0045
                if LCOS == 0 or WG_cum_inj_H2 == 0 or Levelised_capital_cost == 0:
                    check = 1
                WG_inj_TWh = WG_cum_inj_H2 * rho_h2_std * 39.41 / 1e9
                WG_prod_TWh = WG_cum_prod_H2 * rho_h2_std * 39.41 / 1e9
                CG_Twh = CG_cum_inj_H2 * rho_h2_std * 39.41 / 1e9
                data.append({"Field Name": Field_name,
                            "Porosity [-]": poro,
                            "Permeability [mD]": perm,
                            "Reservoir Pressure[bar]": pressure,
                            "Reservoir Temp [K]": temperature,
                            "Density Difference [kg/m3]": delta_rho,
                            "Flow Rate [sm3/d]": Flow_rate,  
                            "Cycle Length [d]": CL,
                            "Cycle_No": cl_i,
                            "CG Ratio": CG_ratio,
                            "Predicted RF [-]": rf, 
                            "Predicted MRf [-]": mrf,
                            "Number of Wells": Number_of_wells,
                            "RGIIP [1e6 scm]": RGIIP,
                            "CG injected [m3]":  CG_cum_inj_H2,
                            "Net H2 Stored [m3]":  (cl_i + 1) * WG_cum_inj_H2 - WG_cum_prod_H2,
                            "Capital Cost [$]": Total_capital_cost,
                            "WG O&M Cost [$]": WG_OM_cost,
                            "LCOS":LCOS,
                            "Cum CG Injected [Twh]": CG_Twh,
                            "Cum H2 Injected [Twh]": (cl_i + 1) * WG_inj_TWh,
                            "Cum H2 Produced [Twh]": WG_prod_TWh,
                            })
    folder = os.path.join(input_directory, f"optim_dataset_{CL}_{CG_type}")
    os.makedirs(folder, exist_ok=True)
    data = pd.DataFrame(data)
    for k in range(10): 
        kk = data[data["Cycle_No"] == k]
        kk.to_csv(os.path.join(folder, f"cycle_{k}.csv"), index=False)
    
def main(input_directory):
    rf_values = []
    labels = []
    inputs = []
    df_list = []
    # file_path = os.path.join(input_directory, 'mixing_results_withCG.xlsx')
    file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
    df = pd.read_excel(file_path)
    
    # valid = []
    # for i in range(len(df)):
    #     if df['RF_final'].iloc[i] == 0:
    #         valid.append(0)
    #     else:
    #         valid.append(1)
    # # df = df.dropna()  # Drop rows with NaN values
    # df = df.rename(columns = {
    #     'FlowRate': 'Flow Rate',
    #     'CycleLength': 'Cycle Length',
    #     'RF_final': 'RF',
    #     'delta_rho': 'Density',
    #     })
    # df['valid'] = valid
    # df = df.drop(columns=['label','CushionGas','theta','CG Ratio','Nusselt_number','Raileigh_number', 'Pe', 'Ng','RF'])
    # X = df[["Flow Rate", "Permeability", "Pressure", "Density"]].values
    # y = df["valid"].values
    # # clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=10)
    # clf = RandomForestClassifier( n_estimators=150, max_depth=12, min_samples_leaf=5, class_weight="balanced", random_state=42)
    # clf.fit(X, y)
    # from joblib import dump, load
    # dump(clf, "rf_validity.joblib")
    clf = load("rf_validity.joblib")
    
    # Path to your consolidated CSV
    csv_path = r"Y:\Mixing Results\July\consolidated_output - Final.csv"

    # Read the CSV file
    df = pd.read_csv(csv_path, encoding='cp1252', thousands=",")

    # Select and convert the necessary columns to numeric
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
    check = ["Number of Wells"]
    df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors='coerce')
 
    df_clean = df.dropna(subset=check).reset_index(drop=True)
    df_clean['Reservoir Pressure[MPa]'] = df_clean['Reservoir Pressure[MPa]'] * 10
    df_clean['Reservoir Temp [C]'] = df_clean['Reservoir Temp [C]'] + 273.15  # Convert to Kelvin
    df_clean = df_clean.rename(columns={"Reservoir Pressure[MPa]": "Pressure","Reservoir Temp [C]": "Temperature","Porosity [-]": "Porosity","Permeability [mD]": "Permeability"})
    df["RGIIP"] = df["RGIIP"].replace({",": ""}, regex=True).astype(float)
    H2_cap = H2_capacity(df_clean)
    df_clean['H2 Capacity [m3]'] = H2_cap
    

    activation = ["tanh", "relu", "sigmoid"]
    model = build_model(input_dim=9, hidden_sizes=[36,92,108], activations=activation)
    model.load_state_dict(torch.load("ann_model_withoutCG_AC.pt"))
    model.eval()
    scalers = joblib.load("scalers_withoutCG_AC.pkl")

    # activation = ["relu", "tanh"]
    # model = build_model(input_dim=8, hidden_sizes=[22, 8], activations=activation)
    # model.load_state_dict(torch.load("ann_model_withoutCG.pt"))
    # model.eval()
    # scalers = joblib.load("scalers_withoutCG.pkl")
    H2_cost = 4.0 # $/kg
    H2_cost = H2_cost * 0.08988 # $/m3
    Number_of_cycles = 20
    CG_type = 'H2'
    results =[]
    Cycle_length = 360
    data = optim_data(df_clean, Cycle_length, scalers, model, clf, CG_type)
    
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory) 