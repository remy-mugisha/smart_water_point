"""
WPDx Water Point Data - Bugesera District extraction & cleaning
for AI-Based Water Point Failure Prediction System (Remy's thesis)
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

RAW_PATH = "/mnt/user-data/uploads/wpdx_enhanced.csv"
ADM_PATH = "/mnt/user-data/uploads/adm_analysis.csv"
OUT_DIR = "/mnt/user-data/outputs"

# ---------------------------------------------------------------------------
# STEP 1: LOAD AND EXPLORE
# ---------------------------------------------------------------------------
print("="*80)
print("STEP 1: LOAD AND EXPLORE")
print("="*80)

# Row 0 after the header is a HXL hashtag row (#geo+lat, #adm2+name, etc.)
# from the HDX export -- it's metadata, not data, so we skip it.
df = pd.read_csv(RAW_PATH, skiprows=[1])

print(f"\nShape: {df.shape[0]} rows, {df.shape[1]} columns\n")
print("Columns and dtypes:")
print(df.dtypes)

print("\nFirst 10 rows (key columns):")
key_cols = ["wpdx_id", "clean_adm1", "clean_adm2", "clean_adm3", "status_clean",
            "water_source_clean", "water_tech_clean", "install_year"]
print(df[key_cols].head(10).to_string())

print("\nUnique clean_adm1 (province):")
print(sorted(df["clean_adm1"].dropna().unique()))

print("\nUnique clean_adm2 (district) — Bugesera check:")
adm2_vals = sorted(df["clean_adm2"].dropna().unique())
print(adm2_vals)
print(f"\n'Bugesera' present in clean_adm2: {'Bugesera' in adm2_vals}")

# ---------------------------------------------------------------------------
# STEP 2: FILTER FOR BUGESERA DISTRICT
# ---------------------------------------------------------------------------
print("\n" + "="*80)
print("STEP 2: FILTER FOR BUGESERA")
print("="*80)

bugesera = df[df["clean_adm2"].str.strip().str.lower() == "bugesera"].copy()
print(f"\nBugesera water points found: {len(bugesera)}")

print("\nFunctional vs Non-Functional (status_clean):")
print(bugesera["status_clean"].value_counts(dropna=False))

print("\nSummary statistics (numeric columns):")
print(bugesera[["lat_deg", "lon_deg", "install_year", "local_population",
                 "assigned_population"]].describe())

print("\nSectors (clean_adm3) represented in Bugesera:")
print(bugesera["clean_adm3"].value_counts(dropna=False))

# --- Cross-check against the district-level aggregate file -----------------
# adm_analysis.csv is a separate, gridded/aggregated HDX export at a finer
# spatial resolution. Its own functional/non-functional counts for Bugesera
# do NOT match wpdx_enhanced.csv (see printed warning below) -- flagging this
# for the thesis write-up rather than silently reconciling it.
adm = pd.read_csv(ADM_PATH, skiprows=[1])
buge_adm = adm[adm["NAME_2"].str.strip().str.lower() == "bugesera"]
agg_func = buge_adm["func_waterpoints"].sum()
agg_nonfunc = buge_adm["non_func_waterpoints"].sum()
print("\n*** DATA QUALITY WARNING ***")
print(f"wpdx_enhanced.csv (point-level): {len(bugesera)} Bugesera points, "
      f"ALL labeled '{bugesera['status_clean'].unique()}'")
print(f"adm_analysis.csv (grid-level) for Bugesera sums to: "
      f"{agg_func:.0f} functional / {agg_nonfunc:.0f} non-functional")
print("These two source files disagree on Bugesera's functional status. "
      "This should be called out explicitly as a data limitation in the "
      "thesis methodology/limitations section -- see summary report.")

# ---------------------------------------------------------------------------
# STEP 3: DATA CLEANING
# ---------------------------------------------------------------------------
print("\n" + "="*80)
print("STEP 3: DATA CLEANING")
print("="*80)

CURRENT_YEAR = 2026

clean = pd.DataFrame()
clean["water_point_id"] = bugesera["wpdx_id"]
clean["district"] = "Bugesera"
clean["sector"] = bugesera["clean_adm3"].fillna("Unknown")
clean["latitude"] = pd.to_numeric(bugesera["lat_deg"], errors="coerce")
clean["longitude"] = pd.to_numeric(bugesera["lon_deg"], errors="coerce")
clean["year_installed"] = pd.to_numeric(bugesera["install_year"], errors="coerce")

# population_served: prefer local_population, fall back to assigned_population,
# then to the district median so no row is left null in the model
pop = bugesera["local_population"].fillna(bugesera["assigned_population"])
pop_median = pop.median()
clean["population_served"] = pop.fillna(pop_median).round().astype("Int64")

# current_status: standardize to Functional / Non-Functional
clean["current_status"] = (
    bugesera["status_clean"]
    .replace({"Functional, needs repair": "Functional"})
    .fillna("Unknown")
)

# monthly_rainfall: NOT present in this WPDx export. Per the thesis design,
# rainfall comes from a separate CHIRPS merge step -- left as NaN here
# rather than fabricated, so the CHIRPS join has a clean column to fill.
clean["monthly_rainfall"] = np.nan

# --- technology_type: map WPDx's tech + source fields onto the four
# categories used in the WaterPoint model (Handpump, Borehole, Piped Kiosk,
# Protected Spring). WPDx's own categories don't line up 1:1 with these
# (e.g. "Motorized Pump" isn't any of the four), so mapped with a clear,
# documented rule and anything left over goes to "Other" for manual review.
def map_tech(row):
    tech = row["water_tech_clean"]
    source = row["water_source_clean"]
    if isinstance(tech, str):
        if "Hand Pump" in tech:
            return "Handpump"
        if tech == "Motorized Pump":
            return "Borehole"          # motorized borehole pump
        if tech == "Public Tapstand":
            return "Piped Kiosk"
    if isinstance(source, str):
        if source == "Borehole/Tubewell":
            return "Borehole"
        if source == "Protected Well":
            return "Protected Spring"  # closest available category
        if source == "Piped Water":
            return "Piped Kiosk"
        if source == "Rainwater Harvesting":
            return "Other"             # doesn't fit the 4 target categories
    return "Other"

clean["technology_type"] = bugesera.apply(map_tech, axis=1)

# year_installed: also derive an "age" helper column (current_year - install_year)
clean["age_years"] = CURRENT_YEAR - clean["year_installed"]

# drop rows with no usable coordinates (can't be mapped/used spatially)
before = len(clean)
clean = clean.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
print(f"Dropped {before - len(clean)} rows with missing coordinates "
      f"({len(clean)} remain)")

print("\nMissing values after cleaning:")
print(clean.isna().sum())

print("\ntechnology_type distribution after mapping:")
print(clean["technology_type"].value_counts())

print("\nClean dataframe preview:")
print(clean.head(10).to_string())

# ---------------------------------------------------------------------------
# STEP 4: SAVE CLEANED DATA + SUMMARY REPORT
# ---------------------------------------------------------------------------
print("\n" + "="*80)
print("STEP 4: SAVE OUTPUTS")
print("="*80)

csv_path = f"{OUT_DIR}/bugesera_water_points_cleaned.csv"
clean.to_csv(csv_path, index=False)
print(f"Saved: {csv_path}")

numeric_stats = clean[["latitude", "longitude", "year_installed",
                        "population_served", "age_years"]].describe()

with open(f"{OUT_DIR}/bugesera_data_summary.txt", "w") as f:
    f.write("BUGESERA DISTRICT WATER POINT DATA -- CLEANING SUMMARY\n")
    f.write("="*60 + "\n")
    f.write(f"Source file: wpdx_enhanced.csv (WPDx / HDX export)\n")
    f.write(f"Total Bugesera water points (with valid coordinates): {len(clean)}\n\n")

    f.write("Status breakdown (current_status):\n")
    f.write(clean["current_status"].value_counts(dropna=False).to_string())
    f.write("\n\n")

    f.write("Technology type breakdown (mapped):\n")
    f.write(clean["technology_type"].value_counts(dropna=False).to_string())
    f.write("\n\n")

    f.write("Sector breakdown:\n")
    f.write(clean["sector"].value_counts(dropna=False).to_string())
    f.write("\n\n")

    f.write("Numeric summary statistics:\n")
    f.write(numeric_stats.to_string())
    f.write("\n\n")

    f.write("DATA QUALITY WARNING\n")
    f.write("-"*60 + "\n")
    f.write(
        f"All {len(bugesera)} point-level Bugesera records in wpdx_enhanced.csv\n"
        f"are labeled 'Non-Functional', while the separate grid-level file\n"
        f"adm_analysis.csv sums to {agg_func:.0f} functional / {agg_nonfunc:.0f}\n"
        f"non-functional water points for Bugesera. The two HDX source files\n"
        f"disagree on functional status for this district. Recommend flagging\n"
        f"this explicitly as a data limitation, and NOT relying solely on\n"
        f"wpdx_enhanced.csv's status labels as ground truth for model training\n"
        f"without further verification (e.g. against MININFRA records).\n\n"
    )
    f.write(
        "Note: 'monthly_rainfall' is left blank in the cleaned CSV -- per the\n"
        "project design this is populated later via a separate CHIRPS merge\n"
        "step, not derived from WPDx.\n"
    )

print(f"Saved: {OUT_DIR}/bugesera_data_summary.txt")

# ---------------------------------------------------------------------------
# STEP 5: VISUALIZATIONS
# ---------------------------------------------------------------------------
print("\n" + "="*80)
print("STEP 5: VISUALIZATIONS")
print("="*80)

# 5a. Map of water point locations (no internet available for basemap tiles,
# so plotted as a georeferenced scatter, colored by status)
fig, ax = plt.subplots(figsize=(8, 8))
colors = {"Functional": "#2a9d8f", "Non-Functional": "#e63946", "Unknown": "#adb5bd"}
for status, group in clean.groupby("current_status"):
    ax.scatter(group["longitude"], group["latitude"], s=45,
               label=status, color=colors.get(status, "#333333"),
               edgecolor="white", linewidth=0.5, zorder=3)
ax.set_title("Bugesera District Water Points", fontsize=14, fontweight="bold")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(title="Status")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/bugesera_map.png", dpi=150)
plt.close()
print(f"Saved: {OUT_DIR}/bugesera_map.png")

# 5b. Bar charts: functional vs non-functional, tech distribution, install year
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

status_counts = clean["current_status"].value_counts()
axes[0].bar(status_counts.index, status_counts.values,
            color=[colors.get(s, "#333333") for s in status_counts.index])
axes[0].set_title("Functional vs Non-Functional")
axes[0].set_ylabel("Count")
axes[0].tick_params(axis="x", rotation=20)

tech_counts = clean["technology_type"].value_counts()
axes[1].bar(tech_counts.index, tech_counts.values, color="#457b9d")
axes[1].set_title("Technology Type Distribution")
axes[1].set_ylabel("Count")
axes[1].tick_params(axis="x", rotation=30)

year_counts = clean["year_installed"].dropna().astype(int).value_counts().sort_index()
axes[2].bar(year_counts.index.astype(str), year_counts.values, color="#f4a261")
axes[2].set_title("Installation Year Distribution")
axes[2].set_ylabel("Count")
axes[2].tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig(f"{OUT_DIR}/bugesera_charts.png", dpi=150)
plt.close()
print(f"Saved: {OUT_DIR}/bugesera_charts.png")

print("\nDONE.")
