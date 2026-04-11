# Project Working Rules

## Purpose

This file defines repository-specific working rules for this project.
Use it together with the global `~/.claude/CLAUDE.md`.

## Project Overview

- **Project name**: multiAgent
- **Primary purpose**: Multi-agent orchestration system with LangGraph, supporting car-assistant chat UI
- **Primary stack**: Python/FastAPI (backend) + Vue3/TypeScript (frontend) + LangGraph (orchestration)
- **Key runtime targets**: Browser (frontend), Server (backend API)
- **Critical quality priorities**: Correctness, architecture compliance, stability

## What Success Looks Like in This Repo

When working in this repository, prefer changes that are:

- correct
- minimal
- easy to review
- compatible with existing architecture
- backed by observable verification when possible

Before implementing, identify:

- the primary goal
- what counts as done
- what must not change

If success criteria are unclear, ask before making broad changes.

## Repository Structure

```text
multiAgent/
├── agents/              # Agent implementations (BaseReActAgent, intent/planner/executor/synthesizer/monitor agents)
├── backend/            # FastAPI backend (main.py, tools.py)
├── core/               # Core framework (models, state_store, event_bus, langgraph_integration)
├── pipelines/          # Execution pipelines (LangGraph-based collaboration pipeline)
├── prompts/            # Agent prompts (system/, context/, tools/, teams/)
│   └── system/        # Agent role definitions (.md files per agent)
├── tests/             # Tests
│   ├── contracts/    # API contract tests
│   ├── e2e/          # End-to-end tests
│   ├── mock_tools/   # Mock tools for testing
│   └── perf/         # Performance tests
├── car-assistant/     # Coordination docs (milestones, coordination)
├── car-assistant-ui/  # Vue3 frontend
│   ├── src/
│   │   ├── components/  # Vue components (chat/, common/)
│   │   ├── viewmodels/ # Vue composables (useChat.ts)
│   │   ├── services/   # API client (chat.ts)
│   │   ├── models/     # TypeScript types (message.ts)
│   │   └── utils/     # Utilities (time.ts, id.ts)
│   ├── e2e/           # Playwright E2E tests
│   └── deploy/         # Docker/nginx deployment configs
└── docs/              # Design docs and ADR records
```

## Source-of-Truth Rules

When there is ambiguity, use these sources in order:

1. explicit user request
2. this CLAUDE.md
3. `.claude/rules/` directory (project-specific rules)
4. existing code patterns already used in this repo
5. tests and type definitions
6. documentation inside the repo
7. global personal defaults

## Change Scope Rules

**Prefer minimal safe changes** — Make the smallest change that satisfies the request. Do not refactor unrelated code unless necessary for correctness or maintainability.

**Do not silently expand scope** — If broader changes are required, explain why, what additional files/modules need to change, and the main risks.

**Preserve existing interfaces** — Avoid breaking public APIs, service contracts, route shapes, event names, and storage formats.

## Frozen or Sensitive Areas

Do not change these without explicit justification:

- `prompts/system/*.md` — Agent prompts define agent behavior; changes affect all agents
- `core/` — Core framework (models, state_store, event_bus, langgraph_integration)
- `agents/base*.py` — Base agent classes
- `pipelines/` — LangGraph pipeline orchestration

## Coding Expectations

- Match local conventions — Follow naming, file organization, and architectural patterns already present
- Prefer consistency with nearby code over generic style preferences
- Prefer async/await over callback-heavy code
- Do not add new dependencies unless necessary

## Error Handling Rules

- Do not swallow errors silently
- Preserve existing error-handling conventions
- For user-facing flows: show actionable failure states, avoid exposing sensitive internals
- For infrastructure failures: log enough context for debugging

## Security and Privacy Rules

- Never weaken authentication, authorization, or data-protection behavior without explicit approval
- Do not log secrets, tokens, passwords, or sensitive personal data
- If a change affects security-sensitive logic, call it out explicitly

## Testing and Verification

**Preferred verification order** (strongest first):

1. targeted unit test
2. integration test
3. existing test suite for affected area
4. API contract tests (`tests/contracts/`)
5. E2E tests (`car-assistant-ui/e2e/`)

**Verification expectations**:

- specify what changed and what was tested
- specify what scenarios were covered
- specify what was not verified
- If you did not run tests, say so

## Task Execution Guidance

**Ask first when needed** — Before implementing, ask if any of the following are unclear:

- target behavior
- expected output format
- acceptance criteria
- affected module/file
- compatibility constraints

**Use structured-analysis skill** when the task is:

- ambiguous or high-risk
- cross-module or architecture-affecting
- dependent on unclear assumptions

**Prefer local repair over broad redesign** — For bug fixes, first identify the failing path, fix the smallest correct layer.

## Output Expectations for Code Tasks

When delivering implementation work:

1. What changed
2. Why
3. Files touched
4. Verification performed
5. Known limitations / follow-ups

## Review Checklist

Before considering a task done:

- [ ] Separated facts from assumptions?
- [ ] Avoided changing unrelated code?
- [ ] Preserved stable interfaces unless explicitly changing them?
- [ ] Followed existing repo conventions?
- [ ] Verified the change as far as realistically possible?
- [ ] Clearly stated what remains uncertain or unverified?

## Project-Specific Commands

### Backend (FastAPI)

```bash
# Dev server
cd /Users/a1234/projects/multiAgent && uvicorn backend.main:app --reload --port 8000

# Run API contract tests
cd /Users/a1234/projects/multiAgent && python -m pytest tests/contracts/ -v

# Run all tests
cd /Users/a1234/projects/multiAgent && python -m pytest tests/ -v
```

### Frontend (Vue3)

```bash
# Dev server
cd /Users/a1234/projects/car-assistant-ui && npm run dev

# Run E2E tests (Chromium)
cd /Users/a1234/projects/car-assistant-ui && npx playwright test e2e/chat.spec.ts --project=chromium

# Build
cd /Users/a1234/projects/car-assistant-ui && npm run build
```

### Docker (MVP)

```bash
cd /Users/a1234/projects/multiAgent && docker-compose -f docker-compose.mvp.yml up
```

## Notes for Future Maintenance

Keep this file specific and short. Remove stale sections quickly — a short accurate file is better than a long outdated one.
