# Code Pipeline: Your AI-Powered Development Team

## Imagine Having a Complete Development Team at Your Fingertips

**Code Pipeline** is like having a full software development team that works for you 24/7. Instead of hiring individual developers, you get a complete workflow system where specialized AI agents handle every step of your project—from understanding what you need, to planning, building, testing, and delivering working code.

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
cp config.example.yaml config.yaml
# Edit config.yaml and set OPENROUTER_API_KEY
```

### Run the Pipeline

```bash
# Using Task (recommended)
task run TASK_DESC="Add a hello world function"

# Or with uv directly
uv run kickoff -t "Add a hello world function" -r .

# Docker
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  -e OPENROUTER_API_KEY=your_key \
  iklobato/mycrew -t "Add feature" -r .
```

---

## Configuration

### Environment Variables

Set these before running:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM API key from [openrouter.ai](https://openrouter.ai) |
| `HUGGINGFACE_API_KEY` | No | HuggingFace token for local models |
| `GITHUB_TOKEN` | No | GitHub token for cloning repos, creating PRs |
| `SERPER_API_KEY` | No | Serper API key for web search |
| `GITHUB_WEBHOOK_SECRET` | No | Secret for webhook signature verification |
| `CODE_PIPELINE_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |

### config.yaml

Copy `config.example.yaml` to `config.yaml` and customize:

```yaml
pipeline:
  task: "Your development task"
  repo_path: "."
  branch: "main"
  dry_run: false
  test_command: "pytest"

api_keys:
  openrouter_api_key: "${OPENROUTER_API_KEY}"  # Or paste key directly
  github_token: "${GITHUB_TOKEN}"
  serper_api_key: "${SERPER_API_KEY}"

# Provider: openrouter (default) or huggingface
provider_type: "openrouter"

# Model configuration (optional - defaults work well)
models:
  analyze_issue:
    primary: "openrouter/deepseek/deepseek-chat"
    fallbacks:
      - "openrouter/qwen/qwen-2.5-coder-32b-instruct"
```

---

## Usage

### Basic Usage

```bash
# Minimal run (uses current directory)
task run TASK_DESC="Add dark mode"

# With repository path
task run TASK_DESC="Fix login bug" R=/path/to/repo

# With test command
task run TASK_DESC="Add feature" TEST="pytest"

# Dry run (skip git commit/PR)
task run TASK_DESC="Add feature" DRY_RUN=1
```

### Advanced Usage

```bash
# Full options via CLI
uv run kickoff \
  -t "Add user authentication" \
  -r ./my-app \
  -b main \
  -n 3 \
  --test-command "pytest" \
  --dry-run

# Run from scratch (ignore checkpoints)
task run TASK_DESC="Add feature" F=1

# With GitHub repo for search
task run TASK_DESC="Fix bug" GITHUB_REPO=owner/repo

# With issue URL for context
task run TASK_DESC="Implement feature" ISSUE_URL="https://github.com/owner/repo/issues/123"
```

### Task Variables

| Variable | Short | Description | Default |
|----------|-------|-------------|---------|
| `TASK_DESC` | - | Task description | (required) |
| `R` | - | Repository path | `.` |
| `B` | - | Git branch | `main` |
| `F` | - | From scratch (1/0) | `1` |
| `DRY_RUN` | - | Skip commit (1/0) | `0` |
| `N` | - | Max retries | `3` |
| `TEST` | - | Test command | - |
| `V` | - | Verbose logging (1/0) | `0` |
| `GITHUB_REPO` | - | GitHub owner/repo | - |
| `ISSUE_URL` | - | GitHub issue URL | - |

### Docker

```bash
# Run with config file
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  iklobato/mycrew -c config.yaml

# Run with task description
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  iklobato/mycrew -t "Add feature" -r .
```

---

## Webhook (GitHub Integration)

Trigger the pipeline from GitHub when an issue is assigned or a PR review comment is created.

### Setup

