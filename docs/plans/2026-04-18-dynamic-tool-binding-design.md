# Dynamic Tool Binding 设计方案

**版本:** v1.0
**日期:** 2026-04-18
**状态:** 待审核

---

## 1. 概述

### 1.1 目标

将 `agents/executor_agent.py` 中的硬编码 `goal_type → tool/action` 映射改为**完全动态的 JSON 配置绑定**，实现：

- 新增工具无需修改代码
- 支持条件逻辑和降级策略
- 支持错误处理和重试机制
- 配置可热更新

### 1.2 当前问题

```python
# executor_agent.py - 硬编码的 if-elif 链 (30+ 分支)
if goal_type == "climate_control":
    return registry.call_tool("climate_control", "control", **params)
elif goal_type == "navigation":
    return registry.call_tool("navigation", "navigate", ...)
elif goal_type == "music_control":
    return registry.call_tool("music_control", "play")
# ... 30+ 个硬编码分支
```

**问题：**
- 每新增一个工具需要修改代码
- 条件逻辑嵌套在 if-elif 中，难以维护
- 无法支持降级策略
- 无法热更新

### 1.3 收益

| 收益 | 说明 |
|------|------|
| 无需修改代码 | 新增工具只需添加 JSON 配置文件 |
| 条件逻辑外置 | 条件表达式在 JSON 中声明式定义 |
| 降级策略 | 支持 primary/secondary 目标链式执行 |
| 热更新 | 配置文件可实时修改生效 |
| 可观测性 | 所有 binding 配置可审计 |

---

## 2. 配置存储

### 2.1 目录结构

```
~/.multiagent/tools/
├── _index.json              # 索引 + 元数据
├── _schema.json             # Schema 定义
├── vehicle/                 # 车载控制类
│   ├── climate_control.json
│   ├── navigation.json
│   ├── music_control.json
│   ├── vehicle_status.json
│   ├── door_control.json
│   └── emergency.json
├── advisory/                # 咨询类
│   ├── legal/
│   │   ├── contract_review.json
│   │   ├── rights_protection.json
│   │   └── compliance_check.json
│   ├── medical/
│   │   ├── symptom_analysis.json
│   │   ├── disease_info.json
│   │   └── hospital_recommend.json
│   ├── emotional/
│   │   ├── emotion_listen.json
│   │   ├── relationship_consult.json
│   │   ├── family_communication.json
│   │   ├── social_advice.json
│   │   └── self_discovery.json
│   ├── finance/
│   │   ├── investment_analysis.json
│   │   ├── budget_planning.json
│   │   ├── tax_consult.json
│   │   └── retirement_plan.json
│   └── learning/
│       ├── study_plan.json
│       ├── skill_learning.json
│       ├── exam_prepare.json
│       └── time_management.json
└── travel/                  # 旅行类
    ├── trip_plan.json
    ├── hotel_book.json
    ├── visa_consult.json
    └── spot_recommend.json
```

### 2.2 文件命名

**规则：** `{goal_type}.json`

**示例：**
- `climate_control.json` → goal_type: "climate_control"
- `legal_contract_review.json` → goal_type: "legal_contract_review"

### 2.3 索引文件 (_index.json)

```json
{
  "version": "1.0",
  "last_updated": "2026-04-18T08:00:00Z",
  "bindings": [
    {
      "goal_type": "climate_control",
      "file": "vehicle/climate_control.json",
      "description": "空调控制"
    },
    {
      "goal_type": "navigation",
      "file": "vehicle/navigation.json",
      "description": "导航"
    }
    // ... 自动发现所有 binding
  ],
  "stats": {
    "total": 30,
    "vehicle": 6,
    "advisory": 19,
    "travel": 4
  }
}
```

---

## 3. Binding Config Schema

### 3.1 完整 Schema

