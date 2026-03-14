<!--
=============================================================================
SYNC IMPACT REPORT — mycrew project
=============================================================================
Version: 1.2.0 | Ratification: 2026-03-04 | Last amended: 2026-03-09

Scope: Backend pipeline and CrewAI orchestration. No frontend; frontend-specific
rules (e.g. CSP, CORS, client-side validation) apply only when exposing HTTP APIs.
=============================================================================
-->

# mycrew Project Constitution

**Version**: 1.2.0
**Ratification Date**: 2026-03-04
**Last Amended**: 2026-03-09

---

## Preamble

This constitution governs all engineering decisions made on the mycrew project
(this repository). It encodes the non-negotiable rules that every contributor —
human or AI — MUST follow. When a rule conflicts with a deadline or convenience,
the rule wins; exceptions require an explicit ADR in `docs/decisions/`.

Guiding philosophy: *Make it work, make it right, make it fast — in that order, and only as
far as you actually need to go. The best code is the code you didn't write.*

---

## Principle 0: Simplicity First — Never Overengineer

**Name**: The Single Most Important Principle

**Rules**:

- Contributors MUST do the simplest thing that correctly solves the **current, real, proven**
  problem. Hypothetical futures MUST NOT drive design.
- Abstraction, layers, patterns, frameworks, services, or complexity MUST NOT be introduced
  before there is **concrete and immediate evidence** they are needed.
- Complexity is the root cause of nearly every other problem; every abstraction is a cognitive
  tax paid by every developer who touches the code forever.
- A system that is simple and slightly wrong is almost always easier to fix than one that is
  architecturally elaborate and slightly wrong.
- When in doubt, prefer the option that writes less code.

**Rationale**: Overengineering creates maintenance burden, obscures intent, and makes bugs harder
to find and fix. The best code is often the code you decided not to write.

**Abstraction gate** (reinforced): Before any abstraction, pattern, or framework:
1. The problem exists today and is proven.
2. The simplest solution has demonstrably failed or is insufficient.
3. Two or more concrete cases justify the abstraction.

If any answer is no, do not add it.

---

## Principle 1: Project Structure

**Name**: Flat-First Architecture

**Rules**:

- Source code MUST live under `src/mycrew/` with the default module set:
  `main.py` (flow orchestration), `llm.py` (LLM configuration), `utils.py`
  (pure helper functions), `crews/` (CrewAI crews and tasks), and `tools/`
  (tool factory and implementations).
- A sub-package (e.g. `mycrew/crews/architect_crew/`) MUST NOT be introduced
  until a module genuinely exceeds ~300 lines **and** its responsibilities are
  clearly distinct from its siblings.
- Nesting MUST NOT exceed 3 levels deep.
- `__init__.py` files MUST contain only public re-exports — no logic.
- Tests MUST be organized as `tests/unit/`, `tests/integration/`, with a shared
  `tests/conftest.py`.
- `pyproject.toml` is the single source of truth for project metadata, dependencies,
  and tool configuration.

**Rationale**: Flat structures reduce navigation cost and make ownership of a module
obvious. Sub-packages are earned through demonstrated pain, not anticipated need.

---

## Principle 2: Dependencies

**Name**: Stdlib-First Dependency Policy

**Rules**:

- Before adding any external package, contributors MUST ask: *does the standard library
  already solve this?*
- All dependencies MUST be declared in `pyproject.toml` with pinned major versions
  (`>=X.Y,<X+1.0`).
- Dependency management MUST use `uv` (not bare pip or pip-tools).
- Prohibited substitutions (use stdlib or already-declared deps instead):

  | Task | MUST NOT add | MUST use instead |
  |---|---|---|
  | Read `.env` | `python-dotenv` standalone | `pydantic-settings` |
  | Retry HTTP | `tenacity` for this alone | `httpx` built-in transport |
  | Parse dates | `arrow`, `pendulum` | `datetime` + `zoneinfo` |
  | Simple 2-command CLI | `click` | `argparse` |
  | Validate emails | `email-validator` alone | Pydantic `EmailStr` or `re` |

**Rationale**: Every additional dependency is a maintenance burden, a potential CVE vector,
and a build-time cost. Lean dependency trees are faster and safer.

---

## Principle 3: Type Hints & Static Analysis

**Name**: Strict Static Typing

**Rules**:

- Every public function and method MUST carry full type annotations.
- The `X | Y` union syntax (Python 3.10+) MUST be used; `Union[X, Y]` is forbidden.
- `mypy --strict` MUST pass in CI with zero suppressed errors unless accompanied by an
  inline comment explaining why `Any` was unavoidable.
