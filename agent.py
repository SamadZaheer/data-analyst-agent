"""Data Analyst Agent: the agent loop (Step 5)."""
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import get_schema, run_sql

load_dotenv(Path(__file__).parent / ".env")

MODEL = "gemini-3.5-flash-lite"

MAX_STEPS = 10

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
        if not res["ok"]:
            return {"error": res["error"]} # goes back to Gemini so it can fix it
        text = res["data"].to_string(index=False)
        if res["truncated"]:
            text += "\n[Result truncated to 100 rows. Use aggregation or LIMIT.]"
        return {"result": text}

    # Gemini asked for a tool that doesn't exist!
    return {"error": f"Unknown tool '{name}'. Available: get_schema, run_sql."}



CLIENT = genai.Client()

CONFIG = types.GenerateContentConfig(
    tools=[TOOLS],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)

def ask(question: str) -> str:
    """Run the agent loop for one question and return the final answer text."""   
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    for step in range(1, MAX_STEPS + 1):
        response = CLIENT.models.generate_content(
            model=MODEL, contents=contents, config=CONFIG
        )

        if not response.candidates or response.candidates[0].content is None:
            return "Gemini returned an empty response."

        model_content = response.candidates[0].content
        contents.append(model_content)

        calls = response.function_calls
        if not calls:  # no tool requested -> this is the final answer
            print(f"[step {step}] final answer")
            return response.text

        result_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            print(f"\n[step {step}] Gemini requests: {fc.name}")
            if "query" in args:
                print(f"  SQL: {args["query"]}")

            result = execute_tool(fc.name, args)

            preview = result.get("result") or ("ERROR: " + result["error"])
            print(f"  -> {preview[:300]}{'...' if len(preview) > 300 else ''}")

            result_parts.append(types.Part(function_response=types.FunctionResponse(
                id=fc.id, name=fc.name, response=result
            )))

        # all results from this round go back together, as one turn
        contents.append(types.Content(role="user", parts=result_parts))

    return f"Stopped after {MAX_STEPS} steps without a final answer."

if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (blank to quit): ").strip()
        if not q:
            break
        print ("\nANSWER:", ask(q))