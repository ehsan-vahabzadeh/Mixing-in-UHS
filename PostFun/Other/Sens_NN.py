import numpy as np
import pandas as pd
from pyDOE2 import lhs
import torch
import joblib
import torch
import torch.nn as nn
import os
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import joblib
from joblib import dump, load
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
    layers.append(nn.Linear(in_dim, 1))  # Output layer
    layers.append(nn.Sigmoid())   # <- bound to (0,1)
    return nn.Sequential(*layers)
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
# --- Load trained model and scaler ---
# activation = ["sigmoid", "sigmoid"]
# model = build_model(input_dim=8, hidden_sizes=[22, 21], activations=activation)
# model.load_state_dict(torch.load("ann_model_withCG.pt"))
# model.eval()
# scalers = joblib.load("scalers_withCG.pkl")

activation = ["relu", "tanh"]
model = build_model(input_dim=8, hidden_sizes=[22, 8], activations=activation)
model.load_state_dict(torch.load("ann_model_withoutCG.pt"))
model.eval()
scalers = joblib.load("scalers_withoutCG.pkl")

# activation = ["relu", "relu"]
# model = build_model(input_dim=8, hidden_sizes=[14, 11], activations=activation)
# model.load_state_dict(torch.load("ann_model_gurobi.pt"))
# model.eval()
# scalers = joblib.load("scalers_gurobi.pkl")

scaler = scalers["X_scaler"]
y_scaler = scalers["y_scaler"]
# Path to your consolidated CSV
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"

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

file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
# file_path = os.path.join(input_directory, 'mixing_results_withCG.xlsx')
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
# df = df.drop(columns=['label','CushionGas','theta','CG Ratio','Nusselt_number','Raileigh_number', 'Pe', 'Ng','RF', 'porosity', 'Temperature'])
# X = df[["Flow Rate", "Permeability", "Pressure", "Density"]].values
# y = df["valid"].values
# # clf = DecisionTreeClassifier(max_depth=10, min_samples_leaf=10, class_weight="balanced")
# clf = RandomForestClassifier( n_estimators=150, max_depth=20, min_samples_leaf=5, class_weight="balanced", random_state=42)
# # clf = RandomForestClassifier( n_estimators=150, max_depth=12, min_samples_leaf=10, class_weight="balanced", random_state=42)
# clf.fit(X, y)
# from joblib import dump, load
# dump(clf, "rf_validity.joblib")
clf = load("rf_validity.joblib")
CG_types = ['H2', 'CO2', 'CH4', 'N2']
# CG_types = ['H2']
results =[]
flow = 1.5e6
cl = 360
for ii in range(len(df_clean)):
    for cg_type in CG_types:
        H2_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii], "Hydrogen")
        CG_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii] , cg_type)
        X_const = np.array([df_clean['Permeability'].iloc[ii], df_clean['Porosity'].iloc[ii], df_clean['Pressure'].iloc[ii], df_clean['Temperature'].iloc[ii], CG_density - H2_density])
        if cg_type != 'H2':
            CG_ratio = 0.0
        else:
            CG_ratio = 5.0
        full_input = np.array([[flow, cl, X_const[0], X_const[2], X_const[4], X_const[1], X_const[3], CG_ratio]])
        scaled = scaler.transform(full_input)
        input_tensor = torch.tensor(scaled, dtype=torch.float32)
        pred = clf.predict(np.array([[flow, X_const[0], X_const[2], X_const[4]]]))
        with torch.no_grad():
            rf = model(input_tensor).item()
        if pred == 0:
            print(f"Not feasible input:'{flow}' - '{cl}'- '{X_const[0]}'- '{X_const[2]}'- '{X_const[4]}'.")
            rf = 0.0
        results.append({
        "Field Name": df_clean['Field Name'].iloc[ii],
        "Porosity [-]": X_const[1],
        "Permeability [mD]": X_const[0],
        "Reservoir Pressure[bar]": X_const[2],
        "Reservoir Temp [K]": X_const[3],
        "Cushion Gas": cg_type,
        "Density Difference [kg/m3]": CG_density - H2_density,
        "Optimized Flow Rate [sm3/d]": flow,
        "Optimized Cycle Length [d]": cl,
        "Optimized CG Ratio": (CG_ratio),
        "Max Predicted RF [-]": rf
        })
df_results = pd.DataFrame(results)
df_results.to_csv(os.path.join(input_directory, 'sens_results.csv'), index=False)


# labels = []
# df_results = []
# file_path = os.path.join(input_directory, 'mixing_results.xlsx')
# df = pd.read_excel(file_path)
# ordered_data = []
# for i in range(len(df)):
#     row = []
#     for label in df:
#         row.append(df[label].iloc[i])
#     ordered_data.append(row)
# for data in ordered_data:
#     df_results.append({
#         "label": data[0],
#         "FlowRate": data[1],
#         "CycleLength":data[2],
#         "Permeability": data[3],
#         "Pressure": data[4],
#         "DensityDiff": data[10],
#         "RF": data[7]
#     })
# df_results = pd.DataFrame(df_results)

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["FlowRate"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("Flow Rate", fontsize=14)
ax[0].set_ylabel("Predicted RF", fontsize=14)
ax[1].scatter(
    df_results["FlowRate"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("Flow Rate", fontsize=14)
ax[1].set_ylabel("Predicted RF", fontsize=14)
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["CycleLength"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("CycleLength")
ax[0].set_ylabel("Predicted RF")
ax[1].scatter(
    df_results["CycleLength"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("CycleLength")
ax[1].set_ylabel("Predicted RF")
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["Pressure"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("Pressure")
ax[0].set_ylabel("Predicted RF")
ax[1].scatter(
    df_results["Pressure"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("Pressure")
ax[1].set_ylabel("Predicted RF")
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["Permeability"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("Permeability")
ax[0].set_ylabel("Predicted RF")
ax[1].scatter(
    df_results["Permeability"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("Permeability")
ax[1].set_ylabel("Predicted RF")
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["DensityDiff"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("DensityDiff")
ax[0].set_ylabel("Predicted RF")
ax[1].scatter(
    df_results["DensityDiff"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("DensityDiff")
ax[1].set_ylabel("Predicted RF")
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
ax[0].hexbin(df_results["Porosity"],  df_results["RF"], gridsize=50, cmap='viridis')
ax[0].set_xlabel("Porosity")
ax[0].set_ylabel("Predicted RF")
ax[1].scatter(
    df_results["Porosity"],
    df_results["RF"],
    edgecolor='k'
)
ax[1].set_xlabel("Porosity")
ax[1].set_ylabel("Predicted RF")
plt.tight_layout()
plt.show()
# --- 7. Save or Use Results ---
df_results.to_csv("RF_predictions_from_LHS.csv", index=False)
print("✅ RF predictions saved to 'RF_predictions_from_LHS.csv'")
