import os
import pandas as pd
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from scipy.interpolate import griddata
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, ConvexHull
from scipy.ndimage import gaussian_filter, distance_transform_edt
from matplotlib.path import Path
from scipy.ndimage import zoom

plt.rcParams.update({
    "font.size": 20,
    "axes.labelsize": 20,
    "axes.titlesize": 20,
    "legend.fontsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "lines.linewidth": 3,
    "lines.markersize": 7,
})
def nearest_outside_fill(Z, mask):
    # Fill ~mask with nearest value from mask==True
    outside = ~mask
    dist, (iy, ix) = distance_transform_edt(outside, return_indices=True)
    Zfilled = Z.copy()
    Zfilled[outside] = Z[iy[outside], ix[outside]]
    return Zfilled

def boundary_safe_gaussian(Z, mask, sigma, mode='nearest'):
    Zfilled = nearest_outside_fill(Z, mask)
    Zsmooth = gaussian_filter(Zfilled, sigma=sigma, mode=mode)
    Zsmooth[~mask] = np.nan
    return Zsmooth
def coutour_map(input_directory):
    file_path = os.path.join(input_directory, 'compiled_optimal_data.csv')
    df = pd.read_csv(file_path)
    # Assume df is your DataFrame with columns:
    # 'H2_Target_TWh', 'H2_Cost_per_kg', 'PSA_Cost', 'CG_Ratio', 'LCOS'
    mask = ~((df["H2_Target_TWh"] == 200) & (df["CG_Ratio"] < 1e-4))
    df = df[mask]

    # df['Ratio'] = df['H2_Cost_per_kg'] / df['PSA_Cost']

    # Define grid
    xi = np.linspace(df['H2_Target_TWh'].min(), df['H2_Target_TWh'].max(), 50)
    yi = np.linspace(df['Ratio'].min(), df['Ratio'].max(), 50)
    Xi, Yi = np.meshgrid(xi, yi)

    
    # Build a regular grid
    z = df["CG_Ratio"]  # ensure physical range if needed
    tri = Delaunay(np.column_stack([df['H2_Target_TWh'], df['Ratio']]))
    lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
    Zi = lin(Xi, Yi)
    mask = np.isfinite(Zi)          # True inside (where Zi is defined)

    Zi_filled = np.where(np.isnan(Zi), np.nanmean(Zi), Zi)

    # Zoom the interpolated data (cubic interpolation)
    Zi_zoomed = zoom(Zi_filled, zoom=2, order=2)
    xi_zoom = np.linspace(xi.min(), xi.max(), Zi_zoomed.shape[1])
    yi_zoom = np.linspace(yi.min(), yi.max(), Zi_zoomed.shape[0])
    Xi_zoom, Yi_zoom = np.meshgrid(xi_zoom, yi_zoom)
    # smooth with boundary-safe method (it already re-masks outside to NaN)
    Zi_cg = boundary_safe_gaussian(Zi, mask, sigma=3)
    Zi_cg[~mask] = np.nan
    
    
    
    # Interpolate data
    z = df["LCOS"]  # ensure physical range if needed
    tri = Delaunay(np.column_stack([df['H2_Target_TWh'], df['Ratio']]))
    lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
    Zi = lin(Xi, Yi)
    mask = np.isfinite(Zi)          # True inside (where Zi is defined)
    Zi_lcos = boundary_safe_gaussian(Zi, mask, sigma=3)
    Zi_lcos[~mask] = np.nan
    
    
    # Zi_cg   = griddata((df['H2_Target_TWh'], df['Ratio']), df['CG_Ratio'], (Xi, Yi), method='cubic')
    # Zi_lcos = griddata((df['H2_Target_TWh'], df['Ratio']), df['LCOS'], (Xi, Yi), method='cubic')
    # Zi_cg = np.clip(Zi_cg, 0.1, 4.6)
    
 
    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    boundaries = [0,0.5,1,1.5,2,2.5,3,3.5,4]
    cmap = plt.get_cmap("plasma", len(boundaries) )
    norm = mcolors.BoundaryNorm(boundaries, cmap.N)
    # Filled contour: CG Ratio
    ctf = ax.contourf(Xi, Yi, Zi_cg, cmap=cmap,norm = norm)
    # ctf = ax.contourf(Xi_zoom, Yi_zoom, Zi_zoomed, levels=10, cmap='viridis')
    plt.colorbar(ctf, label='Cushion Gas Ratio', cmap = cmap, norm = norm, ax=ax, ticks=boundaries,spacing='uniform')
    plt.scatter(df["H2_Target_TWh"], df["H2_Cost_per_kg"]/df["PSA_Cost"], 
    c=df["CG_Ratio"], cmap=cmap, norm = norm, edgecolors="k", linewidths=1, label="Sample Points")
    # Contour lines: LCOS
    cs = ax.contour(Xi, Yi, Zi_lcos, colors='white', linewidths=1.5)
    ax.clabel(cs, fmt='%1.1f', fontsize=16)
    ax.set_yscale('log')
    yticks = [1, 10]
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(y) for y in yticks])
    ax.set_xticks([5,25,50,75,100,125,150,175,200])
    
    # ax.set_ylim((df['Ratio'].min()), (df['Ratio'].max()))
    ax.set_xlabel("Target H$_2$ Demand [TWh]")
    ax.set_ylabel("PCI = C$_{H_2}$ /C$_{PSA}$ [-]")
    # ax.set_title("Contour Map: CG Ratio (filled) with LCOS Isolines")

    plt.tight_layout()
    plt.savefig("Contour_Map_CG_LCOS.jpeg", dpi=500)
    plt.show()

