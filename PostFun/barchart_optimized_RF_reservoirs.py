import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps
import os
# --- 1) Load and clean ---
input_dir = r"Y:\Mixing Results\July"
os.chdir(input_dir) 
df = pd.read_csv("optimized_results_no_CG.csv")

# Ensure the needed columns exist and are numeric
rf_col = "Max Predicted RF [-]"
gas_col = "Cushion Gas"
df[rf_col] = pd.to_numeric(df[rf_col], errors="coerce")
df = df.dropna(subset=[rf_col, gas_col])

# --- 2) Bin RF into three groups ---
# Bins: <0.6, 0.6–0.8, >0.8
bins = [-np.inf, 0.8, 0.9, np.inf]
labels = ["< 0.8", "0.8–0.9", "> 0.9"]
df["RF_bin"] = pd.cut(df[rf_col], bins=bins, labels=labels, right=True, include_lowest=True)

# --- 3) Count per Cushion Gas and RF bin ---
counts = (
    df.groupby([gas_col, "RF_bin"])
      .size()
      .unstack("RF_bin", fill_value=0)
)

# Optional: set a consistent order for gases and bins
gas_order = ["H2", "CO2", "CH4", "N2"]
counts = counts.reindex(index=[g for g in gas_order if g in counts.index])
counts = counts.reindex(columns=labels, fill_value=0)

colors = plt.cm.get_cmap('Greys',len(gas_order))
# --- 4) Grouped bar chart: x = RF bins; one group per gas ---
x = np.arange(len(labels))  # positions for RF bins
width = 0.18                 # bar width
fig, ax = plt.subplots(figsize=(8, 5))

for i, gas in enumerate(counts.index):
    ax.bar(x + i*width - (width*(len(counts.index)-1)/2), counts.loc[gas, labels].values,
           width=width,color=colors(i), label=gas, edgecolor='black', linewidth=1, alpha=0.8)

ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.tick_params(axis= 'both', which='major', labelsize=16)
ax.set_xlabel("RF range [-]", fontsize=18)
ax.set_ylabel("Number of cases" , fontsize=18)
ax.legend(title="Cushion Gas", fontsize=16)

# Annotate counts on bars (optional)
for i, gas in enumerate(counts.index):
    vals = counts.loc[gas, labels].values
    xpos = x + i*width - (width*(len(counts.index)-1)/2)
    for xi, v in zip(xpos, vals):
        ax.text(xi, v + 0.02*max(1, counts.values.max()), str(int(v)),
                ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.show()
