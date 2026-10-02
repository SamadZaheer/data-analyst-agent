import sys
from pathlib import Path
import duckdb

DB_PATH = Path(__file__).parent / "data" / "crashes.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)
print(con.sql(sys.argv[1]))