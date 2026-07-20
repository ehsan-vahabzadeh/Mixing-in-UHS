import os
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from pyDOE2 import lhs
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from CoolProp.CoolProp import PropsSI
from sklearn.ensemble import RandomForestClassifier
import torch
import joblib
from joblib import dump, load
import torch.nn as nn
np.random.seed(4585032)
font = {'family' : 'sans-serif',
        'size'   : 18}
plt.rc('font', **font)


def Diffusion(pressure, GasType):
    if GasType == 'H2':
        Diffusion = 3.4831e-07
        # if pressure == 300:
        #     Diffusion = 1.3072e-7
        # if pressure == 150:
        #     Diffusion = 2.6160e-7
        # if pressure == 60:
        #     Diffusion = 6.526e-7    
    if GasType == 'CH4':
        Diffusion = 1.5324e-07
        # if pressure == 300:
        #     Diffusion = 5.7788e-8
        # if pressure == 150:
        #     Diffusion = 1.1362e-7
        # if pressure == 60:
        #     Diffusion = 2.8831e-7   
    if GasType == 'CO2':
        Diffusion = 1.4056e-07
        # if pressure == 300:
        #     Diffusion = 5.24e-8
        # if pressure == 150:
        #     Diffusion = 1.0478e-7
        # if pressure == 60:
        #     Diffusion = 2.6451e-7   
    if GasType == 'N2':
        Diffusion = 1.6933e-07
        # if pressure == 300:
        #     Diffusion = 6.3615e-8
        # if pressure == 150:
        #     Diffusion = 1.2638e-7
        # if pressure == 60:
        #     Diffusion = 3.18e-7 
    return Diffusion 
def isothermal_cf(P, T, gas, dP=1e5):
    """
    c_f = (1/rho)*(drho/dP)_T. Returns (c_f [1/Pa], rho [kg/m3], Z, method).
    """
    R = 8.31446261815324  # J/(mol*K)

    GASES = {
        "CO2": {"M": 44.0095e-3,  "Tc": 304.13,  "Pc": 7.3773e6, "omega": 0.225},
        "H2":  {"M": 2.01588e-3,  "Tc": 33.19,   "Pc": 1.293e6, "omega": -0.216},
        "N2":  {"M": 28.0134e-3,  "Tc": 126.2,   "Pc": 3.3958e6, "omega": 0.0372},
        "CH4": {"M": 16.04246e-3, "Tc": 190.56,  "Pc": 4.599e6, "omega": 0.011},
}
    g = GASES[gas]
    rho  = PropsSI('D', 'P', P,  'T', T, gas)
    Pm, Pp = max(P-dP, 100.0), P + dP
    rho_m  = PropsSI('D', 'P', Pm, 'T', T, gas)
    rho_p  = PropsSI('D', 'P', Pp, 'T', T, gas)
    drhodP = (rho_p - rho_m) / (Pp - Pm)
    Z = P * g["M"] / (rho * R * T)
    return (drhodP / rho), rho, Z, "CoolProp"
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

def RF_calc(full_input):
    
    # file_path = os.path.join(input_directory, 'mixing_results_plot.xlsx')
    # df = pd.read_excel(file_path)
    
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
    # dump(clf, "rf_validity_plot.joblib")
    clf = load("rf_validity_plot.joblib")

    activation = ["relu", "tanh","relu"]
    model = build_model(input_dim=7, hidden_sizes=[23, 32, 12], activations=activation)
    model.load_state_dict(torch.load("ann_model_plot.pt"))
    model.eval()
    scalers = joblib.load("scalers_plot.pkl")
    scaler = scalers["X_scaler"]
    scaled = scaler.transform(full_input)
    input_tensor = torch.tensor(scaled, dtype=torch.float32)
    if full_input[0][2] <= 10:
        pred = clf.predict(np.array([[full_input[0][0], full_input[0][2], full_input[0][3], full_input[0][4]]]))
        if pred == 0:
            print(f"Not feasible input:'{full_input[0][0]}' - '{full_input[0][1]}'- '{full_input[0][2]}'- '{full_input[0][3]}'- '{full_input[0][4]}'.")
            rf = 0.0
            return rf
    with torch.no_grad():
        rf = model(input_tensor).item()
        return rf
def delta_rho(P, T, gas):


    GASES = {
        "CO2": {"M": 44.0095e-3,  "Tc": 304.13,  "Pc": 7.3773e6, "omega": 0.225},
        "H2":  {"M": 2.01588e-3,  "Tc": 33.19,   "Pc": 1.293e6, "omega": -0.216},
        "N2":  {"M": 28.0134e-3,  "Tc": 126.2,   "Pc": 3.3958e6, "omega": 0.0372},
        "CH4": {"M": 16.04246e-3, "Tc": 190.56,  "Pc": 4.599e6, "omega": 0.011},
}
    g = GASES[gas]
    rho  = PropsSI('D', 'P', P,  'T', T, gas)
    rho_H2  = PropsSI('D', 'P', P, 'T', T, "H2")

    return rho - rho_H2


