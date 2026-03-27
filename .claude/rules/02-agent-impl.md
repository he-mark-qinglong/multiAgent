# Agent 实现规范

**版本: 1.1 | 2026-03-27**

> Prompts 定义: `prompts/system/{agent_name}.md`

## 1. Agent 基类接口

```python
class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        state_store: StateStore,
        event_bus: EventBus,
    ) -> None:
        ...

    @abstractmethod
    def run(self, input: Any) -> Any:
        """主处理入口"""
        ...

    def _emit_delta(
        self,
        entity_type: EntityType,
        entity_id: str,
        changes: dict[str, Any],
    ) -> DeltaUpdate:
        """发送状态更新"""
        ...

    def _request_context(
        self,
        context_type: str,
        **kwargs,
    ) -> ScopedContext:
        """请求作用域上下文"""
        ...
```

## 2. Agent 实现要求

### 2.1 IntentAgent (L0)
```
输入: UserQuery
输出: IntentChain
职责:
  - 多轮意图链追踪
  - 跨话题上下文聚合
  - 隐式意图推断
Prompt: prompts/system/intent_agent.md
```

### 2.2 PlannerAgent (L1)
```
输入: IntentChain
输出: Plan + GoalTree
职责:
  - 基于 IntentChain 制定任务计划
  - 分解为 GoalTree
  - 派发 SubGoal 给 Executor
Prompt: prompts/system/planner_agent.md
```

### 2.3 ExecutorAgent (L2+)
```
输入: SubGoal
输出: ExecutionResult
职责:
  - 执行分配的子目标
  - 报告状态给 Monitor
  - 记录过程日志
Prompt: prompts/system/executor_agent.md
```

### 2.4 SynthesizerAgent (L1)
```
输入: GoalTree + Results
输出: FinalResponse
职责:
  - 聚合子目标结果
  - 映射 Goal → Result
  - 生成最终响应
Prompt: prompts/system/synthesizer_agent.md
```

### 2.5 MonitorAgent (XL)
```
输入: EventBus DeltaUpdate 事件流
输出: Alert + RecoveryAction
职责:
  - 订阅所有状态变更
  - 检测失败/超时
  - 触发 Circuit Breaker
  - 推荐恢复策略
Prompt: prompts/system/monitor_agent.md
```

## 3. Pipeline Runner

```python
class CollaborationPipeline:
    async def run(self, user_query: UserQuery) -> FinalResponse:
        # 顺序: Intent → Planner
        intent_chain = await self.intent_agent.process(user_query)
        goal_tree, plan = await self.planner_agent.process(intent_chain)

        # 并行: Executors
        results = await self._execute_parallel(goals)

        # 顺序: Synthesizer
        return await self.synthesizer.process(results)
```

## 4. 错误处理

```
Executor 失败:
  1. Monitor 检测到 StatusUpdate
  2. Monitor 通知 Planner
  3. Planner 决定: 重试 / 跳过 / 回退
  4. 更新 GoalTree 状态
  5. 重新调度执行
```
