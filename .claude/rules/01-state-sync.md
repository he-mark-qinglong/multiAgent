# 状态同步规范

**版本: 1.0 | 2026-03-27**

## 1. DeltaUpdate 格式

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

## 2. 订阅规则

| Agent | 订阅内容 |
|-------|----------|
| Intent Agent | IntentChain 变更 |
| Planner Agent | IntentChain 变更 |
| Executor Agent | 分配给自己的 Goal 变更 |
| Monitor Agent | 所有 Status 变更 |
| Synthesizer Agent | GoalTree 完成事件 |

## 3. 上下文作用域

```
Intent Agent:    [Query] + [Intent链(最多5条)] + [历史摘要]
Planner Agent:   [IntentChain] + [Goal状态] + [Executor列表]
Executor Agent:  [SubGoal] + [过程日志(最近3步)]
Monitor Agent:   [所有Goal状态摘要] + [异常事件]
Synthesizer:     [完整GoalTree] + [所有SubGoalResults]
```

## 4. 分层存储

```
Hot Storage:   最近20轮完整数据 (< 10ms)
Cold Storage: 历史摘要 (文件系统)
压缩触发:      Hot > 阈值时异步压缩
```

## 5. 长对话 Token 控制

| 对话阶段 | 策略 |
|----------|------|
| 0-20轮 | 全量同步 |
| 20-50轮 | 压缩Intent链，保留最近5条 |
| 50轮+ | 增量同步 + LLM异步压缩 |