- When wrapping an untyped third-party library, `Any` MUST be isolated in a single adapter
  module and MUST NOT leak into application code.
- `TypeAlias` MUST be used to name any complex type used in more than one location.
- Ruff handles formatting and linting (line length 88, double quotes, sorted imports);
  its `check` and `format --check` steps MUST both pass in CI.

**Rationale**: Types are the cheapest form of documentation and catch entire classes of
bugs before runtime. `mypy --strict` eliminates implicit `Any` drift over time.

---

## Principle 4: Data Modeling

**Name**: Named, Immutable Boundary Models

**Rules**:

- Any data crossing a system boundary (HTTP request/response, database row, environment,
  file) MUST be modeled as a frozen Pydantic v2 `BaseModel`
  (`model_config = {"frozen": True}`).
- Internal structures with no validation needs MAY use `@dataclass(frozen=True)`.
- Raw `dict` MUST NOT be passed between architectural layers when the shape is known.
- Model names MUST be nouns that describe the data, not the operation
  (`User`, not `UserData` or `GetUserResponse`).

**Rationale**: Named types surface intent, enable IDE completion, and make invalid states
unrepresentable. Frozen models prevent accidental mutation across layers.

---

## Principle 5: Functions & Logic

**Name**: Single-Responsibility, Side-Effect-Free Functions

**Rules**:

- Each function MUST do exactly one thing; if "and" is needed to describe it, it MUST be
  split.
- Functions MUST be capped at approximately 30 lines and 4 positional arguments.
- Boolean flag arguments are PROHIBITED; separate functions MUST be written instead.
- Functions MUST return values rather than mutate their inputs.
- Side effects (I/O, DB writes, LLM calls, shell execution) MUST be pushed to the edges;
  core logic in `utils.py` or pure helpers MUST remain pure.
- All public symbols MUST have a one-line docstring explaining the *why*, not the what.

**Rationale**: Small, pure functions are trivially testable in isolation. Boolean flags are
hidden branches that obscure control flow and violate SRP.

---

## Principle 6: Error Handling

**Name**: Explicit, Named Exception Hierarchy

**Rules**:

- All application exceptions MUST be defined in `exceptions.py`, inheriting from a common
  `AppError(Exception)` base.
- `except Exception` (bare broad catches) are PROHIBITED unless followed immediately by
  `raise` or an inline comment explaining why swallowing is intentional.
- Silent `pass` inside an `except` block is PROHIBITED without an explanatory comment.
- `contextlib.suppress` MAY be used only when skipping the exception is a deliberate
  design decision (not a shortcut), documented with a comment.
- Logging MUST accompany any exception that is caught and not re-raised.

**Rationale**: Broad, silent exception handling is the primary cause of debugging hell.
Named exceptions make failure modes part of the API contract.

---

## Principle 7: Configuration & Secrets

**Name**: Centralized Settings, No Committed Secrets

**Rules**:

- All configuration MUST live in a single `Settings` object (Pydantic `BaseSettings`)
  loaded once at application startup.
- `os.environ.get` MUST NOT be called anywhere outside the `Settings` class.
- `.env` is PROHIBITED from version control; it MUST be listed in `.gitignore`.
- `.env.example` with all required keys (no real values) MUST always be committed and
  kept up to date.
- `Settings()` MUST fail fast at startup if any required variable is missing.
- `SECRET_KEY`, database credentials, and API tokens MUST NEVER appear in source code.

**Rationale**: Scattered `os.environ.get` calls make configuration untestable and
auditable. A single Settings object provides a clear contract and fast failure at the
right moment.

---

## Principle 8: Testing

**Name**: Fast, Focused, Arrange-Act-Assert Tests

**Rules**:

- All tests MUST follow the Arrange / Act / Assert pattern with one logical concern per
  test.
- Test function names MUST follow `test_<what>_<condition>_<expected>`.
- Target coverage: 80% on `src/` overall; 100% on critical paths (flow orchestration,
  data parsing, error handling).
- The full test suite MUST complete in under 30 seconds.
- Shared setup MUST use `conftest.py` fixtures, not class inheritance.
- Mocking MUST occur at the I/O boundary (HTTP client, DB session), never deep inside
  application logic.
- Over-mocking (patching internal implementation details) is PROHIBITED.
- Tests MUST be run with `pytest -x` (stop on first failure) in CI.

