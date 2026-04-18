# ADR-016: Dynamic Tool Binding 架构决策

## Status
Accepted

## Context
需要将 ExecutorAgent 中硬编码的 goal_type → tool/action 映射转换为动态配置。

## Decision

### 1. HYBRID 执行模式
```
ExecutorAgent._execute_goal()
  ├─ 1. Try dynamic binding (from ~/.multiagent/bindings/*.json)
  │     └─ Success → return
  └─ 2. Fall back to tool-layer helper
        └─ backend.tools.get_tool_and_action_for_goal() → registry.call_tool()
```

### 2. 三层职责分离
| Layer | 职责 | 示例 |
|-------|------|------|
| **Agent** | 编排逻辑，不含映射 | ExecutorAgent |
| **Binding** | 动态配置 (JSON) | ~/.multiagent/bindings/*.json |
| **Tool** | 硬编码fallback映射 | backend/tools.py |

### 3. 核心组件
- `core/binding_schema.py` - BindingConfig 数据模型
- `core/binding_executor.py` - 执行引擎 (retry/fallback)
- `core/binding_manager.py` - 配置加载和执行编排
- `backend/tools.py` - 硬编码 fallback (GOAL_TYPE_TO_TOOL_ACTION)

### 4. BindingConfig Schema
```json
{
  "goal_type": "climate_control",
  "description": "空调控制",
  "primary": {
    "tool": "climate_control",
    "action": "control",
    "params": {...},
    "retry": {...}
  },
  "secondary": {...},
  "fallback": {...}
}
```

## Consequences
- 新增 goal_type 只需创建 JSON 配置文件，无需修改代码
- 硬编码 fallback 确保动态配置失败时有兜底
- CLI 工具支持: list, show, validate, reload

## Migration
- 已迁移: climate_control, navigation, weather, music_control, news, vehicle_status, door_control, emergency
- 待迁移: legal_*, medical_*, emotional_*, finance_*, learning_*, travel_*
