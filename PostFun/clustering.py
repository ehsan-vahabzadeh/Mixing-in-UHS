import os
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from pyDOE2 import lhs
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
np.random.seed(445566)
font = {'family' : 'sans-serif',
        'size'   : 18}
plt.rc('font', **font)

# === 1. Load Data ===
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"
df = pd.read_csv(csv_path)

# === 2. Select and Convert Required Columns ===
columns_needed = ["Permeability [mD]", "Reservoir Pressure[MPa]", "Reservoir Temp [C]", "Porosity [-]"]
df[columns_needed] = df[columns_needed].apply(pd.to_numeric, errors='coerce')
df = df.dropna(subset=columns_needed).reset_index(drop=True)

# === 3. KMeans Clustering on Perm–Pressure ===
n_clusters = 3
X = df[columns_needed].values
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
df["Cluster"] = kmeans.fit_predict(X)

colors = ['red', 'green', 'blue']

# Plot each cluster
for cluster in range(n_clusters):
    cluster_data = df[df["Cluster"] == cluster]
    plt.scatter(
        cluster_data[columns_needed[0]],
        cluster_data[columns_needed[1]],
        color=colors[cluster],
        label=f"Cluster {cluster}",
        alpha=0.7,
        edgecolor='k'
    )

plt.xlabel(columns_needed[0])
plt.ylabel(columns_needed[1])
plt.title("KMeans Clustering")
plt.legend(["K < 200", "200 < K < 1000", "1000 < K"])
plt.grid(True)
plt.show()
# === 4. LHS Sampling for Flow Rate and Cycle Length ===
flow_min, flow_max = 1e5, 1.5e6
cycle_min, cycle_max = 14, 180
CG_min, CG_max = 0.0 , 1.0  # Example values for CG
samples_per_cluster = 33

sampled_data = []
cluster_weights = {}

    
for cluster_id in range(n_clusters):
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
    CG_values = lhs_samples[:, 1]
    # Combine with sampled perm–pressure
    perm_pressure_samples["Flow Rate [m³/d]"] = flow_rates
    perm_pressure_samples["Cycle Length [days]"] = cycle_lengths
    perm_pressure_samples["CG"] = CG_values
    perm_pressure_samples["Cluster"] = cluster_id
    sampled_data.append(perm_pressure_samples)

# === 5. Combine All and Save ===
final_samples = pd.concat(sampled_data, ignore_index=True)
output_path = r"Y:\Mixing Results\Field Data\sampled_doe_hybrid.csv"
final_samples.to_csv(output_path, index=False)

# print("✅ Sampled saved to:", output_path)


plt.figure(figsize=(16, 12))