**Rationale**: Tests that mock their own internals test the mock, not the code. Boundary
mocking ensures real logic runs while isolating external dependencies.

---

## Principle 9: Logging & Observability

**Name**: Stdlib Logging, Configured Once

**Rules**:

- The stdlib `logging` module MUST be used; `print` is PROHIBITED in production code.
- Logging MUST be configured once at the application entry point using `basicConfig` or
  equivalent; it MUST NOT be re-configured in library code.
- Every module that emits logs MUST obtain its logger via `logging.getLogger(__name__)`.
- Log messages MUST use `%`-style formatting (pass args to the logger); f-strings inside
  log calls are PROHIBITED.
- `structlog` or `loguru` MUST NOT be adopted until stdlib logging demonstrably cannot
  meet an operational requirement (document decision in an ADR).

**Rationale**: Premature adoption of structured logging frameworks adds dependencies and
complexity before the pipeline that consumes them exists. `%`-formatting lets the logger
skip string building when the level is disabled.

---

## Principle 10: Async Usage

**Name**: Async Only Where Concurrency Is the Point

**Rules**:

- `async def` MUST only be used where genuine concurrent I/O (multiple simultaneous
  network or disk operations) is required.
- Adding `async` to a function purely "for future scalability" is PROHIBITED.
- Once a function is `async`, all its callers become `async`; this cost MUST be justified
  before making the commitment.
- CPU-bound or trivially fast synchronous operations MUST remain synchronous.

**Rationale**: Async is an infectious design commitment. Premature async spreads
`await`-chains through the codebase with no concurrency benefit and significant cognitive
overhead.

---

## Anti-Patterns Catalogue

The following patterns are explicitly PROHIBITED. Their presence in a PR MUST be justified
with an ADR or the PR MUST be rejected.

| ID | Pattern | Rule |
|---|---|---|
| OE-1 | Premature Base Class | Abstract base with a single child MUST NOT be written; write the concrete function first. |
| OE-2 | God Service | A single class MUST NOT own more than one distinct responsibility domain. |
| OE-3 | Config-Driven Everything | Externalizing behaviour that never changes is PROHIBITED; use `Settings` or hardcode constants. |
| OE-4 | Factory Factory | A factory whose job is to create other factories MUST NOT be introduced. |
| OE-5 | Async Everywhere | `async` on CPU-bound or trivially fast functions is PROHIBITED (see Principle 10). |
| OE-6 | Deep Inheritance | Class hierarchies deeper than one level for shared logic MUST use composition or plain functions instead. |
| OE-7 | Internal Event Bus | Pub/sub within a single module for sequential steps is PROHIBITED; call the steps directly. |
| OE-8 | Over-Mocking | Patching internals in tests is PROHIBITED; mock only I/O boundaries (see Principle 8). |
| OE-9 | Premature Optimisation | Caching, batching, or parallelising MUST NOT be introduced before a profiler measurement justifies it. |
| OE-10 | Logging Framework Stacking | Multiple logging libraries MUST NOT coexist; stdlib `logging` is the default (see Principle 9). |

**Abstraction gate**: Before writing any abstraction, all three of these MUST be true:
1. There are three or more concrete cases that genuinely need it.
2. A junior engineer could understand it in five minutes.
3. It solves a problem that exists today, not a speculated future problem.

If any answer is no, delete the abstraction.

---

## Code Smells & Bad Practices Catalogue

The following code smells and bad practices are PROHIBITED. Contributors MUST avoid them.
Violations MUST be justified with an ADR or corrected before merge.

### Structure & Design

