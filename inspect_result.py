"""Look inside an AgentResult."""
from agent import ask

r = ask("How many fatal crashes were there in 2024?", verbose=True)

print(f"\nstatus={r.status}  steps={r.steps}  failed={r.failed_queries}  seconds={r.seconds}")
if r.error_message:
    print(f"\nERROR DETAIL:\n{r.error_message}")

print(f"\n{len(r.queries)} query/queries recorded")
for q in r.queries:
    print(f"\n--- query at step {q.step} (ok={q.ok}) ---")
    print(q.sql)
    print(q.data)
    print(type(q.data))

print("\nANSWER:\n", r.answer)