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
# Extract simulation parameters from the filename
def Diffusion(pressure, GasType):
    if GasType == 'H2':
        Diffusion = 3.4831e-07
        # if pressure == 300:
        #     Diffusion = 1.3072e-7
        # if pressure == 150:
        #     Diffusion = 2.6160e-7
        # if pressure == 60:
        #     Diffusion = 6.526e-7    
    if GasType == 'CH4':
        Diffusion = 1.5324e-07
        # if pressure == 300:
        #     Diffusion = 5.7788e-8
        # if pressure == 150:
        #     Diffusion = 1.1362e-7
        # if pressure == 60:
        #     Diffusion = 2.8831e-7   
    if GasType == 'CO2':
        Diffusion = 1.4056e-07
        # if pressure == 300:
        #     Diffusion = 5.24e-8
        # if pressure == 150:
        #     Diffusion = 1.0478e-7
        # if pressure == 60:
        #     Diffusion = 2.6451e-7   
    if GasType == 'N2':
        Diffusion = 1.6933e-07
        # if pressure == 300:
        #     Diffusion = 6.3615e-8
        # if pressure == 150:
        #     Diffusion = 1.2638e-7
        # if pressure == 60:
        #     Diffusion = 3.18e-7 
    return Diffusion 
def has_zero_int_part(value):
    return str(value).endswith("0")                            
def extract_simulation_params_from_filename(filename):
    # The filename should follow the format: "CushionGas-FlowRate-CycleLength-Permeability-InjectionInterval.json"
    parts = filename.split('-')
    if len(parts) != 5:
        raise ValueError(f"Filename {filename} doesn't match the expected format")

    CushionGasType = parts[0]  # e.g., CO2
    FlowRate = float(parts[1])  # e.g., 1e5
    CycleLength = int(parts[2])  # e.g., 14
    Permeability = int(parts[3])  # e.g., 100
    pressure = int(parts[4].split('.')[0])  # e.g., 100
     
    # InjectionInterval = int(parts[4].split('.')[0])  # e.g., 10

    # Assuming the injection and withdrawal durations are derived from cycle length
    InjectionDurationDev = 0.0  # Assuming equal durations for injection and withdrawal
    InjectionDurationOp = CycleLength / 2
    ExtractionDurationOp = CycleLength / 2 

    # Create a dictionary with these parameters
    params = {
        'CushionGasType': CushionGasType,
        'FlowRate': FlowRate,
        'CycleLength': CycleLength,
        'Permeability': Permeability,
        'pressure': pressure,
        'InjectionDurationDev': InjectionDurationDev,
        'InjectionDurationOp': InjectionDurationOp,
        'ExtractionDurationOp': ExtractionDurationOp,
        'name': filename ,
    }

    return params