1. Create a GitHub token with `repo` and `admin:repo_hook` scopes
2. Set environment variables:
   ```bash
   export GITHUB_TOKEN=ghp_xxx
   export GITHUB_WEBHOOK_SECRET=your_secret
   export OPENROUTER_API_KEY=your_key
   ```
3. Register the webhook:
   ```bash
   uv run register_webhook owner/repo
   ```
4. Deploy the webhook server:
   ```bash
   # Deploy to your hosting (Fly.io, DigitalOcean, etc.)
   # Or run locally:
   uv run webhook
   ```

### Webhook Events

- **Issues**: Triggers when an issue is assigned
- **Pull Request Review Comment**: Triggers on review comments

---

## Providers

### OpenRouter (Default)

Uses OpenRouter as the LLM backend with automatic model fallback:

- **Cost-effective models**: DeepSeek, Qwen, Gemini Flash, Mistral
- **Automatic retries**: Falls back to alternative models on rate limits
- **No setup**: Just get an API key from [openrouter.ai](https://openrouter.ai)

### HuggingFace

Uses HuggingFace Inference API:

```yaml
provider_type: "huggingface"
models:
  analyze_issue:
    primary: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
```

Supported models are defined in `src/code_pipeline/llm.py` under `ModelMappings`.

---

## Pipeline Flow

```
Issue Analyst → Explorer → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

### Crews

1. **Issue Analyst** - Parse task into structured requirements
2. **Explorer** - Analyze codebase structure and dependencies
3. **Clarify** - Resolve ambiguities via human questions
4. **Architect** - Create file-level implementation plan
5. **Implementer** - Write code following the plan
6. **Test Validator** - Write and validate tests
7. **Reviewer** - Code review with security/perf checks
8. **Commit** - Create branch, commit, and PR

---

## CLI Reference

```
usage: kickoff [-h] [-c CONFIG] [-t TASK] [-r REPO_PATH] [-b BRANCH]
               [-n MAX_RETRIES] [-f] [--dry-run] [--test-command TEST_COMMAND]
               [--programmatic] [-v] [--debug]
               issue_url

positional arguments:
  issue_url             GitHub issue URL

optional arguments:
  -c, --config CONFIG   Path to config.yaml
  -t, --task TASK       Task description
  -r, --repo-path REPO_PATH
                        Repository path (default: .)
  -b, --branch BRANCH   Base branch (default: main)
  -n, --max-retries MAX_RETRIES
                        Max retries (default: 3)
  -f, --from-scratch    Start from scratch, ignoring checkpoints
  --dry-run             Skip git commit and PR
  --test-command TEST_COMMAND
                        Test command (e.g., pytest, npm test)
  --programmatic        Programmatic mode (no human interaction)
  -v, --verbose         Verbose logging
  --debug               Debug logging
```

---

## Development

### Install for Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync --all-extras

# Run tests
pytest

# Run linter
ruff check .
ruff format --check .

# Run type checking
mypy --strict src/code_pipeline
```

### Project Structure

```
src/code_pipeline/
├── main.py          # Pipeline flow orchestration
├── settings.py      # Configuration management
├── llm.py           # LLM provider and model config
├── providers.py     # OpenRouter & HuggingFace providers
├── utils.py         # Shared utilities
├── webhook.py       # Webhook API server
├── crews/           # Crew implementations
│   ├── base.py      # PipelineCrewBase
│   ├── abc_crew.py  # ABCrew abstract base
│   └── */           # Individual crews
└── tools/           # Custom tools
    ├── repo_shell_tool.py
    ├── repo_file_writer_tool.py
    └── ...
```

---

## Troubleshooting

### Rate Limit Errors

The pipeline automatically retries with fallback models. If you hit rate limits frequently:
- Use a paid OpenRouter plan
- Or switch to HuggingFace provider

### Context Length Errors

Reduce task scope or focus on specific files:
```bash
task run TASK_DESC="Fix login in auth.py only" R=. FOCUS_PATHS=auth.py
```

### Webhook Not Triggering

1. Verify webhook is registered: `gh repo hooks list`
2. Check webhook URL is reachable
3. Verify `GITHUB_WEBHOOK_SECRET` matches

---

## License

MIT
