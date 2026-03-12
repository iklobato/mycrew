# Code Pipeline: Your AI-Powered Development Team

## 🚀 Imagine Having a Complete Development Team at Your Fingertips

**Code Pipeline** is like having a full software development team that works for you 24/7. Instead of hiring individual developers, you get a complete workflow system where specialized AI agents handle every step of your project—from understanding what you need, to planning, building, testing, and delivering working code.

### ✨ What Makes This Different?

Think of it as having **7 specialized teams** working together seamlessly:

1. **📋 The Analysis Team** - Transforms your simple request into detailed requirements, breaking down what needs to be built, what's included, and what's not
2. **🔍 The Exploration Team** - Maps your entire codebase like a detective, understanding your tech stack, file structure, and existing patterns to work within your system
3. **❓ The Clarification Team** - Acts as your project consultant, asking targeted questions about ambiguous areas before any work begins to prevent costly misunderstandings
4. **📐 The Architecture Team** - Creates a precise blueprint showing exactly which files need changes, in what order, and how everything connects together
5. **👨‍💻 The Implementation Team** - Writes clean, production-ready code that follows your project's style and integrates seamlessly with existing functionality
6. **✅ The Review Team** - Performs comprehensive quality checks including security audits, performance testing, and compliance verification before anything goes live
7. **🚀 The Deployment Team** - Packages the final solution with proper documentation, creates version-controlled commits, and prepares everything for integration

### 🎯 Who Is This For?

**Perfect for:**
- **Non-technical founders** who need to build software without hiring a full team
- **Small businesses** that can't afford dedicated developers
- **Product managers** who want to prototype ideas quickly
- **Developers** who want to automate routine coding tasks
- **Anyone** with a software idea but limited technical resources

### 💡 How It Works (In Simple Terms)

1. **You describe what you want** - Just tell the system what feature or fix you need in plain English
2. **The Analysis Team translates your request** - They convert your idea into specific, measurable requirements with clear boundaries
3. **The Exploration Team studies your project** - They examine your existing code to understand how everything works and where changes should go
4. **The Clarification Team asks smart questions** - They identify any ambiguities and get clarification before planning begins
5. **The Architecture Team creates the blueprint** - They design exactly what needs to be built, which files to change, and in what order
6. **The Implementation Team writes the code** - They execute the plan by writing clean, working code that follows your project's conventions
7. **The Review Team validates everything** - They perform security checks, performance testing, and quality assurance
8. **The Deployment Team delivers the solution** - They package everything properly with documentation and version control

### 🌟 Key Benefits

**✅ No Technical Knowledge Required** - Just describe what you need in plain English, no coding experience needed
**✅ Consistent Quality** - Every change follows the same rigorous 7-team process with built-in quality gates
**✅ Faster Results** - Multiple AI teams work in perfect sequence, 24/7, with no delays or coordination overhead
**✅ Cost Effective** - Get the capabilities of a full development team without hiring multiple specialists
**✅ Scalable** - Handle one feature or hundreds without additional setup or management complexity
**✅ Reliable** - Built-in review, testing, and validation at every step prevents errors before they happen
**✅ Transparent Process** - See exactly how each team contributes and understand the reasoning behind every decision
**✅ Adapts to Your Style** - Learns and follows your project's specific conventions and patterns

### 🏗️ Real-World Examples

**For a small business owner:**
> "I need a contact form on my website that sends emails to my inbox"
→ **Analysis Team** defines the requirements • **Exploration Team** studies your website structure • **Clarification Team** asks about email format preferences • **Architecture Team** plans the form placement • **Implementation Team** builds the form • **Review Team** tests email delivery • **Deployment Team** integrates it seamlessly

**For a content creator:**
> "Add a newsletter subscription popup to my blog"
→ **Analysis Team** specifies popup behavior • **Exploration Team** maps your blog's theme files • **Clarification Team** confirms design preferences • **Architecture Team** plans popup triggers • **Implementation Team** codes the popup • **Review Team** checks mobile responsiveness • **Deployment Team** connects to your email service

