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