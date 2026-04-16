# Agent Orchestration Engine - 编排引擎

**版本**: 0.1
**日期**: 2026-04-16

## 目标

为 multi-agent 系统构建一个**编排引擎**，具备：

1. **Query 队列** - 接收并管理多来源请求
2. **While 循环驱动** - 主循环持续处理队列
3. **Spawn 产卵模式** - 支持生成多套完整的钻石形态 agent team
4. **层级合作** - 多层 agent team 可协作

## 当前架构

```
User Query → PipelineStateGraph → Agents (intent/planner/executor/synthesizer)
```

问题：
- 无队列管理
- 无并行 team 支持
- 无全局调度

## 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Engine                          │
│                    (Queue + While Loop)                          │
│                                                                  │
│   while running:                                                 │
│     1. dequeue() → query                                         │
│     2. assign to AgentTeam (spawn if needed)                    │
│     3. team.run() → result                                      │
│     4. emit result                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │ Team 1  │         │ Team 2  │         │ Team N  │
    │ (钻石)  │         │ (钻石)  │         │ (钻石)  │
    └─────────┘         └─────────┘         └─────────┘
         │                    │                    │
    IntentAgent          IntentAgent          IntentAgent
         ↓                    ↓                    ↓
    PlannerAgent         PlannerAgent         PlannerAgent
    SynthesizerAgent    SynthesizerAgent    SynthesizerAgent
         ↓                    ↓                    ↓
    ExecutorAgent        ExecutorAgent        ExecutorAgent
```

## 核心组件

### 1. QueryQueue

```python
class QueryQueue:
    """优先级队列，管理所有待处理的 query"""
    def enqueue(self, query: QueryRequest, priority: int = 0) -> str
    def dequeue(self) -> QueryRequest | None
    def preempt(self, query_id: str) -> bool  # 插入高优先级
    def cancel(self, query_id: str) -> bool
    def requeue(self, query_id: str) -> bool    # 重新入队
```

### 2. AgentTeam

```python
class AgentTeam:
    """一套完整的钻石形态 agent team"""

    def __init__(self, team_id: str):
        self.team_id = team_id
        self.intent_agent = IntentAgent(llm=client)
        self.planner_agent = PlannerAgent(llm=client)
        self.executor_agent = ExecutorAgent(llm=client, tool_registry=registry)
        self.synthesizer_agent = SynthesizerAgent(llm=client)

    def run(self, query: str) -> RunResult:
        """运行完整流程"""
        # Intent → Planner → Executor → Synthesizer
        intent_result = self.intent_agent.run(query)
        plan = self.planner_agent.run(intent_result)
        results = self.executor_agent.run(plan)
        final = self.synthesizer_agent.run(results)
        return final

    def cancel(self) -> None:
        """取消当前执行"""
```

### 3. OrchestrationEngine

```python
class OrchestrationEngine:
    """编排引擎 - 全局调度器"""

    def __init__(self):
        self.queue = QueryQueue()
        self.teams: dict[str, AgentTeam] = {}
        self.running: dict[str, asyncio.Task] = {}
        self.max_concurrent_teams = 10

    async def start(self) -> None:
        """启动主循环"""
        while True:
            await self._process_queue()
            await asyncio.sleep(0.1)  # 避免 CPU 100%

    async def _process_queue(self) -> None:
        """处理队列"""
        if len(self.running) >= self.max_concurrent_teams:
            return  # 达到上限，等待

        query = self.queue.dequeue()
        if query is None:
            return  # 队列空

        team = self._get_or_spawn_team(query.team_id)
        task = asyncio.create_task(self._run_team(team, query))
        self.running[query.id] = task

    async def _run_team(self, team: AgentTeam, query: QueryRequest) -> None:
        """运行 team"""
        try:
            result = await team.run_async(query.content)
            await self._emit_result(query.id, result)
        finally:
            del self.running[query.id]

    def spawn_team(self, team_id: str) -> AgentTeam:
        """产卵模式 - 创建新的 agent team"""
        if team_id in self.teams:
            return self.teams[team_id]

        team = AgentTeam(team_id=team_id)
        self.teams[team_id] = team
        return team

    def _get_or_spawn_team(self, team_id: str) -> AgentTeam:
        return self.teams.get(team_id) or self.spawn_team(team_id)
```

## 消息流

```
1. Feishu/其他 channel 收到消息
       ↓
2. OrchestrationEngine.enqueue(query, priority)
       ↓
3. Engine 主循环 dequeue
       ↓
4. 分配到 AgentTeam.run()
       ↓
5. Team 内部: Intent → Planner → Executor → Synthesizer
       ↓
6. 结果通过 EventBus 发布
       ↓
