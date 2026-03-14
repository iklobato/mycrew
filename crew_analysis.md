# Code Pipeline Crew Analysis

## Overview
The mycrew consists of 7 sequential crews that process a software development task from analysis to implementation and deployment.

## 1. Issue Analyst Crew
**Stage**: `analyze_issue`
**Primary Model**: `openrouter/google/gemini-3-flash-preview`
**Purpose**: Parse raw task/issue into structured requirements

### Agents:
1. **similar_issues_synthesizer**
   - **Tools**: `RepoShellTool` (for `gh` CLI commands)
   - **Inputs**: `{repo_context}`, `{task}`, `{github_repo}`
   - **Outputs**: `## Similar Issues` section or "Skipped (no github_repo)"
   - **Responsibilities**:
     - Fetch similar GitHub issues/PRs when `github_repo` is set
     - Execute `gh` CLI commands with `-R "{github_repo}"`
     - Produce "company moment" (recent merges + open work)
     - Output: Issues consulted, Out-of-scope in similar, Company moment

2. **issue_analyst**
   - **Tools**: `ScrapeWebsiteTool`, `GithubSearchTool`, `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: `{repo_context}`, `{task}`, `{branch}`, context from `similar_issues_task`
   - **Outputs**: Structured document with sections:
     - `## Context` (when github_repo/docs available)
     - `## Summary`
     - `## Acceptance Criteria` (numbered)
     - `## Scope` (In-scope / Out-of-scope)
     - `## Technical Hints`
   - **Responsibilities**:
     - Parse task into structured requirements
     - Use tools to gather context
     - Derive scope from task + similar issues
     - Keep acceptance criteria minimal

3. **scope_validator**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Output from `analyze_task`, `{task}`
   - **Outputs**: Original document + appended `## Scope Validation` section
   - **Responsibilities**:
     - Cross-check for scope creep, vague criteria, conflicts
     - Flag: `BROAD_CRITERIA`, `VAGUE`, `CONFLICT`, `SPLIT_RECOMMENDED`, or `NONE`
     - Append validation section without rewriting

4. **acceptance_criteria_normalizer**
   - **Tools**: None (no tools required)
   - **Inputs**: Output from `validate_scope_task`
   - **Outputs**: Full document + `## Acceptance Criteria (Normalized)`
   - **Responsibilities**:
     - Normalize criteria into numbered, unambiguous, testable checklist
     - Keep all prior sections

## 2. Explorer Crew
**Stage**: `explore`
**Primary Model**: `openrouter/deepseek/deepseek-r1`
**Purpose**: Scan codebase structure, conventions, and dependencies

### Agents:
1. **repo_explorer**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: `{repo_context}`, `{task}`, `{docs_url}`
   - **Outputs**: Exploration report
   - **Responsibilities**: Scan tech stack, layout, key files, conventions

2. **dependency_analyzer**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Context from previous agents
   - **Outputs**: Dependency graphs, blast radius analysis
   - **Responsibilities**: Map import/dependency relationships

3. **test_layout_scout**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: `{test_command}`, context from previous agents
   - **Outputs**: Test layout documentation
   - **Responsibilities**: Document test structure when `test_command` is set

4. **convention_extractor**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Context from previous agents
   - **Outputs**: Lint/format configuration extraction
   - **Responsibilities**: Extract black, eslint, pyproject.toml configs

5. **api_boundary_scout**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Context from previous agents, `{task}`
   - **Outputs**: API surface mapping
   - **Responsibilities**: Map API surface when task mentions API/endpoint

## 3. Clarify Crew
**Stage**: `auxiliary` (for ambiguity_detector, question_prioritizer), `analyze_issue` (for clarifier)
**Purpose**: Detect and resolve ambiguities with human interaction

### Agents:
1. **ambiguity_detector**
   - **Tools**: `RepoShellTool`
   - **Inputs**: `{repo_context}`, `{task}`, analysis from previous crews
   - **Outputs**: List of open questions
   - **Responsibilities**: Identify ambiguities (ownership, scope, migrations)

2. **question_prioritizer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Output from `ambiguity_detector`
   - **Outputs**: Prioritized questions list
   - **Responsibilities**: Rank questions by impact

3. **clarifier**
   - **Tools**: `ask_human` (special tool for human interaction)
   - **Inputs**: Prioritized questions, context
   - **Outputs**: Clarified requirements with 2-4 code-snippet options
   - **Responsibilities**: Resolve ambiguities via human interaction

## 4. Architect Crew
**Stage**: `plan`
**Primary Model**: `openrouter/google/gemini-3-flash-preview`
**Purpose**: Create file-level implementation plan without writing code

### Agents:
1. **architect**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional), `GithubSearchTool` (optional)
   - **Inputs**: `{repo_context}`, `{task}`, normalized acceptance criteria, exploration results
   - **Outputs**: File-level plan with `## Files to Create/Modify`
   - **Responsibilities**: Create implementation plan (no code)

2. **dependency_orderer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Architect's plan
   - **Outputs**: Ordered plan with `## Risk` flags
   - **Responsibilities**: Order files by dependency, flag risks

3. **refactor_guard**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Ordered plan
   - **Outputs**: Plan with `REFACTOR_FLAGS` or `NONE`
   - **Responsibilities**: Flag unnecessary refactors

4. **test_plan_advisor**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Plan, `{test_command}`
   - **Outputs**: Plan + `## Test Plan` (when test_command set)
   - **Responsibilities**: Add test strategy

5. **migration_checker**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Plan
   - **Outputs**: Plan with migration flags
   - **Responsibilities**: Flag migration steps when plan touches DB/config

