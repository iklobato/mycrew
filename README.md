# code_pipeline

A software development crew powered by [crewAI](https://crewai.com). Explores a codebase, clarifies ambiguities with the human, plans changes, implements them, reviews the work, and commits—exclusively for software development tasks.

## Installation

**Requirements:** Python >=3.10, <3.13

1. Install [uv](https://docs.astral.sh/uv/): `pip install uv`
2. Clone and install: `uv sync`
3. Create `.env` with `OPENROUTER_API_KEY=your_key_here` (or `OPENAI_API_KEY`)

**Optional:** `GITHUB_TOKEN` + `--github-repo` for GithubSearchTool; `--docs-url` for CodeDocsSearchTool; `--issue-url` for ScrapeWebsiteTool. CodeInterpreterTool (Implement stage) requires Docker.

## How to Use

| Option | Command |
|--------|---------|
| **Task** (recommended) | `task run` — uses `config.yaml`; copy `config.example.yaml` and edit |
| **CLI** | `uv run kickoff -c config.yaml` or `uv run kickoff -t "task" -r /path/to/repo` |
| **Docker** | `docker run -it --rm -v $(pwd):/workspace -w /workspace -e OPENROUTER_API_KEY=... iklobato/mycrew -c config.yaml` |

**Key flags:** `-t` task (required), `-r` repo-path, `-b` branch, `-f` from-scratch, `-n` retries, `--dry-run`, `--test-command`, `--github-repo`, `--issue-url`, `--docs-url`

**Task vars:** `TASK_DESC`, `R`, `B`, `V`, `DRY_RUN`, `TEST`, `GITHUB_REPO`, etc. — `task run TASK_DESC="add feature" R=./my-app`

## Agents

| Agent | Crew | Model | Responsibility |
|-------|------|-------|----------------|
| similar_issues_synthesizer | Issue Analyst | GPT-5 Nano | • Fetches similar issues/PRs via gh when github_repo set<br>• Produces Similar Issues + company moment |
| issue_analyst | Issue Analyst | Gemini 3 Flash | • Parses task into structured requirements (summary, criteria, scope)<br>• Uses ScrapeWebsite, GithubSearch, CodeDocsSearch |
| scope_validator | Issue Analyst | GPT-5 Nano | • Cross-checks for scope creep, vague criteria, conflicts<br>• Appends ## Scope Validation |
| acceptance_criteria_normalizer | Issue Analyst | GPT-5 Nano | • Normalizes criteria into numbered, testable checklist |
| repo_explorer | Explorer | Gemini 3 Flash | • Scans tech stack, layout, key files, conventions (read-only) |
| dependency_analyzer | Explorer | GPT-5 Nano | • Maps import/dependency graphs, blast radius |
| test_layout_scout | Explorer | GPT-5 Nano | • Documents test layout when test_command set |
| convention_extractor | Explorer | GPT-5 Nano | • Extracts lint/format config (black, eslint, pyproject) |
| api_boundary_scout | Explorer | GPT-5 Nano | • Maps API surface when task mentions API/endpoint |
| ambiguity_detector | Clarify | GPT-5 Nano | • Lists open questions (ownership, scope, migrations)—no ask_human |
| question_prioritizer | Clarify | GPT-5 Nano | • Ranks questions by impact for clarifier |
| clarifier | Clarify | Gemini 3 Flash | • Resolves ambiguities via ask_human with 2–4 code-snippet options |
| architect | Architect | Gemini 3 Flash | • Creates file-level plan (## Files to Create/Modify, no code) |
| dependency_orderer | Architect | GPT-5 Nano | • Orders files by dependency; flags ## Risk |
| refactor_guard | Architect | GPT-5 Nano | • Flags unnecessary refactors (REFACTOR_FLAGS or NONE) |
| test_plan_advisor | Architect | GPT-5 Nano | • Adds ## Test Plan when test_command set |
| migration_checker | Architect | GPT-5 Nano | • Flags migration steps when plan touches DB/config |
| rollback_planner | Architect | GPT-5 Nano | • Adds ## Rollback for high-risk areas |
| implementer | Implementer | Gemini 3 Flash | • Writes code via Repo File Writer for every file in plan |
| docstring_writer | Implementer | GPT-5 Nano | • Adds docstrings (Google/NumPy, JSDoc) |
| type_hint_checker | Implementer | GPT-5 Nano | • Adds type hints to Python changed code |
| test_writer | Implementer | GPT-5 Nano | • Adds/updates tests; runs test_command |
| lint_fixer | Implementer | GPT-5 Nano | • Runs black, ruff, eslint --fix per exploration |
| self_reviewer | Implementer | GPT-5 Nano | • Verifies plan adherence (SELF_REVIEW: PASS/ISSUES) |
| reviewer | Reviewer | DeepSeek V3.2 | • Main review: APPROVED or ISSUES; rejects overengineering |
| security_reviewer | Reviewer | GPT-5 Nano | • Checks SQL injection, XSS, auth bypass, secrets |
| performance_reviewer | Reviewer | GPT-5 Nano | • Flags N+1, unindexed queries, large loops |
| accessibility_checker | Reviewer | GPT-5 Nano | • Checks a11y when UI files changed |
| backward_compat_checker | Reviewer | GPT-5 Nano | • Flags breaking API changes |
| convention_checker | Reviewer | GPT-5 Nano | • Verifies conventions; merges final verdict |
| git_agent | Commit | Gemini 3 Flash | • Creates branch, stages, commits with Conventional Commits |
| commit_message_reviewer | Commit | GPT-5 Nano | • Validates commit message; amends if invalid |
| changelog_agent | Commit | GPT-5 Nano | • Appends CHANGELOG when file exists |
| pr_labels_suggester | Commit | GPT-5 Nano | • Suggests PR labels from task/plan |
| publish_agent | Commit | GPT-5 Nano | • Pushes branch, creates PR via gh; applies labels |

## Crew Members & Responsibilities

| Crew | Agents | Responsibilities |
|------|--------|------------------|
| **Issue Analyst** | similar_issues_synthesizer, issue_analyst, scope_validator, acceptance_criteria_normalizer | • Parse task into structured requirements (summary, criteria, scope)<br>• Fetch similar issues when github_repo set<br>• Validate scope; normalize criteria to testable checklist |
| **Explorer** | repo_explorer, dependency_analyzer, test_layout_scout, convention_extractor, api_boundary_scout | • Scan codebase structure, tech stack, conventions<br>• Map dependencies; document test layout; extract lint config<br>• Map API surface when task mentions API |
| **Clarify** | ambiguity_detector, question_prioritizer, clarifier | • List ambiguities; rank by impact<br>• Resolve via ask_human with options and code snippets |
| **Architect** | architect, dependency_orderer, refactor_guard, test_plan_advisor, migration_checker, rollback_planner | • Create file-level plan (no code)<br>• Order by dependency; guard refactors; add test plan<br>• Flag migrations; plan rollback for risky changes |
| **Implementer** | implementer, docstring_writer, type_hint_checker, test_writer, lint_fixer, self_reviewer | • Write code per plan; add docstrings and type hints<br>• Add tests; run linter; self-review plan adherence |
| **Reviewer** | reviewer, security_reviewer, performance_reviewer, accessibility_checker, backward_compat_checker, convention_checker | • Main review (APPROVED/ISSUES); security, perf, a11y<br>• Check API compat; conventions; merge final verdict |
| **Commit** | git_agent, commit_message_reviewer, changelog_agent, pr_labels_suggester, publish_agent | • Branch + commit; validate Conventional Commits<br>• Update CHANGELOG; suggest labels; push + create PR |
