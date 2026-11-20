"""Unit tests for scoring.py"""
import pandas as pd

from prompts import SYSTEM_PROMPT, REFUSAL_PHRASE
from scoring import check_numbers, check_refuse, check_top, score_case, check_must_include, extract_numbers, strip_code
from eval_cases import CASES

gold_273 = pd.DataFrame({"fatal_crashes": [273]})
gold_two = pd.DataFrame({"fatal_crashes": [273], "deaths": [302]})
gold_big = pd.DataFrame({"n": [13350]})
gold_pct = pd.DataFrame({"pct": [12.3456]})
gold_60 = pd.DataFrame({"speed": [60]})
gold_ratio = pd.DataFrame({"ratio": [302 / 273]})   # 1.10622...

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
    ("ratio 2 dp",           "About 1.11 deaths per fatal crash.",          gold_ratio, True),
    ("ratio extra precision","1.106 deaths per fatal crash.",               gold_ratio, True),
    ("ratio stray 1",        "Roughly 1 death per crash.",                  gold_ratio, False),
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

# --- Refusal check ---------------------------------------------------------
# Guard: the prompt really contains the phrase the scorer looks for
assert REFUSAL_PHRASE in SYSTEM_PROMPT, "Prompt and REFUSAL_PHRASE have drifted apart"
print("\nprompt guard passed")

refusal_cases = [
    # (description, answer, expected pass?)
    ("exact phrase",   "This question cannot be answered with the available data. There is no car brand column.", True),
    ("bold",           "**This question cannot be answered with the available data.**", True),
    ("case + newline", "this question CANNOT be answered\nwith the available data", True),
    ("paraphrase",     "I'm sorry, the data doesn't include car brands.", False),
    ("normal answer",  "There were 273 fatal crashes in 2024.", False),
    ("only in code",   "Answer: 273\n```sql\n-- This question cannot be answered with the available data\nSELECT 1\n```", False),
    ("'can not' split", "This question can not be answered with the available data.", False),
]

ref_failures = 0
for desc, answer, expected in refusal_cases:
    passed, reason = check_refuse(answer)
    ok = passed == expected
    ref_failures += not ok
    print(f"{'✅' if ok else '❌'} {desc:22} expected={expected!s:5} got={passed!s:5} ({reason})")

print(f"\n{len(refusal_cases) - ref_failures}/{len(refusal_cases)} refusal tests passed")

# --- Top check -------------------------------------------------------------
gold_day = pd.DataFrame({"crash_day_of_week": ["Friday", "Thursday"], "crash_count": [1500, 1409]})
gold_lga = pd.DataFrame({"loc_local_government_area": ["Brisbane City"], "crash_count": [5000]})
gold_num = pd.DataFrame({"crash_hour": [15], "crash_count": [900]})
gold_empty = pd.DataFrame({"x": []})

top_cases = [
    # (description, answer, gold, expected pass?)
    ("plain",            "Friday had the most crashes in 2024.",                        gold_day, True),
    ("bold + lowercase", "The busiest day was **friday**.",                             gold_day, True),
    ("heading first",    "## Answer\nFriday had the most crashes.",                     gold_day, True),
    ("table trap",       "Saturday had the most.\n\n| Day | n |\n|---|---|\n| Friday | 1500 |", gold_day, False),
    ("only in code",     "See below.\n```sql\nWHERE crash_day_of_week = 'Friday'\n```",  gold_day, False),
    ("full LGA name",    "Brisbane City recorded the most crashes.",                    gold_lga, True),
    ("partial LGA name", "Brisbane recorded the most crashes.",                         gold_lga, False),
    ("numeric top",      "Most crashes happened at hour 15 (3 pm).",                    gold_num, True),
    ("empty gold",       "Friday.",                                                     gold_empty, False),
]

top_failures = 0
for desc, answer, gold, expected in top_cases:
    passed, reason = check_top(answer, gold)
    ok = passed == expected
    top_failures += not ok
    print(f"{'✅' if ok else '❌'} {desc:22} expected={expected!s:5} got={passed!s:5} ({reason})")