def plot_bubble_size_legend_lcos():
    fig, ax = plt.subplots(figsize=(2.5, 5))
    ax.axis("off")

    # LCOS values
    lcos_values = [30, 60, 90]  # In $/kg
    base_size = 300  # Adjust if needed

    # Use squared sizes to exaggerate difference
    sizes = [((val / min(lcos_values)) ** 2) * base_size for val in lcos_values]
    y_positions = [0.8, 0.5, 0.2]

    for val, s, y in zip(lcos_values, sizes, y_positions):
        ax.scatter(0.5, y, s=s, color="gray", alpha=0.6, edgecolors='k', linewidths=0.5)
        ax.text(0.5, y, f"{val:.1f} $/kg", ha="center", va="center", fontsize=10)

    ax.set_title("Bubble Size\nLCOS ($/kg)", fontsize=12, pad=20)
    plt.tight_layout()
    plt.show()
def plot_bubble_chart(df):
    df.sort_values(by="H2_Target_TWh", inplace=True)
    # Convert H2_Target_TWh to string for categorical x-axis
    df["H2_Target_TWh_str"] = df["H2_Target_TWh"].astype(str)
    H2_PSA_ratio  = df["H2_Cost_per_kg"] / df["PSA_Cost"]
    df["H2_Cost_per_kg_str"] = df["H2_Cost_per_kg"].astype(str)
    boundaries = [0, 0.5, 1, 2, 3, 4]
    cmap = plt.get_cmap("viridis", len(boundaries) - 1)
    norm = mcolors.BoundaryNorm(boundaries, ncolors=cmap.N, clip=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(
        x=df["H2_Target_TWh_str"],
        y=H2_PSA_ratio,
        s=df["LCOS"]*100,  # Adjust size multiplier as needed
        c=df["CG_Ratio"],
        cmap=cmap,
        norm=norm,
        alpha=0.7,
        edgecolors="w",
        linewidths=0.5
    )

    # Color bar for LCOS
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Cushion Gas Ratio")    
    
    ax.set_xlabel("Target H$_2$ Demand (TWh)")
    ax.set_ylabel("H₂ Cost (\$/kg) / PSA Cost (\$/kg)")
    plt.tight_layout()
    plt.show()


def plot_bubble_chart_rf(df):
    df.sort_values(by="H2_Target_TWh", inplace=True)
    # Convert H2_Target_TWh to string for categorical x-axis
    df["H2_Target_TWh_str"] = df["H2_Target_TWh"].astype(str)
    H2_PSA_ratio  = df["H2_Cost_per_kg"] / df["PSA_Cost"]
    df["H2_Cost_per_kg_str"] = df["H2_Cost_per_kg"].astype(str)
    boundaries = [0,0.8,0.9,0.95,1]
    cmap = plt.get_cmap("viridis", len(boundaries) - 1)
    norm = mcolors.BoundaryNorm(boundaries, ncolors=cmap.N, clip=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(
        x=df["H2_Target_TWh_str"],
        y=H2_PSA_ratio,
        s=df["CG_Ratio"]*10000,  # Adjust size multiplier as needed
        c=df["Predicted_RF"],
        cmap=cmap,
        norm=norm,
        alpha=0.7,
        edgecolors="w",
        linewidths=0.5
    )

    # Color bar for LCOS
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Recovery Factor [-]")

    ax.set_xlabel("Target H₂ Demand (TWh)")
    ax.set_ylabel("H₂ Cost (\$/kg) / PSA Cost (\$/kg)")
    plt.tight_layout()
    plt.show()

# Set your folder containing Excel files
FOLDER_PATH = r"Y:\Mixing Results\July\Two Term Equation"
os.chdir(FOLDER_PATH)
# Desired columns to extract
COLS_TO_KEEP = [
    "Cum H2 Injected [Twh]",
    "Cum H2 Produced [Twh]",
    "LCOS",
    "Permeability [mD]",
    "Reservoir Pressure[bar]",
    "Number of Wells",
    "CG Ratio",
    "PSA Cost [$/kg]",
    "Predicted RF [-]",
]

# # Regex pattern to extract metadata from filename
# FILENAME_PATTERN = r"optimal_plan_CL(\d+)_TWh(\d+)_ *(Low|Med|High)_H2(\d+(?:\.\d+)?)"

# # Initialize container for all data
# all_data = []

# # Iterate through all Excel files
# for fname in os.listdir(FOLDER_PATH):
#     if not fname.endswith(".xlsx"):
#         continue

#     match = re.search(FILENAME_PATTERN, fname)
#     if not match:
#         print(f"Skipping unrecognized file format: {fname}")
#         continue

#     # Extract metadata from filename
#     cl = int(match.group(1))
#     twh = int(match.group(2))
#     psa_level = match.group(3)
#     h2_cost = float(match.group(4))

#     # Read the last sheet only
#     full_path = os.path.join(FOLDER_PATH, fname)
#     try:
#         sheet_names = pd.ExcelFile(full_path).sheet_names
#         last_sheet = sheet_names[-1]
#         df = pd.read_excel(full_path, sheet_name=last_sheet)
#     except Exception as e:
#         print(f"Error reading {fname}: {e}")
#         continue

#     # Filter required columns and append metadata
#     if not all(col in df.columns for col in COLS_TO_KEEP):
#         print(f"Missing columns in {fname}, skipping.")
#         continue   
    

    
#     w = pd.to_numeric(df["Cum H2 Produced [Twh]"], errors="coerce").fillna(0.0)
#     if w.sum() == 0:
#         w = pd.Series(np.ones(len(df)), index=df.index)

#     lcos = pd.to_numeric(df["LCOS"], errors="coerce")
#     perm = pd.to_numeric(df["Permeability [mD]"], errors="coerce")
#     cg   = pd.to_numeric(df["CG Ratio"],   errors="coerce")
#     PSA_cost = pd.to_numeric(df["PSA Cost [$/kg]"], errors="coerce")
#     RF = pd.to_numeric(df["Predicted RF [-]"], errors="coerce")
#     Res_pressure = pd.to_numeric(df["Reservoir Pressure[bar]"], errors="coerce")
#     Porosity = pd.to_numeric(df.get("Porosity [-]"), errors="coerce")
#     well_no = np.sum(pd.to_numeric(df["Number of Wells"], errors="coerce"))
#     lcos=(lcos * w).sum() / w.sum()
#     perm=(perm * w).sum() / w.sum()
#     cg=(cg * w).sum() / w.sum()
#     PSA_cost=(PSA_cost * w).sum() / w.sum()
#     RF=(RF * w).sum() / w.sum()
#     Res_pressure=(Res_pressure * w).sum() / w.sum()
#     Porosity=(Porosity * w).sum() / w.sum()
#     df_filtered = pd.DataFrame()
#     df_filtered["LCOS"] = [lcos]
#     df_filtered["Cycle Length"] = [cl]
#     df_filtered["Permeability_mD"] = [perm]
#     df_filtered["CG_Ratio"] = [cg]
#     df_filtered["H2_Cost_per_kg"] = [h2_cost]
#     df_filtered["PSA_Cost"] = [PSA_cost]
#     df_filtered["Predicted_RF"] = [RF]
#     df_filtered["Reservoir_Pressure"] = [Res_pressure]
#     df_filtered["Porosity"] = [Porosity]
#     df_filtered["Wells No."] = [well_no]
#     df_filtered["H2_Target_TWh"] = [twh]
#     df_filtered["Source_File"] = [fname]
    
#     all_data.append(df_filtered)

# # Combine into single DataFrame
# final_df = pd.concat(all_data, ignore_index=True)
coutour_map(FOLDER_PATH)
# plot_bubble_chart(final_df)
# plot_bubble_chart_rf(final_df)
# plot_bubble_size_legend_lcos()
# final_df.to_csv("compiled_optimal_data.csv", index=False)
print("Data extraction complete. Final dataset shape:", final_df.shape)
