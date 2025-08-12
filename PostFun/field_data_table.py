import pandas as pd

# Path to the CSV file
csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"

# Read the CSV file
df = pd.read_csv(csv_path)

# Columns to include
columns = [
    "Field Name",
    "Porosity [-]",
    "Permeability [mD]",
    "Reservoir Pressure[MPa]",
    "Reservoir Temp [C]",
    "ref"
]

# Convert numeric columns
numeric_cols = [
    "Porosity [-]",
    "Permeability [mD]",
    "Reservoir Pressure[MPa]",
    "Reservoir Temp [C]"
]
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
df["Reservoir Pressure[MPa]"] = df["Reservoir Pressure[MPa]"] * 10  # Convert MPa to Pa
df["Reservoir Temp [C]"] = df["Reservoir Temp [C]"] + 273.15  # Convert C to K
# Drop rows with missing values in any of the required columns
# df_clean = df[columns].dropna()

# Print LaTeX table
print(r"\begin{table}[htbp]")
print(r"\centering")
print(r"\begin{tabular}{llllll}")
print(r"\hline")
print(r"Field Name & Porosity [-] & Permeability [mD] & Pressure [bar] & Temp [K] & Reference \\")
print(r"\hline")
for _, row in df.iterrows():
    print(f"{row['Field Name']} & {row['Porosity [-]']:.3f} & {row['Permeability [mD]']:.1f} & {row['Reservoir Pressure[MPa]']:.2f} & {row['Reservoir Temp [C]']:.1f} & {row['ref']} \\\\")
print(r"\hline")
print(r"\end{tabular}")
print(r"\caption{Reservoir properties and references for UK depleted gas fields.}")
print(r"\label{tab:field_properties}")
print(r"\end{table}")
