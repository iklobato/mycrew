# Code Pipeline: Your AI-Powered Development Team

## 🚀 Imagine Having a Complete Development Team at Your Fingertips

**Code Pipeline** is like having a full software development team that works for you 24/7. Instead of hiring individual developers, you get a complete workflow system where specialized AI agents handle every step of your project—from understanding what you need, to planning, building, testing, and delivering working code.

### ✨ What Makes This Different?

Think of it as having **7 specialized teams** working together seamlessly:

1. **📋 The Analysis Team** - Understands exactly what you want to build
2. **🔍 The Exploration Team** - Studies your existing codebase to understand how everything works
3. **❓ The Clarification Team** - Asks smart questions to avoid misunderstandings
4. **📐 The Architecture Team** - Plans exactly what needs to be built
5. **👨‍💻 The Implementation Team** - Writes the actual code
6. **✅ The Review Team** - Checks everything for quality and security
7. **🚀 The Deployment Team** - Packages and delivers the final product

### 🎯 Who Is This For?

**Perfect for:**
- **Non-technical founders** who need to build software without hiring a full team
- **Small businesses** that can't afford dedicated developers
- **Product managers** who want to prototype ideas quickly
- **Developers** who want to automate routine coding tasks
- **Anyone** with a software idea but limited technical resources

### 💡 How It Works (In Simple Terms)

1. **You describe what you want** - Just tell the system what feature or fix you need
2. **The AI teams analyze your request** - They understand your goals and your existing code
3. **They plan the work** - Like a project manager breaking down tasks
4. **They write the code** - Following best practices and your project's style
5. **They test everything** - Making sure it works correctly
6. **They deliver the result** - Ready-to-use code that integrates with your project

### 🌟 Key Benefits

**✅ No Technical Knowledge Required** - Just describe what you need in plain English
**✅ Consistent Quality** - Every change follows the same rigorous process
**✅ Faster Results** - Multiple AI agents work in sequence, 24/7
**✅ Cost Effective** - No need to hire multiple specialists
**✅ Scalable** - Handle one feature or hundreds without additional cost
**✅ Reliable** - Built-in review and testing at every step

### 🏗️ Real-World Examples

**For a small business owner:**
> "I need a contact form on my website that sends emails to my inbox"
→ The pipeline analyzes your website, plans the changes, builds the form, tests it works, and deploys it

**For a content creator:**
> "Add a newsletter subscription popup to my blog"
→ The system understands your blog structure, creates the popup, integrates with your email service, and makes sure it looks good

**For an app developer:**
> "Fix the login bug where users can't reset passwords"
→ The pipeline finds the bug, fixes it, tests the solution, and ensures no other features break

### 🚀 Getting Started Is Simple

1. **Install** - One command sets up the entire system
2. **Configure** - Connect to your project (GitHub, local files, etc.)
3. **Describe** - Tell the system what you need
4. **Watch** - See your AI team work through the process
5. **Use** - Get working code delivered to your project

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

The pipeline consists of 7 sequential crews with 28 specialized agents. Each crew processes the task through multiple agents, with output flowing sequentially to the next crew.

**Pipeline Flow**: `Issue Analyst → Explorer → Clarify → Architect → Implementer → Reviewer → Commit`

**Crew Overview:**
- **Issue Analyst** (`analyze_issue`): Parse raw task into structured requirements with clear scope boundaries
- **Explorer** (`explore`): Comprehensive codebase analysis to understand structure, dependencies, and conventions
- **Clarify** (`auxiliary`/`analyze_issue`): Resolve ambiguities before planning via targeted human questions
- **Architect** (`plan`): Create minimal file-level implementation plan (no code)
- **Implementer** (`implement`): Execute plan by writing actual code and tests
- **Reviewer** (`review`/`security`/`auxiliary`): Comprehensive code review with quality gates
- **Commit** (`commit`/`publish`/`auxiliary`): Create feature branch, commit changes, and publish PR

### 1. Issue Analyst Crew (`analyze_issue` stage)
**Primary Model**: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Parse raw task descriptions into structured requirements with clear scope boundaries.

**Agents:**
- **similar_issues_synthesizer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Fetch similar GitHub issues/PRs via `gh` CLI, produce "company moment" (recent merges + open work), research issue patterns via web search
  - **Web Search**: "GitHub issue patterns [technology]", "Common solutions for [problem]", "[Technology] implementation approaches"