```json
{
  "$schema": "./_schema.json",
  "goal_type": "climate_control",
  "version": "v1",
  "description": "空调控制 - 支持开关、温度调节、风速控制",

  "metadata": {
    "author": "system",
    "created": "2026-04-18",
    "tags": ["vehicle", "hvac"]
  },

  "primary": {
    "tool": "climate_control",
    "action_conditions": [
      {
        "if": {"==": ["power", false]},
        "then": "off"
      },
      {
        "if": {"exists": "temperature"},
        "then": "set_temp"
      },
      {
        "if": {"exists": "fan_speed"},
        "then": "set_wind"
      },
      {
        "if": {"==": ["mode", "heat"]},
        "then": "heat"
      },
      {
        "default": "on"
      }
    ],
    "params": {
      "temperature": {
        "source": "entities",
        "key": "temperature",
        "type": "int",
        "if": {"exists": "temperature"},
        "default": 24
      },
      "fan_speed": {
        "source": "entities",
        "key": "fan_speed",
        "type": "int",
        "if": {"exists": "fan_speed"},
        "default": 3
      },
      "mode": {
        "source": "entities",
        "key": "mode",
        "if": {"exists": "mode"},
        "default": "auto"
      },
      "power": {
        "source": "entities",
        "key": "power",
        "if": {"exists": "power"},
        "default": true
      }
    },
    "required_params": []
  },

  "secondary": [
    {
      "description": "降级策略1: 获取状态",
      "tool": "climate_control",
      "action": "get_status",
      "params": {}
    },
    {
      "description": "降级策略2: 默认开启",
      "tool": "climate_control",
      "action": "on",
      "params": {
        "temperature": {"default": 24},
        "mode": {"default": "auto"}
      }
    }
  ],

  "retry": {
    "enabled": true,
    "max_attempts": 5,
    "stop_early_if": [
      {"==": ["error_type", "VALIDATION_ERROR"]},
      {"==": ["error_type", "TOOL_NOT_FOUND"]},
      {"==": ["error_type", "INVALID_ACTION"]}
    ],
    "delay_ms": 100
  },

  "error_strategy": "fallback_then_error"
}
```

### 3.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `goal_type` | string | 是 | 目标类型，唯一标识 |
| `version` | string | 是 | 版本号，如 "v1" |
| `description` | string | 否 | 描述 |
| `primary` | object | 是 | 主要目标配置 |
| `secondary` | array | 否 | 降级目标列表 |
| `retry` | object | 否 | 重试配置 |
| `error_strategy` | string | 否 | 错误策略 |

---

## 4. 条件表达式 (Condition Expressions)

### 4.1 支持的操作符

| 操作符 | 语法 | 说明 | 示例 |
|--------|------|------|------|
| 相等 | `{"==": [值1, 值2]}` | 比较是否相等 | `{"==": ["power", false]}` |
| 不等 | `{"!=": [值1, 值2]}` | 比较是否不等 | `{"!=": ["status", "off"]}` |
| 大于 | `{">": [值1, 值2]}` | 数值大于 | `{">": ["temperature", 30]}` |
| 小于 | `{"<": [值1, 值2]}` | 数值小于 | `{"<": ["age", 18]}` |
| 大于等于 | `{" >=": [值1, 值2]}` | 数值大于等于 | `{" >=": ["score", 60]}` |
| 小于等于 | `{"<=": [值1, 值2]}` | 数值小于等于 | `{"<=": ["price", 100]}` |
| 存在 | `{"exists": "字段名"}` | 字段是否存在 | `{"exists": "temperature"}` |
| 不存在 | `{"not_exists": "字段名"}` | 字段是否不存在 | `{"not_exists": "temperature"}` |
| 包含 | `{"in": [值, [列表]]}` | 值是否在列表中 | `{"in": ["destination", ["机场", "公司"]]}` |
| 开头是 | `{"startswith": [值, 前缀]}` | 字符串开头 | `{"startswith": ["name", "张"]}` |
| 结尾是 | `{"endswith": [值, 后缀]}` | 字符串结尾 | `{"endswith": ["name", "先生"]}` |
| 且 | `{"and": [条件1, 条件2]}` | 所有条件为真 | `{"and": [{"exists": "a"}, {">": ["b", 10]}]}` |
| 或 | `{"or": [条件1, 条件2]}` | 任一条件为真 | `{"or": [{"exists": "a"}, {"exists": "b"}]}` |
| 非 | `{"not": 条件}` | 取反 | `{"not": {"exists": "temperature"}}` |