# Plot 1: Flow rate vs Permeability
plt.subplot(3, 3, 1)
plt.scatter(
    final_samples["Permeability [mD]"],
    final_samples["Flow Rate [m³/d]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Permeability [mD]", fontsize=18)
plt.ylabel("Flow Rate [m³/d]", fontsize=18)
plt.grid(True)

# Plot 2: Flow rate vs Pressure
plt.subplot(3, 3, 2)
plt.scatter(
    final_samples["Reservoir Pressure[MPa]"],
    final_samples["Flow Rate [m³/d]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Reservoir Pressure [MPa]", fontsize=18)
plt.ylabel("Flow Rate [m³/d]", fontsize=18)
plt.grid(True)

# Plot 3: Cycle length vs Permeability
plt.subplot(3, 3, 3)
plt.scatter(
    final_samples["Permeability [mD]"],
    final_samples["Cycle Length [days]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Permeability [mD]", fontsize=18)
plt.ylabel("Cycle Length [days]", fontsize=18)
plt.grid(True)

# Plot 4: Cycle length vs Pressure
plt.subplot(3, 3, 4)
plt.scatter(
    final_samples["Reservoir Pressure[MPa]"],
    final_samples["Cycle Length [days]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Reservoir Pressure [MPa]", fontsize=18)
plt.ylabel("Cycle Length [days]", fontsize=18)
plt.grid(True)

plt.subplot(3, 3, 5)
plt.scatter(
    final_samples["Reservoir Temp [C]"],
    final_samples["Cycle Length [days]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Reservoir Temp [C]", fontsize=18)
plt.ylabel("Cycle Length [days]", fontsize=18)
plt.grid(True)

plt.subplot(3, 3, 6)
plt.scatter(
    final_samples["Reservoir Temp [C]"],
    final_samples["Flow Rate [m³/d]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Reservoir Temp [C]", fontsize=18)
plt.ylabel("Flow Rate [m³/d]", fontsize=18)
plt.grid(True)


plt.subplot(3, 3, 7)
plt.scatter(
    final_samples["Porosity [-]"],
    final_samples["Cycle Length [days]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("Porosity [-]", fontsize=18)
plt.ylabel("Cycle Length [days]", fontsize=18)
plt.grid(True)

plt.subplot(3, 3, 8)
plt.scatter(
    final_samples["CG"],
    final_samples["Cycle Length [days]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("CG", fontsize=18)
plt.ylabel("Cycle Length [days]", fontsize=18)
plt.grid(True)

plt.subplot(3, 3, 9)
plt.scatter(
    final_samples["CG"],
    final_samples["Flow Rate [m³/d]"],
    c=final_samples["Cluster"],
    cmap='Set1',
    edgecolor='k',
    alpha=0.7
)
plt.xlabel("CG", fontsize=18)
plt.ylabel("Flow Rate [m³/d]", fontsize=18)
plt.grid(True)




plt.tight_layout()
plt.show()

# === Plot original Perm vs Pressure again ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Permeability [mD]"],
    df["Reservoir Pressure[MPa]"]*10,
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Permeability [mD]"],
    final_samples["Reservoir Pressure[MPa]"]*10,
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Permeability [mD]", fontsize=18)
plt.ylabel("Reservoir Pressure [bar]", fontsize=18)
plt.legend(fontsize=14)
plt.grid(True)
plt.tight_layout()
plt.show()


# === Plot original porosity vs Temp  ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Porosity [-]"],
    df["Reservoir Temp [C]"] + 273.15,
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Porosity [-]"],
    final_samples["Reservoir Temp [C]"] + 273.15,
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Porosity [-]", fontsize=18)
plt.ylabel("Reservoir Temp [C]", fontsize=18)
plt.legend(fontsize=14)
plt.grid(True)
plt.tight_layout()
plt.show()


# === Plot original porosity vs Temp  ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Porosity [-]"],
    df["Reservoir Pressure[MPa]"],
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Porosity [-]"],
    final_samples["Reservoir Pressure[MPa]"],
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Porosity [-]", fontsize=18)
plt.ylabel("Reservoir Pressure [MPa]", fontsize=18)
plt.legend(fontsize=14)
plt.grid(True)
plt.tight_layout()
plt.show()


# === Plot original porosity vs Temp  ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Porosity [-]"],
    df["Permeability [mD]"],
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Porosity [-]"],
    final_samples["Permeability [mD]"],
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Porosity [-]", fontsize=18)
plt.ylabel("Permeability [mD]", fontsize=18)
# plt.legend(fontsize=14)
# plt.grid(True)
plt.tight_layout()
plt.show()



# === Plot original porosity vs Temp  ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Reservoir Temp [C]"] + 273.15,
    df["Reservoir Pressure[MPa]"] * 10,
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Reservoir Temp [C]"] + 273.15,
    final_samples["Reservoir Pressure[MPa]"] * 10,
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Reservoir Temp [K]", fontsize=18)
plt.ylabel("Reservoir Pressure[bar]", fontsize=18)
plt.legend(fontsize=14)
# plt.grid(True)
plt.tight_layout()
plt.show()


# === Plot original porosity vs Temp  ===
plt.figure(figsize=(8, 6))
plt.scatter(
    df["Reservoir Temp [C]"],
    df["Permeability [mD]"],
    color='black',
    alpha=1,
    s=80,
    label='Field Data'
)
plt.scatter(
    final_samples["Reservoir Temp [C]"],
    final_samples["Permeability [mD]"],
    color='white',
    edgecolor='black',
    s=80,
    label='Sampled'
)
plt.xlabel("Reservoir Temp [C]", fontsize=18)
plt.ylabel("Permeability [mD]", fontsize=18)
plt.legend(fontsize=14)
plt.grid(True)
plt.tight_layout()
plt.show()


