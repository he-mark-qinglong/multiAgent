# PRD: 智能车载助手 - 聊天交互界面

**版本:** 1.0.0
**日期:** 2026-03-29
**状态:** 草稿

---

## 1. 概述与目标

### 1.1 产品愿景

打造一个专业级的智能车载助手聊天界面，能够实时展示 Agent 推理过程，让用户清晰理解 AI 是如何思考、决策、执行工具的。

### 1.2 核心价值

| 价值点 | 描述 |
|--------|------|
| **透明可解释** | 用户能看到完整的 Think → Action → Result 链路 |
| **实时交互** | 流式输出，即时反馈 |
| **多轮对话** | 支持上下文记忆，自然对话 |
| **跨平台** | 支持 Web、移动端、嵌入式终端 |

---

## 2. 功能需求

### 2.1 核心功能

#### F1: 聊天消息展示
- 用户消息：绿色背景，右对齐
- Agent 消息：蓝色边框，左对齐
- 支持 Markdown 渲染（代码块、列表、表格）
- 消息时间戳显示

#### F2: 推理过程可视化
- **Think 阶段**：显示意图分析、路由决策
- **Action 阶段**：显示工具调用（工具名 + 参数）
- **Observation 阶段**：显示工具执行结果
- **Result 阶段**：显示最终回复

每个阶段用不同颜色和图标区分：
```
💭 Think   →  意图识别 + 路由
🔧 Action  →  工具调用
👁️ Observe →  执行结果
✅ Result  →  最终回复
```

#### F3: 工具执行状态
- 加载动画（工具执行中）
- 成功/失败状态图标
- 结构化数据展示（JSON 格式化）
- 可展开/折叠的详细信息

#### F4: 多轮对话管理
- 对话历史列表
- 上下文记忆可视化
- 会话重置功能
- 对话导出（JSON/Markdown）

#### F5: 自动测试模式
- 预设测试用例库
- 路由正确性验证
- 响应时间监控
- 测试报告生成

### 2.2 用户交互

| 操作 | 行为 |
|------|------|
| 输入消息 | 发送按钮 / Enter 键 |
| 重新生成 | 重新运行推理 |
| 复制结果 | 一键复制 Agent 回复 |
| 反馈 | 👍👎 评价回复质量 |

---

## 3. 技术架构

### 3.1 前后端分离架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue3/React)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ ChatView │  │MessageBox│  │ReasonView│  │TestRunner│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       └──────────────┴──────────────┴──────────────┘       │
│                          │                                  │
│                    ┌─────┴─────┐                           │
│                    │  Store    │  (Pinia / Zustand)        │
│                    └─────┬─────┘                           │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────┼──────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ ChatAPI  │  │ ToolExec │  │ Agent    │  │ Session  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 MVC / MVVM 模式

#### Model 层
- `Message`: 消息数据结构
- `Conversation`: 会话数据结构
- `ReasoningStep`: 推理步骤数据结构
- `ToolResult`: 工具执行结果

#### View 层
- `ChatView`: 主聊天界面
- `MessageBubble`: 消息气泡组件
- `ReasoningPanel`: 推理过程面板
- `TestRunner`: 测试运行器

#### ViewModel 层
- `ChatViewModel`: 聊天逻辑（发送消息、接收流式响应）
- `ReasoningViewModel`: 推理过程逻辑（步骤解析、状态管理）
- `SessionViewModel`: 会话管理（历史、重置、导出）

### 3.3 API 设计

#### POST /api/chat
```json
// Request
{
  "message": "开空调，24度",
  "session_id": "uuid-xxx",
  "stream": true
}

// Response (Server-Sent Events)
event: think
data: {"step": "路由到 climate"}

event: action
data: {"tool": "climate_control", "params": {"action": "turn_on", "value": 24}}

event: observation
data: {"success": true, "state": {...}}

event: result
data: {"content": "✅ 已开启空调...", "done": true}
```

#### GET /api/sessions/{id}/history
```json
{
  "session_id": "uuid-xxx",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "agent", "content": "...", "reasoning": [...], "timestamp": "..."}
  ]
}
```

---

## 4. 数据模型

### 4.1 消息模型

```typescript
interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: number;
  reasoning?: ReasoningStep[];
  toolCall?: {
    name: string;
    params: Record<string, any>;
    result?: ToolResult;
  };
  status: 'pending' | 'streaming' | 'done' | 'error';
}

interface ReasoningStep {
  type: 'think' | 'action' | 'observation' | 'result';
  content: string;
  timestamp: number;
}

interface ToolResult {
  success: boolean;
  state: Record<string, any>;
  description: string;
  error?: string;
}
```

---

## 5. 验收标准

### 5.1 功能验收

| ID | 标准 | 验证方法 |
|----|------|----------|
| AC1 | 消息发送后 100ms 内显示 Thinking 状态 | 目视验证 |
| AC2 | 工具调用显示完整参数 JSON | 检查渲染输出 |
| AC3 | 多轮对话上下文正确传递 | 连续 5 轮测试 |
| AC4 | 流式输出无明显卡顿 | 计时验证 |
| AC5 | 自动化测试覆盖率 100% | CI 测试通过 |

### 5.2 性能指标

| 指标 | 目标值 |
|------|--------|
| 首屏加载 | < 1s |
| 消息响应延迟 | < 200ms (不含工具执行) |
| 推理过程渲染 | 60fps |
| 内存占用 | < 200MB |

---

## 6. 项目结构（独立仓库）

```
car-assistant-ui/
├── frontend/                    # Vue3 / React 前端
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── views/              # 页面视图
│   │   ├── viewmodels/         # MVVM ViewModels
│   │   ├── models/             # 数据模型
│   │   ├── stores/             # 状态管理
│   │   ├── services/           # API 服务
│   │   └── utils/              # 工具函数
│   └── tests/                  # 前端测试
│
├── backend/                    # FastAPI 后端
│   ├── api/                    # API 路由
│   ├── agents/                 # Agent 实现
│   ├── tools/                  # 工具定义
│   ├── models/                 # Pydantic 模型
│   └── tests/                  # 后端测试
│
├── docs/                       # 文档
│   ├── PRD.md
│   ├── API.md
│   └── DESIGN.md
│
└── docker-compose.yml          # 本地开发环境
```

---

## 7. 开发计划

### Phase 1: 基础框架
- [ ] 搭建前端项目 (Vue3 + Vite)
- [ ] 搭建后端项目 (FastAPI)
- [ ] 实现基础的 WebSocket 通信
- [ ] 基础聊天界面

### Phase 2: 推理可视化
- [ ] 推理步骤数据模型
- [ ] 推理面板组件
- [ ] SSE 流式响应
- [ ] 工具调用展示

### Phase 3: 测试自动化
- [ ] 测试用例管理
- [ ] 自动化测试运行器
- [ ] 测试报告生成

---

## 8. 依赖关系

```toml
# 前端
vue = "^3.4"
pinia = "^2.1"
vite = "^5.0"

# 后端
fastapi = "^0.109"
uvicorn = "^0.27"
pydantic = "^2.5"

# 共享
# 这边的 Mock Tools 会迁移到 backend/tools/
```