def load_data(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class CycleData:
    def __init__(self, EndofWithdrawal, EndofInjection):
        self.EndofWithdrawal = EndofWithdrawal
        self.EndofInjection = EndofInjection
# Convert time to days (assuming time is in seconds)
def convert_time_to_days(time_in_seconds):
    return np.array(time_in_seconds) / 86400  # 1 day = 86400 seconds        
# Calculate Recovery Factor (RF)
def calculate_rf(values_inj_dt, values_prod_dt, cycle_data):
    rf_values = []
    cumulative_inj = np.zeros(len(values_inj_dt) + 1)
    cumulative_prod = np.zeros(len(values_prod_dt) + 1)
    qq = 1
    # Calculate the cumulative sum for injection and production values up to each time step
    for i in range(1, len(values_inj_dt) + 1):  
        cumulative_inj[i] = np.sum(values_inj_dt[:i])
        cumulative_prod[i] = np.sum(values_prod_dt[:i])

    
    # Calculate RF for each end of withdrawal period
    for i in cycle_data.EndofWithdrawal:
        rf_step = abs(cumulative_prod[i]) / abs(cumulative_inj[i]) if cumulative_inj[i] != 0 else 0
        rf_values.append(rf_step)

    return np.array(rf_values)

# Plot the Recovery Factor (RF) vs Time
def plot_rf(rf_values, labels):
    plt.figure(figsize=(10, 6))

    # Plot each RF curve with a different label (simulation name)
    for rf, label in zip(rf_values, labels):
        plt.plot(range(1, len(rf) + 1), rf, label=label)

    plt.xlabel('Cycle No. [-]', fontsize=18)
    plt.ylabel('Recovery Factor', fontsize=18)
    plt.title('Recovery Factor vs Time', fontsize=18)
    plt.legend()
    plt.grid(True)
    plt.show()

def cycles(params, time_seconds):
    EndofWithdrawal = []
    EndofInjection = []
    qq = 1
    mm = 0
    injection_duration_dev = params['InjectionDurationDev'] * 86400  # Convert to seconds
    # injection_duration_dev = 0  # Convert to seconds
    injection_duration_op = params['InjectionDurationOp'] * 86400  # Convert to seconds
    extraction_duration_op = params['ExtractionDurationOp'] * 86400  # Convert to seconds
    
    for ii in range(len(time_seconds)):
        if (time_seconds[ii] - (qq) * (1 * injection_duration_op) - injection_duration_dev >= 0):
            if qq % 2 == 0:
                EndofWithdrawal.append(ii)
            if qq % 2 == 1:
                EndofInjection.append(ii)
            qq += 1  # Increment qq
    EndofWithdrawal.append(len(time_seconds))
    
    return CycleData(EndofWithdrawal, EndofInjection)


def get_velocity_from_json(json_files, target_label, input_directory,Cycle_No):
    # Make sure json_files is a list
    if isinstance(json_files, str):
        json_files = [json_files]
        
    target_label = os.path.splitext(os.path.basename(target_label))[0]
    
    for json_file in json_files:
        json_path = os.path.join(input_directory, json_file)
        if not os.path.exists(json_path):
            continue  # Skip if the file doesn't exist

        with open(json_path, "r") as f:
            data = json.load(f)
        
        for entry in data:
            if entry["label"] == target_label:
                all_cycle_data = []
                for cycle_data in entry["injection_end_data"]:
                    all_cycle_data.append((
                        cycle_data.get("avg_vx"),
                        cycle_data.get("max_x_valid"),
                        cycle_data.get("simga_rz"),
                        cycle_data.get("tip_velocity"),
                        cycle_data.get("simga_rr"),
                        cycle_data.get("avg_vx_z"),
                        cycle_data.get("avg_vx_z_rev"),
                        cycle_data.get("avg_vx_x_H2"),
                        cycle_data.get("avg_vx_x_H2_rev"),
                        cycle_data.get("avg_mass_velocity"),
                        cycle_data.get("vx_inlet"),
                        cycle_data.get("height")
                    ))
                return all_cycle_data[Cycle_No]
    
    return None  # If not found in any file

def extract_all_params_sorted(input_directory, Cycle_No):
    results = []
    # height = 60.0 
    well_radius = 0.2
    well_height = 10
    GridSize = 3.0
    alpha_L = 3

    # JSON file loop
    json_files = [f for f in os.listdir(input_directory) if f.endswith('.json')]
    for json_file in json_files:
        try:
            # Extract parameters
            params = extract_simulation_params_from_filename(json_file)
            # if params['pressure'] > 150:
            #     continue
            data = load_data(os.path.join(input_directory, json_file))
            time_seconds = data["time"]
            values_inj_dt = np.array(data["InjectionValues_dt"]["H2"])
            values_prod_dt = np.array(data["ProductionValues_dt"]["H2"])
            cycle_data = cycles(params, time_seconds)
            rf = calculate_rf(values_inj_dt, values_prod_dt, cycle_data)
            # Thermophysical properties
            H2_density = PropsSI("D", "P", params['pressure'] * 1e5, "T", 333.15, "Hydrogen")
            H2_viscosity = PropsSI("VISCOSITY", "P", params['pressure'] * 1e5, "T", 333.15, "Hydrogen")

            CG_density = PropsSI("D", "P", params['pressure'] * 1e5, "T", 333.15, params['CushionGasType'])
            CG_viscosity = PropsSI("VISCOSITY", "P", params['pressure'] * 1e5, "T", 333.15, params['CushionGasType'])
            if params['CushionGasType'] == 'H2':
                CG_density = H2_density
                CG_viscosity = H2_viscosity
            # Derived quantities
            if len(rf) < 10:
                rf = np.zeros(10)  # Ensure rf has at least 10 elements
                warnings.warn("RF too short, skipping: " + json_file)
                results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'Pressure': params['pressure'],
                'Pe': 0.0,
                'Ng': 0.0,
                'RF_1': rf[0],
                'RF_5': rf[4],
                'RF_final': rf[Cycle_No],
                'delta_rho': CG_density - H2_density,
                })
                continue
            mass_rate = params['FlowRate'] * 0.041e3 / 86400
            perm = params['Permeability'] * 9.869233e-16
            folder_tag = os.path.basename(input_directory)
            filename = {f"{folder_tag}.json", f"{folder_tag}-June.json"}
            # filename = "_all_injection_ends.json"
            velocity, Length, sigma_rz, tip_velocity, sigma_rr, avg_vx_z, avg_vx_z_rev, avg_vx_x_H2, avg_vx_x_H2_rev, avg_mass_velocity, vx_inlet, height = get_velocity_from_json(filename, json_file,input_directory,Cycle_No)
            # velocity = mass_rate / (H2_density / 2e-3)
            porosity = 0.3
            pore_velocity = velocity / porosity
            # pore_velocity = vx_inlet / porosity
            # Length = (Cycle_No + 1) * 2 * Length
            diffusion = Diffusion(params['pressure'], params['CushionGasType'])
            # Peclet_number = (pore_velocity * Length) / (diffusion)
            Peclet_number = (pore_velocity * Length) / (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400/2))
            if Peclet_number < 0:
                warnings.warn(f"Peclet number is negative for {json_file}, skipping.")
                continue
            theta = (H2_density) / (CG_density)
            t_D = (params['CycleLength'] * 86400) * (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400)) / (height ** 2)
            AR = Length / height
            # theta = np.abs(CG_density - H2_density) 
            # Buoyancy_number = (np.sqrt(perm/10) * (CG_density - H2_density) * 9.81 * height) / (H2_viscosity * pore_velocity)
            Buoyancy_number = ((perm/10) * (CG_density - H2_density) * 9.81 * Length) / (CG_viscosity * pore_velocity * height)
            # Buoyancy_number = ((perm) * (CG_density - H2_density) * 9.81 * height) / (CG_viscosity * pore_velocity * Length )
            
            # Buoyancy_number = ((perm) * (CG_density - H2_density) * 9.81) / (H2_viscosity * (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400)) )
            
            Nusselt_number = (avg_mass_velocity * height) / (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400) * (CG_density - H2_density) )
            Raileigh_number = (CG_density - H2_density) * 9.81 * height * (perm/10) / ((diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400))  * H2_viscosity)
            Raileigh_number = Raileigh_number 
            Peclet_number = Peclet_number
            Buoyancy_number =Buoyancy_number / Peclet_number
            results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'Pressure': params['pressure'],
                'Pe': Peclet_number,
                'Ng': Buoyancy_number,
                'RF_final': rf[Cycle_No],
                'RF_1': rf[0],
                'RF_5': rf[4],
                'Nusselt_number': Nusselt_number,
                'Raileigh_number': Raileigh_number,
                'delta_rho': CG_density - H2_density,
                'theta': theta,
                'tD': t_D,
                'AR': AR,
            })

        except Exception as e:
            warnings.warn(f"Skipping {json_file} due to error: {e}")
            continue

    # Sort by RF_final
    results.sort(key=lambda x: x['RF_final'])

    return results
