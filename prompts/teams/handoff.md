# Agent Handoff Protocol

## When to Handoff

| Scenario | Handoff Type |
|----------|-------------|
| Intent → Planner | Direct (automatic) |
| Planner → Executor | Direct (assigned) |
| Executor → Synthesizer | Event-driven |
| Any → Monitor | Event-driven (always) |

## Handoff Message Format

```json
{
  "handoff_type": "intent | goal | result | alert",
  "from_agent": "agent_id",
  "to_agent": "agent_id",
  "payload": {...},
  "handoff_reason": "string"
}
```

## Context Handoff

### Minimal Context (Executor receives)

```json
{
  "goal_id": "string",
  "goal_type": "climate | nav | ...",
  "parameters": {...},
  "deadline": "ISO datetime",
  "parent_plan_id": "string"
}
```

### Full Context (Synthesizer receives)

```json
{
  "plan_id": "string",
  "goal_tree": {...},
  "all_results": {...},
  "conversation_summary": "string"
}
```

## Handoff Constraints

- Never handoff mid-execution goal
- Always emit completion event before handoff
- Include retry count in handoff metadata
