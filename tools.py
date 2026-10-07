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
    return duckdb.connect(str(DB_PATH), read_only=True, config={"enable_external_access": False},)


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


MAX_ROWS = 100 # most rows the LLM sees from one query

def _query_check(query: str) -> str | None:
    """Return an error message if the query isn't exactly one SELECT, else None."""
    try:
        statements = duckdb.extract_statements(query)
    except duckdb.Error as e:
        return f"SQL could not be parsed: {e}"

    if len(statements) != 1:
        return f"Exactly one SQL statement is allowed; got {len(statements)}."
    if statements[0].type != duckdb.StatementType.SELECT:
        return f"Only SELECT queries are allowed; got {statements[0].type.name}."
    return None

def run_sql(query: str) -> dict:
    "Run a read-only SELECT query and return at most MAX_ROWS."
    problem = _query_check(query)
    if problem:
        return {"ok": False, "error": problem}

    try:
        with _connect() as con:
            df = con.sql(query).limit(MAX_ROWS + 1).df()
    except duckdb.Error as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    truncated = len(df) > MAX_ROWS
    return {"ok": True, "data": df.head(MAX_ROWS), "truncated": truncated}


if __name__ == "__main__":
    tests = {
        "normal query": "SELECT crash_year, COUNT(*) AS crashes FROM crashes "
                        "GROUP BY crash_year ORDER BY crash_year",
        "wrong value (silent zero)": "SELECT COUNT(*) FROM crashes WHERE crash_severity = 'Fatality'",
        "too many rows": "SELECT * FROM crashes",
        "column typo": "SELECT crash_yr FROM crashes",
        "DROP": "DROP TABLE crashes",
        "sneaky second statement": "SELECT 1; DROP TABLE crashes",
        "read a local file": "SELECT * FROM read_csv('requirements.txt')",
    }

    for name, query in tests.items():
        result = run_sql(query)
        print(f"\n=== {name} ===")
        if result["ok"]:
            print(result["data"].head(5))
            print(f"rows returned: {len(result["data"])}, truncated: {result["truncated"]}")
        else:
            print(f"BLOCKED / ERROR:", result["error"])

    print("\n=== layer 1 alone (bypassing the SELECT check) ===")
    try:
        with _connect() as con:
            con.execute("DELETE FROM crashes")
    except duckdb.Error as e:
        print(f"Read-only connection refused it: {e}")