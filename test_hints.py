"""Quick checks for execute_tool's self-correction hints (no API calls)."""
from agent import execute_tool

TESTS = {
    "typo (expect error + hint)":
        "SELECT COUNT(*) AS n FROM crashes WHERE crash_yeer = 2024",
    "wrong case (expect 0-rows warning)":
        "SELECT * FROM crashes WHERE crash_severity = 'fatal' LIMIT 5",
    "SUM over nothing (expect NULL warning)":
        "SELECT SUM(count_casualty_fatality) AS deaths FROM crashes WHERE crash_severity = 'fatal'",
    "control (expect 273, no warning)":
        "SELECT COUNT(*) AS n FROM crashes WHERE crash_severity = 'Fatal' AND crash_year = 2024",
}

for name, sql in TESTS.items():
    print(f"\n=== {name} ===")
    print(execute_tool("run_sql", {"query": sql}))