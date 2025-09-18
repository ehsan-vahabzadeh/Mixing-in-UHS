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
    if len(parts) != 8:
        raise ValueError(f"Filename {filename} doesn't match the expected format")

    CushionGasType = parts[0]  # e.g., CO2
    FlowRate = float(parts[1])  # e.g., 1e5
    CycleLength = int(parts[2])  # e.g., 14
    Permeability = float(parts[3])  # e.g., 100
    pressure = int(parts[4])  # e.g., 100
    temperature = int(parts[5])  # e.g., 100
    porosity = float(parts[6]) / 100  # e.g., 100
    CG = float(parts[7].replace('.json', '')) # e.g., 10
     
    # InjectionInterval = int(parts[4].split('.')[0])  # e.g., 10

    # Assuming the injection and withdrawal durations are derived from cycle length
    InjectionDurationDev = CG * CycleLength/2  # Assuming equal durations for injection and withdrawal
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
        'temperature': temperature,
        'porosity': porosity,
        'CG': CG
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
def calculate_rf(values_inj_dt, values_prod_dt, cycle_data, End_of_CG):
    rf_values = []
    cumulative_inj = np.zeros(len(values_inj_dt) + 1)
    cumulative_prod = np.zeros(len(values_prod_dt) + 1)
    qq = 1
    # End_of_CG = 0
    # Calculate the cumulative sum for injection and production values up to each time step
    for i in range(End_of_CG, len(values_inj_dt) + 1):  
        cumulative_inj[i] = np.sum(values_inj_dt[End_of_CG:i])
        cumulative_prod[i] = np.sum(values_prod_dt[End_of_CG:i])

    
    # Calculate RF for each end of withdrawal period
    for i in cycle_data.EndofWithdrawal:
        rf_step = abs(cumulative_prod[i]) / abs(cumulative_inj[i]) if cumulative_inj[i] != 0 else 0
        rf_values.append(rf_step)

    return np.array(rf_values)
def isothermal_cf(P, T, gas, dP=1e5):
    """
    c_f = (1/rho)*(drho/dP)_T. Returns (c_f [1/Pa], rho [kg/m3], Z, method).
    """
    R = 8.31446261815324  # J/(mol*K)

    GASES = {
        "CO2": {"M": 44.0095e-3,  "Tc": 304.13,  "Pc": 7.3773e6, "omega": 0.225},
        "H2":  {"M": 2.01588e-3,  "Tc": 33.19,   "Pc": 1.293e6, "omega": -0.216},
        "N2":  {"M": 28.0134e-3,  "Tc": 126.2,   "Pc": 3.3958e6, "omega": 0.0372},
        "CH4": {"M": 16.04246e-3, "Tc": 190.56,  "Pc": 4.599e6, "omega": 0.011},
}
    g = GASES[gas]
    rho  = PropsSI('D', 'P', P,  'T', T, gas)
    Pm, Pp = max(P-dP, 100.0), P + dP
    rho_m  = PropsSI('D', 'P', Pm, 'T', T, gas)
    rho_p  = PropsSI('D', 'P', Pp, 'T', T, gas)
    drhodP = (rho_p - rho_m) / (Pp - Pm)
    Z = P * g["M"] / (rho * R * T)
    return (drhodP / rho), rho, Z, "CoolProp"
# Plot the Recovery Factor (RF) vs Time
def plot_rf(rf_values):
    plt.figure(figsize=(10, 6))
    RF_val = []
    avg_rf = np.array
    # Plot each RF curve with a different label (simulation name)
    for RF in rf_values:
        RF = RF['RF']
        if min(RF) != 0:
            plt.plot(range(1, len(RF) + 1), RF, color = 'gray', alpha=0.7)
            RF_val.append(RF)
    min_len = min(len(r) for r in RF_val)
    RF_mat = np.array([r[:min_len] for r in RF_val])
    avg_rf = RF_mat.mean(axis=0)
    plt.plot(range(1, len(avg_rf) + 1), avg_rf, color = 'blue', linewidth = 2)
    plt.xlabel('Cycle No. [-]', fontsize=18)
    plt.ylabel('Recovery Factor [-]', fontsize=18)
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)

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
                        cycle_data.get("height"),
                        cycle_data.get("max_pressure")
                    ))
                if len(all_cycle_data) < Cycle_No:
                    return all_cycle_data[len(all_cycle_data) - 1]  
                else:
                    return all_cycle_data[Cycle_No]
    
    return None  # If not found in any file