### 4.2 值引用

条件中的值可以引用以下上下文：

```python
context = {
    # 来自 Intent 提取的参数
    "entities": {
        "temperature": 24,
        "destination": "机场",
        "power": true
    },

    # Session 级别信息
    "session": {
        "user_id": "user_123",
        "session_id": "sess_abc",
        "team_id": "feishu"
    },

    # Query 元信息
    "query": {
        "query_id": "q_001",
        "priority": "normal",
        "timestamp": 1713427200
    },

    # 自定义上下文
    "custom": {
        "vehicle_model": "Tesla Model 3",
        "location": "北京"
    }
}
```

**值引用语法：** 直接使用字符串键名，自动从 context 查找。

### 4.3 条件求值示例

```json
// 示例1: 开机且温度存在
{
  "and": [
    {"exists": "power"},
    {"exists": "temperature"}
  ]
}

// 示例2: 目的地是机场或公司
{
  "in": ["destination", ["机场", "公司", "天安门"]]
}

// 示例3: 非空调关闭状态
{
  "not": {"==": ["power", false]}
}
```

---

## 5. 参数映射 (Param Mapping)

### 5.1 Param 定义

```json
{
  "param_name": {
    "source": "entities",        // 来源: entities/session/query/custom
    "key": "temperature",        // 字段名
    "type": "int",               // 类型转换: int/float/string/bool
    "transform": "celsius_to_fahrenheit",  // 可选转换函数
    "if": {"exists": "temperature"},  // 条件，为 false 时使用 default
    "default": 24                // 默认值
  }
}
```

### 5.2 转换函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `int` | 转换为整数 | `"type": "int"` |
| `float` | 转换为浮点数 | `"type": "float"` |
| `string` | 转换为字符串 | `"type": "string"` |
| `bool` | 转换为布尔值 | `"type": "bool"` |
| `celsius_to_fahrenheit` | 摄氏转华氏 | `"transform": "celsius_to_fahrenheit"` |
| `km_to_miles` | 公里转英里 | `"transform": "km_to_miles"` |

### 5.3 参数映射示例

```json
"params": {
  "temperature": {
    "source": "entities",
    "key": "temperature",
    "type": "int",
    "if": {"exists": "temperature"},
    "default": 24
  },
  "destination": {
    "source": "entities",
    "key": "destination",
    "if": {"exists": "destination"},
    "default": ""
  },
  "volume": {
    "source": "entities",
    "key": "volume",
    "type": "int",
    "default": 50
  }
}
```

---

## 6. 错误处理

### 6.1 错误策略

| 策略 | 说明 | 行为 |
|------|------|------|
| `fallback_only` | 仅降级 | 依次尝试 secondary 直到成功，否则返回错误 |
| `error_only` | 仅报错 | 直接返回错误，不尝试降级 |
| `fallback_then_error` | 降级后报错 | 依次尝试 secondary 都失败后，返回错误 |

### 6.2 错误类型

| 错误类型 | 说明 |
|----------|------|
| `VALIDATION_ERROR` | 参数验证失败 |
| `TOOL_NOT_FOUND` | 工具不存在 |
| `INVALID_ACTION` | 动作无效 |
| `EXECUTION_ERROR` | 工具执行失败 |
| `TIMEOUT` | 执行超时 |
| `RATE_LIMIT` | 限流 |