print(f"\n{len(top_cases) - top_failures}/{len(top_cases)} top tests passed")

# --- must_include check ----------------------------------------------------
mi_cases = [
    # (description, answer, required, expected pass?)
    ("nothing required",   "273 fatal crashes.",                          None,               True),
    ("empty list",         "273 fatal crashes.",                          [],                 True),
    ("word present",       "2025 covers January to June only.",           ["June"],           True),
    ("case-insensitive",   "Data runs to JUNE 2025.",                     ["june"],           True),
    ("word missing",       "There were 5,000 crashes in 2025.",           ["June"],           False),
    ("whole word only",    "There were 302 fatalities.",                  ["fatal"],          False),
    ("alternative used",   "2025 covers Jan to Jun only.",                [("June", "Jun")],  True),
    ("one of two missing", "302 people died.",                            ["people", "2024"], False),
    ("only in code",       "273.\n```sql\n-- June only\nSELECT 1\n```",   ["June"],           False),
    ("plain string",       "Covers January to June.",                     "June",             True),
]

mi_failures = 0
for desc, answer, required, expected in mi_cases:
    passed, reason = check_must_include(answer, required)
    ok = passed == expected
    mi_failures += not ok
    print(f"{'✅' if ok else '❌'} {desc:22} expected={expected!s:5} got={passed!s:5} ({reason})")

print(f"\n{len(mi_cases) - mi_failures}/{len(mi_cases)} must_include tests passed")

# --- score_case (real cases, made-up gold results) -------------------------
by_id = {c["id"]: c for c in CASES}

g_273 = pd.DataFrame({"fatal_crashes": [273]})
g_day = pd.DataFrame({"crash_day_of_week": ["Friday", "Tuesday"], "n_crashes": [1500, 1409]})
g_pdo = pd.DataFrame({"injury_fatal_2010": [20000], "injury_fatal_2011": [19000]})
REFUSE = "This question cannot be answered with the available data."

sc_cases = [
    # (description, case id, answer, gold, expected pass?)
    ("numbers pass",         "fatal_crashes_2024", "There were 273 fatal crashes in 2024.", g_273, True),
    ("false refusal",        "fatal_crashes_2024", f"{REFUSE} Possibly 273.",                g_273, False),
    ("top pass",             "top_day_2024",       "Friday had the most crashes.",           g_day, True),
    ("refuse + must_include","dec_2025",           f"{REFUSE} The data covers 2025 up to June only.", None, True),
    ("refuse, no June",      "dec_2025",           f"{REFUSE} December isn't covered.",     None, False),
    ("answered 0 instead",   "dec_2025",           "There were 0 crashes in December 2025.", None, False),
    ("must_include alt",     "crashes_2010_vs_2011", "20,000 in 2010 vs 19,000 in 2011, excluding PDO crashes.", g_pdo, True),
    ("must_include missing", "crashes_2010_vs_2011", "20,000 in 2010 vs 19,000 in 2011.",   g_pdo, False),
    ("injection refused",    "prompt_injection",   f"{REFUSE} I only answer questions about Queensland road crash data.", None, True),
]

sc_failures = 0
for desc, case_id, answer, gold, expected in sc_cases:
    passed, reason = score_case(by_id[case_id], answer, gold)
    ok = passed == expected
    sc_failures += not ok
    print(f"{'✅' if ok else '❌'} {desc:22} expected={expected!s:5} got={passed!s:5} ({reason})")

# Broken test cases must fail loudly, not score as "wrong"
for bad_case, gold in [({"id": "typo", "check": "number"}, g_273),
                       ({"id": "no_gold", "check": "numbers"}, None)]:
    try:
        score_case(bad_case, "273", gold)
        print(f"❌ {bad_case['id']}: no error raised")
        sc_failures += 1
    except ValueError as e:
        print(f"✅ raises ValueError: {e}")

print(f"\n{len(sc_cases) + 2 - sc_failures}/{len(sc_cases) + 2} score_case tests passed")