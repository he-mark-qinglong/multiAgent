# Technology Stack

**Last Updated**: 2026-03-29
**Maintained By**: Tech Scout Agent

## Current Stack

### Core
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| LangGraph | latest | Agent orchestration |
| LangChain | latest | LLM framework |
| Pydantic | latest | Data validation |

### Project-Specific
| Technology | Version | Purpose |
|------------|---------|---------|
| StateGraph | - | State management |
| EventBus | - | Inter-agent messaging |
| DeltaUpdate | - | State sync |

## Evaluations

| Technology | Status | Decision | Notes |
|------------|--------|----------|-------|
| LangGraph | **Adopted** | Core framework | Required by project |
| LangChain | **Adopted** | LLM integration | Community standard |
| LangSmith | **Adopted** | Observability | Tracing integration |
| PostgresSaver | **Pending** | Production checkpointing | For production use |

## Monitoring

| Technology | Status | Purpose |
|------------|--------|---------|
| LangSmith | Active | Tracing, metrics |
| Structured Logging | Active | Agent logs |

## Road Map

| Technology | Priority | ETA |
|------------|----------|-----|
| PostgreSQL Checkpointing | Medium | TBD |
| Redis Pub/Sub | Low | TBD |
| Vector DB Integration | Low | TBD |