### 6.3 错误响应格式

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "error_message": "缺少必需参数: temperature",
  "goal_type": "climate_control",
  "primary_attempted": {
    "tool": "climate_control",
    "action": "set_temp",
    "params": {},
    "error": "VALIDATION_ERROR"
  },
  "fallback_attempted": true,
  "fallback_results": [
    {
      "description": "降级策略1: 获取状态",
      "tool": "climate_control",
      "action": "get_status",
      "result": {"success": true, "description": "空调状态: 24°C, 自动模式"}
    }
  ],
  "final_result": {
    "success": true,
    "description": "空调状态: 24°C, 自动模式"
  }
}
```

---

## 7. 重试机制

### 7.1 重试配置

```json
"retry": {
  "enabled": true,
  "max_attempts": 5,
  "stop_early_if": [
    {"==": ["error_type", "VALIDATION_ERROR"]},
    {"==": ["error_type", "TOOL_NOT_FOUND"]},
    {"==": ["error_type", "INVALID_ACTION"]}
  ],
  "delay_ms": 100,
  "backoff": "exponential"
}
```

### 7.2 退避策略

| 策略 | 说明 |
|------|------|
| `fixed` | 固定延迟 |
| `linear` | 线性递增 |
| `exponential` | 指数退避 |

---

## 8. 核心组件

### 8.1 BindingManager

```python
class BindingManager:
    """Binding 配置管理器"""

    def __init__(self, tools_dir: str = "~/.multiagent/tools/"):
        self.tools_dir = Path(tools_dir).expanduser()
        self.bindings: dict[str, BindingConfig] = {}
        self._watcher: Optional[FileWatcher] = None

    def load_all(self) -> None:
        """启动时全量加载所有 binding 配置"""
        index = self._load_index()
        for entry in index["bindings"]:
            binding = self._load_binding(entry["file"])
            self.bindings[binding.goal_type] = binding

    def get(self, goal_type: str) -> Optional[BindingConfig]:
        """获取指定 goal_type 的 binding"""
        return self.bindings.get(goal_type)

    def reload(self, file_path: str) -> None:
        """热更新：重新加载指定文件"""
        binding = self._load_binding(file_path)
        self.bindings[binding.goal_type] = binding

    def _load_binding(self, file_path: str) -> BindingConfig:
        """加载单个 binding 文件"""
        ...

    def validate(self, goal_type: str) -> ValidationResult:
        """验证 binding 配置"""
        ...
```

### 8.2 ConditionEvaluator

```python
class ConditionEvaluator:
    """条件表达式求值器"""

    def evaluate(self, condition: dict, context: dict) -> bool:
        """求值条件表达式"""
        op = list(condition.keys())[0]
        args = condition[op]

        if op == "and":
            return all(self.evaluate(c, context) for c in args)
        elif op == "or":
            return any(self.evaluate(c, context) for c in args)
        elif op == "not":
            return not self.evaluate(args, context)
        elif op == "==":
            return self._resolve(args[0], context) == self._resolve(args[1], context)
        elif op == "!=":
            return self._resolve(args[0], context) != self._resolve(args[1], context)
        elif op == ">":
            return self._resolve(args[0], context) > self._resolve(args[1], context)
        elif op == "exists":
            return self._resolve(args, context) is not None
        # ... 其他操作符

    def _resolve(self, key: str, context: dict) -> Any:
        """解析值引用，从 context 中获取值"""
        # 支持 entities.session.query.custom 多层引用
        ...
```

### 8.3 ParamMapper

```python
class ParamMapper:
    """参数映射器"""

    def map_params(self, param_defs: dict, context: dict) -> dict:
        """根据 param 定义映射参数"""
        result = {}
        for param_name, param_def in param_defs.items():
            # 检查条件
            if "if" in param_def:
                if not condition_evaluator.evaluate(param_def["if"], context):
                    continue

            # 获取值
            value = self._get_value(param_def, context)

            # 类型转换
            if "type" in param_def:
                value = self._convert(value, param_def["type"])

            # 转换函数
            if "transform" in param_def:
                value = self._transform(value, param_def["transform"])

            # 默认值
            if value is None and "default" in param_def:
                value = param_def["default"]

            result[param_name] = value
        return result
