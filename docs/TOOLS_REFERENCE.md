# Code Pipeline Tools Reference

Reference for all tools used by pipeline crews. Parameters and example commands verified against the current repository.

**Running the pipeline:** Use `task run` (default: from scratch + `config.yaml`) or `uv run kickoff -c config.yaml`. See [README](../README.md) for full usage.

---

## Repo Shell Tool

**What it does:** Runs shell commands in the repository with `cwd=repo_path`. Output truncated at 8000 chars. Timeout 120s. Dangerous commands (rm -rf /, mkfs, etc.) are blocked. Absolute paths outside repo are rejected.

**Parameter:** `command` (str, required) — Single shell command. Use relative paths. Prefer read-only: ls, find, cat, head, grep. For tests use project's test runner (e.g. pytest, npm test).

**Example commands (run in repo root):**
```bash
# List directory
ls -la

# Find Python files
find src -name "*.py"

# Read file (first lines)
head -30 pyproject.toml

# Read full file
cat README.md

# Search content
grep -r "def " src --include="*.py" | head -20

# Run tests
pytest tests/ -v
```

**gh CLI (when GITHUB_REPO env is set):** Use `-R "owner/repo"` and `--state=value` (equals form):
```bash
gh issue list -R "owner/repo" --state=all -L 30
gh issue list -R "owner/repo" -S "search term" -L 10
gh issue view 123 -R "owner/repo"
gh pr list -R "owner/repo" --state=merged -L 15
gh pr list -R "owner/repo" --state=open -L 20
```

---

## Scrape Website Tool

**What it does:** Fetches a URL and extracts text content (no JS execution). Uses requests + BeautifulSoup.

**Parameter:** `website_url` (str, required) — Full URL to scrape (e.g. GitHub issue URL, Jira ticket URL).

**Example:** Use when the task contains a URL to fetch the full issue content.

---

## Github Search Tool

**What it does:** Semantic search over GitHub repo content (code, issues, PRs). NOT the GitHub API or gh CLI — uses RAG/embedding search. Requires GITHUB_TOKEN and github_repo.

**Parameters:**
- `search_query` (str, required) — Natural language or keyword query
- `github_repo` (str, optional if set at init) — owner/repo format
- `content_types` (list[str], optional) — Options: `["code", "repo", "pr", "issue"]`. Default all.

**Example:** Search for "login authentication flow" in repo to find similar implementations.

---

## Code Docs Search Tool

**What it does:** Semantic search over documentation site. Requires docs_url at init. Uses RAG.

**Parameter:** `search_query` (str, required) — Query to search docs (e.g. "conventions", "API patterns").

**Example:** When docs_url is provided, search for roadmap, priorities, or coding standards.

---

## File Writer Tool

**What it does:** Writes content to a file. Creates directory if missing.

**Parameters:**
- `filename` (str, required) — File name
- `content` (str, required) — Content to write
- `directory` (str, optional) — Base directory, default `./`
- `overwrite` (bool, optional) — Overwrite if exists, default False

**Example:** Create `src/module/new_file.py` with content. Use relative paths. Set overwrite=true to modify existing files.

---

## Code Interpreter Tool

**What it does:** Executes Python code. Prefers Docker for isolation; falls back to restricted sandbox if Docker unavailable. Requires Docker for full capability.

**Parameters:**
- `code` (str, required) — Python3 code. MUST include a final print of the result.
- `libraries_used` (list[str], required) — Pip-installable packages, e.g. `["numpy","pandas"]`

**Example:** Run data validation or test snippets. Always print the output.

---

## Ask Human Tool

**What it does:** Prompts the human operator with a question and returns their answer. Use when task is ambiguous.

**Parameter:** `question` (str, required) — Single focused question. Offer 2–4 options ordered from best to worst recommendation.

**Example:** One question per call. Ground in specific exploration findings (mention file or pattern).
