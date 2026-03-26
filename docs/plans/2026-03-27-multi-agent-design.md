# 多层级多Agent协作系统设计文档

**作者：Hangfei Lin | 2026年3月27日**

## 1. 设计背景

基于 Google ADK 上下文感知框架的设计理念，构建一套适用于通用AI应用的多层级多Agent协作系统。核心需求：

- 多Agent协作流水线：意图识别 → 任务计划 → 子目标执行 → 结果汇总
- 全量状态同步：上下文、任务、资源、工具全部共享
- 长对话支持（50+轮）：Token线性增长，不爆炸
- 低延迟 + 低Token消耗的平衡优化
- **基于 LangGraph 框架实现 ReAct Agent**
- **集成 LangSmith 实现可观测性**

---

## 2. 框架架构 (LangGraph + LangSmith)

### 2.1 LangGraph 编排架构 (Mermaid)

```mermaid
flowchart TB
    subgraph Graph["LangGraph StateGraph"]
        START([START]) --> intent_node
        intent_node --> planner_node
        planner_node --> fan_out
        fan_out -->|Send API| parallel_executor
        parallel_executor --> synthesizer_node
        synthesizer_node --> END([END])
    end

    subgraph Nodes["Agent Nodes"]
        intent_node["Intent ReAct Agent<br/>L0: 意图识别"]
        planner_node["Planner ReAct Agent<br/>L1: 任务规划"]
        parallel_executor["Executor ReAct Agents<br/>L2+: 并行执行"]
        synthesizer_node["Synthesizer ReAct Agent<br/>L1: 结果汇总"]
    end

    subgraph Persistence["持久化层"]
        Checkpointer["Checkpointer<br/>InMemory / Postgres"]
        Store["Store<br/>长期记忆"]
    end

    subgraph Observability["LangSmith 可观测性"]
        Tracing["Tracing<br/>执行路径"]
        Metrics["Metrics<br/>Token使用"]
        History["History<br/>对话回放"]
    end

    Graph --> Persistence
    Graph --> Observability

    style Graph fill:#e8f5e9
    style Nodes fill:#e3f2fd
    style Persistence fill:#fff3e0
    style Observability fill:#fce4ec
```

### 2.2 ReAct Agent 模式

```
ReAct (Reasoning + Acting) 循环:

┌─────────────────────────────────────────────────────┐
│                    Thought                          │
│   "我需要理解用户的意图，提取关键实体..."              │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                    Action                          │
│   调用工具: query_knowledge_base(query)             │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                  Observation                        │
│   检索结果: [entity_1, entity_2, confidence: 0.9]   │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
              继续循环或结束
```

### 2.3 流式输出架构

```
Client                    LangGraph                    LLM
  │                          │                        │
  │──── stream(query) ──────>│                        │
  │                          │──── invoke ────────────>│
  │                          │<─── tokens ────────────│
  │<──── chunk ──────────────│                        │
  │                          │                        │
  │                          │<─── tokens ────────────│
  │<──── chunk ──────────────│                        │
  │                          │                        │
  │              (实时流式输出)                        │
```

---

## 3. 系统架构

### 3.1 整体架构图 (Mermaid)

