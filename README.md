# mycrew: Your AI-Powered Development Team

## Imagine Having a Complete Development Team at Your Fingertips

**mycrew** is like having a full software development team that works for you 24/7. Instead of hiring individual developers, you get a complete workflow system where specialized AI agents handle every step of your project—from understanding what you need, to planning, building, testing, and delivering working code.

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
# Copy .env.example to .env and set your API keys
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY
```

### Run the Pipeline

```bash
# Run with GitHub issue URL (fetches issue via GitHub API)
python -m mycrew "https://github.com/owner/repo/issues/123"

# Run with GitLab issue URL (fetches issue via GitLab API)
python -m mycrew "https://gitlab.com/owner/repo/-/issues/456"

# Use local repository with issue URL
python -m mycrew --repo-path /path/to/local/repo "https://github.com/owner/repo/issues/123"
```

---

## Configuration

### Environment Variables

Set these before running:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM API key from [openrouter.ai](https://openrouter.ai) |
| `HUGGINGFACE_API_KEY` | No | HuggingFace token for local models |
| `GITHUB_TOKEN` | No | GitHub token for GitHub issues |
| `GITLAB_TOKEN` | No | GitLab token for GitLab issues |
| `SERPER_API_KEY` | No | Serper API key for web search |
| `TACTIQ_TOKEN` | No | Tactiq API token from [Tactiq settings](https://app.tactiq.io/settings) |
| `CODE_PIPELINE_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |
| `PROVIDER_TYPE` | No | LLM provider: "openrouter" (default) or "huggingface" |
| `CREWAI_TRACING_ENABLED` | No | Enable CrewAI telemetry (default: false) |
| `DEFAULT_DRY_RUN` | No | Default dry run mode (default: false) |
| `DEFAULT_BRANCH` | No | Default branch (default: main) |
| `TACTIQ_MEETING_ID` | No | Default Tactiq meeting ID |

---

## Usage

### Basic Usage

```bash
# GitHub issue
python -m mycrew "https://github.com/owner/repo/issues/123"

# GitLab issue
python -m mycrew "https://gitlab.com/owner/repo/-/issues/456"

# Local repo with issue URL
python -m mycrew --repo-path /path/to/local/repo "https://github.com/owner/repo/issues/123"

# Verbose output
python -m mycrew "https://github.com/owner/repo/issues/123" -v
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `issue_url` | GitHub or GitLab issue URL | - |
| `--repo-path` | Local repository path | - |
| `-v, --verbose` | Enable verbose logging | `false` |

---

## Providers

### OpenRouter (Default)

Uses OpenRouter as the LLM backend:

- **Models**: deepseek-r1, qwen3-coder, gemma-3-27b-it, mistral-small-3.1, devstral-small
- **Architect**: Uses claude-3.5-sonnet for detailed planning
- **Stage-specific**: Each pipeline stage uses optimized models

### HuggingFace

Uses HuggingFace Inference API. Set `PROVIDER_TYPE=huggingface` in `.env`.

---

## Pipeline Flow

```
Issue Analyst → Explorer → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

### Crews (in order)

1. **Issue Analyst** - Parse issue into requirements (fetches via GitHub/GitLab API)
2. **Explorer** - Deep codebase analysis with file reading (10 min timeout)
3. **Clarify** - Identify ambiguities and ask clarifying questions
4. **Architect** - Create file-level implementation plan (uses claude-3.5-sonnet)
5. **Implementer** - Write code following architect's plan
6. **Test Validator** - Write tests covering all acceptance criteria
7. **Reviewer** - Security, performance, code quality checks
8. **Commit** - Create branch, commit, PR (if GitHub repo available)

---

## Development

### Install for Development

```bash
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync --all-extras
```

### Project Structure

```
src/mycrew/
├── main.py                 # Pipeline flow orchestration
├── settings.py             # Configuration management (env vars)
├── llm.py                  # LLM provider, stage-specific models
├── providers.py            # OpenRouter & HuggingFace providers
├── utils.py                # Shared utilities
├── exceptions.py           # Custom exception hierarchy
├── pipeline_state.py       # Pipeline state management
├── result.py               # Result types
├── issues/                 # Issue fetching (GitHub/GitLab API)
│   ├── __init__.py
│   ├── models.py          # IssueSource, IssueContent
│   ├── parsers.py         # URL parsers
│   ├── fetchers.py        # GitHub/GitLab API fetchers
│   ├── factory.py         # IssueHandler factory
│   └── exceptions.py      # Issue-specific exceptions
├── crews/                  # Crew implementations
│   ├── issue_analyst_crew/
│   ├── explorer_crew/
│   ├── clarify_crew/
│   ├── architect_crew/
│   ├── implementer_crew/
│   ├── test_validator_crew/
│   ├── reviewer_crew/
│   ├── commit_crew/
│   └── tactiq_research_crew/
└── tools/                  # Tools
    └── __init__.py        # Native crewai_tools + custom tools
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

The pipeline now passes full context to all crews without truncation. If you encounter context length errors, the issue may be too large - consider breaking it into smaller issues.

---

## License

MIT
