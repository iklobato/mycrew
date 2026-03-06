# mycrew

A software development crew powered by [crewAI](https://crewai.com). mycrew runs an event-driven pipeline that explores a codebase, plans changes, implements them, reviews the work, and commits—all driven by a single task description. Use it exclusively for software development workflows.

## Installation

**Requirements:** Python >=3.10, <3.13

This project uses [UV](https://docs.astral.sh/uv/) for dependency management.

1. Install uv (if needed):

```bash
pip install uv
```

2. Clone the repo and install dependencies from the project root:

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

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--task` | `-t` | (required) | Task description for the pipeline |
| `--repo-path` | `-r` | current dir | Repository to work in |
| `--branch` | `-b` | main | Git branch for commits |
| `--retries` | `-n` | 3 | Max implement→review retries |
| `--dry-run` | — | false | Skip actual git commit |

**Examples:**

```bash
# Dry run: explore, plan, implement, review—but do not commit
uv run kickoff -t "add user login" -r ~/projects/myapp --dry-run

# Full run on dev branch, up to 5 retries
uv run kickoff -t "fix the auth bug" -r ~/projects/myapp -b dev -n 5
```

**Plot the flow diagram:**

```bash
uv run plot
```

## Pipeline Overview

The flow runs five crews in sequence:

1. **Explore** — Scans the repo structure, tech stack, and conventions
2. **Plan** — Designs the implementation approach
3. **Implement** — Writes and edits code
4. **Review** — Validates changes; on rejection, loops back to Implement (up to `--retries`)
5. **Commit** — Stages and commits (skipped when `--dry-run` is set)

Agents use a `RepoShellTool` to run safe shell commands inside the target repository.

## Support

For support, questions, or feedback regarding the mycrew or crewAI.

- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