```mermaid
flowchart TB
    subgraph INPUT[" "]
        Q[User Query]
    end

    subgraph L0["Layer 0 - Intent Recognition"]
        IA[Intent Agent<br/>• 意图链追踪<br/>• 跨话题聚合<br/>• 隐式推断]
    end

    subgraph L1["Layer 1 - Planning & Synthesis"]
        PA[Planner Agent<br/>• 任务计划<br/>• Goal分解]
        SA[Synthesizer Agent<br/>• 结果聚合<br/>• Goal→Result映射]
    end

    subgraph L2["Layer 2+ - Execution"]
        EA[Executor A<br/>SubGoal #1]
        EB[Executor B<br/>SubGoal #2]
        EC[Executor C<br/>SubGoal #3]
    end

    subgraph CROSS["Cross-layer"]
        MA[Monitor Agent<br/>• 状态监控<br/>• 异常检测<br/>• 进度同步]
    end

    subgraph STATE["Shared State Store"]
        IG[IntentGraph]
        GT[GoalTree]
        PL[Plan]
        ES[ExecutionStatus]
        PL2[ProcessLog]
        RC[ResultCache]
    end

    subgraph OUTPUT[" "]
        R[User Response]
    end

    Q --> IA
    IA -->|广播 IntentChain| STATE
    STATE --> PA
    PA -->|派发 SubGoals| EA
    PA -->|派发 SubGoals| EB
    PA -->|派发 SubGoals| EC

    EA <-->|状态更新| MA
    EB <-->|状态更新| MA
    EC <-->|状态更新| MA

    MA -->|推送状态| STATE

    EA -->|结果| SA
    EB -->|结果| SA
    EC -->|结果| SA
    STATE --> SA

    SA --> R

    style L0 fill:#e1f5fe
    style L1 fill:#fff3e0
    style L2 fill:#e8f5e9
    style CROSS fill:#fce4ec
    style STATE fill:#f3e5f5
```

### 3.2 ASCII 架构图 (兼容性版本)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Multi-Agent Collaboration                       │
│                                                                       │
│  User Query ───────────────────────────────────────────────────────▶ │
│      │                                                                │
│      ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              Intent Agent (L0 - Intent Recognition)            │     │
│  │  • 多轮意图链追踪                                              │     │
│  │  • 跨话题上下文聚合                                            │     │
│  │  • 隐式意图推断                                                │     │
│  │  输出: IntentChain { current_intent, history, confidence }    │     │
│  └──────────────────────────────┬───────────────────────────────┘     │
│                                 │ 广播 IntentChain                    │
│                                 ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              Planner Agent (L1 - Task Orchestration)         │     │
│  │  • 基于 IntentChain 制定任务计划                              │     │
│  │  • 分解为 Goal Tree                                          │     │
│  │  输出: Plan { goals[], execution_order, dependencies[] }       │     │
│  └──────────────────────────────┬───────────────────────────────┘     │
│                                 │ 派发 SubGoals                       │
│                    ┌────────────┼────────────┐                         │
│                    ▼            ▼            ▼                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │
│  │ Executor A  │  │ Executor B  │  │ Executor C  │  (L2+)               │
│  │ SubGoal #1  │  │ SubGoal #2  │  │ SubGoal #3  │                       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                       │
│         │               │               │                              │
│         └───────────────┼───────────────┘                              │
│                         ▼ 状态更新                                      │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │              Monitor Agent (Cross-layer - Process Tracking)  │      │
│  │  • 实时监控子目标执行状态                                       │      │
│  │  • 异常检测                                                    │      │
│  │  • 进度同步                                                    │      │
│  │  输出: StatusUpdates → StateStore & UI                       │      │
│  └──────────────────────────────┬───────────────────────────────┘      │
│                                 │                                      │
│                                 ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │              Synthesizer Agent (L1 - Result Mapping)         │      │
│  │  • 聚合子目标结果                                              │      │
│  │  • 映射 Goal → Result                                         │      │
│  │  • 生成最终响应                                                │      │
│  └──────────────────────────────┬───────────────────────────────┘      │
│                                 │                                      │
│                                 ▼                                      │
│                         User Response                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 状态同步架构 (Mermaid)

