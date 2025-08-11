import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import warnings
# Extract simulation parameters from the filename
def extract_simulation_params_from_filename(filename):
    # The filename should follow the format: "CushionGas-FlowRate-CycleLength-Permeability-InjectionInterval.json"
    parts = filename.split('-')
    if len(parts) != 5:
        warnings.warn(f"Filename {filename} doesn't match the expected format")
        return None

    CushionGasType = parts[0]  # e.g., CO2
    FlowRate = float(parts[1])  # e.g., 1e5
    CycleLength = int(parts[2])  # e.g., 14
    Permeability = int(parts[3])  # e.g., 100
    pressure = int(parts[4].split('.')[0])  # e.g., 10

    # Assuming the injection and withdrawal durations are derived from cycle length
    InjectionDurationDev = CycleLength / 2  # Assuming equal durations for injection and withdrawal
    InjectionDurationOp = InjectionDurationDev
    ExtractionDurationOp = InjectionDurationDev

    # Create a dictionary with these parameters
    params = {
        'CushionGasType': CushionGasType,
        'FlowRate': FlowRate,
        'CycleLength': CycleLength,
        'Permeability': Permeability,
        'Pressure': pressure,
        'InjectionDurationDev': InjectionDurationDev,
        'InjectionDurationOp': InjectionDurationOp,
        'ExtractionDurationOp': ExtractionDurationOp,
        'name': filename  
    }

    return params

class CycleData:
    def __init__(self, EndofWithdrawal, EndofInjection):
        self.EndofWithdrawal = EndofWithdrawal
        self.EndofInjection = EndofInjection

# Load the data from the JSON file
def load_data(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data

# Convert time to days (assuming time is in seconds)
def convert_time_to_days(time_in_seconds):
    return np.array(time_in_seconds) / 86400  # 1 day = 86400 seconds

# Calculate Recovery Factor (RF)
def calculate_rf(values_inj_dt, values_prod_dt, cycle_data):
    rf_values = []
    cumulative_inj = np.zeros(len(values_inj_dt) + 1)
    cumulative_prod = np.zeros(len(values_prod_dt) + 1)
    
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

    # Filter the lines to be plotted
    filtered = [(rf, label) for rf, label in zip(rf_values, labels) if "0-60" in label and "-1e5-" in label and "-100-" in label]
    # filtered = [(rf, label) for rf, label in zip(rf_values, labels)]
    # Get color map and evenly spaced colors
    cmap = cm.get_cmap('RdBu_r', len(filtered))  # Use as many distinct colors as lines

    for idx, (rf, label) in enumerate(filtered):
        color = cmap(idx)
        plt.plot(range(1, len(rf) + 1), rf, label=label, color=color)

    plt.xlabel('Cycle No. [-]', fontsize=18)
    plt.ylabel('Recovery Factor', fontsize=18)
    plt.title('Recovery Factor vs Time (colored by RdBu_r)', fontsize=18)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    
from collections import defaultdict

def plot_rf_vs_param_grouped(input_directory, x_param='FlowRate', group_by='Permeability'):
    grouped = defaultdict(list)

    # Gather data
    json_files = [f for f in os.listdir(input_directory) if f.endswith('.json')]
    filtered = [js for js in json_files if "-180-" in js and "0-300" in js]  # Filter for specific files
    for json_file in filtered:
        try:
            params = extract_simulation_params_from_filename(json_file)
            if params is None:
                continue
            data = load_data(os.path.join(input_directory, json_file))
            time_seconds = data["time"]
            values_inj_dt = data["InjectionValues_dt"]
            values_prod_dt = data["ProductionValues_dt"]
            cycle_data = cycles(params, time_seconds)
            rf = calculate_rf(np.array(values_inj_dt["H2"]), np.array(values_prod_dt["H2"]), cycle_data)

            if len(rf) == 0:
                continue

            key = params[group_by]
            x_value = params[x_param]
            rf_final = rf[-1]

            grouped[key].append((x_value, rf_final))

        except Exception as e:
            print(f"Skipping {json_file} due to error: {e}")

    # Plotting
    plt.figure(figsize=(9, 6))
    cmap = plt.cm.get_cmap('tab10')  # Use a distinct colormap
    for i, (perm, values) in enumerate(sorted(grouped.items())):
        values.sort()  # Sort by x_param
        x_vals, rf_vals = zip(*values)
        plt.plot(x_vals, rf_vals, marker='o', label=f'{group_by} = {perm}', color=cmap(i % 10))

    plt.xlabel(x_param, fontsize=18)
    plt.ylabel('RF @ 10th Cycle', fontsize=18)
    # plt.title(f'Final RF vs {x_param}, grouped by {group_by}', fontsize=18)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
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
        if (time_seconds[ii] - (qq) * (1 * injection_duration_op) >= 0):
            if qq % 2 == 0:
                EndofWithdrawal.append(ii)
            if qq % 2 == 1:
                EndofInjection.append(ii)
            qq += 1  # Increment qq
    EndofWithdrawal.append(len(time_seconds))
    
    return CycleData(EndofWithdrawal, EndofInjection)

# Main function to load data, calculate RF, and plot the results
def main(input_directory):
    rf_values = []
    labels = []

    # List all JSON files in the directory
    json_files = [f for f in os.listdir(input_directory) if f.endswith('.json')]

    # Loop through each JSON file
    for json_file in json_files:
        # Extract simulation parameters from the JSON filename
        params = extract_simulation_params_from_filename(json_file)
        if params is None:
            continue
        # Load data from the corresponding JSON file
        data = load_data(os.path.join(input_directory, json_file))

        # Extract the time, values_inj_dt, and values_prod_dt from the data
        time_seconds = data["time"]
        values_inj_dt = data["InjectionValues_dt"]
        values_prod_dt = data["ProductionValues_dt"]

        # Convert time to days
        time_days = convert_time_to_days(time_seconds)
        
        # Calculate the Recovery Factor (RF) for this set of data
        cycle_data = cycles(params, time_seconds)
        rf = calculate_rf(np.array(values_inj_dt["H2"]), np.array(values_prod_dt["H2"]), cycle_data)
        if not rf.any():
            AA = 1
        # Store the RF value and the corresponding simulation name (JSON file name)
        rf_values.append(rf)
        labels.append(params['name'])  # Use the cushion gas type as the label
    combined = sorted(zip(rf_values, labels), key=lambda x: x[0][-1])
    rf_values_sorted, labels_sorted = zip(*combined)    
    # Plot the Recovery Factor vs Time for all simulations
    # plot_rf(rf_values_sorted, labels_sorted)
    plot_rf_vs_param_grouped(input_directory, x_param='FlowRate', group_by='Permeability') 

# Example usage
os.chdir("Y:\\Mixing Results\\July\\H2") 
# os.chdir("Y:\\Mixing Results\\New May\\CH4")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory)
