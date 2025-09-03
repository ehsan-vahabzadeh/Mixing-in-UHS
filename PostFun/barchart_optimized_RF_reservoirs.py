import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps
import os
# --- 1) Load and clean ---
input_dir = r"Y:\Mixing Results\July"
os.chdir(input_dir) 
df = pd.read_csv("optimized_results_without_CG_1.csv", encoding='cp1252')

# Ensure the needed columns exist and are numeric
H2_val = []
CH4_val = []
CO2_val = []
N2_val = []
rf_col = "Max Predicted RF [-]"
gas_col = "Cushion Gas"
CG_col = "Optimized CG Ratio"
CL_col = "Optimized Cycle Length [d]"
FR_col = "Optimized Flow Rate [sm3/d]"
df[rf_col] = pd.to_numeric(df[rf_col], errors="coerce")
df[CG_col] = pd.to_numeric(df[CG_col], errors="coerce")
df[CL_col] = pd.to_numeric(df[CL_col], errors="coerce")
df[FR_col] = pd.to_numeric(df[FR_col], errors="coerce")
df = df.dropna(subset=[rf_col, gas_col, CG_col, CL_col, FR_col])
df_all = df.dropna(subset=[gas_col, FR_col, CL_col])          # for FR vs CL
df_h2  = df[(df[gas_col] == "H2")].dropna(subset=[CG_col, rf_col])  # for RF vs CG (H2 only)           
# --- 2) Bin RF into three groups ---
# Bins: <0.6, 0.6–0.8, >0.8
bins = [0.0, 0.8, 0.9, 1]
labels_RF = ["< 0.8", "0.8–0.9", "> 0.9"]
df["RF_bin"] = pd.cut(df[rf_col], bins=bins, labels=labels_RF, right=True, include_lowest=True)
# --- 3) Count per Cushion Gas and RF bin ---
gas_order = ["H2", "CO2", "CH4", "N2"]
counts = (
    df.groupby([gas_col, "RF_bin"])
      .size()
      .unstack("RF_bin", fill_value=0))
counts = counts.reindex(index=[g for g in gas_order if g in counts.index])
counts = counts.reindex(columns=labels_RF, fill_value=0)
bins = [1e5, 5e5, 1e6, 1.5e6]
labels_FR = ["< 5", "5-10", "10-15"]
df["FR_bin"] = pd.cut(df[FR_col], bins=bins, labels=labels_FR, right=True, include_lowest=True)
counts_FR = (
    df.groupby([gas_col, "FR_bin"])
      .size()
      .unstack("FR_bin", fill_value=0))
counts_FR = counts_FR.reindex(index=[g for g in gas_order if g in counts_FR.index])
counts_FR = counts_FR.reindex(columns=labels_FR, fill_value=0)
bins = [14, 60, 120, 180]
labels_CL = ["< 60", "60-120", "> 120"]
df["CL_bin"] = pd.cut(df[CL_col], bins=bins, labels=labels_CL, right=True, include_lowest=True)
counts_CL = (
    df.groupby([gas_col, "CL_bin"])
      .size()
      .unstack("CL_bin", fill_value=0))
counts_CL = counts_CL.reindex(index=[g for g in gas_order if g in counts_CL.index])
counts_CL = counts_CL.reindex(columns=labels_CL, fill_value=0)
bins = [0, 2, 4, 5]
labels_CG = ["< 2", "2-4", "> 5"]
df_h2["CG_bin"] = pd.cut(df_h2[CG_col], bins=bins, labels=labels_CG, right=True, include_lowest=True)
counts_CG = (
    df_h2.groupby([gas_col, "CG_bin"])
      .size()
      .unstack("CG_bin", fill_value=0))
counts_CG = counts_CG.reindex(index=[g for g in gas_order if g in counts_CG.index])
counts_CG = counts_CG.reindex(columns=labels_CG, fill_value=0)