```mermaid
flowchart LR
    subgraph Agents["Agents"]
        IA[Intent Agent]
        PA[Planner Agent]
        EA[Executor A]
        EB[Executor B]
        MA[Monitor Agent]
        SA[Synthesizer]
    end

    subgraph Store["StateStore"]
        direction TB
        subgraph Hot["Hot Storage<br/>(最近20轮)"]
            D1[DeltaUpdates]
        end
        subgraph Cold["Cold Storage<br/>(历史摘要)"]
            D2[Compressed Snapshots]
        end
    end

    IA -->|DeltaUpdate| D1
    PA -->|DeltaUpdate| D1
    EA -->|DeltaUpdate| D1
    EB -->|DeltaUpdate| D1
    MA -->|DeltaUpdate| D1

    D1 -.->|超阈值触发| D2

    D1 -->|订阅| IA
    D1 -->|订阅| PA
    D1 -->|订阅| EA
    D1 -->|订阅| SA
    D1 -.->|订阅全部| MA

    style Hot fill:#ffecb3
    style Cold fill:#cfd8dc
    style Store fill:#e8f5e9
```

---

## 3. Agent 职责矩阵

| Agent | 层级 | 输入 | 输出 | 协作方式 |
|-------|------|------|------|----------|
| **Intent Agent** | L0 | User Query + History | IntentChain | 广播 IntentChain 给所有 Agent |
| **Planner Agent** | L1 | IntentChain | Plan + GoalTree | 派发 SubGoal 给 Executor |
| **Executor Agent** | L2+ | SubGoal | ExecutionResult | 报告状态给 Monitor |
| **Monitor Agent** | 跨层 | 各 Agent 状态 | StatusUpdate | 推送状态到 StateStore |
| **Synthesizer Agent** | L1 | SubGoal Results | FinalResponse | 订阅 GoalTree 完成事件 |

---

## 4. 核心数据模型

### 4.1 IntentChain (意图链)

```typescript
interface IntentNode {
  id: string;
  intent: string;                    // 意图描述
  entities: Record<string, any>;      // 提取的实体
  confidence: number;                 // 置信度 0-1
  parentId: string | null;           // 父意图引用
  createdAt: number;                  // 时间戳
  status: 'active' | 'completed' | 'abandoned';
}

interface IntentChain {
  chainId: string;
  nodes: IntentNode[];               // 意图链节点
  currentNodeId: string;             // 当前活跃意图
  crossTopicRefs: string[];          // 跨话题引用
}
```

### 4.2 GoalTree (目标树)

```typescript
interface Goal {
  id: string;
  type: string;                      // goal type
  description: string;
  params: Record<string, any>;
  parentId: string | null;          // 父目标
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  assignedTo: string | null;        // 分配的 Executor
  result?: any;                      // 执行结果
  processLog: ProcessStep[];         // 过程日志
  createdAt: number;
  completedAt?: number;
}

interface GoalTree {
  rootGoalId: string;
  goals: Map<string, Goal>;
  dependencies: Map<string, string[]>; // goalId -> [dependentGoalIds]
}
```

### 4.3 Plan (任务计划)

```typescript
interface Plan {
  planId: string;
  intentChainRef: string;           // 关联的意图链
  executionOrder: string[];          // 执行顺序的 Goal ID 列表
  dependencies: Map<string, string[]>; // 依赖关系
  estimatedCost: number;             // 预估 Token 消耗
  createdAt: number;
}
```

### 4.4 ExecutionStatus & ProcessLog

```typescript
interface ExecutionStatus {
  goalId: string;
  executorId: string;
  status: 'queued' | 'running' | 'waiting' | 'completed' | 'failed';
  progress: number;                  // 0-100
  lastUpdate: number;
}

interface ProcessStep {
  stepId: string;
  goalId: string;
  action: string;
  input: any;
  output?: any;
  timestamp: number;
  agentId: string;
}
```

---

## 5. 状态同步机制

### 5.1 增量状态同步 (Delta Sync) - Mermaid