def save_results_to_excel(results, output_path='mixing_results.xlsx'):
    # Add CushionGas field based on label
    for res in results:
        res['CushionGas'] = res['label'].split('-')[0]

    # Remove full RF list to simplify Excel output
    simplified_results = [
        {k: v for k, v in res.items() if k != 'RF'} for res in results
    ]

    # Convert to DataFrame
    df = pd.DataFrame(simplified_results)

    # Write to Excel with separate sheets by cushion gas
    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name='AllResults', index=False)
        # for gas, group in df.groupby('CushionGas'):
        #     group.to_excel(writer, sheet_name=gas, index=False)

    print(f"Results saved to '{output_path}' with sheets for each cushion gas.")


# base_input_dir = r"Y:\Mixing Results\New May"
base_input_dir = r"Y:\Mixing Results\July"
gas_types = ["H2", "CH4", "CO2", "N2"]
# gas_types = ["H2", "CH4","CO2"]
# === Accumulate All Results Across Gases ===
all_RF_List = []
RF_values = []
Cycle_No = 9

cycle_RF_list = []
for gas in gas_types:
    gas_dir = os.path.join(base_input_dir, gas)
    if not os.path.exists(gas_dir):
        print(f"Skipping missing folder: {gas_dir}")
        continue
    os.chdir(gas_dir) 
    input_directory = os.getcwd() 
 
    rf_list = extract_all_params_sorted(gas_dir, Cycle_No)
    all_RF_List.extend(rf_list)


