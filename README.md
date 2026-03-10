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
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - LLM API access (required)
- `SERPER_API_KEY` - Serper API key for web search integration (optional)
- `GITHUB_TOKEN` - For GitHub API integration (optional)
- `CODE_PIPELINE_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CREWAI_TRACING_ENABLED` - CrewAI telemetry (set to "false" to disable)

### Web Search Integration (SerperDevTool)

The pipeline includes comprehensive web search integration via SerperDevTool. When enabled, agents can research technologies, patterns, and solutions during analysis, exploration, architecture, and review stages.

**Configuration:**
```yaml
# In config.yaml
api_keys:
  serper_api_key: "your_serper_api_key"  # Get from https://serper.dev

tools:
  serper:
    enabled: true  # Enable/disable web search
    n_results: 5    # Results per search (1-10)
    timeout: 30     # Search timeout in seconds
    search_depth: "moderate"  # moderate|comprehensive
```

**Agents with Web Search:**
- **Issue Analyst**: Research technologies, implementation patterns, common pitfalls
- **Explorer**: Research tech stack best practices, dependency patterns
- **Architect**: Research solution architectures, implementation examples
- **Reviewer**: Validate approaches against industry standards, security best practices

**Cost Control**: Web search is opt-in and can be disabled via `serper.enabled: false` to control costs.

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
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Parse raw task descriptions into structured requirements with clear scope boundaries.

| Agent | Tools | Key Responsibilities | Web Search Integration |
|-------|-------|---------------------|------------------------|
| **similar_issues_synthesizer** | `RepoShellTool`, `SerperDevTool` (when enabled) | • Fetch similar GitHub issues/PRs via `gh` CLI<br>• Produce "company moment" (recent merges + open work)<br>• Research issue patterns via web search | Searches: "GitHub issue patterns [technology]", "Common solutions for [problem]", "[Technology] implementation approaches" |
| **issue_analyst** | `ScrapeWebsiteTool`, `GithubSearchTool`, `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled) | • Parse task into structured requirements (Summary, Acceptance Criteria, Scope, Technical Hints)<br>• Use web/GitHub/docs for context gathering<br>• Derive scope from task + similar issues<br>• Keep acceptance criteria minimal - NO additions | Searches: "technology best practices", "implementation patterns", "common pitfalls", "migration strategies" |
| **scope_validator** | None (context only) | • Cross-check for scope creep, vague criteria, conflicts<br>• Flag: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`<br>• Append validation without rewriting original | N/A - Pure validation agent |
| **acceptance_criteria_normalizer** | None (context only) | • Normalize criteria into numbered, unambiguous, testable checklist<br>• Ensure each criterion is verifiable<br>• Maintain all prior sections | N/A - Pure normalization agent |

**Output**: Structured document with sections: Context (optional), Summary, Acceptance Criteria, Scope (In-scope/Out-of-scope), Technical Hints.

### 2. Explorer Crew (`explore` stage)
**Primary Model**: `openrouter/deepseek/deepseek-r1`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-v3.2`  
**Purpose**: Comprehensive codebase analysis to understand structure, dependencies, and conventions.

| Agent | Tools | Key Responsibilities | Web Search Integration |
|-------|-------|---------------------|------------------------|
| **repo_explorer** | `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled) | • Scan tech stack, directory layout, key files, conventions<br>• Read-only exploration (ls, find, cat, head, grep)<br>• Document test layout when `test_command` set | Searches: "[Technology] best practices", "[Framework] project structure", "[Library] usage patterns", "Technology comparisons" |
| **dependency_analyzer** | `RepoShellTool`, `SerperDevTool` (when enabled) | • Map import/dependency graphs for relevant modules<br>• Analyze blast radius (impact of changes)<br>• Identify "what depends on X" and "what X depends on" | Searches: "[Dependency] compatibility", "[Library] migration patterns", "[Technology] dependency management" |
| **test_layout_scout** | `RepoShellTool` | • Document test directory structure, fixtures, conventions<br>• Skip cleanly when `test_command` empty<br>• Identify how to add new tests | N/A - Pure file system analysis |
| **convention_extractor** | `RepoShellTool` | • Extract lint/format configuration (black, ruff, eslint, prettier)<br>• Document config paths and key options<br>• Identify code style conventions | N/A - Pure configuration parsing |
| **api_boundary_scout** | `RepoShellTool` | • Map API surface when task mentions "API", "endpoint", "route", "REST"<br>• Identify routes, controllers, middleware patterns<br>• Skip when task doesn't mention API | N/A - Pure API discovery |