```mermaid
sequenceDiagram
    participant IA as Intent Agent
    participant PA as Planner Agent
    participant EA as Executor A
    participant EB as Executor B
    participant MA as Monitor Agent
    participant SS as StateStore

    IA->>SS: publish_delta(IntentChain, {new_intent: ...})
    SS-->>PA: notify(IntentChain_changed)
    SS-->>MA: notify(all)

    PA->>SS: publish_delta(GoalTree, {goal_1: ...})
    SS-->>EA: notify(goal_1_assigned)
    SS-->>EB: notify(goal_2_assigned)
    SS-->>MA: notify(all)

    EA->>SS: publish_delta(Status, {goal_1: running})
    EB->>SS: publish_delta(Status, {goal_2: running})
    SS-->>MA: notify(all)

    EA->>SS: publish_delta(Result, {goal_1: completed})
    SS-->>MA: notify(all)

    Note over SS,MA: Monitor aggregates all status changes
    MA->>SS: publish_delta(Summary, {all_goals_status: ...})
```

### 5.2 DeltaUpdate 数据结构

```typescript
interface DeltaUpdate {
  eventId: string;                  // 唯一ID
  timestamp: number;                 // Unix timestamp
  entityType: 'Intent' | 'Goal' | 'Plan' | 'Status' | 'Result';
  entityId: string;                 // 实体ID
  operation: 'create' | 'update' | 'delete';
  changedKeys: string[];            // 变化的字段
  delta: Record<string, any>;        // 变化的部分
  sourceAgent: string;              // 发起更新的Agent
}
```

### 5.3 上下文作用域控制 - Mermaid

```mermaid
graph TD
    subgraph ContextIA["Intent Agent 上下文"]
        Q1["当前 Query"]
        IC1["Intent链 (最多5条)"]
        HS1["历史摘要"]
    end

    subgraph ContextPA["Planner Agent 上下文"]
        IC2["IntentChain"]
        GS["Goal状态"]
        EL["Executor列表"]
    end

    subgraph ContextEA["Executor Agent 上下文"]
        SG["分配的 SubGoal"]
        PL["过程日志 (最近3步)"]
    end

    subgraph ContextMA["Monitor Agent 上下文"]
        SS["所有Goal状态摘要"]
        AE["异常事件"]
    end

    subgraph ContextSA["Synthesizer 上下文"]
        GT["完整 GoalTree"]
        SR["所有SubGoalResults"]
    end

    style ContextIA fill:#e3f2fd
    style ContextPA fill:#fff3e0
    style ContextEA fill:#e8f5e9
    style ContextMA fill:#fce4ec
    style ContextSA fill:#f3e5f5
```

### 5.4 长对话 Token 控制策略

```
每个 Agent 只看到必要上下文：

Intent Agent:     [当前 Query] + [近期 Intent 链(最多5条)] + [压缩的历史摘要]
Planner Agent:    [IntentChain] + [当前 Goal 状态] + [可用 Executor 列表]
Executor Agent:   [分配给自己的 SubGoal] + [必要的过程日志(最近3步)]
Monitor Agent:     [所有 Goal 的 Status 摘要] + [异常事件]
Synthesizer:      [完整 GoalTree] + [所有 SubGoalResults]
```

### 5.3 长对话 Token 控制策略

| 对话阶段 | Token 策略 |
|----------|-----------|
| **0-20 轮** | 全量同步，所有 Agent 看到完整上下文 |
| **20-50 轮** | 启用压缩，Intent 链保留最近 5 条，历史转为摘要 |
| **50 轮+** | 增量同步 + LLM 异步压缩旧上下文 |

---

## 6. StateStore 设计

### 6.1 分层存储 - Mermaid

```mermaid
flowchart TB
    subgraph StateStore["StateStore"]
        direction TB

        subgraph Hot["Hot Storage<br/>(内存/Redis)<br/>最近20轮数据<br/>< 10ms"]
            IG_H[IntentGraph]
            GT_H[GoalTree]
            PL_H[Plan]
            ST_H[Status]
        end

        subgraph Compress["压缩引擎<br/>(异步)"]
            CMP[LLM Summarizer]
        end

        subgraph Cold["Cold Storage<br/>(文件系统/S3)<br/>历史摘要"]
            IG_C[IntentGraph<br/>摘要]
            GT_C[GoalTree<br/>摘要]
        end
    end

    Hot -.->|阈值触发| CMP
    CMP -.->|压缩后| Cold

    style Hot fill:#ffecb3,stroke:#ffb300
    style Cold fill:#cfd8dc,stroke:#90a4ae
    style Compress fill:#e1f5fe,stroke:#03a9f4
```

