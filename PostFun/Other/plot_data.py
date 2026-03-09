import os, re, glob
import numpy as np
import pandas as pd

# ==========================
# USER SETTINGS
# ==========================
INPUT_DIR   = r"Y:\Mixing Results\July\Two Term Equation"
GLOB_PATTERN = "optimal_plan_CL*_TWh*.xlsx"

YEAR_PICK = 30  # pick the sheet closest to this project horizon (years)

# Column names (as used in your exports)
COL_PRO_TWH = "Cum H2 Produced [Twh]"
COL_PRO_M3  = "Cum H2 Produced [m3]"

# Some exports keep "Cum H2 Produced [Twh]" already, some may not
KWH_PER_M3  = 39.41 * 0.08988  # kWh per m3 at STP (your value)

# Candidate column names for reservoir ID and selection indicator
RES_COL_CANDIDATES = [
    "Reservoir", "Reservoir Name", "ReservoirName",
    "Field", "Field Name", "FieldName",
    "Name", "Asset", "Structure"
]
SEL_COL_CANDIDATES = ["x", "Selected", "is_selected", "Select", "Decision", "chosen"]

EPS = 0.0  # "don't count zeros" -> strictly > 0


def m3_to_TWh(m3):
    return m3 * KWH_PER_M3 / 1e9


def parse_metadata_from_filename(fname: str) -> dict:
    """
    Best-effort parser. Works with names like:
    optimal_plan_CL360_TWh100_Low_H24.0.xlsx
    optimal_plan_CL360_TWh100_Base_H23.0.xlsx
    optimal_plan_CL360_TWh100_H25.0.xlsx  (if no PSA label)
    """
    base = os.path.basename(fname)

    cl = None
    twh = None
    psa_label = None
    h2_cost = None

    m = re.search(r"CL(\d+)", base)
    if m: cl = int(m.group(1))

    m = re.search(r"TWh(\d+)", base)
    if m: twh = int(m.group(1))

    # PSA label: the token between _TWhXXX_ and _H2...
    # Example: _TWh100_Low_H24.0
    m = re.search(r"TWh\d+_([A-Za-z]+)_H2", base)
    if m:
        psa_label = m.group(1)
    else:
        # sometimes it might just be _TWh100_H24.0
        psa_label = "NA"

    m = re.search(r"_H2(\d+(\.\d+)?)", base)
    if m:
        h2_cost = float(m.group(1))
    else:
        h2_cost = np.nan

    # A compact scenario key for grouping
    scenario_key = f"PSA={psa_label}|H2={h2_cost}"

    return dict(
        file=base,
        path=fname,
        cl_days=cl,
        target_twh=twh,
        psa_label=psa_label,
        h2_cost=h2_cost,
        scenario_key=scenario_key,
    )


def find_first_existing_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def get_cycle_sheets(xls: pd.ExcelFile):
    cyc = []
    for s in xls.sheet_names:
        m = re.match(r"^cycle_(\d+)$", s)
        if m:
            cyc.append((int(m.group(1)), s))
    cyc.sort(key=lambda x: x[0])
    return cyc


def read_sheet_at_year(path: str, cl_days: int, year_pick: float):
    """
    Reads the cycle sheet closest to 'year_pick' where year_raw = cycle * CL/360.
    If no cycle sheets exist, raises.
    """
    xls = pd.ExcelFile(path)
    cyc_sheets = get_cycle_sheets(xls)
    if not cyc_sheets:
        raise ValueError(f"No cycle_* sheets found in {path}")

    cycles = np.array([c for c, _ in cyc_sheets], dtype=float)
    year_raw = cycles * (cl_days / 360.0)

    idx = int(np.argmin(np.abs(year_raw - year_pick)))
    cyc, sname = cyc_sheets[idx]
    df = pd.read_excel(xls, sheet_name=sname)
    return df, cyc, float(year_raw[idx]), sname


