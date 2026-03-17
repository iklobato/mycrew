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
# Clone repo from issue URL (requires GITHUB_TOKEN)
python -m mycrew "https://github.com/owner/repo/issues/123"

# Use local repository instead of cloning
python -m mycrew --repo-path /path/to/local/repo

# Use local repo with issue URL (uses local repo, parses issue from URL)
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
| `GITHUB_TOKEN` | No* | GitHub token for cloning repos, creating PRs |
| `SERPER_API_KEY` | No | Serper API key for web search |
| `TACTIQ_TOKEN` | No | Tactiq API token from [Tactiq settings](https://app.tactiq.io/settings) |
| `CODE_PIPELINE_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |
| `PROVIDER_TYPE` | No | LLM provider: "openrouter" (default) or "huggingface" |
| `CREWAI_TRACING_ENABLED` | No | Enable CrewAI telemetry (default: false) |
| `DEFAULT_DRY_RUN` | No | Default dry run mode (default: false) |
| `DEFAULT_BRANCH` | No | Default branch (default: main) |
| `TACTIQ_MEETING_ID` | No | Default Tactiq meeting ID |

*Required when using `issue_url` (to clone repo). Not required when using `--repo-path` with local repo.

---

## Usage

### Basic Usage

```bash
# Clone repo from issue URL (requires GITHUB_TOKEN)
python -m mycrew "https://github.com/owner/repo/issues/123"

# Use local repository instead of cloning
python -m mycrew --repo-path /path/to/local/repo

# With repository path and issue URL
python -m mycrew --repo-path /path/to/local/repo "https://github.com/owner/repo/issues/123"

# Dry run (skip git commit/PR)
python -m mycrew "https://github.com/owner/repo/issues/123" --dry-run
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `issue_url` | GitHub issue URL (required if --repo-path not provided) | - |
| `--repo-path` | Local repository path | - |
| `-b, --branch` | Base branch for feature branches | `main` |
| `--from-scratch` | Start from scratch ignoring checkpoints | `false` |
| `-n, --max-retries` | Maximum retry attempts | `3` |
| `--dry-run` | Skip git commit/PR | `false` |
| `--programmatic` | No human interaction | `false` |
| `--tactiq-meeting-id` | Tactiq meeting ID for context | - |
| `-v, --verbose` | Enable verbose logging | `false` |

---

## Providers

### OpenRouter (Default)

Uses OpenRouter as the LLM backend with automatic model fallback:

- **Models**: deepseek-r1, qwen3-coder, gemma-3-27b-it, mistral-small-3.1, devstral-small
- **Automatic fallback**: Falls back to alternative models on rate limits
- **Stage-specific**: Each pipeline stage uses optimized models (analyze: reasoning, explore: code, review: analysis, etc.)

### HuggingFace

Uses HuggingFace Inference API. Set `PROVIDER_TYPE=huggingface` in `.env`.

Supported models are defined in `src/mycrew/llm.py` under `ModelMappings`.

---

## Pipeline Flow

```
Issue Analyst → Explorer → [TactiqResearch] → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

### Crews (in order)

1. **Issue Analyst** - Parse issue into requirements
2. **Explorer** - Analyze codebase structure, dependencies
3. **TactiqResearch** (optional) - Fetch meeting context, decide if clarification needed
4. **Clarify** - Ask human questions for ambiguities
5. **Architect** - Create file-level plan
6. **Implementer** - Write code, docstrings, run linters
7. **Test Validator** - Write tests, validate quality
8. **Reviewer** - Security, performance, accessibility checks
9. **Commit** - Create branch, commit, PR

---

## Development

### Install for Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync --all-extras
```

### Project Structure

```
src/mycrew/
├── main.py              # Pipeline flow orchestration (CrewAI Flow)
├── settings.py          # Configuration management (env vars)
├── llm.py              # LLM provider, stage-specific models, fallbacks
├── providers.py         # OpenRouter & HuggingFace provider implementations
├── utils.py             # Shared utilities
├── exceptions.py        # Custom exception hierarchy
├── pipeline_state.py    # Pipeline state management
├── result.py            # Result types
├── crews/              # Crew implementations (simple Python classes)
│   ├── explorer_crew/
│   ├── issue_analyst_crew/
│   ├── clarify_crew/
│   ├── architect_crew/
│   ├── implementer_crew/
│   ├── test_validator_crew/
│   ├── reviewer_crew/
│   ├── commit_crew/
│   └── tactiq_research_crew/
└── tools/              # Tools (native crewai_tools + custom TactiqMeetingTool)
    └── __init__.py
```

### Tools

The pipeline uses native CrewAI tools:

| Tool | Description |
|------|-------------|
| `FileReadTool` | Read files from repository |
| `DirectoryReadTool` | List directory contents |
| `SerperDevTool` | Web search |
| `EXASearchTool` | Code/web search |
| `ScrapeWebsiteTool` | Scrape web content |
| `CodeInterpreterTool` | Run code in sandbox |
| `TactiqMeetingTool` | Fetch Tactiq meeting context (custom) |

---

## Troubleshooting

### Rate Limit Errors

The pipeline automatically retries with fallback models. If you hit rate limits frequently:
- Use a paid OpenRouter plan
- Or switch to HuggingFace provider

### Context Length Errors

Reduce task scope or focus on specific files by creating a more focused issue.

---

## License

MIT