def input_gen():
    # === 1. Load Data ===
    csv_path = r"Y:\Mixing Results\July\consolidated_output - Final.csv"
    df = pd.read_csv(csv_path, encoding='cp1252')

    # === 2. Select and Convert Required Columns ===
    columns_needed = ["Permeability [mD]", "Reservoir Pressure[MPa]", "Reservoir Temp [C]", "Porosity [-]"]
    df[columns_needed] = df[columns_needed].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=columns_needed).reset_index(drop=True)

    # === 3. KMeans Clustering on Perm–Pressure ===
    n_clusters = 3
    X = df[columns_needed].values
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df["Cluster"] = kmeans.fit_predict(X)

    bins = [-np.inf, 10, 100, np.inf]         # cover all values
    labels = ["<10 mD", "10–100 mD", ">100 mD"]

    df["Cluster"] = pd.cut(df["Permeability [mD]"], bins=bins, labels=labels, right=False)

    print(df["Permeability [mD]"].describe())      # sanity check
    print(df["Cluster"].value_counts(dropna=False)) # see counts
    # === 4. LHS Sampling for Flow Rate and Cycle Length ===
    flow_min, flow_max = 1e5, 1.5e6
    cycle_min, cycle_max = 14, 360
    CG_min, CG_max = 0.0 , 5.0  # Example values for CG
    samples_per_cluster = 50

    sampled_data = []
    cluster_weights = {}

        
    for cluster_id in labels:
        cluster_data = df[df["Cluster"] == cluster_id]
        
        # Sample (with replacement if needed)
        # perm_pressure_samples = cluster_data.sample(
        #     n=samples_per_cluster, replace=True, random_state=cluster_id
        # )[columns_needed].reset_index(drop=True)
        
        lhs_samples = lhs(3, samples=samples_per_cluster)
        
        perm_min = cluster_data["Permeability [mD]"].min()
        perm_max = cluster_data["Permeability [mD]"].max()
        
        if (cluster_id == 2):
            perm_max = 1000
        pressure_min = cluster_data["Reservoir Pressure[MPa]"].min()
        pressure_max = cluster_data["Reservoir Pressure[MPa]"].max()
        porosity_min = cluster_data["Porosity [-]"].min()
        porosity_max = cluster_data["Porosity [-]"].max()
        perm_samples = lhs_samples[:, 0] * (perm_max - perm_min) + perm_min
        pressure_samples = lhs_samples[:, 1] * (pressure_max - pressure_min) + pressure_min
        porosity_samples = lhs_samples[:, 2] * (porosity_max - porosity_min) + porosity_min
        pressure_real = cluster_data["Reservoir Pressure[MPa]"].values.reshape(-1, 1)
        temp_real = cluster_data["Reservoir Temp [C]"].values
        reg = LinearRegression().fit(pressure_real, temp_real)
        temp_pred = reg.predict(pressure_samples.reshape(-1, 1))
        residual_std = np.std(temp_real - reg.predict(pressure_real))
        temp_samples = temp_pred + np.random.normal(0, residual_std, size=temp_pred.shape)  
        perm_pressure_samples = pd.DataFrame({
            "Permeability [mD]": perm_samples,
            "Reservoir Pressure[MPa]": pressure_samples,
            "Reservoir Temp [C]": temp_samples,
            "Porosity [-]": porosity_samples
        })

        # LHS sampling
        lhs_samples = lhs(2, samples=samples_per_cluster)
        flow_rates = lhs_samples[:, 0] * (flow_max - flow_min) + flow_min
        cycle_lengths = np.round(lhs_samples[:, 1] * (cycle_max - cycle_min) + cycle_min)
        # CG_values = lhs_samples[:, 2] * (CG_max - CG_min) + CG_min
        CG_values = lhs_samples[:, 1] * 0
        # Combine with sampled perm–pressure
        perm_pressure_samples["Flow Rate [m³/d]"] = flow_rates
        perm_pressure_samples["Cycle Length [days]"] = cycle_lengths
        perm_pressure_samples["CG"] = CG_values
        perm_pressure_samples["Cluster"] = cluster_id
        sampled_data.append(perm_pressure_samples)

    # === 5. Combine All and Save ===
    final_samples = pd.concat(sampled_data, ignore_index=True)
    return final_samples

