import json
import matplotlib.pyplot as plt
import numpy as np
import os

# Extract simulation parameters from the filename
def extract_simulation_params_from_filename(filename):
    # The filename should follow the format: "CushionGas-FlowRate-CycleLength-Permeability-InjectionInterval.json"
    parts = filename.split('-')
    if len(parts) != 5:
        raise ValueError(f"Filename {filename} doesn't match the expected format")

    CushionGasType = parts[0]  # e.g., CO2
    FlowRate = float(parts[1])  # e.g., 1e5
    CycleLength = int(parts[2])  # e.g., 14
    Permeability = int(parts[3])  # e.g., 100
    InjectionInterval = int(parts[4].split('.')[0])  # e.g., 10

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
        'InjectionInterval': InjectionInterval,
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
    mm = 1
    injection_duration_dev = params['InjectionDurationDev'] * 86400  # Convert to seconds
    injection_duration_op = params['InjectionDurationOp'] * 86400  # Convert to seconds
    extraction_duration_op = params['ExtractionDurationOp'] * 86400  # Convert to seconds
    
    for ii in range(len(time_seconds)):
        if (time_seconds[ii] - (qq) * (2 * injection_duration_op) - injection_duration_dev >= 0):
            EndofWithdrawal.append(ii)
            qq += 1  # Increment qq
        
        if (time_seconds[ii] - (mm) * (injection_duration_op) - injection_duration_dev >= 0):
            EndofInjection.append(ii)
            mm += 1  # Increment mm
    
    return CycleData(EndofWithdrawal, EndofInjection)

# Main function to load data, calculate RF, and plot the results
def main(input_directory):
    rf_values = []
    labels = []

    # List all JSON files in the directory
    json_files = [f for f in os.listdir(input_directory) if f.endswith('.json')]

    # Sort files so that the one with grid size '1' comes first (as reference)
    json_files.sort()  # Optional if they are already ordered
    reference_file = None
    for f in json_files:
        if "-20" in f:  # assuming '1' is the grid identifier in format
            reference_file = f
            break

    if reference_file is None:
        raise ValueError("Reference case (with grid size = 1) not found!")

    rf_values = []
    labels = []
    errors = []

    # Load reference RF
    params_ref = extract_simulation_params_from_filename(reference_file)
    data_ref = load_data(os.path.join(input_directory, reference_file))
    time_ref = data_ref["time"]
    values_inj_ref = np.array(data_ref["InjectionValues_dt"]["H2"])
    values_prod_ref = np.array(data_ref["ProductionValues_dt"]["H2"])
    cycle_data_ref = cycles(params_ref, time_ref)
    rf_ref = calculate_rf(values_inj_ref, values_prod_ref, cycle_data_ref)

    # Store reference first
    rf_values.append(rf_ref)
    labels.append(reference_file)
    errors.append(np.zeros_like(rf_ref))  # Reference has zero error

    # Now loop through all other files
    for json_file in json_files:
        if json_file == reference_file:
            continue  # Already handled

        params = extract_simulation_params_from_filename(json_file)
        data = load_data(os.path.join(input_directory, json_file))
        time = data["time"]
        values_inj = np.array(data["InjectionValues_dt"]["H2"])
        values_prod = np.array(data["ProductionValues_dt"]["H2"])
        cycle_data = cycles(params, time)
        rf = calculate_rf(values_inj, values_prod, cycle_data)

        # Interpolate if needed to match length (simple check)
        min_len = min(len(rf), len(rf_ref))
        rf_trimmed = rf[:min_len]
        rf_ref_trimmed = rf_ref[:min_len]

        # Calculate relative error
        rel_error = np.abs(rf_trimmed - rf_ref_trimmed) / (rf_ref_trimmed + 1e-12)  # avoid div by zero

        # Store
        rf_values.append(rf)
        labels.append(json_file)
        errors.append(rel_error)
        
    plt.figure(figsize=(10, 6))
    plt.rcParams.update({'font.size': 18})
    X_axis = [1000*60, 100*12, 500*30,  333*20,200*12]
    X_axis = np.sqrt(X_axis)
    qq = 0
    for err, label in zip(errors[1:], X_axis):
        cc = X_axis[qq]
        vv = err[-1] * 100
        plt.plot(cc, err[-1]*100, label=f"{label} rel. error", marker='o', markersize=8, color='black')
        qq += 1
    plt.xlabel("$\sqrt{n_x \cdot n_z}$ [-]")
    plt.ylabel("Relative Error = ((RF - RF$_{base}$)/RF$_{base}$) $\cdot$ 100 [%]")
    plt.grid(True)
    # plt.xlim(0, 150)
    plt.ylim(0, 10)
    
    # plt.title("Relative Error in RF Compared to Reference Grid")
    plt.show()



# Example usage
os.chdir("Y:\\Mixing Results\\May\\GridSens")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\May\\CH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory)
