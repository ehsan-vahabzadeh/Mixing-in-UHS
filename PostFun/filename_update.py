import os
import json
import xml.etree.ElementTree as ET

# def rename_files(directory):
#     for filename in os.listdir(directory):
#         if filename.endswith('.json') or filename.endswith('.pvd'):
#             if 'CO2' in filename:
#                 new_filename = filename.replace('CO2', 'N2')
#                 src = os.path.join(directory, filename)
#                 dst = os.path.join(directory, new_filename)
#                 os.rename(src, dst)
#                 print(f"Renamed: {filename} → {new_filename}")
                
# def rename_files(directory):
#     for filename in os.listdir(directory):
#         if filename.endswith('.json') or filename.endswith('.pvd') :
            
#             base, ext = os.path.splitext(filename)
#             parts = base.split("-")
#             if len(parts) != 5:
#                 print(f"Skipping (unexpected parts): {filename}")
#                 continue
#             parts[-1] = str(int(int(float(parts[-1])) / 10))  # or replace with specific value
#             new_name = "-".join(parts) + ext
#             src = os.path.join(directory, filename)
#             dst = os.path.join(directory, new_name)
#             os.rename(src, dst)
#             print(f"Renamed: {filename} → {new_name}")      
                      
def rename_files(directory):
    input_file = "N2-June.json"
    output_file = "N2-June.json"
    with open(input_file, "r") as f:
        data = json.load(f)

    # Modify labels
    for entry in data:
        label_parts = entry["label"].split("-")
        if label_parts[-1].isdigit():
            last_number = int(label_parts[-1])
            label_parts[-1] = str(last_number * 10)
            entry["label"] = "-".join(label_parts)

    # Save to new file (or overwrite)
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

#     print("Updated labels saved to", output_file)
# === Run ===
os.chdir("Y:\\Mixing Results\\June\\N2")
directory = os.getcwd()  # or specify your path
rename_files(directory)
