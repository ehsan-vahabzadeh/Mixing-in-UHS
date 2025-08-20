import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
# --- Mapping libs ---
import cartopy.crs as ccrs
import cartopy.feature as cfeature

input_dir = r"Y:\Mixing Results\July"
os.chdir(input_dir) 
df = pd.read_csv("optimized_results_without_CG.csv", encoding='cp1252')

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
lat_col = "Latitude"
lon_col = "Longitude"
name_col= "Field Name"
df[rf_col] = pd.to_numeric(df[rf_col], errors="coerce")
df[CG_col] = pd.to_numeric(df[CG_col], errors="coerce")
df[CL_col] = pd.to_numeric(df[CL_col], errors="coerce")
df[FR_col] = pd.to_numeric(df[FR_col], errors="coerce")
df[FR_col] = pd.to_numeric(df[FR_col], errors="coerce")
df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
  
df = df.dropna(subset=[rf_col, gas_col, CG_col, CL_col, FR_col])
df_all = df.dropna(subset=[gas_col, FR_col, CL_col])          # for FR vs CL
Gas = "H2"
import matplotlib.pyplot as plt
tab20c = plt.get_cmap("tab20c")
# Choose color indices, e.g. 0, 4, 8 for distinct colors
from matplotlib.colors import ListedColormap, BoundaryNorm
tab20c = plt.cm.tab20c.colors
colors = [tab20c[0], tab20c[4], tab20c[8]]
rf_min, rf_max = 0.7, 1.0  # typical spread; adjust if needed
df_gas  = df[(df[gas_col] == Gas)].dropna(subset=[CG_col, rf_col])  # for RF vs CG (H2 only)   
# -------------------------
# 1) Prep the data (H2 only)
# -------------------------
rf_col  = "Max Predicted RF [-]"
gas_col = "Cushion Gas"
lon_col = "Longitude"
lat_col = "Latitude"
name_col= "Field Name"

# Keep only rows with coords, H2, and RF
df_gas = (df[[name_col, lon_col, lat_col, gas_col, rf_col]]
           .dropna(subset=[lon_col, lat_col, gas_col, rf_col]))
df_gas = df_gas[df_gas[gas_col] == Gas]

# One point per field: take the max RF per field
df_gasmax = (df_gas
            .sort_values(rf_col, ascending=False)
            .groupby(name_col, as_index=False)
            .first())

# Optional clamp if NN could output slightly >1 due to noise
df_gasmax[rf_col] = df_gasmax[rf_col].clip(lower=0, upper=1.0)

# -------------------------
# 2) Visual encodings
# -------------------------
# Size scaling (pixels^2). Tune min/max to taste

sizes = np.interp(df_gasmax[rf_col], [rf_min, rf_max], [40, 400])  # marker area
def rf_to_size(rf):
    if rf < 0.8:
        return 50   # small
    elif rf < 0.9:
        return 150  # medium
    else:
        return 300  # large
df_gasmax["size"] = df_gasmax[rf_col].apply(rf_to_size)
# 3) Make the UK map
# -------------------------
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(9, 11))
ax = plt.axes(projection=ccrs.Mercator())

# Basemap features
ax.add_feature(cfeature.LAND, facecolor="#f5f5f5")
ax.add_feature(cfeature.OCEAN, facecolor="#dbe9ff" )
ax.add_feature(cfeature.COASTLINE, linewidth=0.6)
ax.add_feature(cfeature.BORDERS, linewidth=0.4)
# ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5, linestyle="--")

# Focus the view on UK (rough bounds; tweak if your fields are offshore)
ax.set_extent([-6.0, 4, 49.5, 60.5], crs=proj)
def rf_to_color(rf):
    if rf < 0.8:
        return colors[0]   # small
    elif rf < 0.9 :
        return colors[1]  # medium
    else:
        return colors[2]  # large
df_gasmax["colors"] = df_gasmax[rf_col].apply(rf_to_color)
cmap = ListedColormap(colors)
bounds = [0.0, 0.8, 0.9, 1.0]
norm = BoundaryNorm(bounds, cmap.N)
sc = ax.scatter(
    df_gasmax[df_gasmax[rf_col] > 0]["Longitude"],
    df_gasmax[df_gasmax[rf_col] > 0]["Latitude"],
    s=df_gasmax[df_gasmax[rf_col] > 0]["size"],
    # c=df_gasmax[df_gasmax[rf_col] > 0][rf_col],
    color=df_gasmax[df_gasmax[rf_col] > 0]["colors"], 
    alpha=0.7, edgecolor="k", linewidth=1,
    transform=proj,
    zorder=3,
    label="Max RF"
)

# Plot X markers for RF == 0 (not storage compatible)
df_zero = df_gasmax[df_gasmax[rf_col] == 0]
ax.scatter(
    df_zero["Longitude"], df_zero["Latitude"],
    s=120, marker="x", color="black", linewidth=1,alpha=0.5,
    transform=proj, zorder=4, label="RF = 0 (Not compatible)"
)
# -------------------------
# 4) Legends & colorbar
# -------------------------
# RF colorbar
# cb = plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.03, aspect=10, fraction=0.05, location="bottom")
# cb.set_label("RF", fontsize=18)
# cb.ax.tick_params(labelsize=18)

import matplotlib.lines as mlines

# Create legend handles for marker sizes
size_labels = ["RF < 0.8", "0.8 < RF < 0.9", "RF > 0.9"]
size_values = [50, 150, 300]
import matplotlib.lines as mlines

handles = [
    plt.scatter([], [], s=size, edgecolor="k", color=colors[i], alpha=0.7, label=label)
    for i, (size, label) in enumerate(zip(size_values, size_labels))
]
# Add X marker for incompatible fields
x_handle = plt.scatter([], [], s=120, marker="x", color="black", linewidth=1, alpha=0.5, label="Incompatible")
handles.append(x_handle)

leg = ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=14, bbox_to_anchor=(1.05, 0.05), borderaxespad=0.)
# leg.get_title().set_fontsize(14)
# leg._legend_box.sep = 16  # Increase vertical spacing between legend entries


plt.title(f"UK Depleted Fields — RF {Gas} by Reservoir", fontsize=13, pad=10)
plt.tight_layout()
# plt.savefig("uk_h2_rf_bubblemap.png", dpi=300, bbox_inches="tight")
plt.show()
