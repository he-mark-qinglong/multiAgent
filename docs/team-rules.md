# 团队规范 - 多层级多Agent协作系统

**版本: 1.0 | 2026-03-27**

---

## 1. 核心设计原则 (不可违背)

### 1.1 架构原则
```
✅ 必须遵循:
  - 分层设计: L0 Intent → L1 Planner/Synthesizer → L2+ Executor
  - 增量同步: 使用 DeltaUpdate，禁止全量广播
  - 上下文隔离: 每个Agent只看到必要的最小上下文
  - 状态持久化: 所有状态变更必须写入StateStore

❌ 禁止:
  - Agent间直接通信(除父子关系外)
  - 在Agent代码中硬编码其他Agent的逻辑
  - 绕过StateStore的状态共享
```

### 1.2 代码规范
```
✅ 必须遵循:
  - 不可变数据: 使用 dataclasses/frozen 或 Pydantic models
  - 类型注解: 所有函数必须有完整的类型注解
  - 单一职责: 每个文件 < 400 行，每个函数 < 50 行
  - 错误处理: 所有外部调用必须有 try-except

❌ 禁止:
  - 跨文件循环依赖
  - 使用 global 变量共享状态
  - print() 调试(使用 logging)
```

---

## 2. 范围控制 (Scope Guardrails)

### 2.1 当前Phase锁定
```
当前Phase: Phase 1 - 核心框架搭建

本Phase交付物:
  ✅ StateStore (Redis + SQLite)
  ✅ Agent基类 (BaseAgent)
  ✅ 消息总线 (EventBus)
  ✅ 基础数据模型 (IntentChain, GoalTree, Plan)

非本Phase范围:
  ❌ Monitor Agent (Phase 3)
  ❌ 上下文压缩 (Phase 4)
  ❌ LLM集成细节 (Phase 2+)
  ❌ 持久化存储细节 (Phase 1仅内存)
```

### 2.2 设计决策权限
```
重大决策 (>30分钟工作量的变更):
  → 必须上报 Team Lead 确认
  → 记录到 docs/decisions/

一般决策:
  → Agent可自行决定，但需在 PR 中说明原因
  → 记录到 docs/decisions/

紧急情况:
  → 可先执行，后补决策记录
  → Team Lead 有最终否决权
```

---

## 3. 状态同步规范

### 3.1 DeltaUpdate 格式
```python
@dataclass
class DeltaUpdate:
    event_id: str              # 唯一ID
    timestamp: int            # Unix timestamp
    entity_type: str           # 'Intent' | 'Goal' | 'Plan' | 'Status'
    entity_id: str             # 实体ID
    operation: str            # 'create' | 'update' | 'delete'
    changed_keys: list[str]   # 变化的字段
    delta: dict               # 变化的值
    source_agent: str          # 发起更新的Agent
```

### 3.2 订阅规则
```
Intent Agent → 订阅: IntentChain 变更
Planner Agent → 订阅: IntentChain 变更
Executor Agent → 订阅: 分配给自己的 Goal 变更
Monitor Agent → 订阅: 所有 Status 变更
Synthesizer Agent → 订阅: GoalTree 完成事件
```

---

## 4. 代码组织

```
multiAgent/
├── core/                      # 核心框架
│   ├── state_store.py         # StateStore 实现
│   ├── event_bus.py           # EventBus 实现
│   ├── models.py              # 数据模型定义
│   └── base_agent.py          # Agent 基类
│
├── agents/                    # Agent 实现
│   ├── intent_agent.py
│   ├── planner_agent.py
│   ├── executor_agent.py
│   ├── monitor_agent.py
│   └── synthesizer_agent.py
│
├── pipelines/                 # 执行流水线
│   └── collaboration_pipeline.py
│
├── docs/
│   ├── plans/                 # 设计文档
│   ├── decisions/             # 决策记录
│   └── team-rules.md          # 本文件
│
└── tests/
    ├── unit/
    └── integration/
```

---

## 5. 提交流范

```
Commit Message 格式:
  <type>(<scope>): <description>

  Types:
    - feat: 新功能
    - fix: 修复bug
    - refactor: 重构
    - docs: 文档
    - test: 测试
    - chore: 杂项

示例:
  feat(state): add DeltaUpdate subscription model
  fix(agent): resolve intent chain circular reference
  docs(rules): add delta sync specification
```

---

## 6. 通信规范

### 6.1 团队沟通
```
日常沟通: 使用 SendMessage 工具
会议纪要: 记录到 docs/decisions/meetings/

每周同步:
  - 周一: 确认本周目标
  - 周五: 进度汇报 + 阻塞问题
```

### 6.2 Agent间通信
```
通过 EventBus:
  event_bus.publish(topic, payload)
  event_bus.subscribe(topic, handler)

禁止:
  ❌ Agent A 直接调用 Agent B 的方法
  ❌ 通过全局变量传递消息
```

---

## 7. 质量标准

```
测试覆盖:
  - 单元测试: 核心模块 > 80%
  - 集成测试: Agent间协作 > 60%
  - 端到端: 完整流程验证

代码审查:
  - 必须有至少1人 review
  - CR 问题分级: MUST FIX / SHOULD FIX / NICE TO HAVE
  - MUST FIX 必须在本 PR 中解决
```

---

## 8. 技术决策记录

### ADR-001: 异步模型选择

**状态**: Accepted | **日期**: 2026-03-27

**决策**:
- 核心层 (StateStore, EventBus): 同步 + threading 安全
- Agent 执行层: async/await
- Redis: Phase 3 实现，Phase 1 使用 InMemoryStorage

**理由**:
- 平衡简单性和性能
- 核心状态操作需要强一致性，同步更易保证
- Agent 并行执行用 async 可以提高吞吐量

---

## 9. 决策记录

所有重大技术决策必须记录到 `docs/decisions/`

```markdown
# ADR-XXX: <Title>

## Status
Accepted | Deprecated | Superseded

## Context
<What is the issue that we're seeing that is motivating this decision?>

## Decision
<What is the change that we're proposing and/or doing?>

## Consequences
<What becomes easier or more difficult because of this change?>
```

---

*规范版本: 1.0 | 最后更新: 2026-03-27*
