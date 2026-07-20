import pandas as pd
import os
import numpy as np
import CoolProp.CoolProp as CP


os.chdir("Y:\\Mixing Results\\Field Data")  # Change to the directory containing your simulation files
# Load the sampled CSV file
csv_path = r"Y:\Mixing Results\Field Data\sampled_doe_hybrid.csv"
df = pd.read_csv(csv_path, encoding='cp1252')
# Convert permeability from mD to m²
df["Permeability [m²]"] = df["Permeability [mD]"] * 9.8692e-16
df["Permeability [mD]"] = round(df["Permeability [mD]"], 2) 
df["Reservoir Pressure[MPa]"] = df["Reservoir Pressure[MPa]"] * 10  # Convert MPa to Pa
df["Reservoir Temp [C]"] = df["Reservoir Temp [C]"] + 273.15  # Convert MPa to Pa
df["Porosity [-]"] = df["Porosity [-]"] *100  # Convert MPa to Pa
df["CG"] = round(df["CG"], 2)  # Round CG to 2 decimal places
# df["CG"] = 0
# Define fixed values
fixed_params = {
    "InjectionRateDev": str(-18.85 / 5),
    "InjectionRateOp": str(-18.85 / 5),
    "ProductionRate": str(18.85 / 5),
    "Well_Height": "10"
}

# Function to determine TEnd and durations based on cycle length
def cycle_settings(cycle_len):
    if cycle_len <= 14:
        return {"TEnd": "140", "InjectionDurationOp": "7", "ExtractionDurationOp": "7"}
    elif cycle_len <= 60:
        return {"TEnd": "600", "InjectionDurationOp": "30", "ExtractionDurationOp": "30"}
    else:
        return {"TEnd": "1800", "InjectionDurationOp": "90", "ExtractionDurationOp": "90"}

# Generate test_cases
test_cases = []
fluid = "H2"
MaxTimeStepSize = 10000  # Fixed value for MaxTimeStepSize
for i, row in df.iterrows():
    durations = cycle_settings(row["Cycle Length [days]"])
    # if (row['Reservoir Pressure[MPa]'] < 150):
    #     continue
    # if (row['Permeability [mD]'] > 200):
    MaxTimeStepSize = min((row['Cycle Length [days]'] * 10)*86400/2200, 40000)
    mass_flow_rate = row['Flow Rate [m³/d]'] * 0.041e3 / 10  / 86400 / (2*np.pi*0.2)
    case = {
        "name": f"{fluid}-{int(row['Flow Rate [m³/d]'])}-{int(row['Cycle Length [days]'])}-{(row['Permeability [mD]'])}-{int(row['Reservoir Pressure[MPa]'])}-{int(row['Reservoir Temp [C]'])}-{int(row['Porosity [-]'])}-{row['CG']}",
        # "name": f"{fluid}-{int(row['Flow Rate [m³/d]'])}-{int(row['Cycle Length [days]'])}-{int(row['Permeability [mD]'])}-{int(row['Reservoir Pressure[MPa]'])}-{int(row['Reservoir Temp [C]'])}-{int(row['Porosity [-]'])}-{0}",
        "MaxTimeStepSize": f"{MaxTimeStepSize}",
        "InjectionRateDev": f"{-1 * mass_flow_rate}",
        "InjectionRateOp": f"{-1 * mass_flow_rate}",
        "ProductionRate": f"{mass_flow_rate}",
        "Well_Height": fixed_params["Well_Height"],
        "ReferencePorosity": f"{row['Porosity [-]'] / 100:.6f}",
        "ReferencePermeability": f"{row['Permeability [m²]']:.6e}",
        "Pressure_TOP": f"{row['Reservoir Pressure[MPa]'] * 1e5:.1f}",  # convert MPa to Pa
        "InitialTemperature": f"{row['Reservoir Temp [C]']}",
        "TEnd": f"{row['Cycle Length [days]'] * 10 + row['CG'] * (row['Cycle Length [days]']/2)}",  # convert days to seconds
        "InjectionDurationDev":  f"{row['CG'] * (row['Cycle Length [days]']/2)}",
        "InjectionDurationOp":  f"{row['Cycle Length [days]'] / 2}",
        "ExtractionDurationOp": f"{row['Cycle Length [days]'] / 2}",
    }
    test_cases.append(case)

# Optionally: write to file
import json
with open(f"generated_test_cases_{fluid}-NoCG-lowK.json", "w") as f:
    json.dump(test_cases, f, indent=4)

print("✅ Generated test_cases list with permeability in m² and pressure in Pa.")
