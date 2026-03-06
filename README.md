# mycrew

A software development crew powered by [crewAI](https://crewai.com). mycrew runs an event-driven pipeline that explores a codebase, plans changes, implements them, reviews the work, and commits—exclusively for software development tasks.

## Installation

**Requirements:** Python >=3.10, <3.13

1. Install [uv](https://docs.astral.sh/uv/):

```bash
pip install uv
```

2. Clone this repository and install dependencies:

```bash
cd mycrew  # or your project directory
uv sync
```

Or use the crewAI CLI:

```bash
crewai install
```

3. Create a `.env` file in the project root and add your API key:

```
OPENAI_API_KEY=your_key_here
```

## How to Use

Run the pipeline from the project root with `uv run kickoff`. You must provide a task and the target repository path.

**Basic usage:**

```bash
uv run kickoff --task "add a hello world function" --repo-path /path/to/your/repo
```

**All options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--task` | `-t` | Task description for the pipeline (required) | — |
| `--repo-path` | `-r` | Path to the repository to modify | Current directory |
| `--branch` | `-b` | Git branch for commits | `main` |
| `--retries` | `-n` | Max implement→review retries | `3` |
| `--dry-run` | — | Skip actual git commit; only report what would be committed | `false` |

**Examples:**

```bash
# Dry run: explore, plan, implement, review, but do not commit
uv run kickoff -t "add user authentication" -r ./my-app --dry-run

# Full run on a specific branch
uv run kickoff -t "fix login bug" -r /Users/me/projects/api -b dev

# Allow up to 5 implement→review cycles before aborting
uv run kickoff -t "refactor payment module" -r ./backend -n 5
```

## Pipeline Overview

The flow runs five crews in sequence:

1. **Explore** — Scans the repository structure, tech stack, and conventions
2. **Plan** — Designs the implementation approach
3. **Implement** — Writes and applies code changes
4. **Review** — Validates the implementation; on rejection, loops back to Implement (up to `--retries`)
5. **Commit** — Stages and commits the changes (skipped when `--dry-run` is set)

## Support

- [crewAI documentation](https://docs.crewai.com)
- [crewAI GitHub](https://github.com/joaomdmoura/crewai)
- [crewAI Discord](https://discord.com/invite/X4JWnZnxPb)
