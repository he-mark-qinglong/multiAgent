# 多Agent系统架构文档

**版本**: 1.0
**更新日期**: 2026-04-16
**状态**: 进行中

---

## 1. 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Feishu WebSocket Bot                      │
│                 (接收消息 → 路由 → 发送响应)                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   OrchestrationEngine                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ QueryQueue  │  │EventHandler │  │  Team Spawner   │    │
│  │ (优先级队列) │  │ (事件分发)  │  │ (CompositeTeam) │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌──────────┐       ┌──────────┐       ┌──────────┐
    │ClimateTeam│       │ NavTeam  │       │MusicTeam │
    │ (气候)    │       │ (导航)   │       │ (音乐)   │
    └────┬─────┘       └────┬─────┘       └────┬─────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AgentTeam (钻石形态)                            │
│                                                             │
│   IntentAgent → PlannerAgent → ExecutorAgent → Synthesizer  │
│                                                             │
│   ToolRegistry (工具执行层)                                  │
│   ├── ClimateTool                                           │
│   ├── NavigationTool                                        │
│   ├── MusicTool                                             │
│   ├── WeatherTool ← LLM生成自然语言                          │
│   └── ...                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 核心组件

### 2.1 OrchestrationEngine (编排引擎)

**位置**: `core/orchestration/engine.py`

**职责**:
- 全局 Query 队列管理（优先级队列）
- Team 的生命周期管理（spawn/get/stop）
- 事件分发（query_started/completed/failed）
- 并发控制（max_concurrent_teams）

**关键类**:
```python
class OrchestrationEngine:
    def spawn_team(team_id: str) -> CompositeTeam
    def enqueue(content: str, priority: QueryPriority, team_id: str) -> str
    def get_stats() -> dict  # 队列统计
```

### 2.2 CompositeTeam (复合Team)

**位置**: `core/orchestration/composite.py`

**职责**:
- 管理多个 SubTeam
- 并行执行 SubTeam（asyncio.as_completed）
- 任务分解（基于配置文件的 keyword/task_templates）
- 结果汇总（_synthesize）

**配置驱动**:
```json
// ~/.multiagent/teams/{team_id}.json
{
  "team_id": "default",
  "sub_teams": [
    {
      "team_id": "climate",
      "keywords": ["空调", "温度"],
      "task_templates": {
        "打开空调": {"action": "turn_on"},
        "调节温度": {"action": "set_temperature"}
      },
      "default_task": "空调控制"
    }
  ]
}
```

### 2.3 AgentTeam (Agent团队)

**位置**: `core/orchestration/team.py`

**职责**:
- 封装一个完整的钻石形态 agent team
- 延迟创建 CollaborationPipeline
- 调用 LangGraph pipeline 执行

**钻石形态**:
```
IntentAgent (意图识别)
      ↓
PlannerAgent (任务规划)
      ↓
ExecutorAgent (工具执行) ←→ ToolRegistry
      ↓
SynthesizerAgent (响应汇总)
```

### 2.4 ToolRegistry (工具注册表)

**位置**: `backend/tools.py`

**职责**:
- 统一工具调用接口
- 工具懒加载
- 动作映射（action dispatch）

**已注册工具**:
| 工具名 | 类 | 支持动作 |
|--------|---|---------|
| climate_control | ClimateTool | turn_on, turn_off, set_temperature, set_fan_speed, control |
| navigation | NavigationTool | navigate, get_traffic, cancel |
| music_player | MusicTool | play, pause, skip, set_volume |
| vehicle_status | VehicleStatusTool | get_status |
| get_weather | WeatherTool | get_weather, get_status |
| door_control | DoorTool | lock, unlock, get_status |
| emergency | EmergencyTool | call |
| news | NewsTool | get_news |

---

## 3. 数据流

### 3.1 消息处理流程

```
1. Feishu WebSocket 收到消息
       ↓
2. feishu_message_handler 去重 + 入队
       ↓
3. OrchestrationEngine 主循环取出 Query
       ↓
4. spawn_team (如不存在) 创建 CompositeTeam
       ↓
5. CompositeTeam.run_async():
   a. _plan_sub_teams() - 基于 keywords 选择 SubTeam
   b. _extract_sub_tasks() - 基于 task_templates 提取任务
   c. 并行执行 SubTeam (asyncio.as_completed)
       ↓
6. 流式回调 result_callback 立即发送部分结果到 Feishu
       ↓
7. _synthesize() 汇总所有 SubTeam 结果
       ↓
8. 最终响应发送到 Feishu
```

### 3.2 任务分解流程

输入: `"打开空调、导航去机场、播放音乐"`

```
1. _plan_sub_teams() 基于 keywords 选择:
   - climate (匹配 "空调")
   - nav (匹配 "机场", "去")
   - music (匹配 "音乐", "播放")

2. _extract_sub_tasks() 基于 task_templates:
   - climate → "打开空调"
   - nav → "导航去机场"
   - music → "播放音乐"

3. 各 SubTeam 并行执行
```

### 3.3 LLM增强流程

某些工具类型使用 LLM 生成自然语言描述：

```
ExecutorAgent._execute_goal()
       ↓
registry.call_tool() → ToolResult (结构化数据)
       ↓
如果 goal.type in USE_LLM_RESPONSE_TYPES:
    _generate_llm_description() → LLM生成自然语言
       ↓
最终 description
```

**USE_LLM_RESPONSE_TYPES**: `{"weather", "news", "vehicle_status", "music_control"}`

---

## 4. 配置文件

### 4.1 Team配置