def extract_all_params_sorted(input_directory, Cycle_No):
    results = []
    well_radius = 0.2
    well_height = 10
    GridSize = 3.0
    alpha_L = 3

    # JSON file loop
    json_files = [f for f in os.listdir(input_directory) if f.endswith('.json')]
    for json_file in json_files:
        try:
            if (json_file == "N2-1303791-360-1329-79-307-17-0.0.json" or json_file == "CO2-1061584-337-1247-159-329-21-0.0.json" 
                or json_file == "CO2-1314854-304-1260-126-314-25-0.0.json" or json_file == "CO2-1416192-250-1275-180-337-16-0.0.json"
                or json_file == "CO2-1026081-346-401-121-305-15-0.0.json" or json_file == "CO2-1111641-327-1150-136-315-20-0.0.json"
                or json_file == "CO2-958200-282-1363-87-306-20-0.0.json" or json_file == "CO2-1228931-219-971-125-317-14-0.0.json"
                or json_file == "CO2-1367374-286-1388-182-324-15-0.0.json" or json_file == "CO2-1206093-248-1314-118-315-16-0.0.json"
                or json_file == "CO2-1253017-301-1123-111-307-18-0.0.json" or json_file == "CO2-1086203-313-1234-104-332-23-0.0.json"
                or json_file == "CO2-1161449-299-703-102-314-14-0.0.json" or json_file == "CO2-841540-356-1480-182-325-17-0.0.json"
                or json_file == "CO2-1086203-313-1234-104-332-23-0.0.json" or json_file == "CO2-1471295-273-1376-153-326-16-0.0.json"
                or json_file == "CH4-1269228-311-1113-81-306-17-0.0.json" or json_file == "CO2-1253017-301-1123-111-307-18-0.0.json"
                or json_file == "CO2-1302378-334-1196-177-343-27-0.0.json" or json_file == "CO2-1395683-141-1129-122-314-15-0.0.json"
                or json_file == "CO2-1322040-158-780-119-313-14-0.0.json" or json_file == "CO2-809334-280-1264-132-318-18-0.0.json"
                or json_file == "CO2-1341719-220-1209-108-312-23-0.0.json" or json_file == "CO2-1437024-309-995-154-327-18-0.0.json"
                or json_file == "CO2-1410720-307-1290-123-298-15-0.0.json" or json_file == "CO2-1158399-354-1109-121-312-18-0.0.json"):
                continue
                check = 1
            # Extract parameters
            params = extract_simulation_params_from_filename(json_file)
            # if params['pressure'] > 150:
            #     continue
            data = load_data(os.path.join(input_directory, json_file))
            time_seconds = data["time"]
            values_inj_dt = np.array(data["InjectionValues_dt"]["H2"])
            values_prod_dt = np.array(data["ProductionValues_dt"]["H2"])
            End_of_CG = 0
            for ii in range(len(data["time"])):
                if (data["time"][ii] > params['InjectionDurationDev'] * 86400 and params['CG'] > 0.0):
                    End_of_CG = ii
                    break
            cycle_data = cycles(params, time_seconds)
            rf = calculate_rf(values_inj_dt, values_prod_dt, cycle_data, End_of_CG)
            # Thermophysical properties
            H2_density = PropsSI("D", "P", params['pressure'] * 1e5, "T", params['temperature'], "Hydrogen")
            H2_viscosity = PropsSI("VISCOSITY", "P", params['pressure'] * 1e5, "T", params['temperature'], "Hydrogen")

            CG_density = PropsSI("D", "P", params['pressure'] * 1e5, "T", params['temperature'], params['CushionGasType'])
            CG_viscosity = PropsSI("VISCOSITY", "P", params['pressure'] * 1e5, "T", params['temperature'], params['CushionGasType'])
            
            CF_H2 = isothermal_cf(params['pressure'] * 1e5, params['temperature'], 'H2')[0]
            CF_CG = isothermal_cf(params['pressure'] * 1e5, params['temperature'], params['CushionGasType'])[0]
            if params['CushionGasType'] == 'H2':
                CG_density = H2_density
                CG_viscosity = H2_viscosity
            # Derived quantities
            porosity = params['porosity']
            
            mass_rate = params['FlowRate'] * 0.041e3 / 86400
            perm = params['Permeability'] * 9.869233e-16
            folder_tag = os.path.basename(input_directory)
            # filename = {f"{folder_tag}.json", f"{folder_tag}-June.json"}
            filename = f"{folder_tag}.json"
            velocity, Length, sigma_rz, tip_velocity, sigma_rr, avg_vx_z, avg_vx_z_rev, avg_vx_x_H2, avg_vx_x_H2_rev, avg_mass_velocity, vx_inlet, height, max_pressure = get_velocity_from_json(filename, json_file,input_directory,Cycle_No)
            if len(rf) < 10:
                rf = np.zeros(10)  # Ensure rf has at least 10 elements
                warnings.warn("RF too short, skipping: " + json_file)
                results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'porosity': params['porosity'],
                'Pressure': params['pressure'],
                'Temperature': params['temperature'],
                'Pe': 0.0,
                'Ng': 0.0,
                'theta': 0.0,
                'Fo': 0.0,
                'RF': rf,
                'RF_final': rf[Cycle_No],
                'Nusselt_number': 0.0,
                'Raileigh_number': 0.0,
                'delta_rho': CG_density - H2_density,
                'max_pressure':max_pressure
                })
                continue
            # velocity = mass_rate / (H2_density / 2e-3)
            pore_velocity = velocity / porosity 
            if max_pressure/1e5 > 1.5 * params['pressure']:
                rf = np.zeros(10)  # Ensure rf has at least 10 elements
                warnings.warn("RF too short, skipping: " + json_file)
                results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'porosity': porosity,
                'Pressure': params['pressure'],
                'Temperature': params['temperature'],
                'Pe': 0.0,
                'Ng': 0.0,
                'theta': 0.0,
                'Fo': 0.0,
                'RF': rf,
                'RF_final': rf[Cycle_No],
                'Nusselt_number': 0.0,
                'Raileigh_number': 0.0,
                'delta_rho': CG_density - H2_density,
                'max_pressure':max_pressure
                })
                continue
            # Length = (Cycle_No + 1) * 2 * Length
            
            diffusion = Diffusion(params['pressure'], params['CushionGasType'])
            # Peclet_number = (pore_velocity * Length) / (diffusion)
            Peclet_number = (pore_velocity * Length) / (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400/2))
            Fourier_number = ( pore_velocity * params['CycleLength']*86400/2) / (Length)
            theta = ((H2_density) / (CG_density)) * (CF_H2 / CF_CG)
            # theta = np.abs(CG_density - H2_density) 
            # Buoyancy_number = (np.sqrt(perm/10) * (CG_density - H2_density) * 9.81 * height) / (H2_viscosity * pore_velocity)
            Buoyancy_number = ((perm/10) * (CG_density - H2_density) * 9.81 * Length) / (H2_viscosity * pore_velocity * height * porosity)
            # Buoyancy_number = ((perm) * (CG_density - H2_density) * 9.81 * height) / (CG_viscosity * pore_velocity * Length * porosity)
            
            # Buoyancy_number = ((perm/10) * (CG_density - H2_density) * 9.81 *  params['CycleLength']) / (H2_viscosity * height * porosity * 10)
            
            Nusselt_number = (avg_mass_velocity * height) / (diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400) * (CG_density - H2_density) )
            Raileigh_number = (CG_density - H2_density) * 9.81 * height * (perm/10) / ((diffusion + 0.5 * sigma_rr/(params['CycleLength']*86400))  * H2_viscosity)
            Raileigh_number = Raileigh_number 
            Buoyancy_number = Buoyancy_number 
            Peclet_number = Peclet_number 
            results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'porosity': porosity,
                'Pressure': params['pressure'],
                'Temperature': params['temperature'],
                'delta_rho': CG_density - H2_density,
                'theta': theta,
                'Fo': Fourier_number,
                'RF': rf,
                'CG Ratio': params['CG'],
                'Pe': Peclet_number,
                'Ng': Buoyancy_number,
                'RF_final': rf[Cycle_No],
                'max_pressure':max_pressure
            })
            if Peclet_number < 0:
                warnings.warn(f"Peclet number is negative for {json_file}, skipping.")
                results.append({
                'label': params['name'],
                'FlowRate': params['FlowRate'],
                'CycleLength': params['CycleLength'],
                'Permeability': params['Permeability'],
                'Pressure': params['pressure'],
                'RF': rf,
                'RF_final': rf[Cycle_No],
                'delta_rho': CG_density - H2_density,
                'Pe': 0.0,
                'Ng': 0.0,
                'theta': 0.0,
                'Fo': 0.0,
                })
                continue

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

