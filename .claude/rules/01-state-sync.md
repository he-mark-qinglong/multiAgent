# 状态同步规范

**版本: 2.0 | 2026-03-27**

> **重要更新**: LangGraph Checkpointer 现为默认持久化机制，DeltaUpdate 作为外部通知补充。

## 1. LangGraph Checkpointer (主编排)

### 1.1 配置
```
✅ InMemorySaver: 开发环境
✅ PostgresSaver: 生产环境

每个对话使用 thread_id 隔离状态
```

### 1.2 持久化流程
```
Agent 状态更新 → StateGraph 更新 → Checkpointer 自动保存
```

---

## 2. DeltaUpdate (外部通知)

> DeltaUpdate 保留用于 Agent 间外部通知和 Monitor 监控。

### 2.1 DeltaUpdate 格式

```python
@dataclass
class DeltaUpdate:
    event_id: str              # 唯一ID
    timestamp: int            # Unix timestamp
    entity_type: str           # 'Intent' | 'Goal' | 'Plan' | 'Status'
    entity_id: str             # 实体ID
    operation: str             # 'create' | 'update' | 'delete'
    changed_keys: list[str]    # 变化的字段
    delta: dict               # 变化的值
    source_agent: str          # 发起更新的Agent
```

### 2.2 发布时机
```
✅ Agent 状态变化后发布到 EventBus
✅ Monitor 订阅所有 DeltaUpdate
❌ 内部 ReAct 循环不触发 (由 LangGraph 管理)
```

### 2.3 订阅规则

| Agent | 订阅内容 |
|-------|----------|
| Monitor Agent | 所有 DeltaUpdate (全量监控) |
| 外部系统 | 可订阅特定 entity_type |

---

## 3. 上下文作用域

```
Intent Agent:    [Query] + [Intent链(最多5条)] + [历史摘要]
Planner Agent:   [IntentChain] + [Goal状态] + [Executor列表]
Executor Agent:  [SubGoal] + [过程日志(最近3步)]
Monitor Agent:   [所有Goal状态摘要] + [异常事件]
Synthesizer:     [完整GoalTree] + [所有SubGoalResults]
```

---

## 4. 长对话 Token 控制

| 对话阶段 | 策略 |
|----------|------|
| 0-20轮 | 全量同步 |
| 20-50轮 | Checkpointer 压缩，保留最近 checkpoint |
| 50轮+ | LangGraph get_state_history() 回溯 + 增量压缩 |

---

## 5. 架构整合

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│  Checkpointer 持久化 + ReAct 循环 + Edges                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ DeltaUpdate
┌─────────────────────────────────────────────────────────────┐
│                      EventBus                                │
│  外部通知 + Monitor 订阅 + 跨 Agent 通信                      │
└─────────────────────────────────────────────────────────────┘
```
