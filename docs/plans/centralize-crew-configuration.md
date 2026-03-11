# Plan: Centralize Crew Configuration

## 1. Duplication Audit

### 1.1 Class-level (all 7 crews)

| Duplication | Count | Location |
|-------------|-------|----------|
| `agents_config = "config/agents.yaml"` | 7 | Every crew class |
| `tasks_config = "config/tasks.yaml"` | 7 | Every crew class |

These are required by CrewAI's `CrewBase`; each crew resolves them relative to its package (e.g. `issue_analyst_crew/config/agents.yaml`).

### 1.2 Per-Agent (every `Agent()` call)

| Duplication | Count | Notes |
|-------------|-------|-------|
| `verbose=False` | 47 | Every agent across all crews |
| `config=self.agents_config["agent_name"]` | 47 | Agent name varies |
| `llm=get_llm_for_stage(stage, agent_name)` | 47 | Stage/agent varies |
| `tools=...` | 47 | Varies per agent |

Commit crew only (5 agents):

| Duplication | Count |
|-------------|-------|
| `max_iter=3` | 5 |
| `max_rpm=10` | 5 |

### 1.3 Per-Task (every `Task()` call)

| Duplication | Count |
|-------------|-------|
| `config=self.tasks_config["task_name"]` | 47 | Task name varies |

### 1.4 Per-Crew (every `Crew()` call)

| Setting | issue_analyst | explorer | architect | implementer | reviewer | commit | clarify | test_validator |
|---------|---------------|----------|-----------|-------------|----------|--------|---------|----------------|
| `process=Process.sequential` | yes | yes | yes | yes | yes | yes | yes | yes |
| `verbose=False` | yes | yes | yes | yes | yes | yes | yes | yes |
| `tracing=False` | yes | yes | yes | yes | yes | yes | yes | no |
| `output_log_file=True` | yes | yes | yes | yes | yes | yes | no | no |
| `memory=False` | yes | yes | yes | yes | yes | yes | no | no |

### 1.5 Config file (unused)

`config.example.yaml` defines `agents:` with:
- `verbose: false`
- `memory: false`
- `output_log_file: true`

These are not wired to crews; crews hardcode values instead.

---

## 2. Centralization Strategy

### 2.1 Add crew defaults to Settings

Extend `Settings` (or add frozen `CrewConfig` model) with:

```python
# Crew/agent defaults (from config agents section)
crew_agent_verbose: bool = False
crew_verbose: bool = False
crew_tracing: bool = False
crew_output_log_file: bool = True
crew_memory: bool = False
crew_agent_max_iter: int = 3
crew_agent_max_rpm: int = 10
```

### 2.2 Wire config.yaml

In `init_settings_from_config()`, read `config_data.get("agents", {})`:
- `verbose` -> `crew_agent_verbose`, `crew_verbose`
- `memory` -> `crew_memory`
- `output_log_file` -> `crew_output_log_file`

Add optional `config_data.get("crews", {})` for:
- `tracing` -> `crew_tracing`
- `max_iter`, `max_rpm` -> `crew_agent_max_iter`, `crew_agent_max_rpm`

### 2.3 Config path constants

Create constants (e.g. in `settings.py` or `crews/constants.py`):

```python
CREW_AGENTS_CONFIG = "config/agents.yaml"
CREW_TASKS_CONFIG = "config/tasks.yaml"
```

Each crew: `agents_config = CREW_AGENTS_CONFIG`, `tasks_config = CREW_TASKS_CONFIG`.

### 2.4 Crew kwargs helper

```python
def crew_kwargs(full: bool = True) -> dict:
    """Crew() kwargs from centralized config."""
    stg = get_settings()
    base = {
        "process": Process.sequential,
        "verbose": stg.crew_verbose,
        "tracing": stg.crew_tracing,
    }
    if full:
        base["output_log_file"] = stg.crew_output_log_file
        base["memory"] = stg.crew_memory
    return base
```

- Full crews (6): `**crew_kwargs()`
- clarify: `**crew_kwargs(full=False)` + override if needed
- test_validator: `**crew_kwargs(full=False)`

---

## 3. Implementation Phases

### Phase 1: Settings + config wiring

1. Add to `Settings`: `crew_agent_verbose`, `crew_verbose`, `crew_tracing`, `crew_output_log_file`, `crew_memory`, `crew_agent_max_iter`, `crew_agent_max_rpm` with current defaults.
2. In `init_settings_from_config()`, read `agents.verbose`, `agents.memory`, `agents.output_log_file` and optional `crews.tracing`, `crews.max_iter`, `crews.max_rpm`.
3. Add `CREW_AGENTS_CONFIG`, `CREW_TASKS_CONFIG` constants.

### Phase 2: Crews use Settings

4. Replace `verbose=False` in Agent() with `verbose=get_settings().crew_agent_verbose`.
5. Add `crew_kwargs(full: bool = True)` helper; crews use `**crew_kwargs()` or `**crew_kwargs(full=False)`.
6. Commit crew: use `get_settings().crew_agent_max_iter` and `crew_agent_max_rpm` for its 5 agents.

### Phase 3: Config path constants

7. Replace `agents_config = "config/agents.yaml"` with `agents_config = CREW_AGENTS_CONFIG`.
8. Same for `tasks_config`.

### Phase 4: Agent factory (defer)

9. Only add `create_agent()` if Phase 2 leaves significant duplication. Per Principle 0, avoid abstraction until needed.

---

## 4. Config file schema

Extend `config.example.yaml` with optional `crews` section:

```yaml
agents:
  verbose: false
  memory: false
  output_log_file: true

# Optional: crew-level defaults
crews:
  tracing: false
  max_iter: 3
  max_rpm: 10
```

---

## 5. Summary

| Item | Action |
|------|--------|
| Agent `verbose` | From `Settings.crew_agent_verbose` |
| Crew `process`, `verbose`, `tracing`, `output_log_file`, `memory` | From `Settings` via `crew_kwargs()` |
| Commit `max_iter`, `max_rpm` | From `Settings.crew_agent_max_iter`, `crew_agent_max_rpm` |
| `agents_config`, `tasks_config` paths | Constants `CREW_AGENTS_CONFIG`, `CREW_TASKS_CONFIG` |
| config.yaml `agents` section | Wired in `init_settings_from_config()` |

Avoided: Agent factory (Phase 4 deferred), abstract base class for crews (CrewBase contract unchanged).
