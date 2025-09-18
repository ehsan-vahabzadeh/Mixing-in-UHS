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

def build_objective(permeability, porosity, pressure, temperature, delta_rho, model, scalers, clf, lb, ub, lambdaa):
    def objective(x):
        scaler = scalers["X_scaler"]
        y_scaler = scalers["y_scaler"]
        
        if len(x) == 3:
            flow, cl, cg_ratio = x
            normalized_CG = (cg_ratio - lb[2]) / (ub[2] - lb[2])
            full_input = np.array([[flow, cl, permeability, pressure, delta_rho, porosity, temperature, cg_ratio]])
        else:
            normalized_CG = 0.0
            flow, cl = x
            full_input = np.array([[flow, cl, permeability, pressure, delta_rho, porosity, temperature, 0.0]])
        scaled = scaler.transform(full_input)
        input_tensor = torch.tensor(scaled, dtype=torch.float32)
        X = np.array([[flow, permeability, pressure, delta_rho]])
        if permeability < 8:
            pred = clf.predict(X)
            if pred == 0:
                # print(f"Not feasible input:'{flow}' - '{cl}'- '{permeability}'- '{pressure}'- '{delta_rho}'.")
                return 1e12
        with torch.no_grad():
            rf = model(input_tensor).item()
            if rf > 1:
                print("Warning: RF exceeds 1.0, capping to 1.0")
                rf = 1.0  # Cap RF at 1.0
            # rf_original = y_scaler.inverse_transform([[rf]]).ravel()[0]
        return (1 - lambdaa) * -rf + lambdaa * (normalized_CG)
    return objective

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
    df = pd.read_csv(csv_path, encoding='cp1252')

    # Select and convert the necessary columns to numeric
    columns = [
        "Field Name",
        "Porosity [-]",
        "Permeability [mD]",
        "Reservoir Pressure[MPa]",
        "Reservoir Temp [C]",
    ]
    df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors='coerce')
 
    df_clean = df.dropna(subset=columns).reset_index(drop=True)
    df_clean['Reservoir Pressure[MPa]'] = df_clean['Reservoir Pressure[MPa]'] * 10
    df_clean['Reservoir Temp [C]'] = df_clean['Reservoir Temp [C]'] + 273.15  # Convert to Kelvin
    df_clean = df_clean.rename(columns={"Reservoir Pressure[MPa]": "Pressure","Reservoir Temp [C]": "Temperature","Porosity [-]": "Porosity","Permeability [mD]": "Permeability"})
    
    # activation = ["tanh", "sigmoid"]
    # model = build_model(input_dim=8, hidden_sizes=[15, 30], activations=activation)
    # model.load_state_dict(torch.load("ann_model_withCG.pt"))
    # model.eval()
    # scalers = joblib.load("scalers_withCG.pkl")

    activation = ["relu", "tanh"]
    model = build_model(input_dim=8, hidden_sizes=[22, 8], activations=activation)
    model.load_state_dict(torch.load("ann_model_withoutCG.pt"))
    model.eval()
    scalers = joblib.load("scalers_withoutCG.pkl")

    CG_types = [ 'H2','CO2', 'CH4', 'N2']
    results =[]
    for ii in range(len(df_clean)):
        for cg_type in CG_types:
            H2_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii], "Hydrogen")
            CG_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii] , cg_type)
            X_const = np.array([df_clean['Permeability'].iloc[ii], df_clean['Porosity'].iloc[ii], df_clean['Pressure'].iloc[ii], df_clean['Temperature'].iloc[ii], CG_density - H2_density])
            if cg_type != 'H2':
                lb = [1e5, 14]  
                ub = [1.5e6, 360]
            else:
                lb = [1e5, 14, 0.0]  
                ub = [1.5e6, 360, 5.0] 
            lambdaa = 0.1
            objective = build_objective(X_const[0], X_const[1], X_const[2], X_const[3], X_const[4], model, scalers,clf, lb, ub, lambdaa)
            xopt, fopt = pso(objective, lb, ub, swarmsize=300, maxiter=500, omega=0.7, phip=1.5, phig=1.5, minstep=1e-6, minfunc=1e-6)
            if df_clean['Field Name'].iloc[ii] == "Trent gas field":
                AAA = 1
            if cg_type == 'H2':
                normalized_CG = (xopt[2] - lb[2]) / (ub[2] - lb[2])
            RF = -(fopt - lambdaa * normalized_CG)/ (1 - lambdaa)
            results.append({
            "Field Name": df_clean['Field Name'].iloc[ii],
            "Porosity [-]": X_const[1],
            "Permeability [mD]": X_const[0],
            "Reservoir Pressure[bar]": X_const[2],
            "Reservoir Temp [K]": X_const[3],
            "Cushion Gas": cg_type,
            "Density Difference [kg/m3]": CG_density - H2_density,
            "Optimized Flow Rate [sm3/d]": xopt[0],
            "Optimized Cycle Length [d]": xopt[1],
            "Optimized CG Ratio": (xopt[2] if len(xopt) == 3 else 0),
            "Max Predicted RF [-]": -(fopt - lambdaa * normalized_CG)/ (1 - lambdaa) 
            })
            print(f"Final result:'{xopt[0]}' - '{xopt[1]}'- '{RF}'- '{X_const[0]}'- '{CG_density - H2_density}'.")
            
    df_results = pd.DataFrame(results)
    df_results.to_csv(os.path.join(input_directory, 'optimized_results_without_CG_1.csv'), index=False)
if __name__ != "__main__":
    import sys
    sys.exit()
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory) 