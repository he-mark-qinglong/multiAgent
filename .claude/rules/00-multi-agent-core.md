# 多Agent系统核心规则

**版本: 1.1 | 2026-03-27**

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

文件结构:
agents/
├── langgraph_agents.py   # LangGraph ReAct Agent 基类
├── intent_agent.py        # 保留兼容，内部使用 LangGraph
├── planner_agent.py       # 同上
└── ...

❌ 禁止: 使用手动 ThreadPoolExecutor 或手动状态传递
```

### 1.3 LangSmith 可观测性 (强制)
```
✅ 所有 Agent 必须集成 LangSmith tracing
✅ 使用 LangSmithTracer 记录:
   - Agent 执行路径
   - Token 使用量
   - 错误追踪
   - 对话历史回放

✅ 配置通过环境变量:
   LANGSMITH_API_KEY=xxx
   LANGSMITH_PROJECT=multi-agent
```

### 1.4 流式输出 (强制)
```
✅ 所有 Agent 必须支持 stream() 方法
✅ 使用 LangGraph stream_mode="messages" 输出
✅ 支持实时 token 显示
```

### 1.5 异步模型 (ADR-001)
```
核心层: 同步 + threading.RLock (StateStore, EventBus)
Agent层: async/await
桥接: asyncio.create_task
LangGraph: 内置异步支持
```

### 1.6 状态同步
```
✅ DeltaUpdate: 增量同步，禁止全量广播
✅ 上下文隔离: 每个Agent只看到必要的最小上下文
✅ 订阅规则: 根据 Agent 角色订阅相关状态
✅ 权限控制: PUBLIC/PROTECTED/PRIVATE 三级可见性
```

### 1.7 核心设计 (详见 04-architecture-principles.md)
```
✅ ReAct 循环: 内部推理，保证一致性
✅ Stream 分离: 外层展示最终结构化结果
✅ Interrupt: HITL 人工介入审批点
✅ Session/Working Context 分离
✅ Context 压缩: 长对话支持
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

### 2.3 依赖管理
```
✅ 核心依赖必须写入 requirements.txt:
   langgraph>=0.2.0
   langchain-core>=0.3.0
   langsmith (可选，用于可观测性)

❌ 禁止: 在代码中硬编码依赖版本
```

### 2.4 扩展目录 (预留)
```
mcp/                 # MCP (Model Context Protocol) 扩展
├── __init__.py
├── mcp_client.py     # MCP 客户端封装
└── protocols/        # 协议定义

skills/              # Agent Skills 扩展
├── __init__.py
├── skill_base.py    # Skill 基类
└── builtin/         # 内置 Skills

services/            # Per-Request 服务
├── __init__.py
├── query_service.py  # 请求处理服务
└── context_service.py # 上下文管理服务
```

---

## 3. 文件结构

```
core/               # 核心框架
├── models.py       # 数据模型 (IntentNode, GoalTree, Plan, DeltaUpdate)
├── state_store.py  # 状态存储
├── event_bus.py    # 事件总线
├── base_agent.py  # Agent基类 (同步版本，兼容用)
├── langgraph_integration.py  # LangGraph 编排
├── langsmith_integration.py  # LangSmith 可观测性
└── state_list.py   # 共享状态列表

agents/             # Agent实现
├── langgraph_agents.py   # LangGraph ReAct Agent 基类
├── intent_agent.py       # L0: 意图识别
├── planner_agent.py      # L1: 计划
├── executor_agent.py     # L2+: 执行
├── synthesizer_agent.py  # L1: 汇总
└── monitor_agent.py      # XL: 监控

pipelines/         # 执行流水线
└── collaboration_pipeline.py  # LangGraph Pipeline

docs/
├── plans/         # 设计文档
└── decisions/     # ADR记录
```
