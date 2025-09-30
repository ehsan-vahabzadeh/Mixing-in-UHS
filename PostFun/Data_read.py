import os
import pandas as pd

# Folder containing your CSV files
folder_path = "Y:\\Mixing Results\\Field Data"  # Change to the directory containing your simulation files
os.chdir(folder_path)  # Change to the directory containing your simulation files
base_dir = os.getcwd() 
# List of field names you want to extract (as written in the files)
fields = [
    "description", "porosityml", "formationtempml", "porepressureml", "salinity",
    "storagepermeabilityml", "irreducible_water_saturationml", "co2endpoint_relpermeabilityml",
    "ave_gross_prod_rate_per_wellml", "ave_water_prod_rate_per_wellml", "gassaturation",
    "gasgravity", "giip", "virgin_reservoir_pressure", "virgin_reservoir_temp",
    "gas_compress_factor", "gas_viscosity_at_rev_cond", "porevolume", "temperaturegradient", "shallowestdepthmin", "lat", "lon", "activegasproduction",
    "cum_gas_production"
]

# Nicely formatted column names for output
pretty_fields = [
    "Field Name", "Porosity [-]", "Formation Temp [C]", "Pore Pressure [MPa]", "Salinity [ppm]",
    "Permeability [D]", "Swr [-]", "CO2 Endpoint RelPerm",
    "Gross Prod Rate/Well [cm/d]", "Water Prod Rate/Well [cm/d]", "Gas Saturation [-]",
    "Gas Gravity", "GIIP [1e6 scm/d]", "Reservoir Pressure[MPa]", "Reservoir Temp [C]",
    "Gas Comp. Factor", "Gas Viscosity [cp]", "Pore Volume", "Temp Gradient", "Depth [m]", "Latitude", "Longitude", "NOW",
    "Sg","cum_gas_prod"
]

all_data = []

# Loop through all CSV files
for file in os.listdir(folder_path):
    if file != "consolidated_output.csv" and file != "consolidated_output - Final.csv":
        try:
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)

            # Only keep the fields we care about (if they exist)
            available_cols = [col for col in fields if col in df.columns]
            filtered_df = df[available_cols]

            # Reorder and rename columns
            ordered_data = []
            for i in range(len(filtered_df)):
                row = []
                for field in fields:
                    row.append(filtered_df[field].iloc[i] if field in filtered_df.columns else "")
                ordered_data.append(row)

            all_data.extend(ordered_data)

        except Exception as e:
            print(f"Error processing {file}: {e}")

# Build final DataFrame
final_df = pd.DataFrame(all_data, columns=pretty_fields)
output_path = os.path.join(folder_path, "consolidated_output.csv")
final_df.to_csv(output_path, index=False)

print("✅ Output saved to 'consolidated_output.csv'")