```

### 8.4 BindingExecutor

```python
class BindingExecutor:
    """Binding 执行器"""

    def __init__(self, binding_manager: BindingManager, registry: ToolRegistry):
        self.bindings = binding_manager
        self.registry = registry

    def execute(self, goal_type: str, entities: dict, context: dict) -> ExecutionResult:
        """执行 binding"""
        binding = self.bindings.get(goal_type)
        if not binding:
            return ExecutionResult.error("BINDING_NOT_FOUND", f"未找到 binding: {goal_type}")

        # 构建完整上下文
        full_context = {
            "entities": entities,
            "session": context.get("session", {}),
            "query": context.get("query", {}),
            "custom": context.get("custom", {})
        }

        # 执行 primary
        result = self._execute_primary(binding, full_context)

        # 处理错误和降级
        if not result.success and binding.secondary:
            result = self._execute_with_fallback(binding, full_context)

        return result

    def _execute_primary(self, binding: BindingConfig, context: dict) -> ExecutionResult:
        """执行 primary 目标"""
        ...

    def _execute_with_fallback(self, binding: BindingConfig, context: dict) -> ExecutionResult:
        """执行带降级的目标"""
        ...
```

---

## 9. 执行流程

### 9.1 完整执行流程

```
用户查询: "打开空调，温度24度"
    │
    ▼
Intent Agent 提取意图
    │
    ▼
Planner Agent 创建 Goal
    │
    ▼
Executor Agent 执行 Goal
    │
    ▼
BindingExecutor.execute(goal_type="climate_control", entities={...})
    │
    ├──► BindingManager.get("climate_control")
    │         │
    │         ▼
    │    BindingConfig (from JSON)
    │
    ├──► ConditionEvaluator 求值 action_conditions
    │         │
    │         ▼
    │    action = "set_temp" (匹配到第二个条件)
    │
    ├──► ParamMapper 映射参数
    │         │
    │         ▼
    │    params = {"temperature": 24, "power": true, "mode": "auto"}
    │
    ├──► ToolRegistry.call_tool("climate_control", "set_temp", **params)
    │         │
    │         ▼
    │    ToolResult(success=True, description="已调节温度至24°C")
    │
    ▼
返回执行结果
```

### 9.2 降级流程

```
Primary 执行失败
    │
    ▼
检查 error_strategy
    │
    ├──► "fallback_only" 或 "fallback_then_error"
    │         │
    │         ▼
    │    遍历 secondary 列表
    │         │
    │         ▼
    │    Secondary[0]: tool="climate_control", action="get_status"
    │         │
    │         ▼
    │    执行成功 → 返回结果
    │         │
    │         ▼
    │    执行失败 → 尝试下一个 secondary
    │
    ├──► "error_only"
    │         │
    │         ▼
    │    直接返回错误
    │
    ▼
重试逻辑 (如果 enabled)
    │
    ▼
返回最终结果
```

---

## 10. 迁移策略

### 10.1 迁移阶段

| 阶段 | 内容 | 产物 |
|------|------|------|
| Phase 1 | 创建 Schema，基础设施 | `_schema.json`, `BindingManager` |
| Phase 2 | 实现核心组件 | `ConditionEvaluator`, `ParamMapper` |
| Phase 3 | 迁移 5 个核心 goal_type | 5 个 JSON binding 文件 |
| Phase 4 | 实现错误处理和降级 | `BindingExecutor` 完整版 |
| Phase 5 | 实现热更新支持 | `FileWatcher` 集成 |
| Phase 6 | 迁移剩余 goal_type | 全部 30+ 个 binding 文件 |
| Phase 7 | 移除硬编码 | 清空 `executor_agent.py` 中的 if-elif |

### 10.2 迁移工具

**1. Schema 验证：**
```bash
# 验证单个 binding 文件
python -m tools.validate_binding ~/.multiagent/tools/vehicle/climate_control.json

# 验证所有 binding 文件
python -m tools.validate_binding --all
```

**2. 从硬编码提取：**
```bash
# 从 executor_agent.py 提取现有映射
python -m tools.extract_bindings \
    --source=agents/executor_agent.py \
    --output=~/.multiagent/tools/

