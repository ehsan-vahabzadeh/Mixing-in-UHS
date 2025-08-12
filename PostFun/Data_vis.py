import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Path to your consolidated CSV
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"

# Read the CSV file
df = pd.read_csv(csv_path)

# Select and convert the necessary columns to numeric
columns = [
    "Porosity [-]",
    "Permeability [mD]",
    "Reservoir Pressure[MPa]",
    "Reservoir Temp [C]",
]
df[columns] = df[columns].apply(pd.to_numeric, errors='coerce')
df_clean = df[columns].dropna()

# Create histograms + KDE plots
plt.figure(figsize=(14, 10))
for i, col in enumerate(columns, 1):
    plt.subplot(2, 2, i)
    sns.histplot(df_clean[col], kde=True, color='skyblue', edgecolor='black')
    plt.title(f"Distribution of {col}", fontsize=11)
    plt.xlabel(col, fontsize=16)
    plt.ylabel("Frequency", fontsize=16)

plt.tight_layout()
plt.suptitle("Statistical Distributions of Key Reservoir Properties", fontsize=16, y=1.03)
plt.show()

# Create subplots
fig, axes = plt.subplots(1, 3, figsize=(14, 7))
axes = axes.flatten()

# Scatter plot: Reservoir Pressure vs Porosity
pressure_porosity = df[[ "Porosity [-]","Permeability [mD]"]].dropna()
if not pressure_porosity.empty:
    sns.scatterplot(
        data=pressure_porosity,
        x="Porosity [-]",
        y="Permeability [mD]",
        ax=axes[0],
        color="darkgreen"
    )
    axes[0].set_title("Permeability [mD] vs Porosity", fontsize=11)

# Scatter plot: Reservoir Pressure vs Gross Prod Rate
pressure_flow = df[["Reservoir Temp [C]", "Reservoir Pressure[MPa]"]].dropna()
if not pressure_flow.empty:
    sns.scatterplot(
        data=pressure_flow,
        x="Reservoir Pressure[MPa]",
        y="Reservoir Temp [C]",
        ax=axes[1],
        color="darkred"
    )
    axes[1].set_title("Reservoir Pressure vs Reservoir Temperature", fontsize=11)

# Scatter plot: Reservoir Pressure vs Gross Prod Rate
pressure_perm = df[["Permeability [mD]","Reservoir Pressure[MPa]" ]].dropna()
if not pressure_perm.empty:
    sns.scatterplot(
        data=pressure_perm,
        x="Permeability [mD]",
        y="Reservoir Pressure[MPa]",
        ax=axes[2],
        color="darkred"
    )
    axes[2].set_title("Reservoir Pressure vs Permeability", fontsize=11)
# Clean up any unused plots
for i in range(6, len(axes)):
    fig.delaxes(axes[i])

plt.tight_layout()
plt.suptitle("Reservoir Property Analysis", fontsize=16, y=1.02)
plt.show()