### 6.2 Context Assembler - Mermaid

```mermaid
flowchart LR
    subgraph Request["Agent Request"]
        A[Agent ID]
        CT[Context Types<br/>Intent / Goal / Result]
    end

    subgraph Assembler["Context Assembler"]
        CA[组装最小上下文]
        CP[注入缓存前缀]
    end

    subgraph Output["LLM Input"]
        STATIC["<static> 缓存前缀"]
        DYNAMIC["动态上下文"]
        FINAL["最终组装结果"]
    end

    A --> CA
    CT --> CA
    CA --> CP
    CP --> FINAL

    DYNAMIC --> FINAL
    STATIC --> FINAL

    style Assembler fill:#e8f5e9
    style Output fill:#fff3e0
```

### 6.3 分层存储 (ASCII)

```
┌─────────────────────────────────────────────────────┐
│                   StateStore                         │
│                                                      │
│  Hot Storage:                                        │
│    • 最近 20 轮的完整数据                            │
│    • 快速读写 (< 10ms)                              │
│    • 内存/Redis                                      │
│                                                      │
│  Cold Storage:                                       │
│    • 更早的历史摘要 (低 Token 快照)                   │
│    • 低频访问                                       │
│    • 文件系统/S3                                     │
│                                                      │
│  压缩触发: 当 Hot Storage > 阈值时，                  │
│          异步压缩最旧数据到 Cold Storage             │
└─────────────────────────────────────────────────────┘
```

### 6.4 Context Assembler (ASCII)

```
每个 Agent 调用前:

1. 声明需要的上下文类型 (Intent / Goal / Result)
2. ContextAssembler 根据声明组装最小上下文
3. 注入 <static> 缓存前缀 (系统指令等)

ContextAssembly {
  agentId: string;
  requestContext: RequestContext;  // 本次请求相关
  cachedContext: string;           // 可复用的缓存前缀
  assembled: string;               // 最终组装结果
  tokenCount: number;
}
```

---

## 7. 执行流水线

### 7.1 并行执行示意 - Mermaid

```mermaid
gantt
    title 多Agent执行流水线
    dateFormat X
    axisFormat %s

    section Intent
    Intent Agent          :active, ia, 0, 1

    section Plan
    Planner Agent         :active, pa, 1, 2

    section Execute
    Executor A            :active, ea, 2, 5
    Executor B            :active, eb, 2, 4
    Executor C            :active, ec, 2, 3

    section Synthesize
    Synthesizer Agent     :active, sa, 5, 6
```

### 7.2 执行流程 - Mermaid

```mermaid
flowchart TB
    subgraph Init["初始化"]
        Q[User Query]
    end

    subgraph Phase1["Phase 1: Intent Recognition"]
        IA[Intent Agent]
        IC[IntentChain]
    end

    subgraph Phase2["Phase 2: Planning"]
        PA[Planner Agent]
        GT[GoalTree]
        PL[Plan]
    end

    subgraph Phase3["Phase 3: Parallel Execution"]
        EA[Executor A]
        EB[Executor B]
        EC[Executor C]
    end

    subgraph Phase4["Phase 4: Synthesis"]
        SA[Synthesizer]
        FR[Final Response]
    end

    Q --> IA
    IA --> IC
    IC --> PA
    PA --> GT
    PA --> PL

    GT --> EA
    GT --> EB
    GT --> EC

    EA -->|等待| SA
    EB -->|等待| SA
    EC -->|等待| SA

    SA --> FR

    style Phase1 fill:#e3f2fd
    style Phase2 fill:#fff3e0
    style Phase3 fill:#e8f5e9
    style Phase4 fill:#f3e5f5
```