7. Channel 发送响应
```

## 支持的 Query 类型

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| `normal` | 普通请求 | 排队，正常优先级 |
| `urgent` | 紧急请求 | 可 preempt 正在执行的 query |
| `spawn` | 产卵请求 | 创建新的 AgentTeam |
| `cancel` | 取消请求 | 取消指定的 query 或 team |

## 并发控制

- `max_concurrent_teams`: 最大并发 team 数（默认 10）
- `max_iterations_per_team`: 单个 team 最大 ReAct 迭代（默认 50）
- 超过限制时新 query 排队等待

## 文件结构

```
core/
├── orchestration/
│   ├── __init__.py
│   ├── engine.py        # OrchestrationEngine
│   ├── queue.py         # QueryQueue
│   ├── team.py          # AgentTeam
│   └── types.py         # 类型定义
```

## 待办

- [x] 实现 QueryQueue（优先级队列）
- [x] 实现 AgentTeam（钻石形态 team）
- [x] 实现 OrchestrationEngine（主循环）
- [x] 集成 Feishu channel
- [ ] 集成 ToolRegistry
- [x] 支持 spawn 模式
- [x] 支持 query preempt/cancel
- [ ] 分层 Team（CompositeTeam）
- [ ] 跨级沟通机制
- [ ] Agent 提示词团队化

---

## 分层 Team 设计（Layered Teams）

### 目标

支持多层级 Team，构成更大规模的协作系统：
- Layer 1: 基础 Team（4 个 Agent 的钻石形态）
- Layer 2: CompositeTeam（包含多个 SubTeam）
- Layer N: 可以无限层级组合

### 设计

```python
class CompositeTeam:
    """复合 Team - 包含多个 SubTeam."""

    def __init__(self, team_id: str, sub_team_configs: list[TeamConfig]):
        self.team_id = team_id
        self.sub_teams: dict[str, AgentTeam] = {}
        self.synthesizer = SynthesizerAgent()

        # 创建 SubTeam
        for config in sub_team_configs:
            self.sub_teams[config.team_id] = AgentTeam(config)

    async def run_async(self, query: QueryRequest) -> RunResult:
        """运行复合 Team.

        流程：
        1. Intent 分析 -> 确定需要哪些 SubTeam
        2. 并行调用各 SubTeam
        3. Synthesizer 汇总结果
        """
        # TODO: 实现
        pass


class LayeredOrchestrationEngine:
    """分层编排引擎."""

    def __init__(self):
        self.engine = OrchestrationEngine()
        self.composite_teams: dict[str, CompositeTeam] = {}

    def spawn_composite_team(
        self,
        team_id: str,
        sub_team_configs: list[TeamConfig],
    ) -> CompositeTeam:
        """创建一个复合 Team."""
        team = CompositeTeam(team_id, sub_team_configs)
        self.composite_teams[team_id] = team
        return team
```

### 跨级沟通

SubTeam 之间通过 EventBus 通信：

```python
# SubTeam A 完成后通知 SubTeam B
event_bus.publish(
    topic=f"team.{team_id_b}.input",
    data={"result": subteam_a_result},
)

# SubTeam B 订阅
event_bus.subscribe(
    topic=f"team.{team_id_b}.input",
    handler=subteam_b.handle_input,
)
```

### Agent 提示词团队化

新的目录结构：

```
prompts/
├── teams/
│   ├── default_team/
│   │   ├── team.md          # Team 协调提示词
│   │   └── agents/
│   │       ├── intent_agent.md
│   │       ├── planner_agent.md
│   │       ├── executor_agent.md
│   │       └── synthesizer_agent.md
│   └── research_team/
│       ├── team.md
│       └── agents/
│           └── ...
```

team.md 内容示例：
```markdown
# Team 协调提示词

## Team 角色
你是一个多 Agent 协作团队的协调者。

## 团队成员
- IntentAgent: 意图识别
- PlannerAgent: 任务规划
- ExecutorAgent: 工具执行
- SynthesizerAgent: 响应汇总

## 协作流程
1. 用户输入 -> IntentAgent 分析
2. IntentAgent -> PlannerAgent 制定计划
3. PlannerAgent -> ExecutorAgent 执行
4. ExecutorAgent -> SynthesizerAgent 汇总
5. SynthesizerAgent -> 用户响应

## 跨 Team 协作
当需要多个 Team 协作时：
1. 主 Team 负责任务分解
2. 子 Team 各自执行
3. 主 Team 汇总结果
```

---

## 上下文压缩

已实现压缩限制：
- 单次工具调用结果：20000 字符
- 单次工具调用结果：200 行

压缩策略：
1. 先按行数压缩（保留前 N/2 + 后 N/2）
2. 再按字符数压缩