if __name__ != "__main__":
    import sys
    sys.exit()
# base_input_dir = r"Y:\Mixing Results\New May"
base_input_dir = r"Y:\Mixing Results\July"
# gas_types = ["H2","CO2","CH4", "N2"]
gas_types = ["H2-No CG","CO2","CH4", "N2"]
# gas_types = ["CH4"]
# === Accumulate All Results Across Gases ===
all_RF_List = []
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
    # plot_rf(rf_list)
    all_RF_List.extend(rf_list)


os.chdir(base_input_dir) 
input_directory = os.getcwd() 
all_RF_List.sort(key=lambda x: x['RF_final'])
# save_results_to_excel(all_RF_List, input_directory + '\\mixing_results_withoutCG.xlsx')
save_results_to_excel(all_RF_List, input_directory + '\\mixing_results_plot.xlsx')
# === Extract Combined Parameters ===
RF_values = []
Pe_values = []
Ng_values = []

for item in all_RF_List:
    rf_val = item['RF_final'][0] if isinstance(item['RF_final'], tuple) else item['RF_final']
    pe_val = item['Pe'][0] if isinstance(item['Pe'], tuple) else item['Pe']
    ng_val = item['Ng'][0] if isinstance(item['Ng'], tuple) else item['Ng']
    
    if rf_val > 0 and not np.isnan(pe_val) and pe_val > 0:
        RF_values.append(rf_val)
        Pe_values.append(pe_val)
        Ng_values.append(ng_val)