### 7.3 异常处理流程 - Mermaid

```mermaid
flowchart TB
    subgraph Normal["正常流程"]
        EA1[Executor 执行]
        ST1[Status: completed]
        SA1[Synthesizer 汇总]
    end

    subgraph Error["异常处理"]
        EA2[Executor 执行]
        ST2[Status: failed]
        MA[Monitor 检测]
        PA[Planner 决策]
        DEC{决策}
        RETRY[重试]
        SKIP[跳过]
        ROLLBACK[回退]
        EA3[重新执行]
    end

    EA2 --> ST2
    ST2 --> MA
    MA --> PA
    PA --> DEC

    DEC -->|可重试| RETRY
    DEC -->|非关键| SKIP
    DEC -->|无法继续| ROLLBACK

    RETRY --> EA3
    SKIP --> SA2[Synthesizer<br/>返回部分结果]
    ROLLBACK --> SA2

    style Error fill:#ffebee
    style DEC fill:#fff3e0
```

### 7.4 并行执行示意 (ASCII)

```
                    User Query
                         │
                         ▼
              ┌─────────────────────┐
              │   Intent Agent (L0) │  ← 单线程，依赖前序结果
              │   ~200-500 tokens   │
              └──────────┬──────────┘
                         │ IntentChain
                         ▼
              ┌─────────────────────┐
              │   Planner Agent      │  ← 单线程
              └──────────┬──────────┘
                         │ Plan + GoalTree
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ┌───────────┐ ┌───────────┐ ┌───────────┐
     │Executor A │ │Executor B │ │Executor C │  ← 三者并行执行
     │(SubGoal 1)│ │(SubGoal 2)│ │(SubGoal 3)│
     └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
           │             │             │
           └─────────────┼─────────────┘
                         ▼
              ┌─────────────────────┐
              │   Synthesizer Agent │  ← 等待所有子结果
              └─────────────────────┘
```

### 7.5 异常处理与重试 (ASCII)

```
Executor 失败:
  1. Monitor 检测到 StatusUpdate (status: 'failed')
  2. Monitor 通知 Planner
  3. Planner 决定: 重试 / 跳过 / 回退
  4. 更新 GoalTree 状态
  5. 重新调度执行

超时处理:
  • 单个 Executor 超时: 标记为 failed，触发重试流程
  • 全局超时: Synthesizer 返回部分结果 + 状态说明
```

---

## 8. 技术选型

| 组件 | 技术选型 | 原因 |
|------|----------|------|
| **Agent 框架** | LangGraph | 状态图定义清晰，支持复杂流程 |
| **状态存储** | Redis + SQLite | 热数据高速访问 + 持久化 |
| **消息队列** | In-Memory Event Bus | 低延迟，减少外部依赖 |
| **LLM 调用** | Anthropic Claude API | 高效上下文处理 |
| **上下文压缩** | LLM 异步摘要 | 保证压缩质量 |

---

## 9. 预期性能指标

| 指标 | 目标值 |
|------|--------|
| 单次 Query Token | 8K-15K |
| 端到端延迟 | < 5s (并行执行) |
| 长对话(100轮) Token | 线性增长，无指数爆炸 |
| 状态同步延迟 | < 50ms |

---

## 10. 里程碑

1. **Phase 1**: 核心框架搭建 (StateStore, Agent 基类)
2. **Phase 2**: 基础流水线 (Intent → Planner → Executor → Synthesizer)
3. **Phase 3**: Monitor 集成 + 状态同步优化
4. **Phase 4**: 长对话支持 + 上下文压缩
5. **Phase 5**: 测试与优化

---

*文档版本: 1.0 | 创建日期: 2026-03-27*
