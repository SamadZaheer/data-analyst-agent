from pathlib import Path
import urllib.request

import duckdb
import pandas as pd

PROJECT_DIR = Path(__file__).parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
DB_PATH = PROJECT_DIR / "data" / "crashes.duckdb"

BASE_URL = "https://www.data.qld.gov.au/dataset/f3e0ca94-2d7b-44ee-abef-d6b06e9b0729/resource"

# DuckDB table name -> (CSV file name, resource ID on the data portal)
SOURCES = {
    "crashes":                  ("_1_crash_locations.csv",              "e88943c0-5968-4972-a15f-38e120d72ec0"),
    "agg_casualties":           ("_a_road_casualties.csv",              "3fc53539-d529-4c1d-85f8-6c92d9e06fc8"),
    "agg_driver_involvement":   ("_b_driver_involvement.csv",           "dd13a889-2a48-4b91-8c64-59f824ed3d2c"),
    "agg_restraint_helmet_use": ("_c_restraint_helmet_use.csv",         "177dc50c-0cf7-46ba-8a69-99695aeaa46a"),
    "agg_crash_factors":        ("_e_alcohol_speed_fatigue_defect.csv", "18ee2911-992f-40ed-b6ae-e756859786e6"),
}

# Function for downloading the files if missing, move on if they exist
def download_if_missing(file_name, resource_id):
    path = RAW_DIR / file_name
    if path.exists():
        print(f"  found {file_name}")
        return path

    url = f"{BASE_URL}/{resource_id}/download/{file_name}"
    print(f"  downloading {file_name} ...")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, path)
    return path

# Cleanig Rules
# Columns the agent doesn't need; fewer columns means fewer wrong choices
DROP_FROM_CRASHES = [
    "Loc_Police_Division", "Loc_Queensland_Transport_Region", "Loc_Main_Roads_Region",
    "Loc_ABS_Statistical_Area_2", "Loc_ABS_Statistical_Area_3", "Loc_ABS_Statistical_Area_4",
    "Loc_State_Electorate", "Loc_Federal_Electorate",
    "Crash_DCA_Code", "Crash_DCA_Description", "DCA_Key_Approach_Dir",
]

# One name per concept across all tables (names not in a table are simply ignored)
RENAMES = {
    "Loc_Police_Region": "police_region",
    "Crash_Police_Region": "police_region",
    "Crash_PoliceRegion": "police_region",
    "Casualty_AgeGroup": "casualty_age_group",
    "Casualty_RoadUserType": "casualty_road_user_type",
    "Casualty_Road_User_Type": "casualty_road_user_type",
    "Involving_Young_Driver_16-24": "involving_young_driver_16_24",
    "Count_Casualty_MedicallyTreated": "count_casualty_medically_treated",
    "Count_Casualty_MinorInjury": "count_casualty_minor_injury",
    "Count_Casualty_All": "count_casualty_total",
    "Count_Fatality": "count_casualty_fatality",
    "Count_Hospitalised": "count_casualty_hospitalised",
    "Count_Medically_Treated": "count_casualty_medically_treated",
    "Count_Minor_Injury": "count_casualty_minor_injury",
    "Count_All_Casualties": "count_casualty_total",
}

# Casualty tables use different wording from crash tables for the same levels
SEVERITY_FIX = {
    "Fatality": "Fatal",
    "Hospitalised": "Hospitalisation",
    "Medically treated": "Medical treatment",
}

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

# Cleaning function
def clean(df, table_name):
    if table_name == "crashes":
        df = df.drop(columns=DROP_FROM_CRASHES)
        df["Crash_Month_Num"] = df["Crash_Month"].map(MONTHS)
        if df["Crash_Month_Num"].isna().any():
            raise ValueError("Unrecognised month name in Crash_Month")

    df = df.rename(columns=RENAMES)
    df.columns = [col.lower() for col in df.columns]

    if "casualty_severity" in df.columns:
        df["casualty_severity"] = df["casualty_severity"].replace(SEVERITY_FIX)

    return df

# Build the database
def build_database():
    if DB_PATH.exists():
        DB_PATH.unlink() # to start fresh every time

    con = duckdb.connect(str(DB_PATH))

    for table_name, (file_name, resource_id) in SOURCES.items():
        path = download_if_missing(file_name, resource_id)
        df = pd.read_csv(path, low_memory=False)
        df = clean(df, table_name)

        con.register("df_view", df)
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df_view")
        con.unregister("df_view")

        print(f" {table_name}: {len(df):,} rows, {len(df.columns)} columns")

    con.close()
    print(f"Built {DB_PATH}")


if __name__ == "__main__":
    build_database()