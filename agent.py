"""Data Analyst Agent: the agent loop (Step 5)."""
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT
import time
from google.genai import errors

from tools import get_schema, run_sql

load_dotenv(Path(__file__).parent / ".env")

MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 10
RETRY_DELAYS = [5, 15, 30] # seconds to wait before retry 1, 2, 3
RETRYABLE_CODES = {429, 500, 503}

# Tool descriptions: this is ALL gemini knows about our tools
GET_SCHEMA_DECL = types.FunctionDeclaration(
    name="get_schema",
    description=(
        "Returns every table in the Queensland road crash database, with row counts, "
        "column names, column types, and the allowed values of text columns. "
        "Call this FIRST, before writing any SQL."
    ),
    # no parametrs: this tool takes no arguments
)

RUN_SQL_DECL = types.FunctionDeclaration(
    name="run_sql",
    description=("Runs ONE read-only DuckDB SELECT query and returns the result as text "
        "(at most 100 rows). If the query fails, returns the error message so "
        "you can fix the query and try again."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "object",
                "description": "A single DecukDB SQL SELECT statement"
            }
        },
        "required": ["query"],
    }
)

TOOLS = types.Tool(function_declarations=[GET_SCHEMA_DECL, RUN_SQL_DECL])


def execute_tool(name: str, args: dict | None) -> dict:
    """Run the tool Gemini asked for. Always returns a dict, never raises:"""
    args = args or {}

    if name == "get_schema":
        return {"result": get_schema()}

    if name == "run_sql":
        res = run_sql(args.get("query", ""))

        # Loud failure: SQL error -> goes back to Gemini so it can fixt it
        if not res["ok"]:
            return {
                "error": res["error"],
                "hint": "The query did not run. Read the error, fix the SQL, and call "
                        "run_sql again. Check column names and category values against the schema.",
                } 

        df = res["data"]

        # Quiet failure 1: no rows at all
        if df.empty:
            return{
                "result": "(0 rows)",
                "warning": "Query ran but returned 0 rows. If you expected data, a filter value "
                           "probably doesn't match exactly (check spelling and case against the schema).",
            }

        text = df.to_string(index=False)
        if res["truncated"]:
            text += "\n[Result truncated to 100 rows. Use aggregation or LIMIT.]"
        out = {"result": text}

        # Quiet failure 2: rows exist but every value is NULL (e.g. SUM over 0 rows)
        if df.isna().all().all():
            out["warning"] = ("Every value in this result is NULL. This usually means no rows "
                              "matched the filters (e.g. SUM over zero rows). Check filter values "
                              "against the schema before answering.")

        return out

    # Gemini asked for a tool that doesn't exist!
    return {"error": f"Unknown tool '{name}'. Available: get_schema, run_sql."}



CLIENT = genai.Client()

CONFIG = types.GenerateContentConfig(
    tools=[TOOLS],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    system_instruction=SYSTEM_PROMPT,
)

def call_gemini(contents):
     """Call Gemini, retrying temporary errors with backoff. Raises if it can't recover."""
     for attempt in range(len(RETRY_DELAYS) + 1):
         try:
             return CLIENT.models.generate_content(model=MODEL, contents=contents, config=CONFIG)
         except errors.APIError as e:
             # Daily quota: waiting seconds won't help, give up now
             if e.code == 429 and "PerDay" in str(e):
                 raise
             # Not temporary; or out of retries
             if e.code not in RETRYABLE_CODES or attempt == len(RETRY_DELAYS):
                 raise
             wait = RETRY_DELAYS[attempt]
             print(f"   ⏳ Gemini error {e.code}; waiting {wait}s (retry {attempt + 1}/{len(RETRY_DELAYS)})")
             time.sleep(wait)

def ask(question: str) -> str:
    """Run the agent loop for one question and return the final answer text."""   
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    failed_queries = 0

    for step in range(1, MAX_STEPS + 1):
        try :
            response = call_gemini(contents)
        except errors.APIError as e:
            print(f"\n[stopped: Gemini error {e.code} after {step-1} completed steps.]")
            if e.code == 429:
                return("Gemini's free-tier limit has been reached. If it's the daily limit, "
                        "it resets at midnight US Pacific time (5 pm Brisbane during US "
                        "daylight saving, 6 pm otherwise). Please try again later.")
            return f"Gemini is unavailable right now (error {e.code}). Please try again shortly." 

        if not response.candidates or response.candidates[0].content is None:
            return "Gemini returned an empty response."

        model_content = response.candidates[0].content
        contents.append(model_content)

        calls = response.function_calls
        if not calls:  # no tool requested -> this is the final answer
            print(f"[step {step}] final answer")
            print(f"\n[{step} steps, {failed_queries} failed/suspicious queries]")
            return response.text

        result_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            print(f"\n[step {step}] Gemini requests: {fc.name}")
            if "query" in args:
                print(f"  SQL: {args['query']}")

            result = execute_tool(fc.name, args)

            preview = result.get("result") or ("ERROR: " + result["error"])
            print(f"  -> {preview[:300]}{'...' if len(preview) > 300 else ''}")

            if "warning" in result:
                print(f"  -> WARNING: {result['warning']}")

            if "error" in result or "warning" in result:
                failed_queries += 1
                print("   ↻ problem detected; the model should retry")

            result_parts.append(types.Part(function_response=types.FunctionResponse(
                id=fc.id, name=fc.name, response=result
            )))

        # all results from this round go back together, as one turn
        contents.append(types.Content(role="user", parts=result_parts))

    print(f"\n[{step} steps, {failed_queries} failed/suspicious queries]")

    return f"Stopped after {MAX_STEPS} steps without a final answer."

if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (blank to quit): ").strip()
        if not q:
            break
        print ("\nANSWER:", ask(q))