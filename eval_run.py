"""Evaluation runner: runs the agent on test cases and scores the asnwers."""
import hashlib

from agent import ask, MODEL
from prompts import SYSTEM_PROMPT
from tools import run_sql
from scoring import score_case, diagnose, execution_match
from eval_cases import CASES
import time

# Short fingerprint of the system prompt. It changes whenever the prompt changes.
PROMPT_HASH = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:8]

def get_gold(case):
    """Run the case's gold SQL. Returns a DataFrame, or None for refuse cases."""
    sql = case.get("gold_sql")
    if not sql:
        return None
    res = run_sql(sql)
    if not res["ok"]:
        raise RuntimeError(f"Gold SQL failed for {case['id']}: {res['error']}")
    return res["data"]

def run_case(case):
    """Run one test case end to end and return one result row (a dict)."""
    gold_df = get_gold(case)
    r = ask(case["question"], verbose=False)

    row = {
        "id": case["id"],
        "split": case.get("split"),
        "level": case.get("level"),
        "check": case["check"],
        "status": r.status,
        "steps": r.steps,
        "error": r.error_message,
        "failed_queries": r.failed_queries,
        "seconds": round(r.seconds, 1),
        "answer": r.answer,
        "sql": [q.sql for q in r.queries],
        "model": MODEL,
        "prompt_hash": PROMPT_HASH,
    }

    if r.status == "api_error":
        # Infrastructure failure: excluded from accuracy, re-run later.
        row.update(passed=None, reason=f"excluded: {r.error_code}", exec_match=None, diagnosis="excluded")
        return row

    passed, reason = score_case(case, r.answer, gold_df)
    exec_match = execution_match(case, r.queries, gold_df)
    row.update(passed=passed, reason=reason, exec_match=exec_match, diagnosis=diagnose(passed, exec_match))
    return row

RPM_LIMIT = 15
SECONDS_PER_REQUEST = 60 / RPM_LIMIT    # 4.0 seconds per request

def select_cases(split="dev", ids=None, limit=None):
    """Pick which ytest cases to run: one split, optionally only some ids or the first N."""
    cases = [c for c in CASES if c["split"] == split]
    if ids:
        cases = [c for c in cases if c["id"] in ids]
        missing = set(ids) - {c["id"] for c in cases}
        raise ValueError(f"Unknown case ids for split '{split}': {missing}")
    if limit:
        cases = cases[:limit]
    return cases

def _progress_label(row):
    """One short line summarising a finished case."""
    mark = {True: "PASS", False: "FAIL", None: "SKIP"}[row["passed"]]
    return f"{mark}  {row['diagnosis']}  ({row['steps']} steps, {row['seconds']}s)"

def run_eval(cases):
    """Run cases one by one with pacing. Returns a list of result rows."""
    if not cases:
        raise ValueError("No cases selected: check the split, ids and limit.")
    rows = []
    total = len(cases)
    for i, case in enumerate(cases, start=1):
        print(f"[{i}/{total}] {case['id']} ...", end=" ", flush=True)
        row = run_case(case)
        rows.append(row)
        print(_progress_label(row))

        # Daily quota gone: every remaining case would fail too, so stop.
        if row["status"] == "api_error" and "PerDay" in (row["error"] or ""):
            print("\nDaily quota reached: stopping the run early.")
            break

        # Pacing: ive each request we just used 4 seconds of "budget".
        if i < total:
            wait = SECONDS_PER_REQUEST * row["steps"] - row["seconds"]
            if wait > 1:
                time.sleep(wait)

    return rows

if __name__ == "__main__":
    print(f"Prompt hash: {PROMPT_HASH}  Model: {MODEL}\n")
    cases = select_cases(limit=3)
    rows = run_eval(cases)
    passed = sum(r["passed"] is True for r in rows)
    print(f"\n{passed}/{len(rows)} passed")