- **issue_analyst**
  - **Tools**: `ScrapeWebsiteTool`, `GithubSearchTool`, `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Parse task into structured requirements (Summary, Acceptance Criteria, Scope, Technical Hints), use web/GitHub/docs for context gathering, derive scope from task + similar issues, keep acceptance criteria minimal - NO additions
  - **Web Search**: "technology best practices", "implementation patterns", "common pitfalls", "migration strategies"
- **scope_validator**
  - **Tools**: None (context only)
  - **Responsibilities**: Cross-check for scope creep, vague criteria, conflicts, flag: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`, append validation without rewriting original
- **acceptance_criteria_normalizer**
  - **Tools**: None (context only)
  - **Responsibilities**: Normalize criteria into numbered, unambiguous, testable checklist, ensure each criterion is verifiable, maintain all prior sections

**Output**: Structured document with sections: Context (optional), Summary, Acceptance Criteria, Scope (In-scope/Out-of-scope), Technical Hints.

### 2. Explorer Crew (`explore` stage)
**Primary Model**: `openrouter/deepseek/deepseek-r1`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-v3.2`  
**Purpose**: Comprehensive codebase analysis to understand structure, dependencies, and conventions.

**Agents:**
- **repo_explorer**
  - **Tools**: `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Scan tech stack, directory layout, key files, conventions, read-only exploration (ls, find, cat, head, grep), document test layout when `test_command` set
  - **Web Search**: "[Technology] best practices", "[Framework] project structure", "[Library] usage patterns", "Technology comparisons"
- **dependency_analyzer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Map import/dependency graphs for relevant modules, analyze blast radius (impact of changes), identify "what depends on X" and "what X depends on"
  - **Web Search**: "[Dependency] compatibility", "[Library] migration patterns", "[Technology] dependency management"
- **test_layout_scout**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Document test directory structure, fixtures, conventions, skip cleanly when `test_command` empty, identify how to add new tests
- **convention_extractor**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Extract lint/format configuration (black, ruff, eslint, prettier), document config paths and key options, identify code style conventions
- **api_boundary_scout**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Map API surface when task mentions "API", "endpoint", "route", "REST", identify routes, controllers, middleware patterns, skip when task doesn't mention API

**Output**: Complete exploration document with sections: Tech Stack, Directory Layout, Key Files, Conventions, Dependency Map, Test Layout, Lint & Format, API Boundary.

### 3. Clarify Crew (`auxiliary`/`analyze_issue` stage)
**Primary Model**: `auxiliary`: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Resolve ambiguities before planning via targeted human questions.

**Agents:**
- **ambiguity_detector**
  - **Tools**: None (context only)
  - **Responsibilities**: Identify open questions: file/module ownership, convention conflicts, scope boundaries, test strategy, migration concerns, no human interaction - pure detection
  - **Requirements**: Must output `## Open Questions` with numbered list
- **question_prioritizer**
  - **Tools**: None (context only)
  - **Responsibilities**: Rank questions by impact (wrong assumption = major rework), prepare for human clarification in optimal order
  - **Requirements**: Must output `## Prioritized Questions` with impact ranking
- **clarifier**
  - **Tools**: `ask_human`
  - **Responsibilities**: Resolve ambiguities via human interaction, **CRITICAL**: Each question MUST include 2-4 options with code snippets in ` ```language` format, present best option first, ground in exploration findings
  - **Requirements**: Questions must reference specific files/patterns from exploration

**Output**: Structured `Clarifications & Development Guidelines` document with Q/A sections that override all assumptions for the Architect.

### 4. Architect Crew (`plan` stage)
**Primary Model**: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Create minimal file-level implementation plan (no code).

**Agents:**
- **architect**
  - **Tools**: `GithubSearchTool`, `CodeDocsSearchTool`, `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Create file-level plan with `## Files to Create` and `## Files to Modify`, **CRITICAL**: Output exact paths, no code, minimum changes: prefer modifying over creating, follow clarifications as hard constraints
  - **Web Search**: "[Pattern] implementation examples", "[Technology] best practices", "[Problem] solution architectures", "Alternative approaches"
- **dependency_orderer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Order files by dependency (import graph), flag high-risk areas in `## Risk` section, fix ordering if architect got it wrong
- **refactor_guard**
  - **Tools**: None (context only)
  - **Responsibilities**: Flag unnecessary refactors beyond acceptance criteria, output `REFACTOR_FLAGS` or `NONE`, prevent scope creep through refactoring
