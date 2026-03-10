# Code Pipeline

A comprehensive software development automation system powered by [crewAI](https://crewai.com). The pipeline processes software development tasks through 7 sequential crews: analysis, exploration, clarification, planning, implementation, review, and deployment. Each crew has specialized agents with specific tools and responsibilities.

## 🏗️ Architecture Overview

The pipeline consists of 7 sequential crews with specialized agents:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Code Pipeline Flow                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Issue Analyst → 2. Explorer → 3. Clarify → 4. Architect →            │
│ 5. Implementer → 6. Reviewer → 7. Commit                                │
└─────────────────────────────────────────────────────────────────────────┘
```

Each crew processes the task through multiple specialized agents, with output flowing sequentially to the next crew.

## 🚀 Quick Start

### Installation

**Requirements:** Python >=3.10, <3.13

```bash
# 1. Install uv (Python package manager)
pip install uv

# 2. Clone and install dependencies
git clone <repository-url>
cd code_pipeline
uv sync

# 3. Configure environment
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

### Configuration

Create `config.yaml` (based on `config.example.yaml`) with:

```yaml
pipeline:
  task: "Your development task here"
  repo_path: "."
  branch: "main"
  # ... other pipeline settings

api_keys:
  openrouter_api_key: "your_openrouter_key"  # Or use OPENROUTER_API_KEY env var
  github_token: "your_github_token"          # Optional: for GitHub integration

logging:
  level: "INFO"
  crewai_telemetry: false  # Disabled to avoid SSL issues

models:
  # Hierarchical model configuration
  analyze_issue:
    primary: "openrouter/google/gemini-3-flash-preview"
    fallbacks:
      - "openrouter/qwen/qwen3-coder:free"
      - "openrouter/deepseek/deepseek-r1"
  # ... other stage configurations
```

### Environment Variables (Alternative to config.yaml)
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - LLM API access
- `GITHUB_TOKEN` - For GitHub API integration (optional)
- `CODE_PIPELINE_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CREWAI_TRACING_ENABLED` - CrewAI telemetry (set to "false" to disable)

## 📋 Usage

### Running the Pipeline

```bash
# Using Task (recommended)
task run

# Using CLI directly
uv run kickoff -c config.yaml

# Or with command-line arguments
uv run kickoff -t "Add dark mode toggle" -r ./my-app -b main --dry-run

# Docker (if available)
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  -e OPENROUTER_API_KEY=your_key \
  iklobato/mycrew -c config.yaml
```

### Key Command-Line Arguments
- `-t, --task` - Task description (required)
- `-r, --repo-path` - Repository path (default: current directory)
- `-b, --branch` - Base branch for feature branches (default: "main")
- `-n, --retries` - Maximum retry attempts for failed implementations (default: 3)
- `--dry-run` - Skip git commit and PR creation
- `--test-command` - Test command (e.g., "pytest", "npm test")
- `--github-repo` - GitHub repository in owner/repo format
- `--issue-url` - Issue URL for web scraping
- `--docs-url` - Documentation URL for semantic search
- `--focus-paths` - Comma-separated paths to focus on
- `--exclude-paths` - Comma-separated paths to exclude

### Task Variables (when using `task run`)
```bash
task run TASK_DESC="Add feature" R=./my-app B=develop DRY_RUN=true
```

Available task variables: `TASK_DESC`, `R` (repo_path), `B` (branch), `V` (from_scratch), `DRY_RUN`, `TEST` (test_command), `GITHUB_REPO`, `ISSUE_URL`, `DOCS_URL`, `FOCUS_PATHS`, `EXCLUDE_PATHS`

## 👥 Crews & Agents

### 1. Issue Analyst Crew (`analyze_issue` stage)
**Primary Model**: `openrouter/google/gemini-3-flash-preview`

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **similar_issues_synthesizer** | `RepoShellTool` | `{repo_context}`, `{task}`, `{github_repo}` | `## Similar Issues` section | • Fetch similar GitHub issues/PRs via `gh` CLI<br>• Produce "company moment" (recent merges + open work)<br>• Output: Issues consulted, Out-of-scope in similar |
| **issue_analyst** | `ScrapeWebsiteTool`, `GithubSearchTool`, `RepoShellTool`, `CodeDocsSearchTool` | `{repo_context}`, `{task}`, `{branch}`, context from previous | Structured document with sections: Context, Summary, Acceptance Criteria, Scope, Technical Hints | • Parse task into structured requirements<br>• Use tools to gather context (web, GitHub, docs)<br>• Derive scope from task + similar issues<br>• Keep acceptance criteria minimal |
| **scope_validator** | `RepoShellTool` | Output from `issue_analyst`, `{task}` | Original document + `## Scope Validation` | • Cross-check for scope creep, vague criteria, conflicts<br>• Flag: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`<br>• Append validation without rewriting |
| **acceptance_criteria_normalizer** | None | Output from `scope_validator` | Full document + `## Acceptance Criteria (Normalized)` | • Normalize criteria into numbered, unambiguous, testable checklist<br>• Keep all prior sections |

### 2. Explorer Crew (`explore` stage)
**Primary Model**: `openrouter/deepseek/deepseek-r1`

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **repo_explorer** | `RepoShellTool`, `CodeDocsSearchTool` | `{repo_context}`, `{task}`, `{docs_url}` | Exploration report | • Scan tech stack, layout, key files, conventions<br>• Read-only codebase exploration |
| **dependency_analyzer** | `RepoShellTool`, `CodeDocsSearchTool` | Context from previous agents | Dependency graphs, blast radius analysis | • Map import/dependency relationships<br>• Analyze impact radius of changes |
| **test_layout_scout** | `RepoShellTool`, `CodeDocsSearchTool` | `{test_command}`, context | Test layout documentation | • Document test structure when `test_command` set<br>• Identify test patterns and locations |
| **convention_extractor** | `RepoShellTool`, `CodeDocsSearchTool` | Context from previous agents | Lint/format configuration | • Extract black, eslint, pyproject.toml configs<br>• Identify code style conventions |
| **api_boundary_scout** | `RepoShellTool`, `CodeDocsSearchTool` | Context, `{task}` | API surface mapping | • Map API surface when task mentions API/endpoint<br>• Identify API boundaries and patterns |

### 3. Clarify Crew (`auxiliary`/`analyze_issue` stage)
**Models**: `auxiliary` (GPT-5 Nano), `analyze_issue` (Gemini 3 Flash for clarifier)

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **ambiguity_detector** | `RepoShellTool` | `{repo_context}`, `{task}`, analysis | List of open questions | • Identify ambiguities (ownership, scope, migrations)<br>• No human interaction in this stage |
| **question_prioritizer** | `RepoShellTool` | Output from `ambiguity_detector` | Prioritized questions list | • Rank questions by impact and urgency<br>• Prepare for human clarification |
| **clarifier** | `ask_human` | Prioritized questions, context | Clarified requirements with code-snippet options | • Resolve ambiguities via human interaction<br>• Present 2-4 code-snippet options for decisions |

### 4. Architect Crew (`plan` stage)
**Primary Model**: `openrouter/google/gemini-3-flash-preview`

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **architect** | `RepoShellTool`, `CodeDocsSearchTool`, `GithubSearchTool` | `{repo_context}`, `{task}`, acceptance criteria, exploration | File-level plan with `## Files to Create/Modify` | • Create implementation plan (no code)<br>• Determine which files to create/modify |
| **dependency_orderer** | `RepoShellTool` | Architect's plan | Ordered plan with `## Risk` flags | • Order files by dependency<br>• Flag implementation risks |
| **refactor_guard** | `RepoShellTool` | Ordered plan | Plan with `REFACTOR_FLAGS` or `NONE` | • Flag unnecessary refactors<br>• Prevent scope creep through refactoring |
| **test_plan_advisor** | `RepoShellTool` | Plan, `{test_command}` | Plan + `## Test Plan` | • Add test strategy when `test_command` set<br>• Plan test implementation approach |
| **migration_checker** | `RepoShellTool` | Plan | Plan with migration flags | • Flag migration steps when plan touches DB/config<br>• Identify data migration needs |
| **rollback_planner** | `RepoShellTool` | Plan | Plan + `## Rollback` for high-risk areas | • Add rollback strategy for risky changes<br>• Plan for graceful failure recovery |

### 5. Implementer Crew (`implement` stage)
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **implementer** | `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` | Final plan, `{repo_context}` | Code implementation for all files | • Write actual code using file writer<br>• Implement all files from plan |
| **docstring_writer** | `RepoShellTool`, `RepoFileWriterTool` | Implementation, conventions | Code with docstrings (Google/NumPy, JSDoc) | • Add documentation to changed code<br>• Follow project documentation standards |
| **type_hint_checker** | `RepoShellTool`, `RepoFileWriterTool` | Code with docstrings | Code with type hints | • Add type hints to Python code<br>• Improve code clarity and IDE support |
| **test_writer** | `RepoShellTool`, `RepoFileWriterTool` | Code, `{test_command}`, test layout | Tests added/updated | • Write tests, run `test_command`<br>• Ensure test coverage |
| **lint_fixer** | `RepoShellTool` | Code, conventions | Linted code | • Run black, ruff, eslint --fix<br>• Enforce code style conventions |
| **self_reviewer** | `RepoShellTool` | Final implementation, original plan | `SELF_REVIEW: PASS/ISSUES` | • Verify plan adherence<br>• Perform initial quality check |

### 6. Reviewer Crew (`review` stage)
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **reviewer** | `RepoShellTool`, `CodeDocsSearchTool` | Implementation, plan, acceptance criteria | `ReviewVerdict` (APPROVED or ISSUES) | • Main review against requirements<br>• Reject overengineering, ensure plan adherence |
| **security_reviewer** | `RepoShellTool`, `CodeDocsSearchTool` | Implementation | Security findings | • Check SQL injection, XSS, auth bypass, secrets<br>• Identify security vulnerabilities |
| **performance_reviewer** | `RepoShellTool` | Implementation | Performance findings | • Flag N+1 queries, unindexed queries, large loops<br>• Identify performance bottlenecks |
| **accessibility_checker** | `RepoShellTool` | Implementation (UI files) | Accessibility findings | • Check a11y compliance when UI changed<br>• Ensure accessibility standards |
| **backward_compat_checker** | `RepoShellTool` | Implementation | Compatibility findings | • Flag breaking API changes<br>• Ensure backward compatibility |
| **convention_checker** | `RepoShellTool`, `CodeDocsSearchTool` | Implementation, conventions | Convention compliance findings | • Verify code style conventions<br>• Merge final review verdict |

### 7. Commit Crew (`commit`/`publish`/`auxiliary` stage)
**Models**: `commit` (Qwen Coder Free), `publish`/`auxiliary` (Trinity Mini Free)

| Agent | Tools | Inputs | Outputs | Responsibilities |
|-------|-------|--------|---------|------------------|
| **git_agent** | `RepoShellTool` | Implementation, `{branch}`, `{dry_run}` | Feature branch, committed changes | • Create branch, stage changes<br>• Commit with Conventional Commits format |
| **commit_message_reviewer** | `RepoShellTool` | Commit message | Validated/amended commit message | • Validate Conventional Commits format<br>• Amend if invalid |
| **changelog_agent** | `RepoShellTool`, `RepoFileWriterTool` | Commit, task, `{dry_run}` | Updated CHANGELOG (if exists) | • Append CHANGELOG entry<br>• Maintain project changelog |
| **pr_labels_suggester** | None | Task, plan | Suggested PR labels | • Analyze task to suggest 1-5 relevant labels<br>• Prepare for PR creation |
| **publish_agent** | `CreatePRTool` | Feature branch, base branch, task, implementation, plan, review_verdict, github_repo, labels | PR URL | • Push branch to remote<br>• Create PR via `gh` CLI, apply labels<br>• Complete deployment cycle |

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

## TODO

- **Separate pipelines** — Build a dedicated development pipeline (analyze → implement → commit) and a separate code-review pipeline (review PRs on demand), each with its own flow and entry points.
- **Webhook: development pipeline** — Add webhook handlers to trigger the development pipeline when an issue or project card is assigned (e.g., GitHub issue assigned, Jira/Linear card moved to "In Progress").
- **Webhook: code review pipeline** — Add webhook handlers to trigger the code-review pipeline when a PR receives a new comment or a code review is submitted.
- **CrewAI architecture** — Deepen understanding of CrewAI (crews, tasks, agents, tools, flows) and restructure the codebase for better separation of concerns and maintainability.
- **Model optimization** — Revisit model selection per stage: use cheaper models where sufficient, reserve stronger models for critical steps (e.g., review, plan) to reduce cost without losing quality.
- **Agent prompting** — Refine role, goal, and backstory for all agents to improve clarity, consistency, and output quality.
- **Parallelization** — Identify independent steps (e.g., within Explorer, Reviewer crews) and run them in parallel to reduce end-to-end latency.
- **Ollama integration** — Add Ollama as an LLM backend for local inference and cost savings.
