"""Fault injection: make the FIRST run_sql call fail, check the agent recovers."""
import agent

real_run_tool = agent._run_tool
state = {"failed_once": False}


def flaky_run_tool(name, args):
    # Fail the first run_sql call only; everything else behaves normally
    if name == "run_sql" and not state["failed_once"]:
        state["failed_once"] = True
        return {
            "error": "Simulated error: database temporarily unavailable.",
            "hint": "The query did not run. Try the query again.",
        }, None                      # same shape as _run_tool: (response, df)
    return real_run_tool(name, args)


# Patch the name ask() actually calls (monkeypatching)
agent._run_tool = flaky_run_tool

r = agent.ask("How many fatal crashes were there in 2024?")
print("\nANSWER:", r.answer)

# Check the premise first: did the fault actually happen?
assert state["failed_once"], "fault was never injected: is ask() still calling _run_tool?"
assert r.status == "answered", f"status was {r.status}"
assert r.failed_queries >= 1, "the failed query wasn't counted"
assert r.queries[0].ok is False, "first recorded query should be the failed one"
assert any(q.ok for q in r.queries), "agent never ran a successful query after the failure"
assert "273" in r.answer, "wrong final answer"
print("\n✅ retry test passed: fault injected, recorded, and recovered from")