RF_values = np.array(RF_values)
Pe_values = np.array(Pe_values)
Ng_values = np.array(Ng_values)


################################################################################  Pe vs Ng


# Pe = np.log10(Pe_values)
# Ng = np.log10(Ng_values)
# Pe = Pe_values
# Ng = Ng_values
# fig, ax = plt.subplots(1, 3, figsize=(12, 6))
# fig.subplots_adjust(wspace=0.1)
# def RF_Ng_Pe(x,y, M):
#     return M[0] * np.power(x, M[1]) + M[2] * np.power(y, M[3])
# # Multipliers0 = [0.6069, 0.1270, -0.0404, 0.3488] # For case with porosity in NG equation
# # Multipliers0 = [0.6211, 0.1184, -0.08, 0.3270] # For case without porosity in NG equation
# Multipliers0 = [0.6378, 0.1091, -0.1662, 0.2951] # For case without porosity Ng/Pe
# y_pred = RF_Ng_Pe(Pe,Ng, Multipliers0)
# r2 = r2_score(RF_values, y_pred)
# rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
# # 1) Filled contour
# levels = 10
# colors = plt.cm.get_cmap('Greys',levels)
# plot = ax[0].tricontourf(
#     Pe,
#     Ng,
#     RF_values,
#     cmap='plasma',
#     levels=levels,
# )
# ax[0].plot([], [], ' ', 
#            label=rf'$RF = {Multipliers0[0]:.2f} \cdot Pe^{{{Multipliers0[1]:.2f}}} + {Multipliers0[2]:.2f} \cdot Ng^{{{Multipliers0[3]:.2f}}}$')
# ax[0].text(0.98, 0.02, f"$R^2$ = {r2:.2f}\nRMSE = {rmse:.2f}",
#             transform=ax[0].transAxes, ha='right', va='bottom', fontsize = 12,
#             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
# # plot = ax[0].scatter(
# #     Pe,
# #     Ng,
# #     c=RF_values,
# #     cmap='plasma',
# #     edgecolor='k'
# # )
# # cbar = plt.colorbar(contour, ax=ax[0], pad = 0.3)
# # cbar.set_label("RF", fontsize=12)
# # ax[0].set_xlabel(r"$\theta \, Pe$ [-]", fontsize=18)
# # ax[0].set_xscale('log')
# # ax[0].set_yscale('log')
# ax[0].set_xlabel(r"Pe [-]", fontsize=18)
# ax[0].set_ylabel("Ng [-]", fontsize=18)
# ax[0].tick_params(axis='x', labelsize=18)
# ax[0].tick_params(axis='y', labelsize=18)
# ax[0].legend(loc='best', frameon=True, fontsize=12)
# # 2) Add contour lines at the same levels
# #    You can supply the same 'levels' array or let matplotlib pick automatically.
# # lines = ax[0].tricontour(
# #     Pe,
# #     Ng,
# #     RF_values,
# #     levels=levels,
# #     colors='magenta',      # black lines
# #     linewidths=1.5   # thinner lines for clarity
# # )
# # ax[0].clabel(lines, inline=True, manual=True, fontsize=14, fmt="%.2f")