- **test_plan_advisor**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Add `## Test Plan` when `test_command` set, specify test files to add/update, coverage requirements, skip cleanly when no `test_command`
- **migration_checker**
  - **Tools**: None (context only)
  - **Responsibilities**: Flag migration steps when plan touches DB, schema, config, env, output `## Migration` or `NONE`, identify data migration needs
- **rollback_planner**
  - **Tools**: None (context only)
  - **Responsibilities**: Add `## Rollback` for high-risk areas (from `## Risk`), specify revert steps for risky changes, output `NONE` for low-risk plans

**Output**: Complete plan with sections: Files to Create, Files to Modify, Order (verified), Risk, Refactor Guard, Test Plan, Migration, Rollback.

### 5. Implementer Crew (`implement` stage)
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Execute plan by writing actual code and tests.

**Agents:**
- **implementer**
  - **Tools**: `RepoFileWriterTool` (REQUIRED), `RepoShellTool`, `CodeInterpreterTool`
  - **Responsibilities**: **MUST** call Repo File Writer Tool for EVERY file in plan, surgical changes only - no extra files/abstractions, read existing files before modifying, fix `prior_issues` if non-empty
  - **Rules**: If plan lists 3 files, MUST call tool 3 times - NO exceptions
- **docstring_writer**
  - **Tools**: `RepoFileWriterTool`, `RepoShellTool`
  - **Responsibilities**: Add/update docstrings for new/changed functions/classes, Python: Google/NumPy style; JS/TS: JSDoc, use `git diff --name-only` to find changed files
  - **Rules**: Must maintain existing docstring conventions
- **type_hint_checker**
  - **Tools**: `RepoFileWriterTool`, `RepoShellTool`
  - **Responsibilities**: Ensure Python changed files have type hints, add parameter and return type annotations, skip non-Python files
  - **Rules**: Focus only on .py files with changes
- **test_writer**
  - **Tools**: `RepoFileWriterTool`, `RepoShellTool`
  - **Responsibilities**: Add/update tests per plan's test file paths, run `test_command` to verify, skip when `test_command` empty, follow Test Layout from exploration
  - **Rules**: Must run tests after writing to verify
- **lint_fixer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Run project linter (black, ruff, eslint --fix) from exploration, fix auto-fixable issues, skip when no linter configured
  - **Rules**: Use exploration's Lint & Format section
- **self_reviewer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Verify only planned files were touched, verify EVERY file in plan was modified, output `SELF_REVIEW: PASS` or `ISSUES:`, final gate before external review
  - **Rules**: Use `git status` and `git diff --name-only`

**Output**: Implementation summary with `SELF_REVIEW: PASS/ISSUES` status.

### 6. Reviewer Crew (`review`/`security`/`auxiliary` stage)
**Primary Model**: `review`: `openrouter/deepseek/deepseek-v3.2`, `security`: `openrouter/deepseek/deepseek-v3.2`  
**Fallbacks**: `openrouter/google/gemini-3-flash-preview`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Comprehensive code review with quality gates.

**Agents:**
- **reviewer**
  - **Tools**: `RepoShellTool`, `CodeDocsSearchTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: **CRITICAL**: First line must be exactly `APPROVED` or `ISSUES:`, review against task, acceptance criteria, plan, reject overengineering and scope creep, verify actual file changes (not intent)
  - **Web Search**: "[Pattern] security implications", "[Technology] common pitfalls", "[Implementation] best practice validation"
- **security_reviewer**
  - **Tools**: `RepoShellTool`, `SerperDevTool` (when enabled)
  - **Responsibilities**: Check for SQL injection, XSS, auth bypass, unsafe input, exposed secrets, output `SECURE` or `SECURITY_ISSUES:`, append `## Security` section
  - **Web Search**: "[Technology] security best practices", "[Pattern] vulnerability patterns", "[Library] security advisories"
- **performance_reviewer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Flag N+1 queries, unindexed lookups, large in-memory loops, output `PERF_OK` or `PERF_ISSUES:`, append `## Performance` section
- **accessibility_checker**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Check a11y compliance when UI files changed (.jsx, .tsx, .vue, .html), check labels, ARIA, focus, contrast, skip when no UI changes
- **backward_compat_checker**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Flag breaking changes: signature changes, removed exports, changed return types, output `COMPAT_OK` or `BREAKING:`, append `## Backward Compatibility` section
- **convention_checker**
  - **Tools**: `RepoShellTool`, `CodeDocsSearchTool`
  - **Responsibilities**: Verify conventions (imports, formatting, naming), merge findings from all reviewers, produce FINAL output with merged issue list, pipeline parses first line for routing