**Output**: Complete exploration document with sections: Tech Stack, Directory Layout, Key Files, Conventions, Dependency Map, Test Layout, Lint & Format, API Boundary.

### 3. Clarify Crew (`auxiliary`/`analyze_issue` stage)
**Primary Model**: `auxiliary`: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Resolve ambiguities before planning via targeted human questions.

| Agent | Tools | Key Responsibilities | Special Requirements |
|-------|-------|---------------------|----------------------|
| **ambiguity_detector** | None (context only) | • Identify open questions: file/module ownership, convention conflicts, scope boundaries, test strategy, migration concerns<br>• No human interaction - pure detection | Must output `## Open Questions` with numbered list |
| **question_prioritizer** | None (context only) | • Rank questions by impact (wrong assumption = major rework)<br>• Prepare for human clarification in optimal order | Must output `## Prioritized Questions` with impact ranking |
| **clarifier** | `ask_human` | • Resolve ambiguities via human interaction<br>• **CRITICAL**: Each question MUST include 2-4 options with code snippets in ` ```language` format<br>• Present best option first, ground in exploration findings | Questions must reference specific files/patterns from exploration |

**Output**: Structured `Clarifications & Development Guidelines` document with Q/A sections that override all assumptions for the Architect.

### 4. Architect Crew (`plan` stage)
**Primary Model**: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Create minimal file-level implementation plan (no code).

| Agent | Tools | Key Responsibilities | Web Search Integration |
|-------|-------|---------------------|------------------------|
| **architect** | `GithubSearchTool`, `CodeDocsSearchTool`, `RepoShellTool`, `SerperDevTool` (when enabled) | • Create file-level plan with `## Files to Create` and `## Files to Modify`<br>• **CRITICAL**: Output exact paths, no code<br>• Minimum changes: prefer modifying over creating<br>• Follow clarifications as hard constraints | Searches: "[Pattern] implementation examples", "[Technology] best practices", "[Problem] solution architectures", "Alternative approaches" |
| **dependency_orderer** | `RepoShellTool` | • Order files by dependency (import graph)<br>• Flag high-risk areas in `## Risk` section<br>• Fix ordering if architect got it wrong | N/A - Pure dependency analysis |
| **refactor_guard** | None (context only) | • Flag unnecessary refactors beyond acceptance criteria<br>• Output `REFACTOR_FLAGS` or `NONE`<br>• Prevent scope creep through refactoring | N/A - Pure scope validation |
| **test_plan_advisor** | `RepoShellTool` | • Add `## Test Plan` when `test_command` set<br>• Specify test files to add/update, coverage requirements<br>• Skip cleanly when no `test_command` | N/A - Pure test planning |
| **migration_checker** | None (context only) | • Flag migration steps when plan touches DB, schema, config, env<br>• Output `## Migration` or `NONE`<br>• Identify data migration needs | N/A - Pure migration detection |
| **rollback_planner** | None (context only) | • Add `## Rollback` for high-risk areas (from `## Risk`)<br>• Specify revert steps for risky changes<br>• Output `NONE` for low-risk plans | N/A - Pure contingency planning |

**Output**: Complete plan with sections: Files to Create, Files to Modify, Order (verified), Risk, Refactor Guard, Test Plan, Migration, Rollback.

### 5. Implementer Crew (`implement` stage)
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Execute plan by writing actual code and tests.