input_directory = r"Y:\Mixing Results\July"
os.chdir(input_directory) 
final_samples = input_gen()
Gases = ["CO2", "CH4", "N2", "H2"]
RF_values = []
Pe_values = []
Ng_values = []
Fu_values = []
theta_values = []
for ii in range(len(final_samples)):
    for gas in Gases:
        delta_rho_val = delta_rho(final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15, gas)
        X_const = np.array([final_samples['Permeability [mD]'].iloc[ii], final_samples['Porosity [-]'].iloc[ii], final_samples['Reservoir Pressure[MPa]'].iloc[ii]*10, final_samples['Reservoir Temp [C]'].iloc[ii] +273.15, delta_rho_val])
        full_input = np.array([[final_samples["Flow Rate [m³/d]"].iloc[ii], final_samples["Cycle Length [days]"].iloc[ii], X_const[0], X_const[2], X_const[4], X_const[1], X_const[3]]])
        RF = RF_calc(full_input)
        if RF == 0:
            continue
        diffusion = Diffusion(final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, gas)
        # Peclet_number = (pore_velocity * Length) / (diffusion)
        q_c = final_samples["Flow Rate [m³/d]"].iloc[ii] / 86400 / (2 * np.pi * 0.2 * 10 ** 2)
        Height = 60
        Length = 1000
        pore_velocity = q_c /final_samples['Porosity [-]'].iloc[ii]
        Peclet_number = ( pore_velocity * Length) / (diffusion)
        Fourier_number = ( pore_velocity * final_samples["Cycle Length [days]"].iloc[ii] * 86400 / 2) / (Length)
        CF_H2 = isothermal_cf(final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15, "H2")[0]
        CF_CG = isothermal_cf(final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15, gas)[0]
        H2_density = PropsSI("D", "P", final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e5, "T", final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15, "Hydrogen")
        CG_density = PropsSI("D", "P", final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e5, "T", final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15 , gas)
        H2_viscosity = PropsSI("V", "P", final_samples["Reservoir Pressure[MPa]"].iloc[ii] * 1e5, "T", final_samples["Reservoir Temp [C]"].iloc[ii] + 273.15, "Hydrogen")
        theta = ((H2_density) / (CG_density)) * (CF_H2 / CF_CG)
        perm = final_samples['Permeability [mD]'].iloc[ii] * 9.869233e-16
        Buoyancy_number = ((perm/10) * (CG_density - H2_density) * 9.81 * Length) / (H2_viscosity * pore_velocity * Height * final_samples['Porosity [-]'].iloc[ii])
        
        RF_values.append(RF)
        Pe_values.append(Peclet_number)
        Ng_values.append(Buoyancy_number)
        Fu_values.append(Fourier_number)
        theta_values.append(theta)    


theta_values = np.array(theta_values)
Fo_values = np.array(Fu_values)
RF_values = np.array(RF_values)
Pe_values = np.array(Pe_values) * theta_values
Ng_values = np.array(Ng_values) 



################################################################################  Pe vs Ng


Pe = np.log10(Pe_values)
# Ng = np.log10(Ng_values)
# Pe = Pe_values
Ng = Ng_values

x, y, z = Pe, Ng, RF_values
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay
# Build a regular grid
xi = np.linspace(min(x), max(x), 100)
yi = np.linspace(min(y), max(y), 100)
Xi, Yi = np.meshgrid(xi, yi)
z = np.clip(RF_values, 0, 1)  # ensure physical range if needed
tri = Delaunay(np.column_stack([x, y]))
lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
Zi = lin(Xi, Yi)
mask = np.isnan(Zi)
Zi_smooth = Zi.copy()
Zi_smooth[~mask] = gaussian_filter(Zi[~mask], sigma=4)


fig, ax = plt.subplots(1, 3, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)

# 1) Filled contour
levels = 5
colors = plt.cm.get_cmap('Greys',levels)
plot = ax[0].contourf(
    Xi,
    Yi,
    Zi_smooth,
    cmap='plasma',
    # levels=levels,
)

# plot = ax[0].scatter(
#     Pe,
#     Ng,
#     c=RF_values,
#     cmap='plasma',
#     edgecolor='k'
# )
# cbar = plt.colorbar(contour, ax=ax[0], pad = 0.3)
# cbar.set_label("RF", fontsize=12)
# ax[0].set_xlabel(r"$\theta \, Pe$ [-]", fontsize=18)
# ax[0].set_xscale('log')
# ax[0].set_yscale('log')
ax[0].set_xlabel(r"Pe [-]", fontsize=18)
ax[0].set_ylabel("Ng [-]", fontsize=18)
ax[0].tick_params(axis='x', labelsize=18)
ax[0].tick_params(axis='y', labelsize=18)
ax[0].legend(loc='best', frameon=True, fontsize=12)


# scatter = ax[1].scatter(
#     Pe,
#     Ng,
#     c=RF_values,
#     cmap='plasma',
#     edgecolor='k'
# )
scatter = ax[1].scatter(
    Pe,
    RF_values,
    c=RF_values,
    cmap='plasma',
    edgecolor='k'
)
ax[1].set_xlabel(r"Pe [-]", fontsize=18)
ax[1].set_ylabel("RF [-]", fontsize=18)
ax[1].tick_params(axis='x', labelsize=18)
ax[1].tick_params(axis='y', labelsize=18)
ax[1].legend(loc='best', frameon=True, fontsize=12)
scatter = ax[2].scatter(
    Ng,
    RF_values,
    c=RF_values,
    cmap='plasma',
    edgecolor='k'
)

ax[2].set_xlabel("Ng [-]", fontsize=18)
ax[2].set_ylabel("RF [-]", fontsize=18)
ax[2].tick_params(axis='x', labelsize=18)
ax[2].tick_params(axis='y', labelsize=18)
ax[2].legend(loc='best', frameon=True, fontsize=12)
cbar = plt.colorbar(scatter, ax=ax[2])
cbar.ax.tick_params(labelsize=18)
cbar.set_label("Recovery Factor [-]", fontsize=18)
plt.tight_layout()
plt.show()