def extract_reservoir_contributions(df: pd.DataFrame, target_twh: float, scenario_key: str):
    """
    Returns per-reservoir produced_twh and shares, filtered to produced_twh > 0.
    """
    res_col = find_first_existing_col(df, RES_COL_CANDIDATES)
    if res_col is None:
        raise ValueError(f"Could not find a reservoir name column. Columns={list(df.columns)}")

    sel_col = find_first_existing_col(df, SEL_COL_CANDIDATES)

    # Selection mask (if column exists)
    if sel_col is not None:
        sel_mask = pd.to_numeric(df[sel_col], errors="coerce").fillna(0.0) > 0.0
    else:
        sel_mask = pd.Series(True, index=df.index)

    # Produced TWh
    if COL_PRO_TWH in df.columns:
        produced = pd.to_numeric(df[COL_PRO_TWH], errors="coerce")
    elif COL_PRO_M3 in df.columns:
        produced = m3_to_TWh(pd.to_numeric(df[COL_PRO_M3], errors="coerce"))
    else:
        raise ValueError(f"Neither '{COL_PRO_TWH}' nor '{COL_PRO_M3}' found.")

    tmp = df.loc[sel_mask, [res_col]].copy()
    tmp["produced_twh"] = produced.loc[sel_mask].astype(float)

    # "don't count zeros"
    tmp = tmp[tmp["produced_twh"].fillna(0.0) > EPS].copy()

    # Aggregate in case a reservoir appears multiple times in the sheet
    out = (tmp.groupby(res_col, as_index=False)["produced_twh"]
              .sum()
              .rename(columns={res_col: "reservoir"}))

    total_produced = out["produced_twh"].sum()
    out["share_to_target"] = out["produced_twh"] / float(target_twh)
    out["share_to_total"]  = out["produced_twh"] / (total_produced if total_produced > 0 else np.nan)
    out["scenario_key"] = scenario_key

    return out


# ==========================
# MAIN: LOAD + AGGREGATE
# ==========================
files = sorted(glob.glob(os.path.join(INPUT_DIR, GLOB_PATTERN)))
if not files:
    raise RuntimeError(f"No files matched: {os.path.join(INPUT_DIR, GLOB_PATTERN)}")

meta_rows = []
all_rows = []

for f in files:
    md = parse_metadata_from_filename(f)

    # skip if parser failed
    if md["cl_days"] is None or md["target_twh"] is None:
        print(f"[skip] cannot parse CL/TWh from: {md['file']}")
        continue

    try:
        df_year, cyc, year_raw, sname = read_sheet_at_year(md["path"], md["cl_days"], YEAR_PICK)
        contrib = extract_reservoir_contributions(
            df_year,
            target_twh=md["target_twh"],
            scenario_key=md["scenario_key"]
        )
        contrib["target_twh"] = md["target_twh"]
        contrib["cl_days"] = md["cl_days"]
        contrib["picked_cycle"] = cyc
        contrib["picked_year_raw"] = year_raw
        contrib["sheet"] = sname
        contrib["file"] = md["file"]

        all_rows.append(contrib)

        md["picked_cycle"] = cyc
        md["picked_year_raw"] = year_raw
        md["sheet"] = sname
        md["n_res_selected"] = int(contrib.shape[0])

        meta_rows.append(md)

    except Exception as e:
        print(f"[skip] {md['file']} -> {e}")

df_meta = pd.DataFrame(meta_rows)
df_all  = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()

if df_all.empty:
    raise RuntimeError("No reservoir contribution rows extracted. Check column names / file structure.")

# total scenario count per target (not hard-coded to 6)
target_case_counts = (df_meta.groupby("target_twh")["scenario_key"]
                      .nunique()
                      .rename("n_cases_total")
                      .reset_index())

# per-target reservoir summary
df_summary = (df_all.groupby(["target_twh", "reservoir"], as_index=False)
              .agg(
                  n_cases_selected=("scenario_key", "nunique"),
                  produced_twh_median=("produced_twh", "median"),
                  produced_twh_mean=("produced_twh", "mean"),
                  share_to_target_median=("share_to_target", "median"),
                  share_to_target_p25=("share_to_target", lambda x: np.nanpercentile(x, 25)),
                  share_to_target_p75=("share_to_target", lambda x: np.nanpercentile(x, 75)),
              ))

