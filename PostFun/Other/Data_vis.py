import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
fontsize = 18
# Color = '#a0a0a0'
Color='#7a0b01'
# Path to your consolidated CSV
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"

# Read the CSV file
df = pd.read_csv(csv_path, encoding='cp1252')

# Select and convert the necessary columns to numeric
df = df.rename(columns={"Reservoir Pressure[MPa]": "Reservoir Pressure [bar]","Reservoir Temp [C]": "Reservoir Temperature [K]"})
columns = [
    "Porosity [-]",
    "Permeability [mD]",
    "Reservoir Pressure [bar]",
    "Reservoir Temperature [K]",
]
df[columns] = df[columns].apply(pd.to_numeric, errors='coerce')
df["Reservoir Temperature [K]"] = df["Reservoir Temperature [K]"] + 273.15  # Convert to Kelvin
df["Reservoir Pressure [bar]"] = df["Reservoir Pressure [bar]"] * 10  # Convert to bar

df_clean = df[columns].dropna()

# Create histograms + KDE plots
plt.figure(figsize=(5, 10))
for i, col in enumerate(columns, 1):
    plt.subplot(2, 2, i)
    if col == "Permeability [mD]":
        bins = [0,10,50,100,250,500,750,1000,1500]
        labels = ["10","50","100","250","500","750","1000","1500"]
        counts, _ = np.histogram(df[col], bins=bins)
        plt.bar(range(len(counts)), counts,color = Color,alpha = 0.7, edgecolor='black', width = 1)
        plt.xticks(range(len(counts)), labels)
        plt.tick_params(axis = 'x', rotation=45)        
        # sns.histplot(df_clean[col], color=Color, edgecolor='black', alpha=0.5, bins=[0,10,50,100,500,1000,1500])
        # plt.subplot(2, 2, i).set_xscale('log')
    else:
        sns.histplot(df_clean[col], color=Color, edgecolor='black', bins = 8, alpha=0.7)
    # plt.title(f"Distribution of {col}", fontsize=fontsize)
    plt.xlabel(col, fontsize=fontsize)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.ylabel("Frequency", fontsize=fontsize)

plt.tight_layout()
plt.suptitle("Statistical Distributions of Key Reservoir Properties", fontsize=fontsize, y=1.03)
plt.show()

# Create subplots
fig, axes = plt.subplots(1, 3, figsize=(7, 7))
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
    axes[0].set_title("Permeability [mD] vs Porosity", fontsize=fontsize)

# Scatter plot: Reservoir Pressure vs Gross Prod Rate
pressure_flow = df[["Reservoir Temperature [K]", "Reservoir Pressure [bar]"]].dropna()
if not pressure_flow.empty:
    sns.scatterplot(
        data=pressure_flow,
        x="Reservoir Pressure [bar]",
        y="Reservoir Temperature [K]",
        ax=axes[1],
        color="darkred"
    )
    axes[1].set_title("Reservoir Pressure vs Reservoir Temperature", fontsize=fontsize)

# Scatter plot: Reservoir Pressure vs Gross Prod Rate
pressure_perm = df[["Permeability [mD]","Reservoir Pressure [bar]" ]].dropna()
if not pressure_perm.empty:
    sns.scatterplot(
        data=pressure_perm,
        x="Permeability [mD]",
        y="Reservoir Pressure[bar]",
        ax=axes[2],
        color="darkred"
    )
    axes[2].set_title("Reservoir Pressure vs Permeability", fontsize=fontsize)
# Clean up any unused plots
for i in range(6, len(axes)):
    fig.delaxes(axes[i])

plt.tight_layout()
plt.suptitle("Reservoir Property Analysis", fontsize=fontsize, y=1.02)
plt.show()