| Agent | Tools | Key Responsibilities | Critical Rules |
|-------|-------|---------------------|----------------|
| **implementer** | `RepoFileWriterTool` (REQUIRED), `RepoShellTool`, `CodeInterpreterTool` | • **MUST** call Repo File Writer Tool for EVERY file in plan<br>• Surgical changes only - no extra files/abstractions<br>• Read existing files before modifying<br>• Fix `prior_issues` if non-empty | If plan lists 3 files, MUST call tool 3 times - NO exceptions |
| **docstring_writer** | `RepoFileWriterTool`, `RepoShellTool` | • Add/update docstrings for new/changed functions/classes<br>• Python: Google/NumPy style; JS/TS: JSDoc<br>• Use `git diff --name-only` to find changed files | Must maintain existing docstring conventions |
| **type_hint_checker** | `RepoFileWriterTool`, `RepoShellTool` | • Ensure Python changed files have type hints<br>• Add parameter and return type annotations<br>• Skip non-Python files | Focus only on .py files with changes |
| **test_writer** | `RepoFileWriterTool`, `RepoShellTool` | • Add/update tests per plan's test file paths<br>• Run `test_command` to verify<br>• Skip when `test_command` empty<br>• Follow Test Layout from exploration | Must run tests after writing to verify |
| **lint_fixer** | `RepoShellTool` | • Run project linter (black, ruff, eslint --fix) from exploration<br>• Fix auto-fixable issues<br>• Skip when no linter configured | Use exploration's Lint & Format section |
| **self_reviewer** | `RepoShellTool` | • Verify only planned files were touched<br>• Verify EVERY file in plan was modified<br>• Output `SELF_REVIEW: PASS` or `ISSUES:`<br>• Final gate before external review | Use `git status` and `git diff --name-only` |

**Output**: Implementation summary with `SELF_REVIEW: PASS/ISSUES` status.

### 6. Reviewer Crew (`review`/`security`/`auxiliary` stage)
**Primary Model**: `review`: `openrouter/deepseek/deepseek-v3.2`, `security`: `openrouter/deepseek/deepseek-v3.2`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Comprehensive code review with quality gates.

| Agent | Tools | Key Responsibilities | Web Search Integration |
|-------|-------|---------------------|------------------------|
| **reviewer** | `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled) | • **CRITICAL**: First line must be exactly `APPROVED` or `ISSUES:`<br>• Review against task, acceptance criteria, plan<br>• Reject overengineering and scope creep<br>• Verify actual file changes (not intent) | Searches: "[Pattern] security implications", "[Technology] common pitfalls", "[Implementation] best practice validation" |
| **security_reviewer** | `RepoShellTool`, `SerperDevTool` (when enabled) | • Check for SQL injection, XSS, auth bypass, unsafe input, exposed secrets<br>• Output `SECURE` or `SECURITY_ISSUES:`<br>• Append `## Security` section | Searches: "[Technology] security best practices", "[Pattern] vulnerability patterns", "[Library] security advisories" |
| **performance_reviewer** | `RepoShellTool` | • Flag N+1 queries, unindexed lookups, large in-memory loops<br>• Output `PERF_OK` or `PERF_ISSUES:`<br>• Append `## Performance` section | N/A - Pure performance analysis |
| **accessibility_checker** | `RepoShellTool` | • Check a11y compliance when UI files changed (.jsx, .tsx, .vue, .html)<br>• Check labels, ARIA, focus, contrast<br>• Skip when no UI changes | N/A - Pure accessibility checking |
| **backward_compat_checker** | `RepoShellTool` | • Flag breaking changes: signature changes, removed exports, changed return types<br>• Output `COMPAT_OK` or `BREAKING:`<br>• Append `## Backward Compatibility` | N/A - Pure API compatibility check |
| **convention_checker** | `RepoShellTool`, `CodeDocsSearchTool` | • Verify conventions (imports, formatting, naming)<br>• Merge findings from all reviewers<br>• Produce FINAL output with merged issue list<br>• Pipeline parses first line for routing | N/A - Pure convention validation |

**Output**: Final verdict with first line `APPROVED` or `ISSUES:` followed by merged issue list from all reviewers.

