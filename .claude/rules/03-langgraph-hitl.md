# LangGraph HITL 规范

**版本: 1.0 | 2026-03-27**

---

## 1. 核心设计原则

```
ReAct 循环 (内部) → 结构化输出 → Streaming (外层展示)
```

| 原则 | 说明 |
|------|------|
| **ReAct 完整性** | ReAct 循环必须完整执行，不可中途打断（除非 HITL） |
| **Streaming 分离** | stream() 只输出最终结构化结果，不输出中间步骤 |
| **HITL 中断** | interrupt() 用于需要人工审批的操作 |

---

## 2. LangGraph 状态持久化

### 2.1 Checkpointer
```
✅ InMemorySaver: 开发环境
✅ PostgresSaver: 生产环境

每个对话使用 thread_id 隔离状态
```

### 2.2 状态持久化流程
```
1. Agent 状态更新 → StateGraph 更新
2. Checkpointer 自动保存 checkpoint
3. 中断时保存完整状态
4. resume 时恢复状态继续执行
```

---

## 3. Human-in-the-Loop (HITL)

### 3.1 中断触发条件
```
✅ 执行危险操作前 (如删除、修改)
✅ 需要人工确认的决策点
✅ 外部系统回调
❌ 常规推理过程
```

### 3.2 中断流程
```
executor_node 检测 needs_approval=True
    ↓
interrupt("请确认操作...")
    ↓
状态保存到 Checkpointer
    ↓
返回待审批信息给客户端
    ↓
客户端展示审批 UI
    ↓
用户审批 (approve/reject)
    ↓
submit_approval() → Command(resume={...})
    ↓
executor_node 恢复执行
```

### 3.3 HumanApprovalManager 接口
```python
class HumanApprovalManager:
    def request_approval(
        self,
        thread_id: str,
        action: str,
        details: str,
    ) -> str:  # 返回 approval_id

    def submit_approval(
        self,
        thread_id: str,
        approved: bool,
        reason: str = "",
    ) -> dict:  # 触发 pipeline resume

    def get_pending(self, thread_id: str) -> dict | None:
        """获取待审批项"""
```

---

## 4. Streaming 设计

### 4.1 stream() 输出规范
```python
# ✅ 正确: 输出结构化结果
def stream(self, query):
    result = self._run_full_react_cycle(query)
    yield {"type": "result", "data": result}

# ❌ 错误: 输出中间步骤（破坏 ReAct 一致性）
def stream(self, query):
    for step in self.react_steps:  # 不要这样！
        yield step  # 中间步骤不可用于格式校验
```

### 4.2 流式输出类型
| type | 用途 |
|------|------|
| `result` | 最终结构化结果 |
| `progress` | 执行进度更新 |
| `approval_required` | 需要人工审批 |
| `error` | 错误信息 |
| `interrupt` | 中断等待 |

---

## 5. 与 DeltaUpdate 整合

### 5.1 职责分离
```
LangGraph StateGraph:
  - Agent 内部编排
  - Checkpointer 持久化
  - ReAct 循环控制

DeltaUpdate + EventBus:
  - Agent 间外部通知
  - Monitor 跨 Agent 状态监控
  - 外部系统集成
```

### 5.2 状态更新流程
```
Agent 状态变化
    ↓
LangGraph State 更新 + Checkpointer 保存
    ↓
发布 DeltaUpdate 到 EventBus
    ↓
Monitor 订阅并处理
    ↓
其他 Agent 收到通知（如需要）
```

---

## 6. 错误处理

### 6.1 中断后超时
```
超时时间: 30 分钟 (可配置)
超时后: 任务自动标记为 cancelled
```

### 6.2 拒绝审批后
```
状态: needs_approval = False
元数据: {interrupted: True, reason: "用户拒绝"}
继续执行 synthesizer_node 生成拒绝说明
```