# 生成 binding 文件草稿
python -m tools.extract_bindings \
    --source=agents/executor_agent.py \
    --output=~/.multiagent/tools/ \
    --template=vehicle/climate_control.json.j2
```

**3. 混合模式（过渡期）：**
```python
# executor_agent.py
if binding_exists(goal_type):
    return execute_binding(goal_type, entities, context)
else:
    return execute_hardcoded(goal_type, entities)
```

---

## 11. 文件清单

### 11.1 新增文件

| 文件路径 | 说明 |
|----------|------|
| `core/binding_manager.py` | Binding 加载与管理 |
| `core/condition_evaluator.py` | 条件表达式求值 |
| `core/param_mapper.py` | 参数映射 |
| `core/binding_executor.py` | Binding 执行器 |
| `core/binding_schema.py` | Schema 定义和验证 |
| `tools/__init__.py` | Tools 模块入口 |
| `tools/cli.py` | 命令行工具 |
| `~/.multiagent/tools/_schema.json` | Schema 定义文件 |
| `~/.multiagent/tools/_index.json` | 索引文件 |

### 11.2 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `agents/executor_agent.py` | 移除硬编码，改用 BindingExecutor |
| `backend/tools.py` | 适配动态调用（可选） |

### 11.3 Binding 配置文件

```
~/.multiagent/tools/vehicle/
├── climate_control.json
├── navigation.json
├── music_control.json
├── vehicle_status.json
├── door_control.json
└── emergency.json
```

---

## 12. 测试策略

### 12.1 单元测试

```python
# tests/unit/test_condition_evaluator.py
def test_nested_and_or_conditions():
    context = {"entities": {"power": True, "temperature": 25}}
    condition = {"and": [{"exists": "power"}, {"or": [{"exists": "temperature"}, {"exists": "mode"}]}]}
    assert evaluator.evaluate(condition, context) == True

# tests/unit/test_param_mapper.py
def test_param_mapping_with_transform():
    param_def = {"temperature": {"type": "int", "default": 24}}
    context = {"entities": {"temperature": "25"}}
    result = mapper.map_params(param_def, context)
    assert result["temperature"] == 25
```

### 12.2 集成测试

```python
# tests/integration/test_binding_execution.py
def test_climate_control_binding():
    result = executor.execute(
        goal_type="climate_control",
        entities={"power": True, "temperature": 24},
        context={}
    )
    assert result.success == True
    assert "温度" in result.description
```

### 12.3 迁移测试

```bash
# 验证所有 binding 文件
python -m tools.validate_binding --all

# 对比硬编码和 binding 执行结果
python -m tools.compare_results --goal_type=climate_control
```

---

## 13. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Binding 配置错误导致系统不可用 | 高 | 启动时验证，混合模式下 fallback 到硬编码 |
| 条件表达式复杂难以调试 | 中 | 提供 dry-run 工具，模拟求值 |
| 热更新导致状态不一致 | 中 | 使用版本号，更新前校验 |
| 30+ binding 文件迁移工作量大 | 低 | 提供自动提取工具 |

---

## 14. 后续扩展

| 扩展 | 说明 |
|------|------|
| MCP/Skill 动态加载 | 从 MCP 服务器动态发现和加载工具 |
| A/B Testing | 支持多个 binding 版本进行实验 |
| 绑定优先级 | 支持多个 binding 竞争同一个 goal_type |
| 指标收集 | Binding 执行统计和监控 |

---

## 15. 附录

### 15.1 术语表

| 术语 | 说明 |
|------|------|
| `goal_type` | 目标类型，如 "climate_control" |
| `binding` | goal_type 到 tool/action 的映射配置 |
| `primary` | 主要执行目标 |
| `secondary` | 降级执行目标 |
| `action_conditions` | 决定使用哪个 action 的条件列表 |
| `param_mapping` | 参数如何从 entities 映射到工具参数 |

### 15.2 参考资料

- `agents/executor_agent.py` - 当前硬编码实现
- `backend/tools.py` - ToolRegistry 实现
- `prompts/system/executor_agent.md` - Executor Agent 提示词
