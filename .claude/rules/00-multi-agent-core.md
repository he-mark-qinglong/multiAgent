# 多Agent系统核心规则

**版本: 2.0 | 2026-03-27**

---

# 第一原则: KISS (Keep It Simple, Stupid)

```
优先级: 最高

✅ 优先简单实现，避免过度设计
✅ 每个模块 < 600 行，每个函数 < 80 行
✅ 必要时才引入复杂性
✅ 单点定义：每个规范只在一个地方定义
✅ 禁止重复文件：重复的 md 文档、代码文件必须删除
❌ 禁止: 为未来可能的需求添加代码
❌ 禁止: 保留废弃/重复的文件
❌ 禁止: 过度抽象或过度工程化
```

---

## 1. 架构原则

### 1.1 分层设计
```
✅ 必须遵循:
  - L0: Intent Agent (意图识别)
  - L1: Planner / Synthesizer (计划/汇总)
  - L2+: Executor Agents (执行器)
  - XL: Monitor Agent (跨层监控)

❌ 禁止:
  - Agent间直接通信(除父子关系外)
  - 绕过 StateStore 的状态共享
```

### 1.2 LangGraph 编排 (强制)
```
✅ 必须使用 LangGraph StateGraph 作为 Agent 编排框架
✅ 所有 Agent 必须继承 BaseReActAgent (支持 ReAct 模式)
✅ Pipeline 必须使用 LangGraph 而非手动编排

❌ 禁止: 使用手动 ThreadPoolExecutor 或手动状态传递
```

### 1.3 ReAct + Stream + Interrupt (核心设计)
```
✅ ReAct 循环: 内部完整推理，保证一致性
✅ Stream 分离: stream() 只输出最终结构化结果，不输出中间步骤
✅ Interrupt: HITL 人工介入审批点，interrupt() 暂停执行
✅ Session/Working Context 分离: Checkpointer 持久化 + StateGraph 工作上下文
✅ Context 压缩: 长对话支持

详情见 01-state-sync.md
```

### 1.4 LangSmith 可观测性 (强制)
```
✅ 所有 Agent 必须集成 LangSmith tracing
✅ 使用 LangSmithTracer 记录:
   - Agent 执行路径
   - Token 使用量
   - 错误追踪
   - 对话历史回放

配置: LANGSMITH_API_KEY, LANGSMITH_PROJECT
```

### 1.5 状态同步原则
```
✅ DeltaUpdate: 增量同步，禁止全量广播
✅ 上下文隔离: 每个Agent只看到必要的最小上下文
✅ 订阅规则: 根据 Agent 角色订阅相关状态
✅ 权限控制: PUBLIC/PROTECTED/PRIVATE 三级可见性
```

---

## 2. 代码规范

### 2.1 不可变性
```
✅ 使用 frozen dataclasses 或 Pydantic models
✅ with_xxx() 方法返回新实例
❌ 禁止: 对象原地修改
```

### 2.2 文件组织
```
✅ 模块 < 600 行
✅ 函数 < 80 行
✅ 类型注解: 所有函数必须有
✅ 错误处理: 所有外部调用必须有 try-except
✅ 日志: 使用 logging，禁止 print()
```

### 2.3 扩展目录
```
prompts/              # Agent prompts 定义 (见下方详细说明)
mcp/                  # MCP 扩展
skills/               # Agent Skills 扩展
services/             # Per-Request 服务
```

---

## 3. 文件结构

```
core/               # 核心框架 (< 600行/文件)
├── models.py       # 数据模型
├── state_store.py  # 状态存储
├── event_bus.py    # 事件总线
├── langgraph_integration.py  # LangGraph 编排 + HITL
├── langsmith_integration.py  # LangSmith 可观测性
└── state_list.py   # 共享状态列表

agents/             # Agent实现 (< 400行/文件)
├── langgraph_agents.py   # BaseReActAgent 基类
├── intent_agent.py       # L0: 意图识别
├── planner_agent.py      # L1: 计划
├── executor_agent.py     # L2+: 执行
├── synthesizer_agent.py  # L1: 汇总
└── monitor_agent.py      # XL: 监控

pipelines/         # 执行流水线
└── collaboration_pipeline.py  # LangGraph Pipeline

prompts/           # Agent prompts 定义
├── system/        # Agent 角色定义
├── context/      # 上下文管理
├── tools/        # 工具定义
└── teams/        # Team 协作定义
```

---

## 4. Prompts 目录结构

Agent 的所有 prompt 定义必须放在 `prompts/` 目录中，分类管理。

### 4.1 目录结构
```
prompts/
├── system/              # Agent 角色定义 (system prompt)
│   ├── intent_agent.md
│   ├── planner_agent.md
│   ├── executor_agent.md
│   ├── synthesizer_agent.md
│   └── monitor_agent.md
│
├── context/             # 上下文模板
│   ├── session_start.md
│   ├── session_end.md
│   └── compression.md   # 长对话压缩提示
│
├── tools/               # 工具定义 (tool prompt/MCP skill)
│   ├── tool_base.md
│   ├── mcp/
│   │   └── *.md
│   └── skills/
│       └── *.md
│
└── teams/               # Team 协作定义
    ├── coordination.md
    └── handoff.md
```

### 4.2 分类规范

| 类别 | 用途 | 加载时机 |
|------|------|----------|
| `system/` | 定义 Agent 角色、能力边界、行为准则 | Agent 初始化时 |
| `context/` | 会话开始/结束模板、压缩提示 | 每次调用时注入 |
| `tools/` | 工具描述、MCP 协议、Skill 定义 | 按需加载 |
| `teams/` | Team 协调规则、交接协议 | 多 Agent 协作时 |

### 4.3 命名规范
```
{agent_name}/{purpose}.md
例: system/intent_agent.md, tools/mcp_weather.md
```

### 4.4 Prompts 加载原则
```
✅ Prompts 作为模板字符串加载，不硬编码在 Python 代码中
✅ 每个 Agent 的 system prompt 在 prompts/system/{agent_name}.md 定义
✅ 工具描述在 prompts/tools/ 下按协议分类
✅ Team 协作规则在 prompts/teams/ 下定义
```