**For an app developer:**
> "Fix the login bug where users can't reset passwords"
→ **Analysis Team** identifies the bug scope • **Exploration Team** finds the problematic code • **Clarification Team** confirms user scenarios • **Architecture Team** plans the fix approach • **Implementation Team** writes the corrected code • **Review Team** tests all edge cases • **Deployment Team** ensures backward compatibility

**For a startup founder:**
> "Add user profile pictures to our mobile app"
→ **Analysis Team** defines upload requirements • **Exploration Team** studies your app architecture • **Clarification Team** asks about storage preferences • **Architecture Team** plans image handling • **Implementation Team** builds the feature • **Review Team** checks security and performance • **Deployment Team** updates documentation

### 🚀 Getting Started Is Simple

1. **Install** - One command sets up your complete AI development team
2. **Configure** - Connect to your project (GitHub, local files, or any code repository)
3. **Describe** - Tell your AI teams what you need in simple, everyday language
4. **Watch** - Observe each specialized team working together in perfect coordination
5. **Use** - Receive production-ready code that's been validated by the entire team workflow

### 🤝 How the Teams Work Together

**Perfect Handoffs** - Each team completes its specialized task and passes a refined result to the next team, just like a relay race where each runner is an expert in their leg

**Continuous Validation** - Every team validates the work of previous teams, catching issues early when they're easiest to fix

**Shared Understanding** - All teams work from the same evolving understanding of your project, ensuring consistency across the entire process

**Quality Gates** - Each team acts as a quality checkpoint, preventing problems from moving forward in the pipeline

**Transparent Process** - You can see exactly what each team is doing and why, giving you complete visibility into the development process

### 📈 Why This Changes Everything

Traditional software development requires hiring, managing, and paying multiple people. **Code Pipeline** gives you the same capabilities instantly, at a fraction of the cost, with consistent quality and speed that human teams can't match.

Whether you're building a new feature, fixing a bug, or creating an entire application from scratch—you now have a complete development team ready to work for you.

---