**路径**: `~/.multiagent/teams/{team_id}.json`

**完整示例**:
```json
{
  "team_id": "default",
  "sub_teams": [
    {
      "team_id": "climate",
      "keywords": ["空调", "温度", "冷", "热"],
      "task_templates": {
        "打开空调": { "action": "turn_on", "default_temp": 24 },
        "调节温度": { "action": "set_temperature", "default_temp": 24 },
        "关闭空调": { "action": "turn_off" }
      },
      "default_task": "空调控制"
    },
    {
      "team_id": "nav",
      "keywords": ["导航", "去", "机场", "路线"],
      "task_templates": {
        "导航去{dest}": { "action": "navigate", "extract_dest": true }
      },
      "default_task": "导航"
    },
    {
      "team_id": "weather",
      "keywords": ["天气", "明天", "气温"],
      "task_templates": {
        "查询天气": { "action": "get_weather" },
        "查询明天天气": { "action": "get_weather", "forecast_days": 2 }
      },
      "default_task": "查询天气"
    }
  ]
}
```

### 4.2 Feishu配置

**路径**: `~/.multiagent/channels/feishu.json`

```json
{
  "appId": "cli_xxx",
  "appSecret": "xxx",
  "botName": "车载助手"
}
```

### 4.3 MiniMax配置

**优先级**: env > `~/.multiagent/.env` > `~/.multiagent/config.json`

```json
// ~/.multiagent/config.json
{
  "provider": "minimax",
  "model": "MiniMax-M2.7-8B",
  "address": "https://api.minimax.io"
}
```

---

## 5. 目录结构

```
multiAgent/
├── core/
│   ├── orchestration/
│   │   ├── engine.py      # OrchestrationEngine
│   │   ├── composite.py   # CompositeTeam
│   │   ├── team.py        # AgentTeam
│   │   ├── queue.py       # QueryQueue
│   │   └── types.py       # QueryRequest, RunResult, TeamConfig
│   ├── minimax_client.py  # MiniMax LLM 客户端
│   └── models.py          # AgentState, Goal, IntentChain
│
├── agents/
│   ├── langgraph_agents.py    # BaseReActAgent
│   ├── intent_agent.py         # 意图识别
│   ├── planner_agent.py        # 任务规划
│   ├── executor_agent.py       # 工具执行 (含LLM增强)
│   └── synthesizer_agent.py    # 响应汇总
│
├── backend/
│   ├── main.py            # FastAPI 应用 + Feishu集成
│   └── tools.py           # ToolRegistry
│
├── pipelines/
│   └── collaboration_pipeline.py  # LangGraph StateGraph
│
├── prompts/
│   ├── system/           # Agent prompts
│   ├── tools/mcp/        # MCP工具定义
│   └── context/           # 上下文模板
│
└── tests/
    ├── mock_tools/        # Mock工具实现 (含LLM描述生成)
    └── test_orchestration_sim.py  # 飞书消息处理模拟测试
```

---

## 6. 关键设计决策

### 6.1 为什么用配置文件驱动？

- **可扩展**: 新增 SubTeam 只需修改配置，无需改代码
- **可维护**: 关键词、任务模板集中管理
- **灵活**: 支持动态参数提取（目的地等）

### 6.2 为什么用 asyncio.gather 而非 as_completed？

```python
# 使用 asyncio.gather 等待所有完成
results = await asyncio.gather(*[c[0] for c in coros])
for result, (coro, team_id) in zip(results, coros):
    sub_results[team_id] = result
    if self.result_callback:
        self.result_callback(team_id, result)
```

**历史**: 曾尝试使用 `asyncio.as_completed` 实现流式，但因 dict 与协程配合的 bug（await as_completed 返回值而非 Future）导致错误。最终使用 `asyncio.gather` 保证正确性。

- **正确性优先**: 确保所有 SubTeam 结果正确收集
- **流式通过回调**: result_callback 仍可在每个结果可用时立即通知

### 6.3 为什么工具用 Mock + LLM？

- **Mock**: 保证确定性返回，格式可控
- **LLM描述**: 生成自然语言，提升用户体验
- **分离关注点**: 工具只管格式校验，LLM负责表达

---

## 7. 待办 / 改进方向

- [ ] 天气工具接入真实 API（和风天气等）
- [x] 天气 Intent/Goal 路由（已修复，WeatherTool 已集成）
- [ ] LLM描述生成增加上下文（如用户历史偏好）
- [ ] 支持动态加载 SubTeam（运行时添加新team类型）
- [ ] 完善单元测试覆盖率
- [ ] MonitorAgent 集成（监控+告警）
- [x] 测试模拟框架（test_orchestration_sim.py 已创建）

---

---

## 8. 通信通道

系统支持两条消息处理路径：

| 通道 | 协议 | 用途 | 处理链路 |
|------|------|------|---------|
| 自有客户端 | SSE | 实时推理展示 | `/api/chat` → llm_reasoning() → 单工具调用 |
| 飞书 | WebSocket | 消息推送 | Feishu WS → OrchestrationEngine → CompositeTeam → 多SubTeam并行 |

**飞书专用配置**: `~/.multiagent/teams/feishu.json` 定义飞书消息的 SubTeam 路由。

---

## 9. 相关文档

- [Orchestration Engine 设计](./plans/orchestration-engine.md)
- [多Agent核心规则](../.claude/rules/00-multi-agent-core.md)
- [状态同步与HITL规范](../.claude/rules/01-state-sync.md)
- [Agent实现规范](../.claude/rules/02-agent-impl.md)
