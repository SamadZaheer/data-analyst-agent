# Progress Log — Data Analyst Agent

Paste a new entry at the bottom at the end of each chat. Newest entry = where I am now.

---

## Entry 0 — Planning (28 Sep 2026)
**Done:**
- Learned what an AI agent is (LLM + tools + loop + goal).
- Chose project #1: Data Analyst Agent (ask questions in plain English → agent writes/runs SQL → answers with SQL shown + chart).

**Decisions:**
- Completely free stack: Gemini API free tier, Python, DuckDB, Streamlit, Streamlit Community Cloud, GitHub.
- Version 1 uses the plain Gemini SDK (`google-genai`), no frameworks. LangGraph is an optional Version 2.
- Public Australian/Queensland dataset (to be chosen in Step 3).
- Must include: evaluation, self-correction, guardrails, transparency.
- Work step by step in a Claude Project, one chat per step, with this log for continuity.

**Files created:** none yet.

**Next step:** Step 1 — Set up the computer.

## Entry 1 — Step 1: Computer setup (28 Sep 2026)
**Done:**
- Installed Python 3.13.15, VS Code (+ Microsoft Python extension), Git 2.55.
- Created project folder at `~\Projects\data-analyst-agent` (not in OneDrive).
- Created and activated a virtual environment (`.venv`); installed google-genai, streamlit, pandas, duckdb, python-dotenv. Import test passed.
- Selected the `.venv` interpreter in VS Code, so the VS Code terminal auto-activates the venv.
- Initialised Git, made first commit, created public repo `data-analyst-agent` on personal GitHub, pushed successfully.

