import numpy as np
import pandas as pd
from pyDOE2 import lhs
import torch
import joblib
import torch
import torch.nn as nn
import os
import matplotlib.pyplot as plt

def build_model(input_dim, hidden_sizes, activation_fn):
    layers = []
    current_dim = input_dim
    for h in hidden_sizes:
        layers.append(nn.Linear(current_dim, h))
        if activation_fn == 'relu':
            layers.append(nn.ReLU())
        elif activation_fn == 'tanh':
            layers.append(nn.Tanh())
        current_dim = h
    layers.append(nn.Linear(current_dim, 1))
    return nn.Sequential(*layers)
os.chdir("Y:\\Mixing Results\\New May")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
# --- Load trained model and scaler ---
model = build_model(input_dim=5, hidden_sizes=[57, 28], activation_fn="relu")
model.load_state_dict(torch.load("optimized_model.pt"))
model.eval()
scaler = joblib.load("input_scaler.pkl")

# --- 1. Define Input Ranges ---
input_ranges = {
    'FlowRate': (1e5, 1.5e6),
    'CycleLength': (14, 180),
    'Pressure': (60, 400),         # in bar or MPa based on your model
    'Permeability': (10, 1000),   # in mD
    'DensityDiff': (0, 600)       # kg/m³, adjust based on physical limits
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


plt.figure(figsize=(8, 6))
plt.hexbin(df_results["FlowRate"],  df_results["RF"], gridsize=50, cmap='viridis')
plt.colorbar(label='Point Density')
plt.xlabel("Flow Rate")
plt.ylabel("Predicted RF")
plt.title("Flow Rate vs Predicted RF (200k samples)")
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 6))
plt.hexbin(df_results["CycleLength"], df_results["RF"], gridsize=50, cmap='viridis')
plt.colorbar(label='Point Density')
plt.xlabel("CycleLength")
plt.ylabel("Predicted RF")
plt.title("CycleLength vs Predicted RF (200k samples)")
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 6))
plt.hexbin(df_results["DensityDiff"], df_results["RF"], gridsize=50, cmap='viridis')
plt.colorbar(label='Point Density')
plt.xlabel("DensityDiff")
plt.ylabel("Predicted RF")
plt.title("DensityDiff vs Predicted RF (200k samples)")
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 6))
plt.hexbin(df_results["Pressure"], df_results["RF"], gridsize=50, cmap='viridis')
plt.colorbar(label='Point Density')
plt.xlabel("Pressure")
plt.ylabel("Predicted RF")
plt.title("Pressure vs Predicted RF (200k samples)")
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 6))
plt.hexbin(df_results["Permeability"], df_results["RF"], gridsize=50, cmap='viridis')
plt.colorbar(label='Point Density')
plt.xlabel("Permeability")
plt.ylabel("Predicted RF")
plt.title("Permeability vs Predicted RF (200k samples)")
plt.tight_layout()
plt.show()
# --- 7. Save or Use Results ---
df_results.to_csv("RF_predictions_from_LHS.csv", index=False)
print("✅ RF predictions saved to 'RF_predictions_from_LHS.csv'")
