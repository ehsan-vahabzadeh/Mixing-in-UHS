import os
import re
import pandas as pd
from difflib import get_close_matches

folder_path = r"Y:\Mixing Results\July"
os.chdir(folder_path)

base_file  = "consolidated_output - Final.csv"          # has the Lat/Lon you trust
final_file = "optimized_results_without_CG.csv"  # needs Lat/Lon filled
out_file   = "optimized_results_without_CG_u.csv"

# ---- 1) Load files ----
base  = pd.read_csv(base_file, encoding='cp1252')
final = pd.read_csv(final_file)

# ---- 2) Ensure expected columns exist ----
# Base should have: 'Field Name', 'Latitude', 'Longitude'  (from your generator)
# Final should have at least: 'Field Name' (+ maybe its own Lat/Lon columns)
for col in ["Field Name"]:
    if col not in base.columns or col not in final.columns:
        raise ValueError(f"Missing 'Field Name' in one of the files.")

# If the final file doesn't yet have Lat/Lon columns, create them
for col in ["Latitude", "Longitude"]:
    if col not in final.columns:
        final[col] = pd.NA

# ---- 3) Build a normalization function for names ----
def norm_name(s: str) -> str:
    if pd.isna(s): 
        return ""
    s = str(s).lower().strip()
    s = re.sub(r"\s+", " ", s)                     # collapse spaces
    # optional: remove common suffixes like " gas field"
    s = re.sub(r"\b(gas\s*field|field)\b", "", s).strip()
    s = re.sub(r"[^\w\s]", "", s)                  # drop punctuation
    return s

base["_key"]  = base["Field Name"].apply(norm_name)
final["_key"] = final["Field Name"].apply(norm_name)

# If base has duplicate fields, prefer the first non-null Lat/Lon
base_coords = (base
               .dropna(subset=["Latitude", "Longitude"])
               .drop_duplicates(subset=["_key"], keep="first")
               [["_key", "Latitude", "Longitude"]])

# ---- 4) Exact join on normalized key ----
merged = final.merge(base_coords, on="_key", how="left", suffixes=("", "_from_base"))

# Only fill missing Lat/Lon in final from base
before_fill_lat = merged["Latitude"].isna().sum()
before_fill_lon = merged["Longitude"].isna().sum()

merged["Latitude"]  = merged["Latitude"].fillna(merged["Latitude_from_base"])
merged["Longitude"] = merged["Longitude"].fillna(merged["Longitude_from_base"])

after_fill_lat = merged["Latitude"].isna().sum()
after_fill_lon = merged["Longitude"].isna().sum()

exact_fills_lat = before_fill_lat - after_fill_lat
exact_fills_lon = before_fill_lon - after_fill_lon

# ---- 5) Fuzzy fallback for still-missing coords ----
still_missing = merged[merged["Latitude"].isna() | merged["Longitude"].isna()].copy()
base_keys = base_coords["_key"].tolist()

fuzzy_matches = 0
for idx, row in still_missing.iterrows():
    key = row["_key"]
    if not key:
        continue
    # try a close match (threshold can be tuned)
    candidates = get_close_matches(key, base_keys, n=1, cutoff=0.92)
    if candidates:
        k = candidates[0]
        match_row = base_coords.loc[base_coords["_key"] == k].iloc[0]
        if pd.isna(merged.at[idx, "Latitude"]):
            merged.at[idx, "Latitude"] = match_row["Latitude"]
        if pd.isna(merged.at[idx, "Longitude"]):
            merged.at[idx, "Longitude"] = match_row["Longitude"]
        fuzzy_matches += 1

# ---- 6) Cleanup and save ----
merged = merged.drop(columns=["_key", "Latitude_from_base", "Longitude_from_base"])
merged.to_csv(out_file, index=False)

# ---- 7) Report ----
left_unfilled = merged["Latitude"].isna().sum() + merged["Longitude"].isna().sum()
print("✅ Coordinates merged.")
print(f"   Exact fills:  Latitude {exact_fills_lat}, Longitude {exact_fills_lon}")
print(f"   Fuzzy fills:  {fuzzy_matches}")
print(f"   Remaining rows without coords: {left_unfilled // 2} (both lat & lon missing)")
print(f"   Saved to: {out_file}")
