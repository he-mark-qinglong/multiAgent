# 多Agent系统核心规则

**版本: 1.0 | 2026-03-27**

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

### 1.2 异步模型 (ADR-001)
```
核心层: 同步 + threading.RLock (StateStore, EventBus)
Agent层: async/await
桥接: asyncio.create_task
```

### 1.3 状态同步
```
✅ DeltaUpdate: 增量同步，禁止全量广播
✅ 上下文隔离: 每个Agent只看到必要的最小上下文
✅ 订阅规则: 根据 Agent 角色订阅相关状态
✅ 权限控制: PUBLIC/PROTECTED/PRIVATE 三级可见性
```

### 1.4 数据权限 (详见 04-context-isolation.md)
```
PUBLIC: 所有Agent可见 (IntentChain, GoalTree, Plan)
PROTECTED: 指定Agent组可见
PRIVATE: 仅创建者可见 (LLM_Prompt, Internal_Reasoning)
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
✅ 模块 < 400 行
✅ 函数 < 50 行
✅ 类型注解: 所有函数必须有
✅ 错误处理: 所有外部调用必须有 try-except
✅ 日志: 使用 logging，禁止 print()
```

### 2.3 范围控制
```
当前 Phase 锁定，禁止超出范围开发
重大决策 (>30分钟) 必须上报 Team Lead
```

---

## 3. 文件结构

```
core/               # 核心框架
├── models.py       # 数据模型 (IntentNode, GoalTree, Plan, DeltaUpdate)
├── state_store.py  # 状态存储
├── event_bus.py    # 事件总线
└── base_agent.py  # Agent基类

agents/             # Agent实现
├── intent_agent.py
├── planner_agent.py
├── executor_agent.py
└── synthesizer_agent.py

pipelines/         # 执行流水线
└── collaboration_pipeline.py

docs/
├── plans/         # 设计文档
└── decisions/     # ADR记录
```
