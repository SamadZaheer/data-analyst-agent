from eval_cases import CASES
from tools import run_sql

REQUIRED = {'id', 'level', 'split', 'question', 'gold_sql', 'check'}
LEVELS = {'easy', 'medium', 'hard', 'unanswerable'}
SPLITS = {'dev', 'holdout'}
CHECKS = {'numbers', 'top', 'refuse'}
MAX_CELLS = 10

def validate(case):
    """Return a list of problems with one case's fields (empty = fine)."""
    problems = []
    missing = REQUIRED - case.keys()

    if missing:
        return [f"missing fleids: {sorted(missing)}"]
    if case['level'] not in LEVELS:
        problems.append(f"bad level {case['level']!r}")
    if case['split'] not in SPLITS:
        problems.append(f"bad split {case['split']!r}")
    if case['check'] not in CHECKS:
        problems.append(f"bad check {case['check']!r}")
    if (case['check'] == 'refuse') != (case['gold_sql'] is None):
        problems.append("refuse cases must have gold_sql=None (and only they)")

def main():
    ids = [c.get("id") for c in CASES]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    total_problems = len(dupes)
    if dupes:
        print(f"Duplicate ids: {dupes}")

    for case in CASES:
        cid = case.get("id", "?")
        print(f"\n=== {cid} ({case.get('level')}, {case.get('split')}, {case.get('check')})")
        print(f"Q: {case.get('question')}")

        problems = validate(case)
        if problems:
            total_problems += len(problems)
            for p in problems:
                print(f'  PROBLEM: {p}')
            continue

        if case["gold_sql"] is None:
            print(f"  (no gold SQL; expects refusal; must include {case.get('must_include', [])})")
            continue

        result = run_sql(case["gold_sql"])
        if not result["ok"]:
            total_problems += 1
            print(f"  PROBLEM: gold SQL failed: {result['error']}")
            continue

        df = result["data"]
        print(df.to_string(index=False))

        if case["check"] == "top":
            print(f"expected in answer: {df.iloc[0,0]!r}")
        if case["check"] == "numbers" and df.size > MAX_CELLS:
            print(f"  PROBLEM: {df.size} cells, keep numbers result to {MAX_CELLS} or fewer")
        if case.get("must_include"):
            print(f"  must_include: {case['must_include']}  <- check these matches the result above")

    counts = {}
    for c in CASES:
        key = (c.get("split"), c.get("level"))
        counts[key] = counts.get(key, 0) + 1

    print(f"\n{len(CASES)} cases: " + ", ".join(f"{s}/{l}={n}" for (s, l), n in sorted(counts.items())))
    print(f"All good." if total_problems == 0 else f"{total_problems} problem(s) found.")

if __name__ == '__main__':
    main()