import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from scipy.interpolate import interp1d
import warnings
import average_velocity
import matplotlib.colors as mcolors
from sklearn_extra.cluster import KMedoids
from CoolProp.CoolProp import PropsSI
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error
import plotly.graph_objects as go
base_input_dir = r"Y:\Mixing Results\July"
os.chdir(base_input_dir) 
input_directory = os.getcwd() 
file_path = os.path.join(input_directory, 'mixing_results_plot.xlsx')
df = pd.read_excel(file_path)



# Select and convert the necessary columns to numeric
columns = [
    "RF_final",
    "Pe",
    "Ng",
    "Fo",
    "theta",
    "CycleLength",
    "FlowRate",
    "Permeability",
    "porosity",
    "Pressure",
    "Temperature",
    "delta_rho",
    "CushionGas",
    "max_pressure",
]
df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors='coerce')

# df_clean = df.dropna(subset=columns).reset_index(drop=True)


RF_values = []
Pe_values = []
Ng_values = []
theta_values = []
Fo_values = []
phi_values = []
for ii in range(len(df)):
    if df['RF_final'].iloc[ii] > 0:
        RF_values.append(df['RF_final'].iloc[ii])
        Pe_values.append(df['Pe'].iloc[ii])
        Ng_values.append(df['Ng'].iloc[ii])
        theta_values.append(df['theta'].iloc[ii])
        Fo_values.append(df['Fo'].iloc[ii])
        phi_values.append(df['porosity'].iloc[ii])
theta_values = np.array(theta_values)
Fo_values = np.array(Fo_values)
RF_values = np.array(RF_values)
Pe_values = np.array(Pe_values) 
Ng_values = np.array(Ng_values) * theta_values 





################################################################################  Pe vs Ng


# Pe = np.log10(Pe_values)
# Ng = np.log10(Ng_values)
Pe = Pe_values
Ng = Ng_values

x, y, z = Pe, Ng, RF_values
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay
# Build a regular grid
xi = np.linspace(min(x), max(x), 250)
yi = np.linspace(min(y), max(y), 250)
Xi, Yi = np.meshgrid(xi, yi)
z = np.clip(RF_values, 0, 1)  # ensure physical range if needed
tri = Delaunay(np.column_stack([x, y]))
lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
Zi = lin(Xi, Yi)
mask = np.isnan(Zi)
Zi_smooth = Zi.copy()
Zi_smooth2 = Zi.copy()
Zi_smooth[~mask] = gaussian_filter(Zi[~mask], sigma=0)

# ---- 3) Plotly contour with built-in smoothing ----
# Note: contours.smoothing ranges 0 → 1 (higher = smoother isolines)
fig = go.Figure(
    data=go.Contour(
        x=xi, y=yi, z=Zi,
        contours=dict(
            start=float(np.nanmin(Zi)),
            end=float(np.nanmax(Zi)),
            size=(np.nanmax(Zi)-np.nanmin(Zi))/8,
            coloring="fill",
            showlines=True,
            
        ),
        colorbar=dict(title="Z"),
        # connectgaps=True,   # helps avoid breaks near former NaNs
        line_smoothing=1,  # smooth contour lines
        line=dict(width=1),  # contour line width
        contours_coloring='heatmap'
    )
)

fig.update_layout(
    title="Filled Contour (Plotly) with Smoothing",
    xaxis_title="Pe",
    yaxis_title="Ng",
    width=800,
    height=650
)

# ---- 4) Quick UI to tweak smoothing live ----
buttons = []
for s in [0.0, 0.35, 0.65, 0.9]:
    buttons.append(dict(
        label=f"smoothing={s}",
        method="restyle",
        args=[{"contours.smoothing": [s]}]
    ))

fig.update_layout(
    updatemenus=[dict(
        type="buttons",
        x=1.05, y=1.0,
        xanchor="left",
        buttons=buttons,
        showactive=True
    )]
)

fig.show()







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
print(min(Pe), max(Pe))
ax[0].set_xlabel(r"Pe [-]", fontsize=18)
ax[0].set_ylabel("Ng [-]", fontsize=18)
ax[0].tick_params(axis='x', labelsize=18)
ax[0].tick_params(axis='y', labelsize=18)
ax[0].legend(loc='best', frameon=True, fontsize=12)
ax[0].set_xlim([2.5, max(Pe)])

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
