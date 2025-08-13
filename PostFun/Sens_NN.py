import numpy as np
import pandas as pd
from pyDOE2 import lhs
import torch
import joblib
import torch
import torch.nn as nn
import os
import matplotlib.pyplot as plt

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
activation = ["relu", "tanh"]
model = build_model(input_dim=8, hidden_sizes=[32, 22], activations=activation)
model.load_state_dict(torch.load("trained_ann_model.pt"))
model.eval()
scalers = joblib.load("scalers.pkl")
scaler = scalers["X_scaler"]
y_scaler = scalers["y_scaler"]
# --- 1. Define Input Ranges ---
input_ranges = {
    'FlowRate': (1e5, 1.5e6),
    'CycleLength': (14, 180),
    'Pressure': (76, 447),         # in bar or MPa based on your model
    'Permeability': (3, 1497),   # in mD
    'DensityDiff': (0, 846),       # kg/m³, adjust based on physical limits
    'Porosity': (0.06, 0.28),      # dimensionless
    'Temperature': (282.15, 412),  # Kelvin, adjust based on physical limits
    'CushionGasRatio': (1, 5)      # dimensionless, adjust based on physical limits
}

# --- 2. Generate LHS Samples ---
n_samples = 200000
n_features = len(input_ranges)
lhs_samples = lhs(n_features, samples=n_samples)

# --- 3. Scale to Real Input Ranges ---
X_raw = np.zeros((n_samples, n_features))
for i, (key, (low, high)) in enumerate(input_ranges.items()):
    X_raw[:, i] = lhs_samples[:, i] * (high - low) + low

# --- 4. Normalize Inputs with Trained Scaler ---
X_scaled = scaler.transform(X_raw)
X_tensor = torch.tensor(X_scaled, dtype=torch.float32)

# --- 5. Predict with Neural Network ---
with torch.no_grad():
    rf_preds = model(X_tensor).numpy().flatten()
    # rf_preds = y_scaler.inverse_transform([[rf_preds]]).ravel()[0]

# --- 6. Combine Inputs + Outputs into a DataFrame ---
df_results = pd.DataFrame(X_raw, columns=list(input_ranges.keys()))
df_results["RF"] = rf_preds



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
