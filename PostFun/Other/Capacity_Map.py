import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Mapping
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import to_rgba
from CoolProp.CoolProp import PropsSI
T_std = 293.15
P_std = 1.01325
# ---------------- USER SETTINGS ----------------
INPUT_DIR  = r"Y:\Mixing Results\July"
EXCEL_FILE = "consolidated_output - Final.csv"   # <-- your consolidated file
SHEET_NAME = 0                                 # sheet index or name (e.g., "Sheet1")

# Column names in the consolidated file (edit if different)
COL_NAME   = "Field Name"
COL_LAT    = "Latitude"
COL_LON    = "Longitude"
COL_RGIIP  = "RGIIP"   # million standard cubic meters

# Visuals
TITLE      = "UK Depleted Fields — (RGIIP → TWh)/2"
SAVE_PNG   = "uk_rgiip_twh_over2_bubblemap.png"   # set to None to skip saving
# ------------------------------------------------

# Energy conversion
# kWh per m^3 H2 at STP ≈ 39.41 kWh/kg * 0.08988 kg/m^3  (same constant you used earlier)
KWH_PER_M3 = 39.41 * 0.08988
def H2_capacity(df):
    swr = 0.423
    rho_h2_std = PropsSI("D", "P", P_std * 1e5, "T", T_std, "Hydrogen")
    rho_CH4_std = PropsSI("D", "P", P_std * 1e5, "T", T_std,  "CH4")
    H2_cap = []
    for ii in range(len(df)):
        rho_CH4 = PropsSI("D", "P", df["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, "T", df["Reservoir Temp [C]"].iloc[ii] +273.15,  "CH4")
        rho_H2 = PropsSI("D", "P", df["Reservoir Pressure[MPa]"].iloc[ii] * 1e6, "T", df["Reservoir Temp [C]"].iloc[ii] +273.15, "Hydrogen")
        vol = df["RGIIP"].iloc[ii] * 1e6
        m_H2_std = vol * rho_H2 * (rho_CH4_std / rho_CH4)   # m3 at standard conditions
        H2_HHV = m_H2_std * 39.41 / 1e9 # Twh
        H2_vol = m_H2_std / rho_h2_std  # m3 at standard conditions
        H2_cap.append(H2_vol) 
    return H2_cap
# If RGIIP is in million scm: Energy_TWh = RGIIP * 1e6 * KWH_PER_M3 / 1e9 = RGIIP * KWH_PER_M3 / 1000
def rgiip_mmscm_to_twh(rgiip_mmscm: float) -> float:
    return float(rgiip_mmscm) * KWH_PER_M3 / 1_000.0

# ---------- Load data ----------
os.chdir(INPUT_DIR)
df = pd.read_csv(EXCEL_FILE, encoding='cp1252')
# Ensure columns exist / numeric
for c in [COL_LAT, COL_LON, COL_RGIIP]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=[COL_NAME, COL_LAT, COL_LON, COL_RGIIP]).copy()
df ["TWh_total"] = H2_capacity(df) 
df ["TWh_total"] = df["TWh_total"] * KWH_PER_M3 / 1e9
# Compute TWh and (TWh)/2
df["TWh_half"]  = df["TWh_total"] / 2.0

# Clamp negatives (just in case)
df["TWh_half"] = df["TWh_half"].clip(lower=0)

# ---------- Size mapping ----------
# Use an interpolated mapping from min→max TWh_half into pixel^2 marker areas
# Choose a nice range of areas (points^2). Adjust if you want larger/smaller bubbles.
min_area, max_area = 500, 3600
vmin, vmax = df["TWh_half"].min(), df["TWh_half"].max()
sum_Twh = df["TWh_half"].sum()
print(f"Total capacity (TWh)/2 = {sum_Twh:.2f}")
if vmax <= 0 or np.isclose(vmin, vmax):
    # fallback to a constant size if all values are identical/zero
    df["marker_area"] = 200.0
else:
    df["marker_area"] = np.interp(df["TWh_half"], [vmin, vmax], [min_area, max_area])

# ---------- Make the UK map ----------
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(15, 7))
ax  = plt.axes(projection=ccrs.Mercator())

# Soft backgrounds
ax.add_feature(cfeature.LAND, facecolor="#f5f5f5", zorder=0)
ax.add_feature(cfeature.OCEAN, facecolor="#dbe9ff", zorder=0)
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, zorder=1)
ax.add_feature(cfeature.BORDERS, linewidth=0.4, zorder=1)

# Focus on UK (tweak if needed)
# ax.set_extent([-6.0, 4.0, 49.5, 60.5], crs=proj)
ax.set_extent([-6.0, 4.0, 52.5, 55], crs=proj)
# Color: single hue with slight transparency
dot_color = "#1f77b4"
edge_col  = "#333333"

sc = ax.scatter(
    df[COL_LON], df[COL_LAT],
    s=df["marker_area"],
    color=to_rgba(dot_color, 0.7),
    edgecolor=edge_col, linewidth=0.8,
    transform=proj, zorder=3
)

# ---------- Legend: show size examples ----------
def size_handle(area, label):
    return plt.scatter([], [], s=area, color=to_rgba(dot_color, 0.7),
                       edgecolor=edge_col, linewidth=0.8, label=label)

# Pick 3–4 representative values for the legend
q_vals = np.unique(np.round(np.quantile(df["TWh_half"], [0.1, 0.6, 0.9]), 2))
if len(q_vals) == 0:
    q_vals = np.array([np.round(df["TWh_half"].mean(), 2)])
handles = [size_handle(np.interp(v, [vmin, vmax], [min_area, max_area]), f"{v:.2f} TWh")
           for v in q_vals]

leg = ax.legend(handles=handles, title="Capacity", loc="lower left",
                bbox_to_anchor=(1.02, 0.05), borderaxespad=0., frameon=True, fontsize=12)
if leg and leg.get_title():
    leg.get_title().set_fontsize(20)

# Title & layout
plt.title(TITLE, fontsize=14, pad=10)
plt.tight_layout()

if SAVE_PNG:
    plt.savefig(SAVE_PNG, dpi=300, bbox_inches="tight")

plt.show()
