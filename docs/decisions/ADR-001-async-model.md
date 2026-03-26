# ADR-001: 异步模型选择

## Status
Accepted

## Date
2026-03-27

## Decision

- **核心层 (StateStore, EventBus)**: 同步 + threading.RLock
- **Agent 执行层**: async/await
- **Redis**: Phase 3 实现，Phase 1 使用 InMemoryStorage

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                 Hybrid Sync/Async Model                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SYNC LAYER (thread-safe)         ASYNC LAYER               │
│  ┌─────────────────────────┐     ┌───────────────────┐     │
│  │ • StateStore (RLock)    │     │ • BaseAgent       │     │
│  │ • HotStorage (RLock)    │     │ • Agent.process()│     │
│  │ • EventBus (RLock)      │     │ • Pipeline Runner │     │
│  │ • All DeltaUpdates      │     │ • Executor agents │     │
│  └─────────────────────────┘     └───────────────────┘     │
│                                                              │
│  Bridge: Async agents call sync StateStore/EventBus         │
│          via asyncio.create_task                            │
└─────────────────────────────────────────────────────────────┘
```

## 理由

- **简单性**: 核心状态操作需要强一致性，同步更易保证正确性
- **性能**: Agent 并行执行用 async 可以提高吞吐量
- **延迟**: 同步 EventBus 确保 < 50ms 状态同步

## 后果

**正面**:
- 核心操作简单，< 50ms EventBus 延迟
- async 并发提高 Agent 吞吐量
- 清晰的关注点分离

**负面**:
- Sync/async 桥接复杂性
- 需要双重测试覆盖 (同步 + 异步)