### 7. Commit Crew (`commit`/`publish`/`auxiliary` stage)
**Primary Model**: `commit`: `openrouter/google/gemini-3-flash-preview`, `publish`: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Create feature branch, commit changes, and publish PR.

| Agent | Tools | Key Responsibilities | Critical Rules |
|-------|-------|---------------------|----------------|
| **git_agent** | `RepoShellTool` | • Create feature branch from base branch<br>• Stage changes (excluding `.code_pipeline`)<br>• Commit with Conventional Commits format<br>• Skip when `dry_run` true | Must exclude `.code_pipeline` (pipeline state) from commits |
| **commit_message_reviewer** | `RepoShellTool` | • Validate last commit message via `git log -1 --format=%B`<br>• Conventional Commits: `<type>[scope]: <description>`<br>• Amend if invalid, confirm if valid | Types: feat, fix, docs, style, refactor, test, chore, perf, ci |
| **changelog_agent** | `RepoFileWriterTool`, `RepoShellTool` | • Update CHANGELOG if file exists<br>• Append `## [Unreleased]` or `### YYYY-MM-DD` entry<br>• Skip when `dry_run` or no CHANGELOG file | Must check for CHANGELOG.md or CHANGELOG.rst |
| **pr_labels_suggester** | None (context only) | • Analyze task and plan to suggest 1-5 relevant GitHub labels<br>• Common: feat, fix, docs, refactor, test, chore, dependencies, breaking-change<br>• Output: `Suggested labels: label1, label2, ...` | Labels must be lowercase, hyphenated for multi-word |
| **publish_agent** | `CreatePRTool` | • Push feature branch to origin<br>• Create PR via GitHub API<br>• Include task, implementation, plan, review_verdict<br>• Apply suggested labels<br>• Skip when `dry_run` or no `github_repo` | Must extract labels from `pr_labels_suggester` output |

**Output**: PR URL or skip message with commit/PR creation details.

## 📊 Agent Inputs & Outputs

Each agent receives specific inputs and produces defined outputs that flow through the pipeline:

### **Issue Analyst Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **similar_issues_synthesizer** | `task`, `github_repo`, `repo_path` | Similar issues analysis, "company moment" (recent merges + open work) |
| **issue_analyst** | `task`, `issue_url`, `github_repo`, `docs_url`, `repo_path` | Structured requirements: Summary, Acceptance Criteria, Scope, Technical Hints |
| **scope_validator** | Issue analyst output | Validation flags: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE` |
| **acceptance_criteria_normalizer** | Issue analyst + scope validator outputs | Normalized, numbered, testable acceptance criteria checklist |

### **Explorer Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **repo_explorer** | `repo_path`, `task`, `test_command`, `focus_paths`, `exclude_paths` | Tech stack analysis, directory layout, key files, conventions |
| **dependency_analyzer** | `repo_path`, task context | Dependency graphs, blast radius analysis, import relationships |
| **test_layout_scout** | `repo_path`, `test_command` | Test directory structure, fixtures, test conventions |
| **convention_extractor** | `repo_path` | Lint/format configuration, code style conventions |
| **api_boundary_scout** | `repo_path`, task (if mentions API) | API surface mapping, routes, controllers, middleware patterns |

### **Clarify Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **ambiguity_detector** | `task`, `exploration`, `issue_analysis` | `## Open Questions` with numbered list of ambiguities |
| **question_prioritizer** | Open questions from ambiguity detector | `## Prioritized Questions` with impact ranking |
| **clarifier** | Prioritized questions, exploration findings | Human Q/A with code snippet options, final clarifications document |

### **Architect Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **architect** | `task`, `exploration`, `issue_analysis`, `clarifications` | File-level plan: `## Files to Create`, `## Files to Modify` (paths only) |
| **dependency_orderer** | Architect's file list, `repo_path` | Ordered file list by dependency, `## Risk` section |
| **refactor_guard** | Architect plan, acceptance criteria | `REFACTOR_FLAGS` or `NONE` (prevents scope creep) |
| **test_plan_advisor** | Architect plan, `test_command` | `## Test Plan` or skipped if no test command |
| **migration_checker** | Architect plan | `## Migration` or `NONE` (for DB/schema/config changes) |
| **rollback_planner** | Architect plan, risk section | `## Rollback` or `NONE` (for high-risk changes) |

