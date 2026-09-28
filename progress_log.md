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
- Git identity (name/email) set **per repo only** (no `--global`) to keep work laptop settings untouched.
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