| ID | Smell | Rule |
|---|---|---|
| CS-1 | Long methods | Methods that do too much MUST be broken into smaller focused pieces. |
| CS-2 | God classes | A class that centralizes all logic MUST NOT exist; split by responsibility. |
| CS-3 | Long parameter lists | Groups of arguments that travel together MUST become a single parameter object. |
| CS-4 | Primitive obsession | Domain concepts MUST use named types, not raw strings, integers, or booleans. |
| CS-5 | Large files / mega-modules | Thousands of unrelated lines in one file are PROHIBITED; split by responsibility. |
| CS-6 | Arrow anti-pattern | Deeply nested conditionals MUST be flattened with early returns and guard clauses. |
| CS-7 | Switch/type-check chains | Long if-else chains checking object types MUST use polymorphism or pattern matching. |
| CS-8 | Feature envy | A method that spends more time on another class's data MUST move to that class. |
| CS-9 | Message chains | Code navigating through long object sequences is PROHIBITED; break the chain. |
| CS-10 | Inheritance for reuse only | Composition MUST be preferred when inheritance does not express a type relationship. |
| CS-11 | Premature abstraction | Abstractions MUST NOT be created before two concrete implementations exist. |
| CS-12 | Anemic domain models | Models that only hold data with getters/setters and no logic are PROHIBITED. |
| CS-12a | Data clumps | The same group of variables traveling together MUST become a parameter object. |
| CS-12b | Combinatorial explosion | Enumerating every boolean combination MUST be replaced by composing independent rules. |
| CS-12c | Refused bequest | Subclasses that override most inherited methods with exceptions signal wrong hierarchy. |
| CS-12d | Temporary fields | Instance variables set only under certain conditions, null otherwise, are PROHIBITED. |
| CS-12e | Middle man classes | Classes that only delegate every call to another class MUST be removed. |
| CS-12f | Inappropriate intimacy | Reaching into another class's private fields instead of its public interface is PROHIBITED. |
| CS-12g | Open-Closed violation | Code that must be modified for every new type instead of extended is PROHIBITED. |
| CS-12h | Liskov violation | Subtypes that cannot be fully substituted for their parent are PROHIBITED. |
| CS-12i | Interface Segregation violation | Fat interfaces forcing clients to depend on unused methods are PROHIBITED. |

### State, Dependencies & Coupling

| ID | Smell | Rule |
|---|---|---|
| CS-13 | Global state / singleton abuse | Hidden dependencies inside functions are PROHIBITED; inject collaborators. |
| CS-14 | Hardcoded dependencies | Classes MUST NOT construct their own collaborators; accept them from outside. |
| CS-15 | Service locator | Classes MUST NOT fetch dependencies from a global registry; use DI. |
| CS-16 | Circular dependencies | Two modules importing each other are PROHIBITED; break the cycle. |
| CS-16a | Hidden side effects | Functions that modify external state invisibly are PROHIBITED; keep logic pure. |
| CS-16b | Mutating arguments | Modifying function arguments in place instead of returning new values is PROHIBITED. |
| CS-16c | Mutable default arguments | Shared mutable defaults (e.g. Python `def f(x=[])`) are PROHIBITED. |
| CS-16d | Pure logic entangled with I/O | Computation MUST be separated from I/O at system boundaries. |

### Error Handling & Control Flow

| ID | Smell | Rule |
|---|---|---|
| CS-17 | Swallowing exceptions | Catching and doing nothing is PROHIBITED; log or re-raise. |
| CS-18 | Returning null for failure | Raise exceptions instead of returning None to shift failure handling to every caller. |
| CS-19 | Exceptions for control flow | Non-exceptional situations MUST NOT use exceptions (e.g. key-exists checks). |
| CS-20 | Catching base Exception | Catching broadly PROHIBITED unless immediately re-raising or documented. |
| CS-21 | Failing silently with defaults | Substituting defaults on error without logging is PROHIBITED. |

### Naming & Readability

| ID | Smell | Rule |
|---|---|---|
| CS-22 | Cryptic names | Single-letter variables, unexplained abbreviations, generic terms (data, temp) are PROHIBITED. |
| CS-23 | Magic numbers/strings | Literals embedded in code MUST be named constants with clear meaning. |
| CS-24 | Boolean traps | Multiple boolean arguments are PROHIBITED; use options object or separate functions. |
| CS-25 | Redundant/lying comments | Comments that restate code or describe outdated behaviour are PROHIBITED. |

### Security

| ID | Smell | Rule |
|---|---|---|
| CS-26 | SQL injection | Query construction via string concatenation of user input is PROHIBITED. |
| CS-27 | Hardcoded credentials | Passwords, API keys, secrets in source code are PROHIBITED. |
| CS-28 | Plaintext passwords | MUST use slow hashing (e.g. bcrypt); MD5/SHA1 for passwords are PROHIBITED. |
| CS-29 | Mass assignment | Applying all user fields without whitelist is PROHIBITED. |
| CS-30 | Logging sensitive data | Passwords, tokens, PII in logs are PROHIBITED. |
| CS-30a | IDOR | Using resource IDs from the user without verifying ownership is PROHIBITED. |
| CS-30b | Disabling security checks | Turning off SSL verification or CSRF, even for tests, is PROHIBITED. |
| CS-30c | Client-side validation alone | When exposing HTTP APIs, all validation MUST run server-side; client checks can be bypassed. |
| CS-30d | Missing security headers | When exposing HTTP APIs, CSP, HSTS, X-Content-Type-Options MUST be set where applicable. |
| CS-30e | CORS misconfiguration | When exposing HTTP APIs, allowing any origin for credentialed requests is PROHIBITED. |
| CS-30f | Cookie flags | When using auth cookies (e.g. HTTP APIs), they MUST use Secure and HttpOnly. |