colors = plt.cm.get_cmap('Greys',len(gas_order))
# --- 4) Grouped bar chart: x = RF bins; one group per gas ---
x = np.arange(len(labels_RF))  # positions for RF bins
width = 0.18                 # bar width
fig, ax = plt.subplots(1,3, figsize=(12, 4))
fig.subplots_adjust(wspace=0.1)

for i, gas in enumerate(counts.index):
    ax[0].bar(x + i*width - (width*(len(counts.index)-1)/2), counts.loc[gas, labels_RF].values,
           width=width,color=colors(i), label=gas, edgecolor='black', linewidth=1, alpha=0.8)

ax[0].set_xticks(x)
ax[0].set_xticklabels(labels_RF)
ax[0].tick_params(axis= 'both', which='major', labelsize=16)
ax[0].set_xlabel("RF range [-]", fontsize=18)
ax[0].set_ylabel("Number of cases" , fontsize=18)
ax[0].legend(title="Cushion Gas", fontsize=16)

# Annotate counts on bars (optional)
for i, gas in enumerate(counts.index):
    vals = counts.loc[gas, labels_RF].values
    xpos = x + i*width - (width*(len(counts.index)-1)/2)
    for xi, v in zip(xpos, vals):
        ax[0].text(xi, v + 0.02*max(1, counts.values.max()), str(int(v)),
                ha="center", va="bottom", fontsize=9)

for i, gas in enumerate(counts_FR.index):
    ax[1].bar(x + i*width - (width*(len(counts_FR.index)-1)/2), counts_FR.loc[gas, labels_FR].values,
           width=width,color=colors(i), label=gas, edgecolor='black', linewidth=1, alpha=0.8)

ax[1].set_xticks(x)
ax[1].set_xticklabels(labels_FR)
ax[1].tick_params(axis= 'both', which='major', labelsize=16)
ax[1].set_xlabel("Flow Rate[sm3/d]", fontsize=18)
ax[1].set_ylabel("Number of cases" , fontsize=18)
# ax[1].legend(title="Cushion Gas", fontsize=16)

# Annotate counts on bars (optional)
for i, gas in enumerate(counts_FR.index):
    vals = counts_FR.loc[gas, labels_FR].values
    xpos = x + i*width - (width*(len(counts_FR.index)-1)/2)
    for xi, v in zip(xpos, vals):
        ax[1].text(xi, v + 0.02*max(1, counts_FR.values.max()), str(int(v)),
                ha="center", va="bottom", fontsize=9)

for i, gas in enumerate(counts_CL.index):
    ax[2].bar(x + i*width - (width*(len(counts_CL.index)-1)/2), counts_CL.loc[gas, labels_CL].values,
           width=width,color=colors(i), label=gas, edgecolor='black', linewidth=1, alpha=0.8)

ax[2].set_xticks(x)
ax[2].set_xticklabels(labels_CL)
ax[2].tick_params(axis= 'both', which='major', labelsize=16)
ax[2].set_xlabel("Cycle Length [days]", fontsize=18)
ax[2].set_ylabel("Number of cases" , fontsize=18)
# ax[2].legend(title="Cushion Gas", fontsize=16)

# Annotate counts on bars (optional)
for i, gas in enumerate(counts_CL.index):
    vals = counts_CL.loc[gas, labels_CL].values
    xpos = x + i*width - (width*(len(counts_CL.index)-1)/2)
    for xi, v in zip(xpos, vals):
        ax[2].text(xi, v + 0.02*max(1, counts_CL.values.max()), str(int(v)),
                ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.show()        



fig, ax = plt.subplots(1,1, figsize=(4, 4))
fig.subplots_adjust(wspace=0.1)

for i, gas in enumerate(counts_CG.index):
    ax.scatter(df_h2[rf_col], df_h2[CG_col],
            edgecolor='black', alpha=0.8)

ax.set_xticks(x)
ax.tick_params(axis= 'both', which='major', labelsize=16)
ax.set_xlabel("RF[-]", fontsize=18)
ax.set_ylabel("CG Ratio" , fontsize=18)
ax.set_xticks([0.7, 0.85, 1])
ax.set_xlim(0.67, 1)
plt.tight_layout()
plt.show()         