---
marp: true
theme: uncover
paginate: true
backgroundColor: #0f172a
color: #f8fafc
style: |
  section {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  }
  section.title {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  }
  h1 {
    color: #f1f5f9;
    border-bottom: 3px solid #6366f1;
    padding-bottom: 10px;
    padding-top: 10px;
    font-size: 2.2em;
    margin-bottom: 0.5em;
  }
  h2 {
    color: #c4b5fd;
    font-size: 1.5em;
    margin-top: 0.5em;
    margin-bottom: 0.3em;
  }
  strong {
    color: #fbbf24;
  }
  em {
    color: #a5b4fc;
  }
  code {
    background: #1e293b;
    border-radius: 8px;
    padding: 4px 10px;
    color: #fbbf24;
  }
  pre {
    background: #1e293b !important;
    border-radius: 12px;
    border: 1px solid #334155;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }
  pre code {
    background: transparent;
    padding: 0;
    color: #e2e8f0;
  }
  blockquote {
    background: linear-gradient(90deg, rgba(99,102,241,0.2) 0%, transparent 100%);
    border-left: 4px solid #6366f1;
    padding: 20px 30px;
    border-radius: 0 12px 12px 0;
  }
  table {
    background: rgba(30,41,59,0.8);
    border-radius: 12px;
  }
  th {
    background: #6366f1 !important;
    color: white !important;
  }
  td {
    background: rgba(30,41,59,0.6) !important;
  }
  footer {
    color: #64748b;
    font-size: 0.6em;
  }
  section ul li::marker {
    color: #6366f1;
  }
  section ol li::marker {
    color: #6366f1;
  }
---

<!-- _class: title -->

# 多Agent系统开发

## 基于大模型的协作智能体架构

---

## 什么是多Agent系统？

### 像一个分工明确的团队

```
用户请求：帮我调研LangGraph最新发展，整理成报告

团队分工：

    🎯 Intent Agent
    "理解用户想要什么"
         ↓
    📋 Planner Agent
    "制定执行计划"
         ↓
    ┌────────────┬────────────┐
    ↓            ↓
⚙️ Executor A  ⚙️ Executor B
"搜索论文"    "搜索博客"
    ↓            ↓
    └────────────┬────────────┘
                 ↓
    👁️ Monitor Agent
    "监督进度，处理问题"
                 ↓
    📝 Synthesizer
    "汇总成报告"
```

---

## 核心流程

### Intent → Task → Execute → Monitor → Result

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  理解    │───►│  规划   │───►│  执行   │───►│  监督     │───►│  汇总   │
│ Intent  │    │  Task   │    │ Execute │    │ Monitor │    │ Result  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

### 完整架构图

```
用户输入
    ↓
PipelineStateGraph (LangGraph编排)
    ↓
IntentAgent → PlannerAgent → ExecutorAgent → SynthesizerAgent
(MiniMax LLM)  (MiniMax LLM)  (ToolRegistry)    ↓
                                           最终响应
```

---

## 一、意图识别 (Intent Recognition)

### 理解用户真正想要什么

**生活中的比喻**：前台接待员

```
顾客： "我想查一下我的保险什么时候到期"

接待员理解：
├── 意图：查询保单
├── 客户ID：12345
├── 查询类型：保单到期日
└── 紧迫程度：普通
```

**技术实现**：IntentAgent 内部集成 MiniMax LLM，支持复合意图提取（例如"打开空调、导航去机场、播放音乐"可分解为3个并行意图）。

---

## 意图缓存 (Intent Cache)

### 避免重复理解相同问题

```
问题：同样的意图需要重复理解吗？

答案：不需要！缓存起来

┌────────────────────────────────────────┐
│              意图缓存                    │
│                                         │
│  "帮我调研LangGraph" → [意图链A]          │
│  "调研LangGraph"      → [意图链A] ← 命中！│
│  "搜索LangGraph"      → [意图链B]        │
│                                         │
└────────────────────────────────────────┘

好处：加快响应、节省成本、保持一致
```

---

## 二、任务编排 (Task Planning)

### 把大任务分解成小任务

```
大任务："举办一场产品发布会"

分解为：
├── 任务1：确定发布会时间和地点
├── 任务2：准备演讲稿
├── 任务3：制作PPT
├── 任务4：邀请媒体
└── 任务5：现场执行

依赖关系：
任务5依赖任务1、2、3、4全部完成
```

---

## 三、任务执行 (Task Execution)

### 执行者真正干活

```
         Planner分配任务
              │
    ┌─────────┴─────────┐
    ▼                   ▼
⚙️ Executor A       ⚙️ Executor B
搜索论文             搜索博客
    │                   │
    └─────────┬─────────┘
              ▼
        Monitor汇总结果
```

---

### Query：智能查询理解

```
┌─────────────────────────────────────────────┐
│  Query Agent 的职责                          │
│                                             │
│  用户说："帮我看看那个项目的进度"                │
│                                             │
│  Query理解：                                 │
│  ├── 意图：查询项目进度                        │
│  ├── 项目标识：需要从上下文/记忆中获取           │
│  └── 时间范围：本周/本月                       │
│                                             │
│  可能触发：                                   │
│  ├── 记忆检索：查找"那个项目"是哪个              │
│  ├── 工具调用：查询项目管理API                  │
│  └── 等待用户确认：如果项目标识模糊              │
└─────────────────────────────────────────────┘
```

---

## Tool System

### MCP (Model Context Protocol)

MCP 是标准的工具定义协议：

```
MCP 工具结构：
├── description  - 工具功能描述
├── parameters   - 输入参数定义（JSON Schema）
├── returns      - 输出格式定义
└── example     - 使用示例
```

**示例：天气查询工具**

```
get_weather(location, unit, forecast_days)
get_traffic(出发地, 目的地)
search_files(关键词, 文件类型)
```

---

### Skill：可复用工具能力包

```
Skill 特点：
├── 独立命名 - 每个Skill有唯一标识
├── 模块化设计 - 可组合使用
├── 按需加载 - 不影响启动速度
└── 版本管理 - 支持迭代升级
```

**示例：**

```
code_executor  - 代码执行
file_manager   - 文件管理
api_caller     - API调用
```

---

### 工具注册流程

```
prompts/tools/
├── mcp/           ← MCP工具定义
│   ├── weather.md
│   └── traffic.md
└── skills/        ← Skill定义
    ├── code_executor.md
    └── file_manager.md

        ↓ Tool Registry 自动扫描注册

Agent 调用时：
Agent ──► Tool Registry ──► 匹配MCP/Skill ──► 执行
```

---

### ReAct模式：思考与行动循环

```
┌─────────────────────────────────────────────┐
│         ReAct = Thought → Action → ...      │
│                                             │
│  Thought: "用户想知道天气，我需要调用搜索"       │
│       ↓                                     │
│  Action: search_weather(location="北京")     │
│       ↓                                     │
│  Observation: "北京今天晴，25度"              │
│       ↓                                     │
│  Thought: "现在我有答案了，可以回复用户"         │
│       ↓                                     │
│  Final Answer: "北京今天天气晴朗，气温25度"     │
└─────────────────────────────────────────────┘

Agent就是这样不断循环：思考 → 行动 → 观察 → 再思考
```

---

## 四、监控监督 (Monitor)

### 全局视野，处理异常

```
Monitor Agent职责：
├── 接收所有执行事件
├── 跟踪每个Goal的状态
├── 检测失败并触发重试
├── 连续失败3次 → 熔断
└── 汇报整体进度
```

---

## 熔断机制

```
正常状态：
执行者A ✓  完成
执行者B ✓  完成
执行者C ✗  失败 → 重试 → 失败 → 重试 → 失败

连续3次失败：

⚠️ 熔断触发！
┌─────────────────────────────────────┐
│  🔴 CIRCUIT OPEN                    │
│                                     │
│  停止所有执行                         │
│  通知用户：系统繁忙，请稍后再试          │
│  60秒后自动恢复                       │
└─────────────────────────────────────┘
```

---

## 五、结果汇总 (Synthesis)

### 把分散的结果整理成完整输出

```
收集：
├── 会议记录A：产品功能讨论
├── 会议记录B：技术方案讨论
└── 会议记录C：时间安排讨论

整理：
└── 统一格式的会议纪要.pdf
```

---

## Session：会话管理

### 理解多轮对话的上下文

**生活中的比喻**：记住之前的对话

```
第一轮：
用户： LangGraph是什么？
Agent： 它是一个...

第二轮：
用户： 它和LangChain什么关系？
Agent： 让我解释一下它们的关系...

如果没有Session记忆：
Agent： "它"指的是什么？

有Session记忆：
Agent： "它"指的是LangGraph，...
```

---

## Session的结构

### 记录会话的完整上下文

```
┌─────────────────────────────────────────┐
│              Session                     │
│                                          │
│  session_id: "sess_001"                  │
│                                          │
│  messages: [                             │
│    {role: "user", content: "LangGraph是..."},
│    {role: "assistant", content: "它是..."},
│    {role: "user", content: "和LangChain关系?"},
│    {role: "assistant", content: "它们关系是..."}
│  ]                                       │
│                                          │
│  metadata: {                             │
│    created_at: "2024-01-01",             │
│    last_active: "2024-01-01 10:30",      │
│    user_id: "user_123"                   │
│  }                                       │
└─────────────────────────────────────────┘
```

---

## 记忆系统：Pointer理念

### 像指针一样高效引用

**问题**：完整记忆太占上下文空间？

```
传统方式：
┌─────────────────────────────────────────┐
│ 记忆1：用户喜欢详细格式的报告                │
│ 记忆2：用户之前做过LangChain项目            │
│ 记忆3：用户偏好Markdown格式                │
│ ...                                     │
│ 记忆N：...                               │
└─────────────────────────────────────────┘
    ↓
全部加载到上下文？ → 上下文爆炸！
```

---

## Pointer记忆：按需加载

```
┌─────────────────────────────────────────┐
│            Pointer 理念                   │
│                                          │
│  记忆存储（外部）：                         │
│  memory_001: {                           │
│    summary: "用户偏好详细格式Markdown"      │ ← 只有摘要
│    full: "用户之前做过LangChain项目..."     │ ← 完整内容
│  }                                       │
│                                          │
│  上下文窗口：                              │
│  [用户问题] + [Pointer: memory_001]       │ ← 只占一个指针
│                                          │
│  需要时：解引用 → 加载完整内容               │
└─────────────────────────────────────────┘
```

---

## Pointer vs 完整加载

### 对比

```
┌─────────────────────────────────────────┐
│         完整加载（传统方式）               │
├─────────────────────────────────────────┤
│                                         │
│  上下文：[                                │
│    用户问题: "...",                       │
│    记忆1: "用户喜欢详细格式...",            │
│    记忆2: "用户之前做过...",               │
│    记忆3: "用户偏好Markdown...",          │
│    ...                                  │
│    记忆100: "..."                        │
│  ]                                       │
│                                          │
│  问题：上下文窗口很快填满！                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Pointer加载（我们的方式）          │
├─────────────────────────────────────────┤
│                                         │
│  上下文：                                │
│  [用户问题] +                            │
│  [Pointer: memory_001] ← 只占1个位置     │
│  [Pointer: memory_003] ← 只占1个位置     │
│                                        │
│  按需解引用：                            │
│  memory_001 → "用户喜欢详细格式Markdown"  │
│                                        │
│  好处：上下文高效利用，支持大量记忆          │
└─────────────────────────────────────────┘
```

---

## 记忆的层级结构

```
┌─────────────────────────────────────────┐
│            记忆层级                       │
│                                          │
│  🔷 Working Memory (工作记忆)             │
│     当前会话直接可用，容量有限               │
│     └── 正在处理的任务、当前用户问题         │
│                                         │
│  🔷 Session Memory (会话记忆)             │
│     本次会话内共享                         │
│     └── 对话历史、已完成的步骤              │
│                                         │
│  🔷 Long-term Memory (长期记忆)          │
│     跨会话持久化，需要时加载                │
│     └── 用户偏好、历史项目、常用工具         │
│                                         │
│     └── Pointer方式：按需加载完整内容       │
└─────────────────────────────────────────┘
```

---

## 上下文中的Pointer

### 如何工作

```
Step 1: 用户提问
┌─────────────────────────────────────────┐
│ 用户： "之前那个项目的技术栈是什么？"         │
└─────────────────────────────────────────┘

Step 2: 检索相关记忆
┌─────────────────────────────────────────┐
│ 找到相关记忆: project_001                 │
│ 摘要: "2023年电商项目，使用Vue+Django"     │
└─────────────────────────────────────────┘

Step 3: Pointer加入上下文
┌─────────────────────────────────────────┐
│ 上下文: [                                │
│   用户问题,                              │
│   Pointer(project_001) ← 只占一个位置     │
│ ]                                       │
└─────────────────────────────────────────┘

Step 4: 需要时解引用
┌─────────────────────────────────────────┐
│ 解引用 → 完整加载:                        │
│ "项目名称: 电商平台                        │
│  技术栈: Vue3 + Django + PostgreSQL      │
│  时间: 2023年Q2"                         │
└─────────────────────────────────────────┘
```

---

## 上下文操作集

### 上下文操作类型

```
ADD      - 添加内容    DELETE   - 移除内容
MERGE    - 合并片段    SLICE    - 切片提取
RETRIEVE - 检索查找    MODIFY   - 修改内容
REORDER  - 重排序      CACHE    - 缓存暂存
SPLIT    - 分割片段    CHECK    - 检查验证
SUMMARIZE- 压缩摘要
```

---

### 上下文压缩

**触发：** 使用率 > 80%

**策略：** 保留关键实体 + 摘要20%

```
100轮对话 → [摘要]
工具结果 → [已执行]
```

---

### 上下文输入来源

四大输入来源：

1. **用户输入** - 对话、文件、API
2. **记忆系统** - Session/Long-term Memory
3. **系统提示词** - Agent角色定义
4. **工具结果** - 搜索、API、代码执行

### 工具上下文同步

工具调用 → 添加调用记录
工具完成 → 添加结果

**工具删除时（待实现）：**
- 调用记录 → 删除
- 结果 → 替换为"[已清除]"

### 内置操作 vs 自定义操作

| 内置 | 自定义 |
|------|--------|
| SUMM, RET, REM | SPL, SLC, MRG |
| CHK, CAC | MOD, RE |

---

## Agent层级总结

```
XL层: Monitor
├── 全局监督
├── 熔断保护
└── 异常处理

L2+层: Executor
├── 真正执行任务
├── 可并行运行
└── 支持人工审批

L1层: Planner / Synthesizer
├── 规划任务分解
└── 汇总结果输出

L0层: Intent Agent
└── 理解用户意图
```

---

## EventBus：Agent间通信

### 发布/订阅模式

```
         ┌─────────────────┐
         │    EventBus     │
         │   (事件总线)     │
         └────────┬────────┘
                  │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
  goal_completed needs_approval state_update
```

### 支持多种消息中间件

```
本地模式：                          分布式模式：
┌─────────────┐                    ┌─────────────┐
│  内存EventBus│  ← 简单场景         │    Kafka    │  ← 高吞吐
└─────────────┘                    └─────────────┘
                                        │
┌─────────────┐                    ┌─────────────┐
│   Redis     │  ← 需要持久化        │   RabbitMQ  │  ← 可靠性
└─────────────┘                    └─────────────┘

好处：水平扩展、故障恢复、顺序保证
```

### DeltaUpdate：状态变更同步

EventBus传输的具体数据模型：

```
DeltaUpdate 包含：
├── entity_type - 实体类型（INTENT / GOAL / PLAN / STATUS）
├── entity_id - 实体唯一标识
├── operation - 操作类型（create / update / delete）
├── changed_keys - 变更的字段列表
├── delta - 变更的数据内容
└── source_agent - 触发变更的Agent

用途：
- 外部系统监听状态变化
- 跨Agent状态同步
- 审计日志记录
```

---

## 中断机制 (HITL)

### Human-in-the-Loop

```
⚠️ 危险操作需要人工确认

• 删除文件
• 发送邮件/消息
• 执行代码
• 访问敏感API
• 修改重要配置

流程：
执行中... → 检测需要审批 → 暂停等待 → 用户确认 → 继续/终止
```

### Interrupt扩展：多种中断类型

```
┌─────────────────────────────────────────────┐
│              Interrupt 类型                  │
│                                             │
│  🔴 强制中断 (FORCE_STOP)                    │
│     立即终止所有操作，用户紧急叫停               │
│                                             │
│  🟡 审批中断 (NEEDS_APPROVAL)                │
│     等待用户确认后再继续                       │
│                                             │
│  🔵 查询中断 (CLARIFICATION)                  │
│     用户输入不明确，需要补充信息                 │
│     例如："那个项目"是哪个？                    │
│                                             │
│  🟢 超时中断 (TIMEOUT)                       │
│     长时间无响应，自动触发重试或跳过             │
└─────────────────────────────────────────────┘
```

---

## 流式通信

### SSE (Server-Sent Events)

```
非流式：等公交车
─────────────────────
请求 ──等待...等待...完成 ──► 响应

流式：实时推送
─────────────────────
请求 ─────────────────────►
        ◄── 思考中...
        ◄── 搜索论文...
        ◄── 找到10篇
        ◄── 最终报告
```

### 流式协议：完整的事件流

```
┌─────────────────────────────────────────────┐
│           SSE 事件类型                       │
│                                             │
│  event: think                               │
│  data: "我需要先搜索相关信息..."               │
│                                             │
│  event: action                              │
│  data: {"tool": "search", "input": "..."}   │
│                                             │
│  event: observation                         │
│  data: {"result": "找到20条相关结果"}         │
│                                             │
│  event: result                              │
│  data: {"content": "最终报告内容..."}         │
│                                             │
│  event: done                                │
│  data: {"finished": true}                   │
└─────────────────────────────────────────────┘

与 polling 相比：延迟更低、带宽更省、体验更流畅
```

### LangGraph StateGraph：核心编排框架

项目使用 LangGraph StateGraph 作为核心编排架构：

```
PipelineStateGraph 架构：

START → intent → planner → executor
                              │
                    [needs_approval?]
                       ↓ yes    ↓ no
                  human_approval → synthesizer → END

关键组件：
├── StateGraph - 状态流图定义
├── Checkpointer - 状态持久化（中断恢复）
├── InMemoryStore - 内存存储
└── interrupt() - 中断点暂停执行
```

**Checkpointer 机制：**
- 保存中断点状态
- 支持中断恢复后继续执行
- 实现真正的暂停/恢复交互

### stream() 输出特性

**重要设计原则：stream() 输出的是最终结构化结果，而非逐token输出**

```
ReAct 循环完全在内部运行，保证一致性后再输出：

外部看到的：
  stream() → {type: "result", data: {final_response, intent_chain, execution_results}}

内部实际发生的（外部不可见）：
  think → act → observe → think → act → ... → 最终结果
```

这样设计的好处：
- 保持 ReAct 内部推理的一致性
- 避免中间步骤暴露导致的混乱
- 输出的是完整、结构化的结果

### Command(resume) 机制

HITL 审批后，用 Command 恢复执行：

```
用户审批：
  pipeline.request_approval(thread_id, action, details)
  # ... 等待用户操作 ...

用户确认后：
  pipeline.submit_approval(thread_id, approved=True, reason="确认执行")

LangGraph 内部：
  Command(resume={"approved": True, "reason": "确认执行"})
  → 中断点恢复，继续执行后续流程
```

### LangSmith 集成

可选的 tracing 组件，用于调试和监控：

```
开启方式：
  CollaborationPipeline(langsmith_project="my-project", enable_tracing=True)

追踪内容：
  - 每个节点的输入/输出
  - ReAct 循环的每次 think → act
  - 执行时间、token 消耗
  - Agent 间的状态流转
```

---

## 项目结构

```
multiAgent/
├── agents/              ← Agent实现
│   ├── intent_agent.py     ← L0: 意图识别 (集成MiniMax LLM)
│   ├── planner_agent.py    ← L1: 任务规划
│   ├── executor_agent.py   ← L2+: 任务执行 (集成ToolRegistry)
│   ├── synthesizer_agent.py ← L1: 结果汇总
│   └── monitor_agent.py     ← XL: 监控
│
├── core/              ← 核心组件
│   ├── models.py            ← 数据模型
│   ├── event_bus.py         ← 事件总线
│   ├── minimax_client.py    ← MiniMax LLM客户端
│   ├── agent_factory.py     ← Agent工厂
│   └── langgraph_integration.py ← LangGraph编排
│
├── pipelines/              ← 执行流水线
│   └── collaboration_pipeline.py ← 多Agent协作流水线
│
├── backend/           ← FastAPI服务入口
│   └── main.py
│
├── tools/              ← 演示脚本
│   ├── llm_chat_cli.py     ← CLI对话演示
│   └── demo_multi_agent.py ← 多Agent并行任务演示
│
└── tests/              ← 测试
    ├── contracts/           ← API契约测试
    ├── e2e/                 ← 端到端测试
    └── perf/                ← 性能测试
```

---

## 技能迁移对照

```
传统开发       →    Agent开发
───────────────────────────────
API路由       →    Intent识别 / Query
任务队列      →    Task编排
函数调用      →    Tool System + ReAct
全局异常      →    Monitor监控 / Interrupt
结果汇总      →    Synthesizer
Redis缓存     →    Intent Cache
同步/异步     →    流式SSE
会话管理      →    Session
内存指针      →    Memory Pointer
消息中间件    →    EventBus (Kafka/Redis)
前端轮询      →    Streaming SSE
人工审批      →    HITL Interrupt
```

---

## 运行示例

```
# 1. 启动API服务
$ cd multiAgent
$ python backend/main.py

# 2. 运行多Agent并行任务演示（推荐）
$ python tools/demo_multi_agent.py

# 3. CLI对话演示
$ python tools/llm_chat_cli.py

# 4. 多轮对话演示
$ python tests/demo_multi_round.py
```

### 并行任务效果示例

```
用户输入：打开空调、导航去机场、播放音乐

分解结果：3个并行任务
├── [climate_control] 空调控制
├── [navigation] 导航到机场
└── [music_control] 播放音乐

执行结果：
✅ 已开启空调，温度24°C，auto模式
🧭 已规划前往「机场」的路线，预计45分钟
🎵 正在播放「七里香」
```

---

## 总结

### 完整流程

```
    ┌─────────────────────────────────────────────┐
    │                                              │
    │  🎯 Intent ──► 📋 Planner ──► ⚙️ Executor    │
    │      │              │               │        │
    │      │              │         ┌────┴────┐    │
    │      │              │         ▼         ▼    │
    │      │              │      执行A    执行B     │
    │      │              │         └────┬────┘    │
    │      │              │              │         │
    │      │              │    👁️ Monitor          │
    │      │              │              │         │
    │      │              │    📝 Synthesizer      │
    │      │              │              │         │
    └─────────────────────────────────────────────┘
```

### 核心要点

1. **Intent** = 理解用户真正想要什么
2. **Query** = 智能解析模糊/不完整的查询
3. **Plan** = 把大任务分解成可执行的小任务
4. **Tool System** = Agent的能力扩展（搜索、代码、文件等）
5. **ReAct** = 思考→行动→观察→循环
6. **Execute** = 并行执行，互不干扰
7. **Interrupt** = 多层次中断机制（审批、澄清、强制）
8. **Monitor** = 全局监督，熔断保护
9. **Synthesize** = 汇总结果，生成报告
10. **Session** = 管理多轮对话的上下文
11. **Memory Pointer** = 高效利用上下文空间
12. **EventBus** = 支持本地内存/Kafka/Redis等消息中间件
13. **Streaming SSE** = 实时推送事件流

---

<!-- _class: title -->

# 谢谢！

## 欢迎提问
