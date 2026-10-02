from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).parent / "data" / "raw"

# Show every column instead of hiding the middle ones with "..."
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

for csv_path in sorted(RAW_DIR.glob("*.csv")):
    df = pd.read_csv(csv_path, low_memory=False)
    size_mb = csv_path.stat().st_size / 1_000_000

    print("=" * 80)
    print(f"{csv_path.name} | {size_mb:.1f} MB | {df.shape[0]:,} rows x {df.shape[1]} cols")
    print("\n-- Column types --")
    print(df.dtypes.to_string())
    print("\n-- First 3 rows (turned sideways) --")
    print(df.head(3).T)