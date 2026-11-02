"""Data Analyst Agent: the agent loop (Step 5)."""
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT
import time
from google.genai import errors
from dataclasses import dataclass, field
import pandas as pd

from tools import get_schema, run_sql

@dataclass
class QueryRecord:
    """One run_sql call, exactly as OUR code executed it."""
    step: int
    sql: str
    ok: bool
    data: pd.DataFrame | None = None  # full result (<=100 rows): for scoring and charts
    error: str | None = None
    warning: str | None = None

@dataclass
class AgentResult:
    """Everything that happened while answering one question."""
    question: str
    answer: str = ""
    status: str = ""
    steps: int = 0
    failed_queries: int = 0
    queries: list[QueryRecord] = field(default_factory=list)
    error_code: int | None = None
    error_message: str | None = None   # raw API error text, for debugging
    seconds: float = 0.0

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
                "type": "string",
                "description": "A single DecukDB SQL SELECT statement"
            }
        },
        "required": ["query"],
    }
)

TOOLS = types.Tool(function_declarations=[GET_SCHEMA_DECL, RUN_SQL_DECL])


def _run_tool(name: str, args: dict | None) -> tuple[dict, pd.DataFrame | None]:
    """Run a tool. Returns (response for Gemini, raw DataFrame or None). Never raises."""
    args = args or {}

    if name == "get_schema":
        return {"result": get_schema()}, None

    if name == "run_sql":
        res = run_sql(str(args.get("query", "")))

        # Loud failure: SQL error -> goes back to Gemini so it can fix it
        if not res["ok"]:
            return {
                "error": res["error"],
                "hint": "The query did not run. Read the error, fix the SQL, and call "
                        "run_sql again. Check column names and category values against the schema.",
                }, None

        df = res["data"]

        # Quiet failure 1: no rows at all
        if df.empty:
            return{
                "result": "(0 rows)",
                "warning": "Query ran but returned 0 rows. If you expected data, a filter value "
                           "probably doesn't match exactly (check spelling and case against the schema).",
            }, df

        text = df.to_string(index=False)
        if res["truncated"]:
            text += "\n[Result truncated to 100 rows. Use aggregation or LIMIT.]"
        out = {"result": text}

        # Quiet failure 2: rows exist but every value is NULL (e.g. SUM over 0 rows)
        if df.isna().all().all():
            out["warning"] = ("Every value in this result is NULL. This usually means no rows "
                              "matched the filters (e.g. SUM over zero rows). Check filter values "
                              "against the schema before answering.")

        return out, df

    # Gemini asked for a tool that doesn't exist!
    return {"error": f"Unknown tool '{name}'. Available: get_schema, run_sql."}, None

def execute_tool(name: str, args:dict | None) -> dict:
    """Gemini's view only (kept so existing tests still work)."""
    return _run_tool(name, args)[0]


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

def ask(question: str, verbose: bool = True) -> AgentResult:
    """Run the agent loop for one question and return everything that happened."""
    log = print if verbose else (lambda *a, **k: None)
    start = time.perf_counter()
    result = AgentResult(question=question)
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    def finish(status: str, answer: str, error_code: int | None = None, error_message: str | None = None) -> AgentResult:
        result.status, result.answer = status, answer
        result.error_code, result.error_message = error_code, error_message
        result.seconds = round(time.perf_counter() - start, 1)
        log(f"\n[{status}: {result.steps} steps, {result.failed_queries} "
            f"failed/suspicious queries, {result.seconds}s]")
        return result

    for step in range(1, MAX_STEPS + 1):
        try:
            response = call_gemini(contents)
        except errors.APIError as e:
            if e.code == 429:
                msg = ("Gemini's free-tier limit has been reached. If it's the daily limit, "
                       "it resets at midnight US Pacific time (5 pm Brisbane during US "
                       "daylight saving, 6 pm otherwise). Please try again later.")
            elif e.code >= 500:
                msg = f"Gemini is unavailable right now (error {e.code}). Please try again shortly."
            else:
                msg = (f"The request to Gemini was rejected (error {e.code}). "
                       "This is a problem in the app, not a temporary outage.")
            return finish("api_error", msg, e.code, str(e))

        result.steps = step  # only counts requests that succeeded

        if not response.candidates or response.candidates[0].content is None:
            return finish("empty_response", "Gemini returned an empty response.")

        contents.append(response.candidates[0].content)

        calls = response.function_calls
        if not calls:
            log(f"[step {step}] final answer")
            return finish("answered", response.text or "")

        result_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            log(f"\n[step {step}] Gemini requests: {fc.name}")
            if "query" in args:
                log(f"  SQL: {args['query']}")

            tool_response, df = _run_tool(fc.name, args)

            # The recorder: what OUR code actually executed
            if fc.name == "run_sql":
                result.queries.append(QueryRecord(
                    step=step,
                    sql=str(args.get("query", "")),
                    ok="error" not in tool_response,
                    data=df,
                    error=tool_response.get("error"),
                    warning=tool_response.get("warning")
                ))

            preview = tool_response.get("result") or ("ERROR: " + tool_response["error"])
            log(f"  -> {preview[:300]}{'...' if len(preview) > 300 else ''}")
            if "warning" in tool_response:
                log(f"  -> WARNING: {tool_response['warning']}")
            if "error" in tool_response or "warning" in tool_response:
                result.failed_queries += 1
                log("   ↻ problem detected; the model should retry")

            result_parts.append(types.Part(function_response=types.FunctionResponse(
                    id=fc.id, name=fc.name, response=tool_response
            )))

        contents.append(types.Content(role="user", parts=result_parts))

    return finish("max_steps", f"Stopped after {MAX_STEPS} steps without a final answer.")    

if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (blank to quit): ").strip()
        if not q:
            break
        r = ask(q)
        print ("\nANSWER:", r.answer)