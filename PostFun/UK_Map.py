import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
# --- Mapping libs ---
import cartopy.crs as ccrs
import cartopy.feature as cfeature
input_dir = r"Y:\Mixing Results\Field Data"
os.chdir(input_dir) 
df_loc = pd.read_csv("consolidated_output - Final.csv", encoding='cp1252')
input_dir = r"Y:\Mixing Results\July"
os.chdir(input_dir) 
df = pd.read_csv("optimized_results_without_CG.csv")

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
df[lat_col] = pd.to_numeric(df_loc[lat_col], errors="coerce")
df[lon_col] = pd.to_numeric(df_loc[lon_col], errors="coerce")
df = df.dropna(subset=[rf_col, gas_col, CG_col, CL_col, FR_col])
df_all = df.dropna(subset=[gas_col, FR_col, CL_col])          # for FR vs CL
df_h2  = df[(df[gas_col] == "H2")].dropna(subset=[CG_col, rf_col])  # for RF vs CG (H2 only)     
# -------------------------
# 1) Prep the data (H2 only)
# -------------------------
rf_col  = "Max Predicted RF [-]"
gas_col = "Cushion Gas"
lon_col = "Longitude"
lat_col = "Latitude"
name_col= "Field Name"

# Keep only rows with coords, H2, and RF
df_h2 = (df[[name_col, lon_col, lat_col, gas_col, rf_col]]
           .dropna(subset=[lon_col, lat_col, gas_col, rf_col]))
df_h2 = df_h2[df_h2[gas_col] == "H2"]

# One point per field: take the max RF per field
df_h2max = (df_h2
            .sort_values(rf_col, ascending=False)
            .groupby(name_col, as_index=False)
            .first())

# Optional clamp if NN could output slightly >1 due to noise
df_h2max[rf_col] = df_h2max[rf_col].clip(lower=0, upper=1.0)

# -------------------------
# 2) Visual encodings
# -------------------------
# Size scaling (pixels^2). Tune min/max to taste
rf_min, rf_max = 0.6, 1.0  # typical spread; adjust if needed
sizes = np.interp(df_h2max[rf_col], [rf_min, rf_max], [40, 400])  # marker area
def rf_to_size(rf):
    if rf < 0.8:
        return 50   # small
    elif rf < 0.9:
        return 150  # medium
    else:
        return 300  # large
df_h2max["size"] = df_h2max[rf_col].apply(rf_to_size)
# Colormap by RF
cmap = plt.cm.Purples
cmap.set_bad(color='lightgray')  # for NaN values

# -------------------------
# 3) Make the UK map
# -------------------------
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(9, 11))
ax = plt.axes(projection=ccrs.Mercator())

# Basemap features
ax.add_feature(cfeature.LAND, facecolor="#f5f5f5")
ax.add_feature(cfeature.OCEAN, facecolor="#dbe9ff")
ax.add_feature(cfeature.COASTLINE, linewidth=0.6)
ax.add_feature(cfeature.BORDERS, linewidth=0.4)
# ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5, linestyle="--")

# Focus the view on UK (rough bounds; tweak if your fields are offshore)
ax.set_extent([-6.0, 4, 49.5, 60.5], crs=proj)

# Plot bubbles
# sc = ax.scatter(
#     df_h2max[lon_col], df_h2max[lat_col],
#     s=sizes,
#     c=df_h2max[rf_col],
#     cmap=cmap,
#     vmin=rf_min, vmax=rf_max,
#     alpha=0.9, edgecolor="k", linewidth=0.6,
#     transform=proj,
#     zorder=3
# )
for label, (cond, color) in {
    "<0.8": (df_h2max[rf_col] < 0.8, "red"),
    "0.8–0.9": ((df_h2max[rf_col] >= 0.8) & (df_h2max[rf_col] < 0.9), "orange"),
    ">0.9": (df_h2max[rf_col] >= 0.9, "green")
}.items():
    sub = df_h2max[cond]
    sc = ax.scatter(sub["Longitude"], sub["Latitude"],
               s=sub["size"], c=cmap, alpha=0.7, edgecolor="k", label=label)
# -------------------------
# 4) Legends & colorbar
# -------------------------
# RF colorbar
cb = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
cb.set_label("Max RF (H₂)", fontsize=11)

# Size legend (pick a few reference RFs)
ref_rfs = [0.7, 0.85, 1.0]
ref_sizes = np.interp(ref_rfs, [rf_min, rf_max], [40, 400])
for s, r in zip(ref_sizes, ref_rfs):
    ax.scatter([], [], s=s, color="white", edgecolor="k", linewidth=0.6, transform=proj,
               label=f"RF ≈ {r:.2f}")
leg = ax.legend(title="Marker Size", loc="lower left", frameon=True, fontsize=9)
leg.get_title().set_fontsize(10)

# Optional: annotate a few top fields
top = df_h2max.nlargest(5, rf_col)
for _, r in top.iterrows():
    ax.text(r[lon_col], r[lat_col], f"  {r[name_col]}",
            transform=proj, fontsize=8, weight="bold",
            va="center", ha="left", zorder=4)

plt.title("UK Depleted Fields — Max RF (H₂) by Reservoir", fontsize=13, pad=10)
plt.tight_layout()
# plt.savefig("uk_h2_rf_bubblemap.png", dpi=300, bbox_inches="tight")
plt.show()
