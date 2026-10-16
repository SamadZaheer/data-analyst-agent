"""Fault injection: make the FIRST run_sql call fail, check the agent recovers."""
import agent

real_execute_tool = agent.execute_tool
state = {"failed_once": False}

def flaky_execute_tool(name, args):
    # Fail the first run_sql call only; everything else behaves normally
    if name == "run_sql" and not state["failed_once"]:
        state["failed_once"] = True
        return{
            "error": "Simulated error: database temporarily unavailable.",
            "hint": "The query did not run. Try the query again.",
        }

    return real_execute_tool(name, args)

# Swap in the flaky version (monkeypatching)

agent.execute_tool = flaky_execute_tool

print(agent.ask("How many fatal crashes were there in 2024?"))