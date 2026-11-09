"""Unit tests for scoring.py"""
import pandas as pd

from scoring import check_numbers, extract_numbers, strip_code

gold_273 = pd.DataFrame({"fatal_crashes": [273]})
gold_two = pd.DataFrame({"fatal_crashes": [273], "deaths": [302]})
gold_big = pd.DataFrame({"n": [13350]})
gold_pct = pd.DataFrame({"pct": [12.3456]})
gold_60 = pd.DataFrame({"speed": [60]})

cases = [
    # (description, answer, gold, expected pass?)
    ("plain match",          "There were 273 fatal crashes.",              gold_273, True),
    ("sentence-end dot",     "The total was 273.",                         gold_273, True),
    ("substring trap",       "There were 2738 crashes.",                   gold_273, False),
    ("thousands comma",      "In total, 13,350 crashes.",                  gold_big, True),
    ("bold markdown",        "**273** fatal crashes",                      gold_273, True),
    ("both numbers",         "273 fatal crashes, 302 deaths.",             gold_two, True),
    ("one number missing",   "273 fatal crashes.",                         gold_two, False),
    ("rounded percent",      "About 12.3% of crashes.",                    gold_pct, True),
    ("badly rounded",        "About 15% of crashes.",                      gold_pct, False),
    ("SQL echo only",        "Here you go.\n```sql\nWHERE x = 60\n```",    gold_60,  False),
    ("unclosed SQL fence",   "Answer below\n```sql\nSELECT 273",           gold_273, False),
]

failures = 0
for desc, answer, gold, expected in cases:
    passed, reason = check_numbers(answer, gold)
    ok = passed == expected
    failures += not ok
    print(f"{'✅' if ok else '❌'} {desc:22} expected={expected!s:5} got={passed!s:5} ({reason})")

# Helper sanity checks
assert extract_numbers("2007-2015") == [2007.0, 2015.0], extract_numbers("2007-2015")
assert extract_numbers("-5 and 1,234.5") == [-5.0, 1234.5]
assert "SELECT" not in strip_code("a\n```sql\nSELECT 1\n```\nb")
print("helper asserts passed")

print(f"\n{len(cases) - failures}/{len(cases)} scoring tests passed")