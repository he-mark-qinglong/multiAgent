# Plan: Prompt-Driven Agent 架构迁移

## Context

**问题**: 当前 agent 仍需为每个任务写一个 Python 类（IntentAgent、PlannerAgent 等），think/act 逻辑硬编码在各子类中，无法统一优化。

**目标**: Agent 完全由 prompt 配置生成，无硬编码逻辑。Agent 之间可组成 team 协作。新增 agent 只需编写 YAML 配置 + Markdown prompt。

## 架构设计

### 核心思想：Prompt-as-Agent

```
GenericAgentRunner (通用执行器)
├── system_prompt: 从 .md 加载
├── tools: 从配置加载
├── output_schema: 期望的输出格式
└── ReAct 循环: think() → act() → observe() (通用模板)
```

### 新增组件

```
agents/
├── base/
│   ├── agent_runner.py      # GenericAgentRunner (通用执行器)
│   └── prompt_loader.py     # Prompt 加载 (支持变量替换)
├── config/
│   └── team_config.py       # Team 配置模型
└── teams/
    └── team_coordinator.py  # Team 协调器

prompts/system/               # Agent prompts (YAML frontmatter + markdown)
├── intent_agent.md           # 包含 frontmatter 配置
├── planner_agent.md
├── executor_agent.md
├── synthesizer_agent.md
└── teams/
    └── car_assistant_team.md # Team 配置
```

### Agent 配置格式 (Markdown + YAML Frontmatter)

每个 agent 一个 `.md` 文件，头部是 YAML frontmatter 配置，后面是 prompt 内容：

```markdown
---
agent_id: intent_agent
name: Intent Recognition Agent
role: L0
output_schema:
  type: intent_chain
react:
  max_iterations: 10
  finish_condition: confidence_threshold
  finish_value: 0.7
tools: null
---
# Intent Agent - System Prompt

## Role
...
```

### Team 协作机制

```yaml
# prompts/system/teams/car_assistant_team.md
---
team_id: car_assistant_team
members:
  - agent_id: intent
    role: orchestrator
  - agent_id: planner
    role: planner
  - agent_id: executor
    role: worker
  - agent_id: synthesizer
    role: synthesizer
---
# Team Coordination Prompt
...
```

## 实施步骤

### Phase 1: 基础设施 (不破坏现有功能)

1. [ ] 创建 `agents/base/prompt_loader.py` - Prompt 加载器，支持 $VAR 替换
2. [ ] 创建 `agents/config/agent_config.py` - Agent 配置模型 (Pydantic)
3. [ ] 创建 `agents/base/agent_runner.py` - GenericAgentRunner (通用 ReAct 循环)

### Phase 2: 配置准备

4. [ ] 创建 `prompts/config/intent_agent.yaml`
5. [ ] 创建 `prompts/config/planner_agent.yaml`
6. [ ] 创建 `prompts/config/executor_agent.yaml`
7. [ ] 创建 `prompts/config/synthesizer_agent.yaml`
8. [ ] 创建 `prompts/config/car_assistant_team.yaml`

### Phase 3: 改造现有 Agent (保持接口兼容)

9.  [ ] 改造 `agents/intent_agent.py` - 继承 GenericAgentRunner
10. [ ] 改造 `agents/planner_agent.py` - 继承 GenericAgentRunner
11. [ ] 改造 `agents/executor_agent.py` - 继承 GenericAgentRunner
12. [ ] 改造 `agents/synthesizer_agent.py` - 继承 GenericAgentRunner

### Phase 4: 工厂和 Pipeline 改造

13. [ ] 改造 `core/agent_factory.py` - 从 YAML 配置创建 Agent
14. [ ] 改造 `pipelines/collaboration_pipeline.py` - 支持 Team 模式

### Phase 5: 清理

15. [ ] 删除各 agent 中的 `*_SYSTEM_PROMPT` fallback 常量
16. [ ] (可选) 删除 `agents/langgraph_agents.py` - 被 agent_runner.py 替代

## 关键文件

| 操作 | 文件 |
|------|------|
| **新增** | `agents/base/agent_runner.py` |
| **新增** | `agents/base/prompt_loader.py` |
| **新增** | `agents/config/agent_config.py` |
| **新增** | `agents/teams/team_coordinator.py` |
| **新增** | `prompts/config/*.yaml` |
| **修改** | `agents/{intent,planner,executor,synthesizer}_agent.py` |
| **修改** | `core/agent_factory.py` |
| **修改** | `pipelines/collaboration_pipeline.py` |
| **删除** | `agents/langgraph_agents.py` (可选) |

## 可复用现有代码

- `core/minimax_client.py` - LLM 调用封装
- `core/models.py` - AgentState 等数据模型
- `core/event_bus.py` - 事件总线 (Team 通信)
- `prompts/system/*.md` - 现有完整 prompt 定义

## 验证方法

1. 运行现有测试: `python -m pytest tests/ -v`
2. 运行多轮对话: `python -X utf8 tests/demo_chat_ui.py --auto`
3. 新增配置后测试: 创建新 agent 只需配置 YAML
4. Team 协作测试: 多 agent 联合执行场景

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| output_schema 验证失败 | 添加 schema 验证 + fallback |
| 性能下降 | 通用 Runner 可按需优化 |
| 调试困难 | 增加 prompt 版本管理 |

## 预期结果

- **Agent 数量**: 10个具体类 → 1个 GenericAgentRunner + N个 YAML 配置
- **新增 Agent**: 只需写 YAML 配置 + Markdown prompt
- **Team 支持**: 原生 Team 协作机制

## 相关文档

- 现有 Agent 实现: `agents/*_agent.py`
- 现有 Prompts: `prompts/system/`
- 核心框架: `core/minimax_client.py`, `core/models.py`