df_summary = df_summary.merge(target_case_counts, on="target_twh", how="left")
df_summary["selection_freq"] = df_summary["n_cases_selected"] / df_summary["n_cases_total"]

# optional: sort within each target by frequency then median share
df_summary = df_summary.sort_values(
    ["target_twh", "selection_freq", "share_to_target_median"],
    ascending=[True, False, False]
).reset_index(drop=True)

# ==========================
# ADD LAT/LON FROM CONSOLIDATED FILE
# ==========================
GEO_FILE = os.path.join(INPUT_DIR, "consolidated_output - Final.csv")

def norm_name(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    # remove common punctuation / extra spaces
    s = re.sub(r"[\.\,\-\_\(\)\[\]\/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

df_geo = pd.read_csv(GEO_FILE, encoding='cp1252' )

# expected columns: Field Name, Latitude, Longitude
# (handle slight variations just in case)
geo_field_col = None
for c in df_geo.columns:
    if norm_name(c) in ["field name", "fieldname", "field"]:
        geo_field_col = c
        break
if geo_field_col is None:
    raise ValueError(f"Could not find 'Field Name' column in {GEO_FILE}. Columns={list(df_geo.columns)}")

lat_col = None
lon_col = None
for c in df_geo.columns:
    if norm_name(c) == "latitude":
        lat_col = c
    if norm_name(c) == "longitude":
        lon_col = c
if lat_col is None or lon_col is None:
    raise ValueError(f"Could not find Latitude/Longitude columns in {GEO_FILE}. Columns={list(df_geo.columns)}")

df_geo = df_geo[[geo_field_col, lat_col, lon_col]].copy()
df_geo.rename(columns={geo_field_col: "field_name", lat_col: "Latitude", lon_col: "Longitude"}, inplace=True)

# normalize names for matching
df_geo["name_key"] = df_geo["field_name"].apply(norm_name)
df_summary["name_key"] = df_summary["reservoir"].apply(norm_name)

# if duplicate field names exist, keep first (or you can aggregate)
df_geo = df_geo.drop_duplicates(subset="name_key", keep="first")

# merge coordinates into summary
df_summary = df_summary.merge(
    df_geo[["name_key", "Latitude", "Longitude"]],
    on="name_key",
    how="left"
)

# optional: also add coords to df_all (long format) if you want later
df_all["name_key"] = df_all["reservoir"].apply(norm_name)
df_all = df_all.merge(
    df_geo[["name_key", "Latitude", "Longitude"]],
    on="name_key",
    how="left"
)

# report unmatched reservoirs (so you can fix naming inconsistencies)
unmatched = df_summary[df_summary["Latitude"].isna() | df_summary["Longitude"].isna()]["reservoir"].unique()
if len(unmatched) > 0:
    print("\n[WARNING] Unmatched reservoirs (no lat/lon found). Example list:")
    print(pd.Series(unmatched).sort_values().head(50).to_string(index=False))
    print(f"... total unmatched: {len(unmatched)}")
else:
    print("\nAll reservoirs matched with lat/lon ✅")



# ==========================
# OUTPUTS (for your next step: mapping)
# ==========================
out_dir = os.path.join(INPUT_DIR, "_map_inputs")
os.makedirs(out_dir, exist_ok=True)

df_meta.to_csv(os.path.join(out_dir, "scenario_metadata.csv"), index=False)
df_all.to_csv(os.path.join(out_dir, "scenario_reservoir_contributions_long.csv"), index=False)
df_summary.to_csv(os.path.join(out_dir, "per_target_reservoir_summary.csv"), index=False)

print("\nSaved:")
print(" - scenario_metadata.csv")
print(" - scenario_reservoir_contributions_long.csv")
print(" - per_target_reservoir_summary.csv")

# quick sanity: show top reservoirs per target
for t in sorted(df_summary["target_twh"].unique()):
    top = df_summary[df_summary["target_twh"] == t].head(10)
    print(f"\n=== Target {t} TWh: top 10 by selection frequency then median share ===")
    print(top[["reservoir", "n_cases_selected", "n_cases_total", "selection_freq",
               "share_to_target_median", "produced_twh_median"]].to_string(index=False))