**Output**: Final verdict with first line `APPROVED` or `ISSUES:` followed by merged issue list from all reviewers.

### 7. Commit Crew (`commit`/`publish`/`auxiliary` stage)
**Primary Model**: `commit`: `openrouter/google/gemini-3-flash-preview`, `publish`: `openrouter/google/gemini-3-flash-preview`  
**Fallbacks**: `openrouter/deepseek/deepseek-v3.2`, `openrouter/deepseek/deepseek-r1`  
**Purpose**: Create feature branch, commit changes, and publish PR.

**Agents:**
- **git_agent**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Create feature branch from base branch, stage changes (excluding `.code_pipeline`), commit with Conventional Commits format, skip when `dry_run` true
  - **Rules**: Must exclude `.code_pipeline` (pipeline state) from commits
- **commit_message_reviewer**
  - **Tools**: `RepoShellTool`
  - **Responsibilities**: Validate last commit message via `git log -1 --format=%B`, Conventional Commits: `<type>[scope]: <description>`, amend if invalid, confirm if valid
  - **Rules**: Types: feat, fix, docs, style, refactor, test, chore, perf, ci
- **changelog_agent**
  - **Tools**: `RepoFileWriterTool`, `RepoShellTool`
  - **Responsibilities**: Update CHANGELOG if file exists, append `## [Unreleased]` or `### YYYY-MM-DD` entry, skip when `dry_run` or no CHANGELOG file
  - **Rules**: Must check for CHANGELOG.md or CHANGELOG.rst
- **pr_labels_suggester**
  - **Tools**: None (context only)
  - **Responsibilities**: Analyze task and plan to suggest 1-5 relevant GitHub labels, common: feat, fix, docs, refactor, test, chore, dependencies, breaking-change, output: `Suggested labels: label1, label2, ...`
  - **Rules**: Labels must be lowercase, hyphenated for multi-word
- **publish_agent**
  - **Tools**: `CreatePRTool`
  - **Responsibilities**: Push feature branch to origin, create PR via GitHub API, include task, implementation, plan, review_verdict, apply suggested labels, skip when `dry_run` or no `github_repo`
  - **Rules**: Must extract labels from `pr_labels_suggester` output

**Output**: PR URL or skip message with commit/PR creation details.

## 📊 Agent Inputs & Outputs

Each agent receives specific inputs and produces defined outputs that flow through the pipeline:

**Data Flow**: `task` → `issue_analysis` → `exploration` → `clarifications` → `plan` → `implementation` → `review_verdict` → `commit/PR`

### **Issue Analyst Crew**
- **similar_issues_synthesizer**
  - **Inputs**: `task`, `github_repo`, `repo_path`
  - **Outputs**: Similar issues analysis, "company moment" (recent merges + open work)
- **issue_analyst**
  - **Inputs**: `task`, `issue_url`, `github_repo`, `docs_url`, `repo_path`
  - **Outputs**: Structured requirements: Summary, Acceptance Criteria, Scope, Technical Hints
- **scope_validator**
  - **Inputs**: Issue analyst output
  - **Outputs**: Validation flags: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`
- **issue_analyst**: `task`, `issue_url`, `github_repo`, `docs_url`, `repo_path` → Structured requirements: Summary, Acceptance Criteria, Scope, Technical Hints
- **scope_validator**: Issue analyst output → Validation flags
- **acceptance_criteria_normalizer**: Issue analyst + scope validator outputs → Normalized, numbered, testable acceptance criteria checklist

### **Explorer Crew**
- **repo_explorer**: `repo_path`, `task`, `test_command`, `focus_paths`, `exclude_paths` → Tech stack analysis, directory layout, key files, conventions
- **dependency_analyzer**: `repo_path`, task context → Dependency graphs, blast radius analysis, import relationships
- **test_layout_scout**: `repo_path`, `test_command` → Test directory structure, fixtures, test conventions
- **convention_extractor**: `repo_path` → Lint/format configuration, code style conventions
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
- **test_writer**: Test plan, `test_command`, `repo_path` → Added/updated test files, test execution results
- **lint_fixer**: Changed files, exploration conventions, `repo_path` → Lint fixes applied, auto-fixed issues summary
- **self_reviewer**: Plan vs actual changes (via `git status`/`git diff`) → `SELF_REVIEW: PASS` or `ISSUES:` with discrepancies

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
