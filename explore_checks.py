from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).parent / "data" / "raw"

# Load only the two columns we need, which is much faster than all 52
crashes = pd.read_csv(
    RAW_DIR / "_1_crash_locations.csv",
    usecols=["Crash_Year", "Crash_Severity", "Crash_Month"],
)

# Crashes per year, split by severity
print(pd.crosstab(crashes["Crash_Year"], crashes["Crash_Severity"]))

# Which months appear in the latest year?
latest = crashes["Crash_Year"].max()
print(f"\nMonths present in {latest}:")
print(crashes.loc[crashes["Crash_Year"] == latest, "Crash_Month"].unique())