*Ready to experience the future of software development? [Get started with the installation guide below ↓](#-quick-start)*

---

## 🏗️ Technical Architecture Overview

A comprehensive software development automation system powered by [crewAI](https://crewai.com). The pipeline processes software development tasks through 7 sequential crews: analysis, exploration, clarification, planning, implementation, review, and deployment. Each crew has specialized agents with specific tools and responsibilities.

## 🏗️ Architecture Overview

The pipeline consists of 7 sequential crews with specialized agents:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Code Pipeline Flow                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Issue Analyst → 2. Explorer → 3. Clarify → 4. Architect →            │
│ 5. Implementer → 6. Test Validator → 7. Reviewer → 8. Commit            │
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
  # Hierarchical model configuration (cost-optimized defaults)
  analyze_issue:
    primary: "openrouter/deepseek/deepseek-chat"
    fallbacks:
      - "openrouter/qwen/qwen-2.5-coder-32b-instruct"
      - "openrouter/mistralai/mistral-small-24b-instruct-2501"
  # ... other stage configurations (explore, plan, implement, review, commit, etc.)
```

### Environment Variables (Alternative to config.yaml)
- `OPENROUTER_API_KEY` - LLM API access (required)
- `SERPER_API_KEY` - Serper API key for web search integration (optional)
- `GITHUB_TOKEN` - For GitHub API integration (required for issue_url; clone, fetch issue, create PR)
- `GITHUB_WEBHOOK_SECRET` - For GitHub webhook signature verification (required when using webhooks)
- `CODE_PIPELINE_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CREWAI_TRACING_ENABLED` - CrewAI telemetry (set to "false" to disable)

### GitHub Webhook (issues assigned, PR review comments)

To trigger the pipeline from GitHub (e.g. when an issue is assigned or a PR review comment is created), register a webhook and set `GITHUB_WEBHOOK_SECRET`. See [docs/WEBHOOK_REGISTRATION.md](docs/WEBHOOK_REGISTRATION.md) for URL, events, GITHUB_TOKEN scopes, and step-by-step registration.

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

The pipeline consists of **8 sequential crews with 37 specialized agents**. Each crew processes the task through multiple agents, with output flowing sequentially to the next crew.

**Pipeline Flow**: `Issue Analyst → Explorer → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit`

**Crew Overview:**
- **Issue Analyst** (`analyze_issue`): Parse raw task into structured requirements with clear scope boundaries
- **Explorer** (`explore`): Comprehensive codebase analysis to understand structure, dependencies, and conventions
- **Clarify** (`auxiliary`/`analyze_issue`): Resolve ambiguities before planning via targeted human questions
- **Architect** (`plan`): Create minimal file-level implementation plan (no code)
- **Implementer** (`implement`): Execute plan by writing actual code (no test writing—handled by Test Validator)
- **Test Validator** (`test_validation`): Write and validate tests, ensure tests catch bugs via bug injection
- **Reviewer** (`review`/`security`/`auxiliary`): Comprehensive code review with quality gates
- **Commit** (`commit`/`publish`/`auxiliary`): Create feature branch, commit changes, and publish PR

### 1. Issue Analyst Crew (`analyze_issue` stage)
**Primary Model**: `openrouter/deepseek/deepseek-chat`  
**Fallbacks**: `openrouter/qwen/qwen-2.5-coder-32b-instruct`, `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Purpose**: Parse raw task descriptions into structured requirements with clear scope boundaries.

**Agents:**
- **similar_issues_synthesizer**
  - **Tools**: `ScrapeWebsiteTool`, `RepoShellTool`, `SerperDevTool` (when enabled), `GithubSearchTool` (when github_repo set)
  - **Responsibilities**: Fetch similar GitHub issues/PRs via `gh` CLI (`-R "{github_repo}"`), produce "company moment" (recent merges + open work), research issue patterns via web search. Output: Issues consulted, out-of-scope in similar issues, company moment, web research insights.
  - **Web Search**: "GitHub issue patterns [technology]", "Common solutions for [problem]", "[Technology] implementation approaches"
- **issue_analyst**
  - **Tools**: `ScrapeWebsiteTool`, `RepoShellTool`, `SerperDevTool` (when enabled), `GithubSearchTool` (when github_repo set)
  - **Responsibilities**: Parse task into structured requirements (Summary, Acceptance Criteria, Scope, Technical Hints), use web/GitHub for context, derive scope from task + similar issues, keep acceptance criteria minimal—NO additions. Output sections: Context, Summary, Acceptance Criteria, Scope, Technical Hints.
  - **Web Search**: "technology best practices", "implementation patterns", "common pitfalls", "migration strategies"
- **scope_validator**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Cross-check for scope creep, vague criteria, conflicts. Append `## Scope Validation` with flags: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`. Keep original document intact.
- **acceptance_criteria_normalizer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Normalize criteria into numbered, unambiguous, testable checklist. Append `## Acceptance Criteria (Normalized)`. Ensure each criterion is verifiable. Keep all prior sections.

**Output**: Structured document with sections: Context (optional), Summary, Acceptance Criteria, Scope (In-scope/Out-of-scope), Technical Hints, Scope Validation, Acceptance Criteria (Normalized).

### 2. Explorer Crew (`explore` stage)
**Primary Model**: `openrouter/qwen/qwen-2.5-coder-32b-instruct`  
**Fallbacks**: `openrouter/deepseek/deepseek-chat`, `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Purpose**: Comprehensive codebase analysis to understand structure, dependencies, and conventions.

**Agents:**
- **repo_explorer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Scan tech stack, directory layout, key files, conventions. Read-only exploration (ls, find, cat, head, grep). Document test layout when `test_command` set. Use focus_paths/exclude_paths when set.
  - **Web Search**: "[Technology] best practices", "[Framework] project structure", "[Library] usage patterns"
- **dependency_analyzer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Map import/dependency graphs for relevant modules, analyze blast radius. Append `## Dependency Map`: what depends on X, what X depends on, blast radius.
  - **Web Search**: "[Dependency] compatibility", "[Library] migration patterns", "[Technology] dependency management"
- **test_layout_scout**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Document test directory structure, fixtures, how to run tests, how to add new tests. Append `## Test Layout`. Skip when `test_command` empty.
- **convention_extractor**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Extract lint/format configuration. Append `## Lint & Format`: Linters (use uvx for Python: `uvx ruff check --fix .`, `uvx black .`), Formatters, config paths.
- **api_boundary_scout**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Map API surface when task mentions "API", "endpoint", "route", "REST". Append `## API Boundary` with routes/endpoints structure. Skip when task doesn't mention API.

**Output**: Complete exploration document with sections: Tech Stack, Directory Layout, Key Files, Conventions, Dependency Map, Test Layout, Lint & Format, API Boundary.

### 3. Clarify Crew (`auxiliary`/`analyze_issue` stage)
**Primary Model**: `auxiliary`: `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Fallbacks**: `openrouter/google/gemini-2.0-flash-001`, `openrouter/deepseek/deepseek-chat`  
**Purpose**: Resolve ambiguities before planning via targeted human questions.

**Agents:**
- **ambiguity_detector**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Cross-reference task, issue_analysis, exploration. Produce `## Open Questions` with numbered list. No human interaction—pure detection.
- **question_prioritizer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Rank open questions by impact (wrong assumption = major rework). Produce `## Prioritized Questions` for clarifier to ask in optimal order.
- **clarifier**
  - **Tools**: `ask_human`
  - **Responsibilities**: Resolve ambiguities via `ask_human`. **CRITICAL**: Each question MUST include 2–4 options with code snippets in ```language format. Ground in exploration findings. Produce final `# Clarifications & Development Guidelines`—authoritative for Architect.

**Output**: Structured `Clarifications & Development Guidelines` document with Q/A sections.

### 4. Architect Crew (`plan` stage)
**Primary Model**: `openrouter/google/gemini-2.0-flash-001`  
**Fallbacks**: `openrouter/mistralai/mistral-small-24b-instruct-2501`, `openrouter/deepseek/deepseek-chat`  
**Purpose**: Create minimal file-level implementation plan (no code).

**Agents:**
- **architect**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled), `GithubSearchTool` (when github_repo set)
  - **Responsibilities**: Create file-level plan with `## Files to Create` and `## Files to Modify`. No code—only exact paths and change descriptions. Prefer modifying over creating. Follow clarifications as hard constraints.
  - **Web Search**: "[Pattern] implementation examples", "[Technology] best practices", "[Problem] solution architectures"
- **dependency_orderer**
  - **Tools**: `RepoShellTool`, `SerperDevTool`, `GithubSearchTool` (when available)
  - **Responsibilities**: Order files by dependency (import graph), flag high-risk areas. Append `## Order (verified)` and `## Risk`.
- **refactor_guard**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Flag unnecessary refactors beyond acceptance criteria. Append `## Refactor Guard` with `REFACTOR_FLAGS` or `NONE`.
- **test_plan_advisor**
  - **Tools**: `RepoShellTool`, `SerperDevTool`, `GithubSearchTool` (when available)
  - **Responsibilities**: Add `## Test Plan` when `test_command` set (test files to add/update, what to cover). Skip when `test_command` empty.
- **migration_checker**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Flag migration steps when plan touches DB, schema, config, env. Append `## Migration` or `NONE`.
- **rollback_planner**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Add `## Rollback` for high-risk areas (from `## Risk`). Append `NONE` for low-risk plans.

**Output**: Complete plan with sections: Files to Create, Files to Modify, Order (verified), Risk, Refactor Guard, Test Plan, Migration, Rollback.

### 5. Implementer Crew (`implement` stage)
**Primary Model**: `openrouter/qwen/qwen-2.5-coder-32b-instruct`  
**Fallbacks**: `openrouter/deepseek/deepseek-chat`, `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Purpose**: Execute plan by writing actual code. Test writing is handled by Test Validator crew.

**Agents:**
- **implementer**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
  - **Responsibilities**: **MUST** call Repo File Writer Tool for EVERY file in plan. Surgical changes only. Read existing files before modifying. Run tests. Fix `prior_issues` if non-empty. Workflow: Read → Write → Run tests.
- **docstring_writer**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
  - **Responsibilities**: Add/update docstrings for new/changed functions/classes. Python: Google/NumPy style; JS/TS: JSDoc. Use `git diff --name-only` to find changed files.
- **type_hint_checker**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
  - **Responsibilities**: Ensure Python changed files have type hints on def/async def params and returns. Skip non-Python.
- **lint_fixer**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
  - **Responsibilities**: Run project linter from exploration's Lint & Format section. For Python use `uvx ruff check --fix .` and `uvx black .` (uvx runs tools without PATH). Use `npx eslint --fix` for JS/TS. Fix auto-fixable issues.
- **self_reviewer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Verify only planned files were touched, every file in plan was modified. Output `SELF_REVIEW: PASS` or `ISSUES:`. Use `git status` and `git diff --name-only`. Final gate before Review crew.

**Output**: Implementation summary with `SELF_REVIEW: PASS/ISSUES` status.

### 6. Test Validator Crew (`test_validation` stage)
**Primary Model**: `openrouter/qwen/qwen-2.5-coder-32b-instruct`  
**Fallbacks**: `openrouter/deepseek/deepseek-chat`, `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Purpose**: Write and validate tests, ensure test quality via bug injection and coverage.

**Agents:**
- **test_implementer**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
  - **Responsibilities**: Write or update tests based on plan and acceptance criteria. Follow project test patterns, Arrange-Act-Assert, meaningful assertions.
- **test_quality_checker**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
  - **Responsibilities**: **CRITICAL**: Ensure tests catch implementation errors by injecting bugs (logic operators, null checks, error handling, boundary conditions). Create backup → inject bug → run test_command (tests MUST fail) → restore. If tests don't fail, improve tests and repeat.
- **test_coverage_checker**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
  - **Responsibilities**: Run coverage tools if available (pytest --cov, jest --coverage). Check 80% minimum. Output "Coverage check: SKIPPED (no tools)" if no coverage tools.

**Output**: Test validation status: "Test validation: PASS" or "Test validation: FAIL - [reason]", coverage report.

### 7. Reviewer Crew (`review`/`security`/`auxiliary` stage)
**Primary Model**: `review`/`security`: `openrouter/deepseek/deepseek-chat`  
**Fallbacks**: `openrouter/qwen/qwen-2.5-coder-32b-instruct`, `openrouter/mistralai/mistral-small-24b-instruct-2501`  
**Purpose**: Comprehensive code review with quality gates.

**Agents:**
- **reviewer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: **CRITICAL**: First line must be exactly `APPROVED` or `ISSUES:`. Review against task, acceptance criteria, plan. Verify actual file changes (not intent). Reject overengineering. Format: `ISSUES:\n- <file>: <description>`.
  - **Web Search**: "[Pattern] security implications", "[Technology] common pitfalls", "[Implementation] best practice validation"
- **security_reviewer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Check for SQL injection, XSS, auth bypass, unsafe input, exposed secrets. Append `## Security` with `SECURE` or `SECURITY_ISSUES:`.
  - **Web Search**: "[Technology] security best practices", "[Pattern] vulnerability patterns", "[Library] security advisories"
- **performance_reviewer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Flag N+1 queries, unindexed lookups, large in-memory loops. Append `## Performance` with `PERF_OK` or `PERF_ISSUES:`.
- **accessibility_checker**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Check a11y when UI files changed (.jsx, .tsx, .vue, .html). Append `## Accessibility` with A11Y_OK or A11Y_ISSUES. Skip when no UI changes.
- **backward_compat_checker**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Flag breaking changes: signature changes, removed exports, changed return types. Append `## Backward Compatibility` with `COMPAT_OK` or `BREAKING:`.
- **convention_checker**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Verify conventions (imports, formatting, naming). Merge findings from all reviewers. Produce FINAL output: first line `APPROVED` or `ISSUES:`, merged issue list. Pipeline parses for routing.

**Output**: Final verdict with first line `APPROVED` or `ISSUES:` followed by merged issue list.

### 8. Commit Crew (`commit`/`publish`/`auxiliary` stage)
**Primary Model**: `commit`/`publish`: `openrouter/google/gemini-2.0-flash-001`  
**Fallbacks**: `openrouter/mistralai/mistral-small-24b-instruct-2501`, `openrouter/deepseek/deepseek-chat`  
**Purpose**: Create feature branch, commit changes, and publish PR.

**Agents:**
- **git_agent**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Create feature branch, stage changes (excluding `.code_pipeline`), commit with Conventional Commits. Skip when `dry_run`. Types: feat, fix, docs, style, refactor, test, chore, perf, ci.
- **commit_message_reviewer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Validate last commit via `git log -1 --format=%B`. Amend if invalid. Confirm if valid.
- **changelog_agent**
  - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
  - **Responsibilities**: Append CHANGELOG entry if CHANGELOG.md/CHANGELOG.rst exists. Skip when `dry_run` or no CHANGELOG.
- **pr_labels_suggester**
  - **Tools**: None
  - **Responsibilities**: Suggest 1–5 GitHub labels from task/plan. Output: "Suggested labels: label1, label2, ...". Lowercase, hyphenated.
- **publish_agent**
  - **Tools**: `CreatePRTool`, `RepoShellTool`
  - **Responsibilities**: Push feature branch, create PR via Create PR Tool. Pass task, implementation, plan, review_verdict, issue_url, issue_id, labels. Resolve conflicts if needed. Skip when `dry_run` or no `github_repo`.

**Output**: PR URL or skip message.

## 📊 Agent Inputs & Outputs

Each agent receives specific inputs and produces defined outputs that flow through the pipeline:

**Data Flow**: `task` → `issue_analysis` → `exploration` → `clarifications` → `plan` → `implementation` → `review_verdict` → `commit/PR`

### **Issue Analyst Crew**
- **similar_issues_synthesizer**: `task`, `github_repo`, `repo_path` → Similar issues analysis, "company moment" (recent merges + open work)
- **issue_analyst**: `task`, `issue_url`, `github_repo`, `docs_url`, `repo_path` → Structured requirements: Summary, Acceptance Criteria, Scope, Technical Hints
- **scope_validator**: Issue analyst output → Validation flags: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`
- **acceptance_criteria_normalizer**: Issue analyst + scope validator outputs → Normalized, numbered, testable acceptance criteria checklist

### **Explorer Crew**
- **repo_explorer**: `repo_path`, `task`, `test_command`, `focus_paths`, `exclude_paths` → Tech stack analysis, directory layout, key files, conventions
- **dependency_analyzer**: `repo_path`, task context → Dependency graphs, blast radius analysis, import relationships
- **test_layout_scout**: `repo_path`, `test_command` → Test directory structure, fixtures, test conventions
- **convention_extractor**: `repo_path` → Lint/format configuration (uvx for Python), code style conventions
- **api_boundary_scout**: `repo_path`, task (if mentions API) → API surface mapping, routes, controllers, middleware patterns

### **Clarify Crew**
- **ambiguity_detector**: `task`, `exploration`, `issue_analysis` → `## Open Questions` with numbered list of ambiguities
- **question_prioritizer**: Open questions from ambiguity detector → `## Prioritized Questions` with impact ranking
- **clarifier**: Prioritized questions, exploration findings → Human Q/A with code snippet options, final clarifications document

### **Architect Crew**
- **architect**: `task`, `exploration`, `issue_analysis`, `clarifications` → File-level plan: `## Files to Create`, `## Files to Modify` (paths only)
- **dependency_orderer**: Architect's file list, `repo_path` → Ordered file list by dependency, `## Risk` section
- **refactor_guard**: Architect plan, acceptance criteria → `REFACTOR_FLAGS` or `NONE` (prevents scope creep)
- **test_plan_advisor**: Architect plan, `test_command` → `## Test Plan` or skipped if no test command
- **migration_checker**: Architect plan → `## Migration` or `NONE` (for DB/schema/config changes)
- **rollback_planner**: Architect plan, risk section → `## Rollback` or `NONE` (for high-risk changes)

### **Implementer Crew**
- **implementer**: `plan`, `repo_path`, `prior_issues` → Actual code written to files, implementation summary
- **docstring_writer**: Changed files (via `git diff`), `repo_path` → Updated docstrings following project conventions
- **type_hint_checker**: Changed Python files, `repo_path` → Added/updated type hints for Python functions/classes
- **lint_fixer**: Changed files, exploration (Lint & Format), `repo_path` → Lint fixes applied (uvx ruff, uvx black, npx eslint)
- **self_reviewer**: Plan vs actual changes (via `git status`/`git diff`) → `SELF_REVIEW: PASS` or `ISSUES:` with discrepancies

### **Test Validator Crew**
- **test_implementer**: `plan`, `implementation`, `exploration`, `repo_path`, `test_command` → Written/updated test files following project conventions
- **test_quality_checker**: Test files, `test_command`, `repo_path` → Bug injection validation results, ensures tests catch implementation errors
- **test_coverage_checker**: Test files, `repo_path` → Coverage percentage report or "SKIPPED (no tools)"

### **Reviewer Crew**
- **reviewer**: `task`, `plan`, `implementation`, `repo_path` → First line: `APPROVED` or `ISSUES:` with detailed review
- **security_reviewer**: Implementation changes, `repo_path` → `SECURE` or `SECURITY_ISSUES:` with security findings
- **performance_reviewer**: Implementation changes, `repo_path` → `PERF_OK` or `PERF_ISSUES:` with performance findings
- **accessibility_checker**: UI file changes, `repo_path` → A11y compliance check (skipped if no UI changes)
- **backward_compat_checker**: API changes, `repo_path` → `COMPAT_OK` or `BREAKING:` with compatibility findings
- **convention_checker**: All reviewer outputs, `repo_path` → Merged final verdict with all issues consolidated

### **Commit Crew**
- **git_agent**: `branch`, `feature_branch`, `dry_run`, `issue_id`, `repo_path` → Git commit output or dry-run summary
- **commit_message_reviewer**: Last commit message (via `git log`), `dry_run` → `Commit message valid: ...` or amended message
- **changelog_agent**: CHANGELOG file status, task summary, `dry_run` → Updated CHANGELOG or skip message
- **pr_labels_suggester**: `task`, `plan` → `Suggested labels: label1, label2, ...`
- **publish_agent**: `feature_branch`, `base_branch`, `task`, `implementation`, `plan`, `review_verdict`, `issue_url`, `issue_id`, `github_repo`, `dry_run` → PR URL or skip message

**Pipeline Flow**: Each crew processes output from previous crew, with quality gates between stages. The `ReviewVerdict` from Reviewer crew determines if pipeline proceeds to Commit or retries implementation.

## ✅ Completed Improvements

### **Recent Major Updates:**
- **Serper Web Search Integration**: All relevant agents include SerperDevTool for web research when `serper.enabled=true` (config) or `SERPER_API_KEY` set
- **Model Configuration**: Cost-optimized defaults (DeepSeek Chat, Qwen2.5 Coder, Gemini 2.0 Flash, Mistral Small) with rate-limit retry and backoff (factor 0.5)
- **Agent Prompt Enhancement**: Comprehensive refinement of role, goal, and backstory for all agents
- **Security Improvements**: Expanded dangerous command patterns with comprehensive regex blocks
- **Tool Optimization**: Added performance settings (max concurrent tools, retry attempts, rate limiting)
- **Memory Exhaustion Prevention**: Implemented 64KB output limits in RepoShellTool with streaming to prevent container crashes from large outputs
- **Token Overflow Protection**: Reduced max_tokens from 8192 to 4096 and added exploration truncation to prevent LLM context length errors
- **Programmatic Mode Enhancement**: Auto-selection of recommended options in human clarification questions when running in programmatic/webhook mode
- **Callback URL Support**: Added callback URL parameter for pipeline status notifications via HTTP POST
- **Test Validator Crew**: Added dedicated test validation crew for comprehensive test writing and quality assurance

### **Current Status:**
- ✅ **Agent Prompting**: Completed comprehensive refinement across all crews
- ✅ **Model Optimization**: Cost-effective defaults (DeepSeek Chat, Qwen2.5 Coder, Gemini 2.0 Flash, Mistral Small)
- ✅ **Rate Limit Retry**: Exponential backoff (factor 0.5) for 429/RateLimitError
- ✅ **Serper Integration**: Fully implemented web search capabilities across analysis, exploration, architecture, and review stages
- ✅ **Configuration**: Enhanced config.yaml with improved tool settings and security patterns
- ✅ **Memory Safety**: Output limiting prevents container crashes from memory-intensive commands
- ✅ **Context Management**: Token overflow protection ensures stable LLM interactions
- ✅ **Automation**: Programmatic mode enables fully automated pipeline execution
- ✅ **Notifications**: Callback URL support for pipeline status updates
- ✅ **Test Quality**: Dedicated test validation ensures comprehensive test coverage

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
