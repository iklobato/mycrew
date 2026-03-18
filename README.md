# mycrew: Your AI-Powered Development Team

## Imagine Having a Complete Development Team at Your Fingertips

**mycrew** is like having a full software development team that works for you 24/7. Instead of hiring individual developers, you get a complete workflow system where specialized AI agents handle every step of your project—from understanding what you need, to planning, building, testing, and delivering working code.

It also includes a **PR Review Pipeline** that performs comprehensive code review with 10 parallel specialized agents.

---

## Quick Start

### 3 Steps to Run

```bash
# 1. Install uv (Python package manager)
pip install uv

# 2. Clone and install dependencies
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY
```

---

## Usage

### CLI

```bash
# From project root
./cli.py development <issue-url>
./cli.py dev <issue-url>

./cli.py review <pr-url>
./cli.py rev <pr-url>

# Help
./cli.py --help
./cli.py development --help
./cli.py review --help
```

### Development Pipeline

The development pipeline transforms GitHub/GitLab issues into implemented code.

```bash
# GitHub issue
./cli.py development "https://github.com/owner/repo/issues/123"

# GitLab issue
./cli.py dev "https://gitlab.com/owner/repo/-/issues/456"

# With local repo
./cli.py development --repo-path /path/to/repo "https://github.com/owner/repo/issues/123"

# Verbose output
./cli.py dev "https://github.com/owner/repo/issues/123" -v
```

### Review Pipeline

The review pipeline performs comprehensive PR review with 10 parallel agents and posts a comment to the PR.

```bash
# GitHub PR
./cli.py review "https://github.com/owner/repo/pull/123"

# GitLab MR
./cli.py rev "https://gitlab.com/owner/repo/-/merge_requests/456"

# With local repo (for reading files)
./cli.py review --repo-path /path/to/repo "https://github.com/owner/repo/pull/123"
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM API key from [openrouter.ai](https://openrouter.ai) |
| `HUGGINGFACE_API_KEY` | No | HuggingFace token for local models |
| `GITHUB_TOKEN` | No | GitHub token for GitHub issues/PRs |
| `GITLAB_TOKEN` | No | GitLab token for GitLab issues/MRs |
| `SERPER_API_KEY` | No | Serper API key for web search |
| `TACTIQ_TOKEN` | No | Tactiq API token from [Tactiq settings](https://app.tactiq.io/settings) |
| `CODE_PIPELINE_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |
| `PROVIDER_TYPE` | No | LLM provider: "openrouter" (default) or "huggingface" |
| `CREWAI_TRACING_ENABLED` | No | Enable CrewAI telemetry (default: false) |
| `DEFAULT_DRY_RUN` | No | Default dry run mode (default: false) |
| `DEFAULT_BRANCH` | No | Default branch (default: main) |
| `TACTIQ_MEETING_ID` | No | Default Tactiq meeting ID |

---

## Pipelines

### Development Pipeline

```
Issue Analyst → Explorer → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

| Agent | Description |
|-------|-------------|
| Issue Analyst | Parse issue into requirements (fetches via GitHub/GitLab API) |
| Explorer | Deep codebase analysis with file reading (10 min timeout) |
| Clarify | Identify ambiguities and ask clarifying questions |
| Architect | Create file-level implementation plan |
| Implementer | Write code following architect's plan |
| Test Validator | Write tests covering all acceptance criteria |
| Reviewer | Security, performance, code quality checks |
| Commit | Create branch, commit, PR (if GitHub repo available) |

### Review Pipeline

10 parallel agents analyze different aspects of the PR, followed by a Signoff agent:

| Agent | Category |
|-------|----------|
| Context | PR description clarity, linked issues, scope |
| Architecture | Design decisions, patterns, coupling |
| Correctness | Logic errors, edge cases, async handling |
| Security | Injection risks, secrets, auth/authz |
| Performance | N+1 queries, blocking calls, memory |
| Test Coverage | Unit tests, edge cases, test quality |
| Readability | Naming, complexity, duplication |
| Consistency | Style guide, naming conventions |
| Error Handling | Error catching, logging, retries |
| Documentation | Comments, API docs, changelog |
| Signoff | Final synthesis and recommendation |

---

## Project Structure

```
mycrew/
├── cli.py                    # Unified CLI (development/review)
├── main.py                   # CLI dispatcher
│
├── agents/                  # All agents
│   ├── development/          # Development pipeline agents
│   │   ├── architect.py
│   │   ├── clarify.py
│   │   ├── commit.py
│   │   ├── explorer.py
│   │   ├── implementer.py
│   │   ├── issue_analyst.py
│   │   ├── reviewer.py
│   │   └── test_validator.py
│   │
│   └── review/              # Review pipeline agents
│       ├── architecture.py
│       ├── consistency.py
│       ├── context.py
│       ├── correctness.py
│       ├── documentation.py
│       ├── error_handling.py
│       ├── performance.py
│       ├── pr_review.py       # Orchestrator
│       ├── readability.py
│       ├── security.py
│       ├── signoff.py
│       └── test_coverage.py
│
├── pipelines/                # Orchestration
│   ├── development/
│   │   ├── pipeline_runner.py
│   │   └── cli.py
│   │
│   └── review/
│       ├── review_runner.py
│       └── cli.py
│
├── shared/                   # Shared modules
│   ├── base.py               # BaseCrew
│   ├── exceptions.py
│   ├── issues.py             # Issue fetching
│   ├── pulls.py              # PR fetching
│   ├── llm.py               # LLM config
│   ├── settings.py           # Settings
│   └── tools.py              # Tools
│
├── git_providers/
├── pipeline_state.py
├── providers.py
├── result.py
└── utils.py
```

---

## Development

### Install for Development

```bash
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync --all-extras
```

### Tools

The pipeline uses native CrewAI tools:

| Tool | Description |
|------|-------------|
| `FileReadTool` | Read files from repository |
| `DirectoryReadTool` | List directory contents |
| `WriteFileTool` | Write files to repository |
| `SerperDevTool` | Web search |
| `EXASearchTool` | Code/web search |
| `ScrapeWebsiteTool` | Scrape web content |
| `CodeInterpreterTool` | Run code in sandbox |
| `TactiqMeetingTool` | Fetch Tactiq meeting context (custom) |

---

## Troubleshooting

### Rate Limit Errors

The pipeline uses OpenRouter with automatic model fallback. If you hit rate limits frequently:
- Use a paid OpenRouter plan
- Or switch to HuggingFace provider

### Context Length Errors

The pipeline passes full context to all crews without truncation. If you encounter context length errors, the issue may be too large—consider breaking it into smaller issues.

---

## License

MIT