os.chdir(base_input_dir) 
input_directory = os.getcwd() 
all_RF_List.sort(key=lambda x: x['RF_final'])
save_results_to_excel(all_RF_List, input_directory + '\\mixing_results.xlsx')
# === Extract Combined Parameters ===
RF_values = [
    item['RF_final'] for item in all_RF_List
    if (item['RF_final'][0] if isinstance(item['RF_final'], tuple) else item['RF_final']) != 0
]
Pe_values = np.array([
    item['Pe'][0] if isinstance(item['Pe'], tuple) else item['Pe']
    for item in all_RF_List
    if item['RF_final'] != 0
])
Ng_values = np.array([
    item['Ng'][0] if isinstance(item['Ng'], tuple) else item['Ng']
    for item in all_RF_List
    if item['RF_final'] != 0
])
Nusselt_number = [
    item['Nusselt_number'][0] if isinstance(item['Nusselt_number'], tuple) else item['Nusselt_number']
    for item in all_RF_List
    if item['RF_final'] != 0
]
Raileigh_number = [
    item['Raileigh_number'][0] if isinstance(item['Raileigh_number'], tuple) else item['Raileigh_number']
    for item in all_RF_List
    if item['RF_final'] != 0
]
tD_values = [
    item['tD'][0] if isinstance(item['tD'], tuple) else item['tD']
    for item in all_RF_List
    if item['RF_final'] != 0
]
AR_values = [
    item['AR'][0] if isinstance(item['AR'], tuple) else item['AR']
    for item in all_RF_List
    if item['RF_final'] != 0
]
################################################################################  Pe vs Ng


# Pe = np.log10(Pe_values)
# Ng = np.log10(Ng_values)
Pe = Pe_values
Ng = Ng_values
fig, ax = plt.subplots(1, 3, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
# 1) Filled contour
levels = 10
contour = ax[0].tricontourf(
    Pe,
    Ng,
    RF_values,
    levels=levels,
    cmap='plasma'
)
# sc = ax[0].scatter(Pe, Ng, c=RF_values, cmap='gist_yarg', edgecolor='k')
ax[0].set_xlabel(r"Pe [-]", fontsize=18)
ax[0].set_ylabel("Ng [-]", fontsize=18)
ax[0].tick_params(axis='x', labelsize=18)
ax[0].tick_params(axis='y', labelsize=18)
# 2) Add contour lines at the same levels
#    You can supply the same 'levels' array or let matplotlib pick automatically.
# lines = ax[0].tricontour(
#     Pe,
#     Ng,
#     RF_values,
#     levels=levels,
#     colors='magenta',      # black lines
#     linewidths=1.5   # thinner lines for clarity
# )
# ax[0].clabel(lines, inline=True, manual=True, fontsize=14, fmt="%.2f")

# 3) Scatter plots
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
cbar = plt.colorbar(contour, ax=ax[2])
cbar.ax.tick_params(labelsize=18)
cbar.set_label("Recovery Factor [-]", fontsize=18)
plt.tight_layout()
plt.show()


################################################################################  Pe vs td


# Pe = np.log10(Pe_values)
# Ng = np.log10(Ng_values)
Pe = Pe_values
AR = AR_values
fig, ax = plt.subplots(1, 3, figsize=(12, 6))
fig.subplots_adjust(wspace=0.1)
# 1) Filled contour
levels = 10
contour = ax[0].tricontourf(
    Pe,
    AR,
    RF_values,
    levels=levels,
    cmap='gist_yarg'
)
# cbar = plt.colorbar(contour, ax=ax[0], pad = 0.3)
# cbar.set_label("RF", fontsize=12)
# ax[0].set_xlabel(r"$\theta \, Pe$ [-]", fontsize=18)
ax[0].set_xlabel(r"Pe [-]", fontsize=18)
ax[0].set_ylabel("AR [-]", fontsize=18)
ax[0].tick_params(axis='x', labelsize=18)
ax[0].tick_params(axis='y', labelsize=18)
# 2) Add contour lines at the same levels
#    You can supply the same 'levels' array or let matplotlib pick automatically.
# lines = ax[0].tricontour(
#     Pe,
#     Ng,
#     RF_values,
#     levels=levels,
#     colors='magenta',      # black lines
#     linewidths=1.5   # thinner lines for clarity
# )
# ax[0].clabel(lines, inline=True, manual=True, fontsize=14, fmt="%.2f")

# 3) Scatter plots
scatter = ax[1].scatter(
    Pe,
    RF_values,
    c=RF_values,
    cmap='gist_yarg',
    edgecolor='k'
)
ax[1].set_xlabel(r"Pe [-]", fontsize=18)
ax[1].set_ylabel("RF [-]", fontsize=18)
ax[1].tick_params(axis='x', labelsize=18)
ax[1].tick_params(axis='y', labelsize=18)
scatter = ax[2].scatter(
    AR,
    RF_values,
    c=RF_values,
    cmap='binary',
    edgecolor='k'
)
ax[2].set_xlabel("AR [-]", fontsize=18)
ax[2].set_ylabel("RF [-]", fontsize=18)
ax[2].tick_params(axis='x', labelsize=18)
ax[2].tick_params(axis='y', labelsize=18)
cbar = plt.colorbar(contour, ax=ax[2])
cbar.ax.tick_params(labelsize=18)
cbar.set_label("Recovery Factor [-]", fontsize=18)
plt.tight_layout()
plt.show()