6. **rollback_planner**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Plan
   - **Outputs**: Plan + `## Rollback` for high-risk areas
   - **Responsibilities**: Add rollback strategy

## 5. Implementer Crew
**Stage**: `implement`
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`
**Purpose**: Write code, tests, and perform self-review

### Agents:
1. **implementer**
   - **Tools**: `RepoShellTool`, `RepoFileWriterTool`, `CodeInterpreterTool` (optional)
   - **Inputs**: Final plan, `{repo_context}`
   - **Outputs**: Code implementation for all files in plan
   - **Responsibilities**: Write actual code using file writer

2. **docstring_writer**
   - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
   - **Inputs**: Implementation, conventions from exploration
   - **Outputs**: Code with docstrings (Google/NumPy, JSDoc)
   - **Responsibilities**: Add documentation to changed code

3. **type_hint_checker**
   - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
   - **Inputs**: Code with docstrings
   - **Outputs**: Code with type hints
   - **Responsibilities**: Add type hints to Python code

4. **test_writer**
   - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
   - **Inputs**: Code, `{test_command}`, test layout from exploration
   - **Outputs**: Tests added/updated
   - **Responsibilities**: Write tests, run test_command

5. **lint_fixer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Code, conventions from exploration
   - **Outputs**: Linted code
   - **Responsibilities**: Run black, ruff, eslint --fix

6. **self_reviewer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Final implementation, original plan
   - **Outputs**: `SELF_REVIEW: PASS/ISSUES`
   - **Responsibilities**: Verify plan adherence

## 6. Reviewer Crew
**Stage**: `review`
**Primary Model**: `openrouter/deepseek/deepseek-v3.2`
**Purpose**: Review implementation against plan and requirements

### Agents:
1. **reviewer**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Implementation, plan, acceptance criteria
   - **Outputs**: `ReviewVerdict` (APPROVED or ISSUES with list)
   - **Responsibilities**: Main review, reject overengineering

2. **security_reviewer**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Implementation
   - **Outputs**: Security findings
   - **Responsibilities**: Check SQL injection, XSS, auth bypass, secrets

3. **performance_reviewer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Implementation
   - **Outputs**: Performance findings
   - **Responsibilities**: Flag N+1 queries, unindexed queries, large loops

4. **accessibility_checker**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Implementation (when UI files changed)
   - **Outputs**: Accessibility findings
   - **Responsibilities**: Check a11y compliance

5. **backward_compat_checker**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Implementation
   - **Outputs**: Compatibility findings
   - **Responsibilities**: Flag breaking API changes

6. **convention_checker**
   - **Tools**: `RepoShellTool`, `CodeDocsSearchTool` (optional)
   - **Inputs**: Implementation, conventions from exploration
   - **Outputs**: Convention compliance findings
   - **Responsibilities**: Verify conventions, merge final verdict

## 7. Commit Crew
**Stage**: `commit`, `publish`, `auxiliary`
**Purpose**: Commit changes, create PR, and publish

### Agents:
1. **git_agent**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Implementation, `{branch}`, `{dry_run}`
   - **Outputs**: Feature branch created, changes committed
   - **Responsibilities**: Create branch, stage changes, commit with Conventional Commits

2. **commit_message_reviewer**
   - **Tools**: `RepoShellTool`
   - **Inputs**: Commit message
   - **Outputs**: Validated or amended commit message
   - **Responsibilities**: Validate Conventional Commits format

3. **changelog_agent**
   - **Tools**: `RepoShellTool`, `RepoFileWriterTool`
   - **Inputs**: Commit, task, `{dry_run}`
   - **Outputs**: Updated CHANGELOG (if file exists)
   - **Responsibilities**: Append CHANGELOG entry

4. **pr_labels_suggester**
   - **Tools**: None
   - **Inputs**: Task, plan
   - **Outputs**: Suggested PR labels
   - **Responsibilities**: Analyze task to suggest 1-5 relevant labels

5. **publish_agent**
   - **Tools**: `CreatePRTool`
   - **Inputs**: Feature branch, base branch, task, implementation, plan, review_verdict, github_repo, labels
   - **Outputs**: PR URL
   - **Responsibilities**: Push branch, create PR via gh CLI, apply labels

## Tool Summary

### Available Tools:
1. **RepoShellTool** - Run shell commands in repo with safety checks
2. **RepoFileWriterTool** - Write/modify files in repo
3. **CreatePRTool** - Create GitHub PRs via gh CLI
4. **ScrapeWebsiteTool** - Fetch web content (for issue URLs)
5. **GithubSearchTool** - Semantic search over GitHub repo (requires GITHUB_TOKEN)
6. **CodeDocsSearchTool** - Semantic search over documentation (requires docs_url)
7. **CodeInterpreterTool** - Execute code in Docker (optional, for implement stage)
8. **ask_human** - Special tool for human clarification

### Tool Availability by Stage:
- `analyze_issue`: ScrapeWebsiteTool, RepoShellTool, GithubSearchTool, CodeDocsSearchTool
- `explore`: RepoShellTool, CodeDocsSearchTool
- `plan`: RepoShellTool, CodeDocsSearchTool, GithubSearchTool
- `implement`: RepoShellTool, RepoFileWriterTool, CodeInterpreterTool
- `review`: RepoShellTool, CodeDocsSearchTool
- `commit`: RepoShellTool
- `commit_review`: RepoShellTool
- `publish`: CreatePRTool
- `auxiliary/scope_validate/refactor_guard/self_review`: RepoShellTool
- `test_write`: RepoShellTool, RepoFileWriterTool
- `changelog`: RepoShellTool, RepoFileWriterTool
- `security_review`: RepoShellTool, CodeDocsSearchTool