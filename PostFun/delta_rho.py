import matplotlib.pyplot as plt
import numpy as np
import CoolProp.CoolProp as cp
import pandas as pd
import os

csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"
df = pd.read_csv(csv_path)

# === 2. Select and Convert Required Columns ===
columns_needed = ["Permeability [mD]", "Reservoir Pressure[MPa]", "Reservoir Temp [C]", "Porosity [-]"]
df[columns_needed] = df[columns_needed].apply(pd.to_numeric, errors='coerce')
df = df.dropna(subset=columns_needed).reset_index(drop=True)

# Define pressure and temperature ranges
pressures = np.linspace(50e5, 450e5, 100)  # Pa
temperatures = [20,30, 40,50, 60, 80, 100, 120]  # Celsius

# Define gases
gases = ['CO2', 'N2', 'H2', 'CH4']

# Prepare figure
fig, axs = plt.subplots(2, 2, figsize=(14, 10))
axs = axs.flatten()

# Plot density profiles for each gas
for i, gas in enumerate(gases):
    ax = axs[i]
    for T_C in temperatures:
        rho = []
        for P in pressures:
            try:
                r = cp.PropsSI('D', 'P', P, 'T', T_C + 273.15, gas)
            except:
                r = np.nan
            rho.append(r)
        ax.plot(pressures / 1e5, rho, label=f'{T_C} °C')  # pressure in bar

    ax.set_title(f'Density of {gas}')
    ax.set_xlabel('Pressure [bar]')
    ax.set_ylabel('Density [kg/m³]')
    ax.grid(True)
    ax.legend(title='Temperature')
    ax.set_ylim(bottom=0)

plt.tight_layout()
plt.show()


import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import CoolProp.CoolProp as cp

# Define fluid and ranges
fluid = 'H2'
T_vals = np.linspace(293.15, 393.15, 500)
P_vals = np.linspace(50e5, 450e5, 500)
T_grid, P_grid = np.meshgrid(T_vals, P_vals)

# Prepare phase grid
phase_grid = np.empty(T_grid.shape, dtype='U30')
for i in range(T_grid.shape[0]):
    for j in range(T_grid.shape[1]):
        T = T_grid[i, j]
        P = P_grid[i, j]
        try:
            phase = cp.PhaseSI('T', T, 'P', P, fluid)
            phase_grid[i, j] = phase
        except:
            phase_grid[i, j] = 'error'

# Phase mapping
phase_map = {
    'gas': 0,
    'liquid': 1,
    'two-phase': 2,
    'supercritical_liquid': 3,
    'supercritical_gas': 4,
    'supercritical': 5
}
colors = ['powderblue', 'lightcoral', 'lightgreen', 'violet', 'bisque', 'steelblue']
labels = ['Gas', 'Liquid', 'Two-phase', 'Supercritical Liquid', 'Supercritical Gas', 'supercritical']
int_grid = np.vectorize(lambda x: phase_map.get(x.lower(), 5))(phase_grid)

# Create custom colormap and norm with exact bin edges
cmap = ListedColormap(colors)
boundaries = np.arange(-0.5, len(colors))  # [-0.5, 0.5, 1.5, ..., 5.5]
norm = BoundaryNorm(boundaries, cmap.N)

# Plot
plt.figure(figsize=(10, 6))
plt.imshow(int_grid, origin='lower', aspect='auto',
           extent=[T_vals.min(), T_vals.max(), P_vals.min()/1e5, P_vals.max()/1e5],
           cmap=cmap, norm=norm)

# Legend
handles = [Patch(color=colors[i], label=labels[i]) for i in range(len(labels))]
# plt.legend(handles=handles, loc='upper left')
plt.scatter(
    df["Reservoir Temp [C]"] + 273.15,
    df["Reservoir Pressure[MPa]"] * 10,
    color='black',
    alpha=0.8,
    label='Field Data'
)
plt.title('H2 Phase Regions')
plt.xlabel('Temperature [K]')
plt.ylabel('Pressure [bar]')
plt.grid(True)
plt.show()



