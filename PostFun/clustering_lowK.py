import os
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from pyDOE2 import lhs
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
np.random.seed(4585032)
font = {'family' : 'sans-serif',
        'size'   : 18}
plt.rc('font', **font)

# === 1. Load Data ===
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"
df = pd.read_csv(csv_path, encoding='cp1252')

# === 2. Select and Convert Required Columns ===
columns_needed = ["Permeability [mD]", "Reservoir Pressure[MPa]", "Reservoir Temp [C]", "Porosity [-]"]
df[columns_needed] = df[columns_needed].apply(pd.to_numeric, errors='coerce')
df = df.dropna(subset=columns_needed).reset_index(drop=True)

# === 3. KMeans Clustering on Perm–Pressure ===
n_clusters = 3
X = df[columns_needed].values


# Select low-perm subset
low_perm = df[df["Permeability [mD]"] <= 10].reset_index(drop=True)
print("Low-perm count:", len(low_perm))

# LHS in the low-perm bounds
from pyDOE2 import lhs
from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd

samples_per_cluster = 80  # set how many you want
lhs_xyz = lhs(3, samples=samples_per_cluster)

perm_min, perm_max = low_perm["Permeability [mD]"].min(), low_perm["Permeability [mD]"].max()
p_min, p_max       = low_perm["Reservoir Pressure[MPa]"].min(), low_perm["Reservoir Pressure[MPa]"].max()
phi_min, phi_max   = low_perm["Porosity [-]"].min(),             low_perm["Porosity [-]"].max()

perm_samples     = lhs_xyz[:,0]*(perm_max-perm_min) + perm_min
pressure_samples = lhs_xyz[:,1]*(p_max-p_min) + p_min
phi_samples      = lhs_xyz[:,2]*(phi_max-phi_min) + phi_min

# Temp correlated with pressure
reg = LinearRegression().fit(low_perm["Reservoir Pressure[MPa]"].values.reshape(-1,1),
                             low_perm["Reservoir Temp [C]"].values)
temp_pred = reg.predict(pressure_samples.reshape(-1,1))
resid = low_perm["Reservoir Temp [C]"].values - reg.predict(low_perm["Reservoir Pressure[MPa]"].values.reshape(-1,1))
temp_samples = temp_pred + np.random.normal(0, np.std(resid), size=temp_pred.shape)

# Flow & cycle LHS
flow_min, flow_max = 1e5, 1.5e6
cycle_min, cycle_max = 0, 360
CG_max, CG_min = 5.0, 0.0
lhs_fc = lhs(2, samples=samples_per_cluster)
flow_rates = lhs_fc[:,0]*(flow_max-flow_min) + flow_min
cycle_lengths = np.round(lhs_fc[:,1]*(cycle_max-cycle_min) + cycle_min)
# CG_values = lhs_fc[:, 2] * (CG_max - CG_min) + CG_min
CG_values = 0.0  # or array of zeros if needed

out = pd.DataFrame({
    "Permeability [mD]": perm_samples,
    "Reservoir Pressure[MPa]": pressure_samples,
    "Reservoir Temp [C]": temp_samples,
    "Porosity [-]": phi_samples,
    "Flow Rate [m³/d]": flow_rates,
    "Cycle Length [days]": cycle_lengths,
    "CG": CG_values,
    "Cluster": "<10 mD"
})

out.to_csv(r"Y:\Mixing Results\Field Data\sampled_doe_hybrid.csv", index=False)
print("Saved:", len(out))