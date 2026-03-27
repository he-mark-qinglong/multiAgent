# Team Coordination Protocol

## Team Structure

```
Orchestrator (Pipeline)
  ├── Intent Agent (L0)
  ├── Planner Agent (L1)
  │     └── Executor Agents (L2+)
  │           ├── Climate Executor
  │           ├── Navigation Executor
  │           ├── Music Executor
  │           └── ...
  ├── Synthesizer Agent (L1)
  └── Monitor Agent (XL)
```

## Coordination Rules

### 1. Message Passing

```
✅ Use EventBus for all inter-agent communication
✅ Each message includes: source_agent, target_agent, entity_type, delta
❌ No direct function calls between agents (except parent→child)
```

### 2. Error Propagation

```
Executor fails
    ↓
Monitor detects via EventBus
    ↓
Monitor notifies Planner
    ↓
Planner decides: retry | skip | fallback | abort
    ↓
Planner updates GoalTree
    ↓
Resume execution
```

### 3. Resource Management

```
Max concurrent Executors: 4
Max goals per plan: 10
Executor timeout: 30 seconds
Plan timeout: 5 minutes
```

## State Transitions

```
PENDING → RUNNING → COMPLETED | FAILED | SKIPPED | TIMEOUT
```

## Circuit Breaker

- 3 consecutive failures → pause new goals
- 60 second cooldown
- Resume with exponential backoff
