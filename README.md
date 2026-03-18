# mycrew: AI-Powered Development & Review Pipelines

**mycrew** provides two AI-powered pipelines:
- **Development Pipeline**: Transforms GitHub/GitLab issues into implemented code
- **Review Pipeline**: Comprehensive PR review with 10 parallel specialized agents

---

## Quick Start

```bash
# 1. Install
pip install uv
git clone https://github.com/iklobato/mycrew.git
cd mycrew
uv sync

# 2. Configure
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# 3. Run
./cli.py development "https://github.com/owner/repo/issues/123"
./cli.py review "https://github.com/owner/repo/pull/123"
```

---

## CLI Usage

```bash
# Development pipeline
./cli.py development <issue-url>
./cli.py dev <issue-url>

# Review pipeline
./cli.py review <pr-url>
./cli.py rev <pr-url>

# Options
--repo-path /path/to/repo    # Local repository path
-v                              # Verbose output

# Help
./cli.py --help
./cli.py development --help
./cli.py review --help
```

---

## Development Pipeline

Transforms GitHub/GitLab issues into implemented code.

```
Issue Analyst → Explorer → Clarify → Architect → Implementer → Test Validator → Reviewer → Commit
```

| Agent | Description |
|-------|-------------|
| Issue Analyst | Parse issue into requirements |
| Explorer | Deep codebase analysis with file reading |
| Clarify | Identify ambiguities |
| Architect | Create file-level implementation plan |
| Implementer | Write code following architect's plan |
| Test Validator | Write tests covering acceptance criteria |
| Reviewer | Security, performance, code quality checks |
| Commit | Create branch, commit, PR |

---

## Review Pipeline

Comprehensive PR review with 10 parallel agents + Signoff.

```
┌─────────────────────────────────────────────────────────────┐
│              10 Parallel Agents (async_execution=True)    │
│                                                             │
│  Context | Architecture | Correctness | Security | Perf    │
│  Test Coverage | Readability | Consistency | Err Handling  │
│  Documentation                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    ┌─────────────┐
                    │  Signoff    │
                    └─────────────┘
```

| Agent | Focus |
|-------|-------|
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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM API key from [openrouter.ai](https://openrouter.ai) |
| `GITHUB_TOKEN` | No | GitHub token for issues/PRs |
| `GITLAB_TOKEN` | No | GitLab token for issues/MRs |
| `SERPER_API_KEY` | No | Web search |
| `PROVIDER_TYPE` | No | "openrouter" (default) or "huggingface" |

---

## Project Structure

```
mycrew/
├── cli.py                    # Unified CLI
├── agents/
│   ├── development/          # Development agents
│   └── review/              # Review agents (10 + Signoff)
├── pipelines/
│   ├── development/
│   └── review/
├── shared/                  # Issues, pulls, LLM, settings, tools
└── ...
```

---

## License

MIT
