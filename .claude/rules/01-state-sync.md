# 状态同步与 HITL 规范

**版本: 2.0 | 2026-03-27**

---

## 1. 状态层职责划分

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: LangGraph (编排 + 持久化)                  │
│  - StateGraph: Working Context                      │
│  - Checkpointer: Session 持久化 (thread_id 隔离)   │
│  - ReAct 循环: 内部推理，完整执行                    │
└─────────────────────────────────────────────────────┘
                         ↕ DeltaUpdate
┌─────────────────────────────────────────────────────┐
│  Layer 2: DeltaUpdate + EventBus (外部通知)          │
│  - 发布 Agent 间状态变化给外部订阅者                  │
│  - Monitor 跨 Agent 状态监控                         │
│  - 外部系统集成 (WebSocket UI, Monitoring)           │
└─────────────────────────────────────────────────────┘
```

| 组件 | 职责 | 触发时机 |
|------|------|----------|
| **Checkpointer** | LangGraph 内部状态持久化，resume 恢复 | 每个 super-step 自动 |
| **DeltaUpdate** | Agent 间外部通知，EventBus 发布 | 显式调用 `_emit_delta()` |

---

## 2. LangGraph Checkpointer

```
✅ InMemorySaver: 开发环境
✅ PostgresSaver: 生产环境

每个对话使用 thread_id 隔离状态
```

---

## 3. DeltaUpdate 格式

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

---

## 4. LangGraph HITL 机制

### 4.1 中断触发条件
```
✅ 执行危险操作前 (如删除、修改)
✅ 需要人工确认的决策点
✅ 外部系统回调
❌ 常规推理过程
```

### 4.2 中断流程
```
executor_node 检测 needs_approval=True
    ↓
interrupt("请确认操作...")
    ↓
状态保存到 Checkpointer
    ↓
返回待审批信息给客户端
    ↓
submit_approval() → Command(resume={...})
    ↓
executor_node 恢复执行
```

### 4.3 HumanApprovalManager
```python
class HumanApprovalManager:
    def request_approval(self, thread_id, action, details) -> str
    def submit_approval(self, thread_id, approved, reason) -> dict
    def get_pending(self, thread_id) -> dict | None
```

### 4.4 stream() 输出规范
```
✅ 正确: ReAct 完整执行 → 输出结构化结果
def stream(self, query):
    result = self._run_full_react_cycle(query)
    yield {"type": "result", "data": result}

❌ 错误: 输出中间步骤
def stream(self, query):
    for step in self.react_steps:
        yield step  # 破坏 ReAct 一致性
```

流式类型: `result`, `progress`, `approval_required`, `error`, `interrupt`

---

## 5. 订阅规则

| Agent | 订阅内容 |
|-------|----------|
| Intent Agent | IntentChain 变更 |
| Planner Agent | IntentChain 变更 |
| Executor Agent | 分配给自己的 Goal 变更 |
| Monitor Agent | 所有 Status 变更 |
| Synthesizer Agent | GoalTree 完成事件 |

---

## 6. 上下文作用域

```
Intent Agent:    [Query] + [Intent链(最多5条)] + [历史摘要]
Planner Agent:   [IntentChain] + [Goal状态] + [Executor列表]
Executor Agent:  [SubGoal] + [过程日志(最近3步)]
Monitor Agent:   [所有Goal状态摘要] + [异常事件]
Synthesizer:     [完整GoalTree] + [所有SubGoalResults]
```

---

## 7. 长对话 Token 控制

| 对话阶段 | 策略 |
|----------|------|
| 0-20轮 | 全量同步 |
| 20-50轮 | Checkpointer 压缩，保留最近 checkpoint |
| 50轮+ | LangGraph get_state_history() 回溯 + 增量压缩 |

压缩触发: Token 达到 context window 80%

---

## 8. Agent 协作模式

### 8.1 两种主要模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| **Agents as Tools** | 根 Agent 把子 Agent 当函数调用 | 简单任务分解 |
| **Agent Transfer** | 移交控制权，子 Agent 继承有限上下文 | 复杂多轮协作 |

### 8.2 上下文移交 (Scoped Handoffs)
```
include_contents: [intent_chain, current_goal]  # 仅必要的
exclude: [internal_reasoning, raw_history]     # 排除敏感的
```