### Testing

| ID | Smell | Rule |
|---|---|---|
| CS-31 | No tests | Code with no tests is PROHIBITED for production paths. |
| CS-32 | Testing implementation | Inspecting private fields or internal counters instead of behaviour is PROHIBITED. |
| CS-33 | Tests with no assertions | Tests that run code without asserting outcomes are PROHIBITED. |
| CS-34 | Test interdependency | Tests relying on execution order or shared mutable state are PROHIBITED. |
| CS-35 | Over-mocking | Replacing so many real objects that the test only verifies mocks is PROHIBITED. |
| CS-36 | Wrong testing layer | Unit tests depending on real DB, or integration tests for pure logic, are PROHIBITED. |

### Database & Performance

| ID | Smell | Rule |
|---|---|---|
| CS-37 | N+1 queries | Loading a collection then querying per record is PROHIBITED; use joins or batch. |
| CS-38 | Premature optimization | Optimization before measuring bottlenecks is PROHIBITED. |
| CS-39 | Repeated expensive ops in loops | Config reads, regex compile, network calls inside loops are PROHIBITED. |
| CS-40 | Inefficient data structures | Using list for membership when set/dict gives O(1) is PROHIBITED. |
| CS-41 | Over-fetching | Loading full rows/collections when a subset is needed is PROHIBITED. |
| CS-42 | Missing transactions | Multi-step DB operations MUST run in a transaction. |
| CS-43 | No pagination | Unbounded list endpoints are PROHIBITED. |
| CS-43a | Resource leaks | Failing to close file handles, connections, or sockets is PROHIBITED. |
| CS-43b | No connection pooling | Opening a new DB connection per request instead of pooling is PROHIBITED. |
| CS-43c | Holding locks too long | Locks or transactions held longer than necessary are PROHIBITED. |
| CS-43d | Unbounded data structures | Structures that grow without limits or bounds are PROHIBITED. |
| CS-43e | Float for money | Floating point for monetary values is PROHIBITED; use decimal/fixed-point. |
| CS-43f | Query logic scattered | Data access MUST be isolated in repository objects, not services/controllers. |

### Concurrency

| ID | Smell | Rule |
|---|---|---|
| CS-44 | Race conditions | Unsynchronized shared state between threads is PROHIBITED. |
| CS-45 | Fire-and-forget async | Launching tasks with no error handler so failures are silently discarded is PROHIBITED. |
| CS-45a | No timeouts | Outbound network calls without timeouts are PROHIBITED. |
| CS-45b | No retry/backoff | Transient failures MUST use retry with exponential backoff; not permanent failure. |
| CS-45c | Observer without unsubscribe | Listeners without a way to unsubscribe cause leaks; PROHIBITED. |

### API & Operations

| ID | Smell | Rule |
|---|---|---|
| CS-46 | 200 for errors | Errors MUST NOT return 200 OK; use appropriate status codes. |
| CS-47 | Exposing sequential IDs | Internal integer IDs in public API that allow enumeration are discouraged. |
| CS-48 | No rate limiting on auth | Login and similar endpoints MUST be rate limited. |
| CS-49 | No health checks | Services MUST expose health check endpoints for load balancers. |
| CS-50 | Logging without context | Error entries with only generic messages, no user/record/operation, are PROHIBITED. |
| CS-50a | Hardcoded configuration | Environment-specific values (servers, feature flags) in source are PROHIBITED. |
| CS-50b | Unpinned dependencies | Non-reproducible builds from floating versions are PROHIBITED. |
| CS-50c | No staging/tests before deploy | Deploying without staging, automated tests, or review is PROHIBITED. |
| CS-50d | No rollback strategy | Every deployment MUST have a rehearsed rollback procedure. |
| CS-50e | Session state in process | State that breaks horizontal scaling (per-instance) is PROHIBITED. |

### Dead Code & Duplication

| ID | Smell | Rule |
|---|---|---|
| CS-51 | Dead code | Commented blocks, unreachable branches, uncalled functions MUST be removed. |
| CS-52 | Duplicate code | Copy-paste logic MUST be extracted; fix in one place. |

---

## Governance

### Amendment Procedure