**Decisions:**
- Use plain "Windows PowerShell" or (preferably) the VS Code terminal (Ctrl+`); not admin, not x86/ISE.
- Execution policy set to RemoteSigned for CurrentUser (permanent).
- Git identity (name/email) set **per repo only** (no `--global`) to keep global Git settings untouched.
- `requirements.txt` hand-written with top-level libraries only (no `pip freeze`: avoids Windows-specific deps and PowerShell UTF-16 encoding bug). Pin versions before deploying.
- Skipped GitHub Copilot sign-in in VS Code (learning by writing code myself).
- Repo is public (portfolio); created without README/.gitignore on GitHub to avoid history conflicts.

**Files created:**
- `requirements.txt`: the 5 libraries.
- `.gitignore`: .venv/, .env, .streamlit/secrets.toml, data/, *.duckdb, *.duckdb.wal, __pycache__/, *.pyc, .vscode/, .DS_Store, Thumbs.db.

**Problems solved:**
- "Running scripts is disabled": fixed with `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`.
- "No matching commands" for Python in VS Code: the Python extension wasn't installed.
- `git status` said "nothing to commit": files were already committed (checked with `git log --oneline` and `git ls-files`).

**Concepts learned:**
- venv = private library folder per project; activation is per terminal session, the execution policy is permanent.
- Git: init → add (stage) → commit (save point) → remote (origin) → push (-u sets tracking).
- `.gitignore` must come before the first commit: a committed secret stays in history.

**Session habit:** open the project with `code .` or from VS Code, use the VS Code terminal, and finish each session with `git add .` → `git commit -m "..."` → `git push`.

**Next step:** Step 2: Get a Gemini API key from Google AI Studio (personal Google account), store it in `.env`, and write a hello-world script.

## Entry 2 — Step 2: Gemini API key + hello world (29 Sep 2026)
**Done:**
- Created a free Gemini API key in Google AI Studio (personal Google account).
- Stored it in `.env` as `GEMINI_API_KEY`; confirmed Git ignores it (`git check-ignore -v .env` → line 5 of .gitignore).
- Wrote `hello_gemini.py`: loads `.env` with python-dotenv (pathlib path), creates `genai.Client()`, calls `generate_content`, prints the reply. Works.

**Decisions:**
- Development model: `gemini-3.5-flash-lite` (free tier: 15 RPM, 250k TPM, 500 RPD). `gemini-3.8-flash` is smarter but only 20 RPD, which is too few for an agent (~4–6 requests per question). Keep 3.8 Flash for a model comparison in Step 7.
- Model name kept in one constant (`MODEL`) because Google renames models often.
- Did NOT enable VS Code's "python.terminal.useEnvFile": the code loads `.env` itself so it behaves the same everywhere (Mac, plain terminal, Streamlit Cloud).

**Files created:**
- `.env` (not in Git): the API key.
- `hello_gemini.py`: connection test script.

**Problems solved / notes:**
- AFC warning ("Direct use of automatic function calling... not recommended"): harmless. AFC = the SDK's built-in agent loop; we'll disable it in Step 5 because we write our own loop.
- Rate limits: RPM = requests/minute, TPM = tokens/minute, RPD = requests/day (resets at midnight US Pacific). Check live numbers at aistudio.google.com/rate-limit. A public app will share this quota: add a "daily limit reached" message at deploy time.

**Concepts learned:**
- API key = identifies who's calling; keep it in env variables, never in code.
- LLM APIs are stateless: each call is independent, so the agent's "memory" (conversation history) must be kept and resent by my code. This is why the agent needs a loop.

**Next step:** Step 3: Choose a public Queensland/Australian dataset, write a data-loading script (pandas → DuckDB), and write 5 questions with answers I've checked myself.

## Entry 3 — Step 3: Data chosen and loaded (30 Sep – 2 Oct 2026)
**Done:**
- Chose Queensland road crash data (TMR, data.qld.gov.au, CC BY 4.0).
- Downloaded 6 CSVs into `data/raw/`; links saved in `datasources.md`.
- Explored each file with pandas and identified each table's grain.
- Wrote `load_data.py`: downloads missing files, cleans, builds `data/crashes.duckdb` from scratch (idempotent).
- Ran consistency checks and reconciliations; wrote 5 hand-checked test questions.

**Decisions:**
- 5 tables: `crashes` (row-level, 1 row = 1 crash, 415,407 rows, 42 cols) + 4 aggregated tables with `agg_` prefix (casualties, driver_involvement, restraint_helmet_use, crash_factors).
- Dropped `_d_vehicle_involvement` (duplicates the crash table's vehicle counts; one source of truth per question).
- Dropped 11 crash columns (extra geography levels, detailed DCA codes) to keep the schema simple for the agent.
- Standardised names: all lowercase snake_case; one `police_region` column everywhere; consistent `count_casualty_*` names; casualty severity values mapped to crash wording (Fatality → Fatal, etc.).
- Added `crash_month_num` (month names sort alphabetically).
- `exploration.txt` added to `.gitignore` (regenerable output).
- Deployment data size (213 MB raw CSV) to be decided in Step 9.

**Files created:**
- `explore_data.py` (shape/types/sample of each CSV), `explore_checks.py` (year × severity crosstab)
- `load_data.py` (pipeline), `sql.py` (run a SQL query from the terminal, read-only)
- `datasources.md` (download links), `test_questions.md` (5 questions + data caveats)

**Data findings (caveats for the system prompt):**
- Property-damage-only crashes only included up to 2010 (drop to 0 from 2011 is not real).
- 2025 covers Jan–Jun only.
- 'Fatal' severity counts crashes; `count_casualty_fatality` counts people (2024: 273 fatal crashes, 302 deaths).
- `agg_` tables need `SUM(count_crashes)` / `SUM(casualty_count)`, not `COUNT(*)`.
- `police_region` has an "Unknown" value; police regions ≠ LGAs ("Brisbane"); some LGA names are outdated ("Moreton Bay Region").
- Minor-injury counts drop sharply 2007–2015 (likely a recording change, not a real trend).

**Checks passed:**
- All 8 police regions spelled identically in all 5 tables.
- `agg_crash_factors` totals for 2024 match `crashes` exactly (273 / 7051 / 4409 / 2625).
- Deaths in 2024 match across `crashes` and `agg_casualties` (302).

**Concepts learned:**
- Grain: what one row represents; row-level vs pre-aggregated tables; look for ID columns and count columns.
- Idempotent pipelines; raw data never edited; fail loudly on unexpected values.
- Reconciliation as a data-quality check; SQL row order isn't guaranteed without ORDER BY.

**Next step:** Step 4 — Write the tools: `get_schema()` and `run_sql(query)` (SELECT-only, read-only, row limit).

## Entry 4 — Step 4: Tools written (5–7 Oct 2026)
**Done:**
- Wrote `tools.py` with two agent tools: `get_schema()` and `run_sql(query)`.
- `get_schema()`: lists every table (with row count), column and type; for VARCHAR columns, lists all values if ≤ 25 distinct, otherwise the distinct count + 3 most common values. Output ~2,050 tokens. Cached with `@lru_cache`.
- `run_sql()`: three guardrail layers, all tested: (1) read-only connection with `enable_external_access: False`, (2) `duckdb.extract_statements()` check for exactly one SELECT, (3) 100-row cap (fetch 101 to detect truncation).
- Test suite in `tools.py` (`python tools.py`): normal query, silent wrong value, truncation, column typo, DROP, multi-statement, local file read, read-only bypass test. All passed.

**Decisions:**
- Tools return plain text (schema) / a dict (`{"ok", "data", "truncated"}` or `{"ok": False, "error"}`), never raise on SQL errors, so errors can go back to the LLM for self-correction (Step 6).
- `run_sql` keeps a DataFrame (not text) so Streamlit can chart it later; converting to text for the LLM happens in Step 5.
- Schema = facts the database can report automatically; human knowledge (caveats) goes in the system prompt.
- Fresh connection per call (cheap in DuckDB, avoids file locks with Streamlit).

**Files created/changed:**
- `tools.py` (new).
- `test_questions.md`: added "Schema findings (Step 4)" caveats.

**Problems solved:**
- Top-3 values showed `None`: the query was missing `WHERE ... IS NOT NULL` (Python `None` = SQL NULL; a string would print as `'None'`).

**Data findings (for the system prompt):**
- Speed limits are buckets ('100 - 110 km/h'); road user categories differ between `agg_casualties` and `agg_restraint_helmet_use` (no pedestrians in the latter); 'Hit pedestrian' in both `crash_type` and `crash_nature`; sort months by `crash_month_num`; `involving_*` flags are 'Yes'/'No' text; NULL is the most common value in `crash_street_intersecting` and `state_road_name`.
- Always alias aggregates (unnamed `COUNT(*)` comes back as `count_star()`).

**Concepts learned:**
- A tool is a plain function; the LLM only *requests* calls, and my code decides whether to run them.
- Silent wrong answers (guessed categorical values) are a key text-to-SQL failure; real values in the schema are the fix.
- Defence in depth; read-only ≠ safe (file access must be blocked too, as a prompt-injection defence); parse SQL rather than string-match it.
- Token budgeting: measure the size of anything sent on every request.
- Handy command: `python -c "from tools import get_schema; print(get_schema())"`.

**Next step:** Step 5: Build the agent loop (describe tools to Gemini, disable AFC, run requested tools, send results back, cap at ~10 steps, print each step in the terminal).