### **Implementer Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **implementer** | `plan`, `repo_path`, `prior_issues` | Actual code written to files, implementation summary |
| **docstring_writer** | Changed files (via `git diff`), `repo_path` | Updated docstrings following project conventions |
| **type_hint_checker** | Changed Python files, `repo_path` | Added/updated type hints for Python functions/classes |
| **test_writer** | Test plan, `test_command`, `repo_path` | Added/updated test files, test execution results |
| **lint_fixer** | Changed files, exploration conventions, `repo_path` | Lint fixes applied, auto-fixed issues summary |
| **self_reviewer** | Plan vs actual changes (via `git status`/`git diff`) | `SELF_REVIEW: PASS` or `ISSUES:` with discrepancies |

### **Reviewer Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **reviewer** | `task`, `plan`, `implementation`, `repo_path` | First line: `APPROVED` or `ISSUES:` with detailed review |
| **security_reviewer** | Implementation changes, `repo_path` | `SECURE` or `SECURITY_ISSUES:` with security findings |
| **performance_reviewer** | Implementation changes, `repo_path` | `PERF_OK` or `PERF_ISSUES:` with performance findings |
| **accessibility_checker** | UI file changes, `repo_path` | A11y compliance check (skipped if no UI changes) |
| **backward_compat_checker** | API changes, `repo_path` | `COMPAT_OK` or `BREAKING:` with compatibility findings |
| **convention_checker** | All reviewer outputs, `repo_path` | Merged final verdict with all issues consolidated |

### **Commit Crew**
| Agent | Primary Inputs | Key Outputs |
|-------|---------------|-------------|
| **git_agent** | `branch`, `feature_branch`, `dry_run`, `issue_id`, `repo_path` | Git commit output or dry-run summary |
| **commit_message_reviewer** | Last commit message (via `git log`), `dry_run` | `Commit message valid: ...` or amended message |
| **changelog_agent** | CHANGELOG file status, task summary, `dry_run` | Updated CHANGELOG or skip message |
| **pr_labels_suggester** | `task`, `plan` | `Suggested labels: label1, label2, ...` |
| **publish_agent** | `feature_branch`, `base_branch`, `task`, `implementation`, `plan`, `review_verdict`, `issue_url`, `issue_id`, `github_repo`, `dry_run` | PR URL or skip message |

**Data Flow**: Inputs flow sequentially through the pipeline: `task` → `issue_analysis` → `exploration` → `clarifications` → `plan` → `implementation` → `review_verdict` → `commit/PR`.

## Crew Members & Responsibilities

| Crew | Agents | Primary Responsibilities | Web Search Integration |
|------|--------|-------------------------|------------------------|
| **Issue Analyst** | similar_issues_synthesizer, issue_analyst, scope_validator, acceptance_criteria_normalizer | • Parse raw task into structured requirements with clear scope boundaries<br>• Fetch similar GitHub issues for context and scope guidance<br>• Validate scope creep and normalize criteria to testable checklist | ✅ Yes - Research technologies, patterns, solutions via SerperDevTool |
| **Explorer** | repo_explorer, dependency_analyzer, test_layout_scout, convention_extractor, api_boundary_scout | • Comprehensive codebase analysis: structure, dependencies, conventions<br>• Map tech stack, directory layout, key files, and patterns<br>• Extract lint/config and document test architecture | ✅ Yes - Research technologies, best practices, dependency patterns |
| **Clarify** | ambiguity_detector, question_prioritizer, clarifier | • Detect and prioritize implementation ambiguities<br>• Resolve via human interaction with code-snippet options<br>• Create authoritative development guidelines for Architect | ❌ No - Pure human interaction for ambiguity resolution |
| **Architect** | architect, dependency_orderer, refactor_guard, test_plan_advisor, migration_checker, rollback_planner | • Create minimal file-level implementation plan (paths only, no code)<br>• Order by dependency, flag risks, guard against refactor creep<br>• Plan tests, migrations, and rollback strategies | ✅ Yes - Research solution architectures and implementation patterns |
| **Implementer** | implementer, docstring_writer, type_hint_checker, test_writer, lint_fixer, self_reviewer | • Execute plan by writing actual code to specified files<br>• Add documentation, type hints, tests as per conventions<br>• Run linters and perform self-review before external review | ❌ No - Pure code writing and project tool execution |
| **Reviewer** | reviewer, security_reviewer, performance_reviewer, accessibility_checker, backward_compat_checker, convention_checker | • Comprehensive quality gates: main review, security, performance, a11y<br>• Check API compatibility and convention adherence<br>• Merge findings into final APPROVED/ISSUES verdict | ✅ Yes - Validate approaches against industry standards and security best practices |
| **Commit** | git_agent, commit_message_reviewer, changelog_agent, pr_labels_suggester, publish_agent | • Create feature branch, commit with Conventional Commits format<br>• Update CHANGELOG, suggest PR labels, create and publish PR<br>• Complete deployment cycle with proper GitHub integration | ❌ No - Pure Git and GitHub operations |

