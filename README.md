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
# Clone repo from issue URL (requires GITHUB_TOKEN)
python -m mycrew "https://github.com/owner/repo/issues/123"

# Use local repository instead of cloning
python -m mycrew --repo-path /path/to/local/repo

# Use local repo with issue URL (uses local repo, parses issue from URL)
python -m mycrew --repo-path /path/to/local/repo "https://github.com/owner/repo/issues/123"

# Using the kickoff client (recommended)
kickoff-client "https://github.com/owner/repo/issues/123"

# Docker
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  -e OPENROUTER_API_KEY=your_key \
  iklobato/mycrew "https://github.com/owner/repo/issues/123"
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
| `GITHUB_WEBHOOK_SECRET` | No | Secret for webhook signature verification |
| `CODE_PIPELINE_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |

*Required when using `issue_url` (to clone repo). Not required when using `--repo-path` with local repo.

### config.yaml

Copy `config.example.yaml` to `config.yaml` and customize:

```yaml
pipeline:
  issue_url: "https://github.com/owner/repo/issues/123"
  branch: "main"
  from_scratch: false
  max_retries: 3
  dry_run: false
  programmatic: false

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

## Docker

### Prerequisites

1. Install Docker
2. Build the image:
   ```bash
   docker build -t mycrew/webhook:latest .
   ```

### Docker Compose (Recommended)

```bash
# Start webhook server
docker compose up -d webhook

# View logs
docker compose logs -f webhook

# Stop
docker compose down
```

### Docker Run

```bash
# Start webhook server
docker run -d --name mycrew-webhook -p 8000:8000 \
  -e OPENROUTER_API_KEY=your_key \
  -e GITHUB_TOKEN=your_token \
  mycrew/webhook:latest

# Stop
docker rm -f mycrew-webhook
```

### Volume Mounts

| Mount | Description |
|-------|-------------|
| `./workspace:/workspace` | Where the pipeline clones and modifies the target repository |
| `./config.yaml:/app/config.yaml:ro` | Custom configuration file (optional) |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes* | LLM API key from openrouter.ai. Required for AI agents to generate code |
| `GITHUB_TOKEN` | No | Personal Access Token with `repo` scope. Used to clone repos, commit changes, create PRs |
| `GITHUB_WEBHOOK_SECRET` | No | Secret string to verify webhook requests from GitHub |
| `SERPER_API_KEY` | No | API key for Serper web search. Enables agents to search for best practices |
| `DEFAULT_DRY_RUN` | No | When true, pipeline runs without git commits or PRs. Default: `false` |
| `DEFAULT_BRANCH` | No | Base branch for feature branches. Default: `main` |

*Required when using OpenRouter provider

---

## Kickoff Client

Trigger the pipeline from inside the container using the kickoff client.

### Prerequisites

```bash
# Start webhook server first
docker compose up -d webhook
```

### Usage

```bash
# Inside container via docker exec
docker exec mycrew-webhook /app/.venv/bin/python -m mycrew.kickoff_client \
  "https://github.com/owner/repo/issues/123" \
  --branch main
```

### Parameters

| Arg | Description |
|-----|-------------|
| `issue_url` (positional) | GitHub issue URL. The pipeline will implement the feature/fix described in this issue. Format: `https://github.com/owner/repo/issues/123` |
| `--branch` | Target branch name. Base branch for feature branch. Default: `main` |
| `--from-scratch` | Start pipeline from beginning, ignoring saved checkpoint state. Use when you want a fresh start |
| `--max-retries` | Number of retry attempts if implementation fails. Default: `3` |
| `--dry-run` | Run pipeline without making git commits or creating PRs. Changes exist locally but aren't pushed |
| `--programmatic` | Disable human-in-the-loop interactions. Agents won't ask questions - they'll make their best guess |
| `--url` | Base URL of the webhook server. Default: `http://localhost:8000` |

### Examples

```bash
# Dry run (no commits)
docker exec mycrew-webhook /app/.venv/bin/python -m mycrew.kickoff_client \
  "https://github.com/owner/repo/issues/123" \
  --dry-run

# Full options
docker exec mycrew-webhook /app/.venv/bin/python -m mycrew.kickoff_client \
  "https://github.com/owner/repo/issues/123" \
  --branch main \
  --from-scratch \
  --max-retries 3 \
  --programmatic
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

### Webhook JSON Body

| Field | Type | Description |
|-------|------|-------------|
| `issue_url` | string | GitHub issue URL to implement |
| `branch` | string | Base branch name. Default: `main` |
| `from_scratch` | boolean | Start fresh, ignoring checkpoints. Default: `false` |
| `max_retries` | integer | Max retry attempts. Default: `3` |
| `dry_run` | boolean | Skip git operations. Default: `false` |
| `programmatic` | boolean | No human interaction. Default: `false` |
| `callback_url` | string | URL to receive POST callback when pipeline completes |

### Example Webhook Call

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issue_url": "https://github.com/owner/repo/issues/123",
    "branch": "main",
    "dry_run": false
  }'
```

---

## Parameters Reference

### CLI (kickoff command)