1. Open a PR against `main` with the proposed change to this file.
2. The PR description MUST include: rationale, affected principles, and version bump
   classification (MAJOR / MINOR / PATCH).
3. At least one other maintainer MUST approve before merge.
4. Non-obvious decisions MUST produce an ADR in `docs/decisions/`.

### Versioning Policy

- **MAJOR**: Backward-incompatible governance changes — principle removals, redefinitions
  that invalidate prior work.
- **MINOR**: New principle or section added; materially expanded guidance.
- **PATCH**: Clarifications, wording improvements, typo fixes with no semantic change.

### CI Compliance Gates

Every PR MUST pass all four gates before merge:

1. `ruff check` — linting
2. `ruff format --check` — formatting
3. `mypy --strict` — static analysis
4. `pytest -x` — full test suite

Direct pushes to `main` are PROHIBITED. PRs MUST be squash-merged.

### Compliance Review

Constitution alignment MUST be validated during every planning phase via the "Constitution
Check" section of the implementation plan. Violations discovered post-merge MUST be
tracked as issues and resolved in the next sprint.

### ADR Policy

Architectural Decision Records live in `docs/decisions/`. An ADR is REQUIRED whenever:
- A principle is violated with justification.
- A new external dependency is added.
- An anti-pattern from the catalogue is intentionally used.

---

## Crew System Architecture

### Abstract Crew Base (ABCrew)

The codebase uses an abstract base class `ABCrew` (in `src/mycrew/crews/abc_crew.py`) to define the contract for all crews. This enforces SOLID principles:

- **SRP**: Each crew has a single responsibility (e.g., exploration, implementation, review)
- **OCP**: Crews can be extended without modifying the base
- **LSP**: Subclasses can be substituted for the base
- **ISP**: Mixins provide focused interfaces (stage-specific LLMs, config loading)
- **DIP**: Depend on abstractions, not concrete implementations

### Key Components

1. **ABCrew**: Abstract base with required properties:
   - `required_agents: List[str]` - Agent keys the crew needs
   - `required_tasks: List[str]` - Task keys the crew needs
   - `_build_agent(agent_key: str) -> Agent` - Build agent from config
   - `_build_task(task_key: str) -> Task` - Build task from config
   - `crew() -> Crew` - Returns assembled Crew instance

2. **StageSpecificCrew**: Mixin for stage-specific LLMs
   - `stage_llm: LLM` - Gets LLM for crew's stage via `get_llm_for_stage()`

3. **ConfigurableCrew**: Mixin for YAML config loading
   - `_load_config(config_key: str) -> dict` - Loads config from YAML files

4. **PipelineCrewBase**: Concrete base implementing ABCrew
   - Provides shared tools (repo_shell, github_search, etc.)
   - Implements `_build_agent` with provider_type integration
   - Implements `_build_task` with YAML config loading

### Provider System Integration

The LLM provider system is integrated via global `provider_type` setting:

1. **Settings**: `provider_type: str | None` in `Settings` class
2. **Propagation**: `_build_agent` passes `provider_type` to `get_llm_for_stage()`
3. **Default**: `None` auto-detects provider based on available API keys

### Crew Subclass Pattern

Concrete crews follow this pattern:

```python
@CrewBase
class ExplorerCrew(PipelineCrewBase):
    stage: ClassVar[str] = "explore"
    
    @property
    def required_agents(self) -> List[str]:
        return ["repo_explorer", "dependency_analyzer", ...]
    
    @property
    def required_tasks(self) -> List[str]:
        return ["explore_task", "dependency_analyze_task", ...]
    
    @agent
    def repo_explorer(self) -> Agent:
        return self._build_agent("repo_explorer")
    
    @task
    def explore_task(self) -> Task:
        return self._build_task("explore_task")
```

### Benefits

1. **Reduced Boilerplate**: ~80% reduction in repetitive code
2. **Type Safety**: Full type hints and mypy strict compliance
3. **Testability**: Easy mocking of abstract methods
4. **Extensibility**: New crews follow consistent pattern
5. **Documentation**: Required properties serve as documentation
6. **Backward Compatible**: Existing YAML configs and decorators unchanged

### Creating a New Crew

1. Create file in `src/mycrew/crews/<crew_name>/<crew_name>.py`
2. Import `PipelineCrewBase` and decorators
3. Define `stage` class variable
4. Implement `required_agents` and `required_tasks` properties
5. Add `@agent` and `@task` methods calling `_build_agent`/`_build_task`
6. Add YAML configs to `config/agents.yaml` and `config/tasks.yaml`