# # 3) Scatter plots
# def exp_fun(x, M):
#     return M[0] * np.exp( M[1] * x) + M[2]

# Multipliers = [-1.0046, -0.2070, 0.8869]
# y_pred = exp_fun(Pe, Multipliers)
# r2 = r2_score(RF_values, y_pred)
# rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
# scatter = ax[1].scatter(
#     Pe,
#     RF_values,
#     c=RF_values,
#     cmap='plasma',
#     edgecolor='k'
# )
# xs = np.linspace(Pe.min(), Pe.max(), 500)
# ax[1].plot(xs, exp_fun(xs, Multipliers), 'r-', lw=2,
#             label=rf'$RF = {Multipliers[0]:.2f} \cdot exp({Multipliers[1]:.2f} \cdot Pe) + {Multipliers[2]:.2f}$')
# ax[1].text(0.98, 0.02, f"$R^2$ = {r2:.2f}\nRMSE = {rmse:.2f}",
#             transform=ax[1].transAxes, ha='right', va='bottom', fontsize = 12,
#             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
# ax[1].set_xlabel(r"Pe [-]", fontsize=18)
# ax[1].set_ylabel("RF [-]", fontsize=18)
# ax[1].tick_params(axis='x', labelsize=18)
# ax[1].tick_params(axis='y', labelsize=18)
# ax[1].legend(loc='best', frameon=True, fontsize=12)
# scatter = ax[2].scatter(
#     Ng,
#     RF_values,
#     c=RF_values,
#     cmap='plasma',
#     edgecolor='k'
# )
# def ln_fun(x, M):
#     return M[0] * np.log((M[1] * x) + 1) + M[2]  
# # Multipliers2 = [-0.0932,0.3556,0.8587] # For case with porosity in NG equation
# # Multipliers2 = [-0.0864,2.526,0.8568] # For case without porosity in NG equation
# Multipliers2 = [-0.0780,28.0083,0.8544] # For case without porosity Ng/Pe in NG equation
# y_pred = ln_fun(Ng, Multipliers2)
# r2 = r2_score(RF_values, y_pred)
# rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
# ax[2].set_xlabel("Ng [-]", fontsize=18)
# ax[2].set_ylabel("RF [-]", fontsize=18)
# ax[2].tick_params(axis='x', labelsize=18)
# ax[2].tick_params(axis='y', labelsize=18)
# xs = np.linspace(Ng.min()+1e-6, Ng.max(), 500)
# ax[2].plot(xs, ln_fun(xs, Multipliers2), 'r-', lw=2,
#             label=rf'$RF = {Multipliers2[0]:.2f} \cdot log({Multipliers2[1]:.2f}\cdot Ng + 1) + {Multipliers2[2]:.2f}$')
# ax[2].text(0.98, 0.02, f"$R^2$ = {r2:.2f}\nRMSE = {rmse:.2f}",
#             transform=ax[2].transAxes, ha='right', va='bottom', fontsize = 12,
#             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
# ax[2].legend(loc='best', frameon=True, fontsize=12)
# cbar = plt.colorbar(scatter, ax=ax[2])
# cbar.ax.tick_params(labelsize=18)
# cbar.set_label("Recovery Factor [-]", fontsize=18)
# plt.tight_layout()
# plt.show()








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
xi = np.linspace(min(x), max(x), 200)
yi = np.linspace(min(y), max(y), 200)
Xi, Yi = np.meshgrid(xi, yi)
z = np.clip(RF_values, 0, 1)  # ensure physical range if needed
tri = Delaunay(np.column_stack([x, y]))
lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
Zi = lin(Xi, Yi)
mask = np.isnan(Zi)
Zi_smooth = Zi.copy()
Zi_smooth[~mask] = gaussian_filter(Zi[~mask], sigma=1)
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
ax[0].set_xlabel(r"Pe [-]", fontsize=18)
ax[0].set_ylabel("Ng [-]", fontsize=18)
ax[0].tick_params(axis='x', labelsize=18)
ax[0].tick_params(axis='y', labelsize=18)
ax[0].legend(loc='best', frameon=True, fontsize=12)


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