| Arg | Description |
|-----|-------------|
| `issue_url` (positional) | GitHub issue URL. The pipeline will implement the feature/fix described in this issue. Format: `https://github.com/owner/repo/issues/123`. Optional if `--repo-path` is provided. |
| `--repo-path` | Local repository path. If provided, uses this directory instead of cloning from issue URL. If no issue_url provided, detects github_repo from local repo. |
| `-c, --config` | Path to config.yaml file. Contains pipeline configuration including model settings |
| `-b, --branch` | Base branch name. The branch to create feature branches from. Default: `main` |
| `-n, --max-retries` | Maximum retry attempts if implementation fails. The pipeline will retry the implementer crew up to this many times. Default: `3` |
| `-f, --from-scratch` | Ignore all previous checkpoints and run the entire pipeline from the start. Use when you want a fresh start |
| `--dry-run` | Run pipeline without making git commits or creating PRs. Changes exist locally but aren't pushed |
| `--programmatic` | Disable all human-in-the-loop interactions. Agents won't ask questions - they'll make their best guess |
| `-v, --verbose` | Enable verbose logging. Shows more detailed output about what agents are doing |
| `--debug` | Enable debug logging. Shows all internal details including API calls |

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

### Advanced Usage

```bash
# Full options via CLI
python -m mycrew "https://github.com/owner/repo/issues/123" \
  --branch main \
  --max-retries 3 \
  --dry-run

# Run from scratch (ignore checkpoints)
kickoff-client "https://github.com/owner/repo/issues/123" --from-scratch

# With custom webhook URL
kickoff-client "https://github.com/owner/repo/issues/123" --url http://localhost:8000
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `issue_url` | GitHub issue URL (required) | - |
| `--branch` | Git branch | `main` |
| `--from-scratch` | Start from scratch ignoring checkpoints | `false` |
| `--max-retries` | Maximum retry attempts | `3` |
| `--dry-run` | Skip git commit/PR | `false` |
| `--programmatic` | No human interaction | `false` |
| `--url` | Webhook URL | `http://localhost:8000` |

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

Supported models are defined in `src/mycrew/llm.py` under `ModelMappings`.

---

## Tactiq Integration (Optional)

Get implementation context from meeting transcripts to reduce clarifying questions.

### Setup

1. Get your Tactiq API token from [Tactiq Settings](https://app.tactiq.io/settings)
2. Set the environment variable:
   ```bash
   export TACTIQ_TOKEN=your_token
   ```

### How It Works

```
Issue Analyst → Explorer → [TactiqResearch] → Clarify → Architect → ...
                                       ↓
                              If meeting resolves all questions:
                                       ↓
                                   Skip Clarify
```

When a Tactiq meeting ID is provided:
1. **TactiqResearch** fetches meeting details (transcript, decisions, action items)
2. **Tactiq AI** answers questions about ambiguities from the issue
3. **Decision**: If meeting resolves all questions → skip Clarify, go directly to Architect
4. **If gaps remain** → Clarify asks only unanswered questions

### Usage

```bash
# Standard run with issue URL
kickoff-client "https://github.com/owner/repo/issues/123"

# Without issue - specify task description via config
# (set issue_url in config.yaml or pass via environment)
```

### Configuration

```yaml
# config.yaml
pipeline:
  issue_url: "https://github.com/owner/repo/issues/123"
  branch: "main"
  dry_run: false

api_keys:
  github_token: "${GITHUB_TOKEN}"
```

---

## Pipeline Flow

```
Issue Analyst → Explorer → [TactiqResearch (optional)] → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

### Crews

1. **Issue Analyst** - Parse task into structured requirements
2. **Explorer** - Analyze codebase structure and dependencies
3. **TactiqResearch** - (Optional) Fetch meeting context, ask AI questions, determine if clarification needed
4. **Clarify** - Resolve ambiguities via human questions (skipped if Tactiq resolves all)
5. **Architect** - Create file-level implementation plan
6. **Implementer** - Write code following the plan
7. **Test Validator** - Write and validate tests
8. **Reviewer** - Code review with security/perf checks
8. **Commit** - Create branch, commit, and PR

---

## CLI Reference

```
usage: main.py [-h] [--repo-path REPO_PATH] [--branch BRANCH] [--from-scratch]
               [--max-retries MAX_RETRIES] [--dry-run] [--programmatic]
               [--tactiq-meeting-id TACTIQ_MEETING_ID] [--verbose] [--debug]
               [issue_url]

positional arguments:
  issue_url             GitHub issue URL (optional if --repo-path is provided)

optional arguments:
  -h, --help           show this help message and exit
  --repo-path REPO_PATH
                       Local repo path (if not provided, repo will be cloned)
  --branch BRANCH       Base branch (default: main)
  --from-scratch        Start from scratch, ignoring checkpoints
  --max-retries MAX_RETRIES
                       Max retries (default: 3)
  --dry-run             Skip git commit and PR
  --programmatic        Programmatic mode (no human interaction)
  --tactiq-meeting-id TACTIQ_MEETING_ID
                       Tactiq meeting ID for context
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
mypy --strict src/mycrew
```

### Project Structure

```
src/mycrew/
├── main.py          # Pipeline flow orchestration
├── settings.py      # Configuration management
├── llm.py           # LLM provider and model config
├── providers.py     # OpenRouter & HuggingFace providers
├── utils.py         # Shared utilities
├── webhook.py       # Webhook API server
├── kickoff_client.py # HTTP client for triggering pipeline
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

Reduce task scope or focus on specific files by creating a more focused issue:
```bash
# Create a focused issue for a specific file
kickoff-client "https://github.com/owner/repo/issues/456"  # Issue: Fix login in auth.py
```

### Webhook Not Triggering

1. Verify webhook is registered: `gh repo hooks list`
2. Check webhook URL is reachable
3. Verify `GITHUB_WEBHOOK_SECRET` matches

---

## License

MIT
