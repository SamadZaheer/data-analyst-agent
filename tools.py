"""Tools the agent can call: get_schema() and run_sql()."""
from pathlib import Path
from functools import lru_cache

import duckdb

MAX_LISTED_VALUES = 25 # list every value if a text column has this many or fewer

DB_PATH = Path(__file__).parent / "data" / "crashes.duckdb"

def _connect():
    """Open a READ-ONLY connection to the crash database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run load_data.py first."
        )
    return duckdb.connect(str(DB_PATH), read_only=True)


def _describe_text_columns(con, table: str, column: str) -> str:
    """Describe the values in a VARCHAR column so the LLM knows real values in WHERE clauses."""
    n_distinct = con.execute(
        f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"'
    ).fetchone()[0]

    if n_distinct <= MAX_LISTED_VALUES:
        values = con.execute(
            f'SELECT DISTINCT "{column}" FROM "{table}"'
            f'WHERE "{column}" IS NOT NULL ORDER BY 1'
        ).fetchall()
        return "values: " + ", ".join(repr(v[0]) for v in values)

    top = con.execute(
        f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL '
        f'GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 3'
    ).fetchall()
    examples = ", ".join(repr(v[0]) for v in top)
    return f"{n_distinct:,} distinct values, e.g. {examples}"

@lru_cache(maxsize=1)
def get_schema() -> str:
    """Return a text description of every table, column and text-column values."""
    with _connect() as con:
        columns = con.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'main'
        ORDER BY table_name, ordinal_position
        """).fetchall()

        lines = []
        current_table = None
        for table, column, dtype in columns:
            if table != current_table:
                row_count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                lines.append(f"\ntable: {table} ({row_count:,} rows)")
                current_table = table
   
            line = f"  - {column}: {dtype}"
            if dtype == "VARCHAR":
               line += " | " + _describe_text_columns(con, table, column)
            lines.append(line) 

    return "\n".join(lines).strip()

if __name__ == "__main__":
    schema = get_schema()
    print(schema)
    print(f"\n~{len(schema) // 4:,} tokens (rough estimate: 1 tokens = 4 characters)")