**Pipeline Flow**: Each crew processes output from previous crew, with quality gates between stages. The `ReviewVerdict` from Reviewer crew determines if pipeline proceeds to Commit or retries implementation.

## ✅ Completed Improvements

### **Recent Major Updates:**
- **Serper Web Search Integration**: All relevant agents now include SerperDevTool for web research when `SERPER_ENABLED=true`
- **Model Configuration**: Replaced free models with non-free alternatives to avoid rate limiting (429 errors)
- **Agent Prompt Enhancement**: Comprehensive refinement of role, goal, and backstory for all agents
- **Security Improvements**: Expanded dangerous command patterns with comprehensive regex blocks
- **Tool Optimization**: Added performance settings (max concurrent tools, retry attempts, rate limiting)

### **Current Status:**
- ✅ **Agent Prompting**: Completed comprehensive refinement across all crews
- ✅ **Model Optimization**: Updated to use cost-effective non-free models (Gemini 3 Flash, DeepSeek)
- ✅ **Serper Integration**: Fully implemented web search capabilities across analysis, exploration, architecture, and review stages
- ✅ **Configuration**: Enhanced config.yaml with improved tool settings and security patterns

## 🔄 Future Roadmap

### **High Priority:**
- **Parallelization** — Identify independent steps within crews (Explorer, Reviewer) for parallel execution to reduce latency
- **Webhook Integration** — Add handlers to trigger pipeline via GitHub issues, PR comments, or project management tools
- **Error Recovery** — Enhance retry logic with better context preservation and failure analysis
- **Cost Optimization** — Implement usage tracking and cost-aware model selection

### **Medium Priority:**
- **Separate Pipelines** — Build dedicated development pipeline (analyze → implement → commit) and separate code-review pipeline
- **Ollama Integration** — Add local inference backend for cost savings and privacy
- **Enhanced Testing** — Add integration tests for full pipeline flows and edge cases
- **Configuration UI** — Web-based configuration interface for easier setup

### **Research & Exploration:**
- **Multi-repo Analysis** — Support for cross-repository dependency analysis and impact assessment
- **Custom Tool Development** — Domain-specific tools for specialized workflows (data science, mobile, infra)
- **Performance Benchmarking** — Comparative analysis of different model combinations and configurations
- **Community Templates** — Pre-configured templates for common project types and frameworks

## 🚀 Getting Involved

### **Contributing:**
1. Fork the repository and create a feature branch
2. Follow the [Project Constitution](AGENTS.md) for all changes
3. Ensure all CI checks pass (ruff, mypy, pytest)
4. Submit a PR with clear description of changes

### **Reporting Issues:**
- **Bug Reports**: Include configuration, error logs, and reproduction steps
- **Feature Requests**: Describe use case, expected behavior, and alternatives considered
- **Security Issues**: Report responsibly via security contact

### **Community:**
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Examples**: Share your pipeline configurations and success stories
- **Feedback**: Help shape the roadmap with your experience and needs
