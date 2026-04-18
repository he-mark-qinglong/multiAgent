# Dynamic Tool Binding 设计方案

**版本:** v1.1
**日期:** 2026-04-18
**状态:** 待审核 / 可进入实施

---

## 0. 修订原则

本次修订遵循以下原则：

1. **保留原方案主体结构**
2. **优先修正语义不清的部分**
3. **保证先能落地，再可持续迭代**
4. **所有后续修改都能映射回整体执行链路**
5. **动态能力必须具备可观测性和可回退性**

---

## 1. 概述

### 1.1 目标

将 `agents/executor_agent.py` 中的硬编码 `goal_type -> tool/action` 映射改为**动态 JSON 配置绑定**，实现：

- 新增工具无需修改代码
- 支持条件逻辑和降级策略
- 支持错误处理和受控重试
- 支持热更新
- 执行链路可观测、可审计

### 1.2 当前问题

```python
if goal_type == "climate_control":
    return registry.call_tool("climate_control", "control", **params)
elif goal_type == "navigation":
    return registry.call_tool("navigation", "navigate", ...)
elif goal_type == "music_control":
    return registry.call_tool("music_control", "play")
```

**问题：**

- 每新增工具需要修改代码
- 条件逻辑散落在 if-elif 中
- 难以支持 fallback / retry
- 无法热更新
- 缺少统一审计信息

### 1.3 收益

| 收益 | 说明 |
|------|------|
| 无需修改代码 | 新增 goal_type 仅需新增 binding 文件 |
| 条件逻辑外置 | action 选择逻辑可配置化 |
| 降级策略 | 支持 primary / secondary |
| 热更新 | 修改配置后可生效 |
| 可观测性 | 每次绑定执行都能追踪 |

---

## 2. 配置存储

### 2.1 目录结构

```
configs/bindings/
├── _schema.json
├── _index.json              # 自动生成，只读，不作为真相源
├── vehicle/
│   ├── climate_control.json
│   ├── navigation.json
│   ├── music_control.json
│   ├── vehicle_status.json
│   ├── door_control.json
│   └── emergency.json
├── advisory/
│   ├── legal/
│   │   ├── legal_contract_review.json
│   │   ├── legal_rights_protection.json
│   │   └── legal_compliance_check.json
│   ├── medical/
│   │   ├── medical_symptom_analysis.json
│   │   ├── medical_disease_info.json
│   │   └── medical_hospital_recommend.json
│   └── ...
└── travel/
    ├── trip_plan.json
    ├── hotel_book.json
    ├── visa_consult.json
    └── spot_recommend.json
```

### 2.2 文件命名

**规则：** 文件名必须与 `goal_type` 完全一致，即 `{goal_type}.json`

**示例：**

- `climate_control.json` -> `goal_type: "climate_control"`
- `legal_contract_review.json` -> `goal_type: "legal_contract_review"`

### 2.3 `_index.json` 定位

`_index.json` 保留，但改为：

- **自动生成**
- **只用于展示、审计、CLI**
- **不是 source of truth**
- **真实加载以目录扫描结果为准**

示例：

```json
{
  "version": "1.1",
  "generated_at": "2026-04-18T08:00:00Z",
  "bindings": [
    {
      "goal_type": "climate_control",
      "file": "vehicle/climate_control.json",
      "description": "空调控制",
      "binding_version": "v1"
    }
  ],
  "stats": {
    "total": 30
  }
}
```

---

## 3. Binding Config Schema

### 3.1 核心结构说明

相较 v1.0，核心调整为：

1. `action_conditions` 改为 `action_selector`
2. action 的参数定义收敛到 `actions`
3. `required_params` 下沉到 action 级
4. 显式值引用 `{ "var": "path.to.value" }` 避免字符串歧义

### 3.2 示例

```json
{
  "$schema": "./_schema.json",
  "goal_type": "climate_control",
  "version": "v1",
  "description": "空调控制 - 支持开关，温度调节、风速控制",

  "metadata": {
    "author": "system",
    "created": "2026-04-18",
    "category": "vehicle",
    "tags": ["vehicle", "hvac"]
  },

  "primary": {
    "tool": "climate_control",

    "action_selector": [
      {
        "when": { "==": [ { "var": "entities.power" }, false ] },
        "action": "off"
      },
      {
        "when": { "exists": { "var": "entities.temperature" } },
        "action": "set_temp"
      },
      {
        "when": { "exists": { "var": "entities.fan_speed" } },
        "action": "set_wind"
      },
      {
        "when": { "==": [ { "var": "entities.mode" }, "heat" ] },
        "action": "heat"
      },
      {
        "default": "on"
      }
    ],

    "actions": {
      "off": {
        "params": {},
        "idempotent": true
      },
      "on": {
        "params": {
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 24
          },
          "mode": {
            "from": "entities.mode",
            "default": "auto"
          }
        },
        "idempotent": true
      },
      "set_temp": {
        "required_params": ["temperature"],
        "params": {
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 24
          },
          "mode": {
            "from": "entities.mode",
            "default": "auto"
          }
        },
        "idempotent": true
      },
      "set_wind": {
        "required_params": ["fan_speed"],
        "params": {
          "fan_speed": {
            "from": "entities.fan_speed",
            "type": "int",
            "default": 3
          }
        },
        "idempotent": true
      },
      "heat": {
        "params": {
          "mode": {
            "default": "heat"
          },
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 26
          }
        },
        "idempotent": true
      }
    }
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
        "temperature": { "default": 24 },
        "mode": { "default": "auto" }
      }
    }
  ],

  "retry": {
    "enabled": true,
    "max_attempts": 3,
    "delay_ms": 100,
    "backoff": "exponential",
    "retry_on": ["EXECUTION_ERROR", "TIMEOUT", "RATE_LIMIT"],
    "stop_early_if": [
      { "==": [ { "var": "runtime.error_type" }, "VALIDATION_ERROR" ] },
      { "==": [ { "var": "runtime.error_type" }, "TOOL_NOT_FOUND" ] },
      { "==": [ { "var": "runtime.error_type" }, "INVALID_ACTION" ] }
    ]
  },

  "error_strategy": "fallback_then_error"
}
```

### 3.3 字段说明

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

## 4. 条件表达式

### 4.1 设计原则

**核心歧义修正：** v1.0 中 `"power"` 到底表示字面量字符串还是上下文字段引用。

v1.1 改为：

- **字面量**：直接写原值
- **上下文引用**：使用 `{ "var": "path.to.value" }`

### 4.2 支持的操作符

| 操作符 | 示例 |
|--------|------|
| `==` | `{ "==": [ { "var": "entities.mode" }, "heat" ] }` |
| `!=` | `{ "!=": [ { "var": "entities.status" }, "off" ] }` |
| `>` | `{ ">": [ { "var": "entities.temperature" }, 30 ] }` |
| `<` | `{ "<": [ { "var": "entities.age" }, 18 ] }` |
| `>=` | `{ ">=": [ { "var": "entities.score" }, 60 ] }` |
| `<=` | `{ "<=": [ { "var": "entities.price" }, 100 ] }` |
| `exists` | `{ "exists": { "var": "entities.temperature" } }` |
| `not_exists` | `{ "not_exists": { "var": "entities.temperature" } }` |
| `in` | `{ "in": [ { "var": "entities.destination" }, ["机场", "公司"] ] }` |
| `startswith` | `{ "startswith": [ { "var": "entities.name" }, "张" ] }` |
| `endswith` | `{ "endswith": [ { "var": "entities.name" }, "先生" ] }` |
| `and` | `{ "and": [cond1, cond2] }` |
| `or` | `{ "or": [cond1, cond2] }` |
| `not` | `{ "not": cond }` |

### 4.3 上下文结构

```python
context = {
    "entities": {...},    # Intent 提取的参数
    "session": {...},     # Session 级别信息
    "query": {...},       # Query 元信息
    "custom": {...},      # 自定义上下文
    "runtime": {...}      # 运行时信息（error_type 等）
}
```

### 4.4 action 选择规则

`action_selector` 明确采用：

- **按顺序求值**
- **first-match-wins**
- 最多只允许 **1 个 default**
- 如果没有匹配项且没有 default，则返回 `INVALID_ACTION_SELECTION`

---

## 5. 参数映射

### 5.1 Param 定义

```json
{
  "temperature": {
    "from": "entities.temperature",
    "type": "int",
    "transform": "celsius_to_fahrenheit",
    "when": { "exists": { "var": "entities.temperature" } },
    "default": 24,
    "omit_if_missing": false
  }
}
```

### 5.2 字段说明

| 字段 | 说明 |
|------|------|
| `from` | 值来源路径，如 `entities.temperature` |
| `type` | 基础类型转换 |
| `transform` | 白名单转换函数 |
| `when` | 条件成立才尝试读取 |
| `default` | 缺失或条件不满足时的默认值 |
| `omit_if_missing` | 为 `true` 时，无法解析且无 default 则不传该参数 |

### 5.3 参数求值顺序

参数计算规则统一为：

1. 若存在 `when` 且条件不成立：
   - 有 `default` -> 使用 `default`
   - 否则 -> 根据 `omit_if_missing` 决定省略
2. 读取 `from`
3. 若值缺失：
   - 有 `default` -> 使用 `default`
   - 否则 -> 缺失
4. 执行 `type`
5. 执行 `transform`
6. 产出最终参数

> 不再使用"条件不满足直接 continue 跳过"的隐式行为。

### 5.4 Transform 规则

`transform` 只能来自**注册白名单**，不能任意反射执行。

```python
TRANSFORMS = {
    "celsius_to_fahrenheit": celsius_to_fahrenheit,
    "km_to_miles": km_to_miles
}
```

---

## 6. 错误处理

### 6.1 错误策略

| 策略 | 说明 |
|------|------|
| `error_only` | primary 失败直接返回错误 |
| `fallback_only` | primary 失败后只返回 fallback 执行结果 |
| `fallback_then_error` | primary 失败后尝试 fallback，若 fallback 也失败则返回错误 |

### 6.2 错误类型

| 错误类型 | 说明 |
|----------|------|
| `BINDING_NOT_FOUND` | 未找到 binding |
| `STATIC_CONFIG_ERROR` | 配置静态校验失败 |
| `VALIDATION_ERROR` | 参数校验失败 |
| `TOOL_NOT_FOUND` | 工具不存在 |
| `INVALID_ACTION` | action 不存在 |
| `INVALID_ACTION_SELECTION` | action_selector 无法选出 action |
| `PARAM_MAPPING_ERROR` | 参数映射失败 |
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
      "result": {
        "success": true,
        "description": "空调状态: 24°C, 自动模式"
      }
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
  "max_attempts": 3,
  "delay_ms": 100,
  "backoff": "exponential",
  "retry_on": ["EXECUTION_ERROR", "TIMEOUT", "RATE_LIMIT"],
  "stop_early_if": [
    { "==": [ { "var": "runtime.error_type" }, "VALIDATION_ERROR" ] },
    { "==": [ { "var": "runtime.error_type" }, "TOOL_NOT_FOUND" ] },
    { "==": [ { "var": "runtime.error_type" }, "INVALID_ACTION" ] }
  ]
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

    def __init__(self, bindings_dir: str = "configs/bindings/"):
        self.bindings_dir = Path(bindings_dir).expanduser()
        self.bindings: dict[str, BindingConfig] = {}
        self._watcher: Optional[FileWatcher] = None

    def load_all(self) -> None:
        """启动时全量加载所有 binding 配置"""
        for file_path in self.bindings_dir.rglob("*.json"):
            if file_path.name.startswith("_"):
                continue
            binding = self._load_binding(file_path)
            self.bindings[binding.goal_type] = binding

    def get(self, goal_type: str) -> Optional[BindingConfig]:
        """获取指定 goal_type 的 binding"""
        return self.bindings.get(goal_type)

    def reload(self, file_path: str) -> None:
        """热更新：重新加载指定文件"""
        binding = self._load_binding(file_path)
        self.bindings[binding.goal_type] = binding

    def _load_binding(self, file_path: Path) -> BindingConfig:
        """加载单个 binding 文件"""
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

        if op == "var":
            return self._resolve_var(args, context)

        elif op == "and":
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
            return self._resolve_var(args, context) is not None
        # ... 其他操作符

    def _resolve_var(self, path: str, context: dict) -> Any:
        """解析 { "var": "path.to.value" }"""
        keys = path.split(".")
        value = context
        for key in keys:
            value = value.get(key, None)
            if value is None:
                return None
        return value

    def _resolve(self, value: Any, context: dict) -> Any:
        """解析值，字面量原样返回，变量引用则查找"""
        if isinstance(value, dict) and "var" in value:
            return self._resolve_var(value["var"], context)
        return value
```

### 8.3 ParamMapper

```python
class ParamMapper:
    """参数映射器"""

    TRANSFORMS = {
        "celsius_to_fahrenheit": lambda c: c * 9/5 + 32,
        "km_to_miles": lambda km: km * 0.621371,
    }

    def map_params(self, param_defs: dict, context: dict) -> dict:
        """根据 param 定义映射参数"""
        result = {}
        for param_name, param_def in param_defs.items():

            # 1. 检查 when 条件
            if "when" in param_def:
                if not condition_evaluator.evaluate(param_def["when"], context):
                    if "default" in param_def:
                        result[param_name] = param_def["default"]
                    elif not param_def.get("omit_if_missing", False):
                        continue
                    else:
                        continue

            # 2. 获取值
            value = self._get_value(param_def, context)

            # 3. 类型转换
            if "type" in param_def and value is not None:
                value = self._convert(value, param_def["type"])

            # 4. 转换函数
            if "transform" in param_def and value is not None:
                transform = self.TRANSFORMS.get(param_def["transform"])
                if transform:
                    value = transform(value)

            # 5. 默认值
            if value is None and "default" in param_def:
                value = param_def["default"]

            if value is not None or not param_def.get("omit_if_missing", False):
                result[param_name] = value

        return result
```

### 8.4 BindingExecutor

```python
class BindingExecutor:
    """Binding 执行器"""

    def __init__(
        self,
        binding_manager: BindingManager,
        registry: ToolRegistry
    ):
        self.bindings = binding_manager
        self.registry = registry
        self.evaluator = ConditionEvaluator()
        self.mapper = ParamMapper()

    def execute(
        self,
        goal_type: str,
        entities: dict,
        context: dict
    ) -> ExecutionResult:
        """执行 binding"""
        binding = self.bindings.get(goal_type)
        if not binding:
            return ExecutionResult.error(
                "BINDING_NOT_FOUND",
                f"未找到 binding: {goal_type}"
            )

        # 构建完整上下文
        full_context = {
            "entities": entities,
            "session": context.get("session", {}),
            "query": context.get("query", {}),
            "custom": context.get("custom", {}),
            "runtime": {}
        }

        # 执行 primary
        result = self._execute_primary(binding, full_context)

        # 处理错误和降级
        if not result.success:
            if binding.secondary and binding.error_strategy != "error_only":
                result = self._execute_with_fallback(binding, full_context)
            elif binding.error_strategy == "error_only":
                pass  # 直接返回错误

        return result

    def _execute_primary(
        self,
        binding: BindingConfig,
        context: dict
    ) -> ExecutionResult:
        """执行 primary 目标"""
        # 1. 求值 action_selector
        action_name = self._select_action(
            binding.primary.action_selector,
            context
        )
        if not action_name:
            return ExecutionResult.error(
                "INVALID_ACTION_SELECTION",
                f"无法为 {binding.goal_type} 选择 action"
            )

        # 2. 获取 action 定义
        action_def = binding.primary.actions.get(action_name)
        if not action_def:
            return ExecutionResult.error(
                "INVALID_ACTION",
                f"action 不存在: {action_name}"
            )

        # 3. 检查 required_params
        params = self.mapper.map_params(action_def.params, context)
        for required in action_def.required_params:
            if required not in params:
                return ExecutionResult.error(
                    "VALIDATION_ERROR",
                    f"缺少必需参数: {required}"
                )

        # 4. 调用工具
        return self.registry.call_tool(
            binding.primary.tool,
            action_name,
            **params
        )

    def _select_action(
        self,
        action_selector: list,
        context: dict
    ) -> Optional[str]:
        """从 action_selector 选择 action"""
        default_action = None
        for selector in action_selector:
            if "default" in selector:
                default_action = selector["default"]
                continue
            if "when" in selector:
                if self.evaluator.evaluate(selector["when"], context):
                    return selector["action"]
        return default_action
```

---

## 9. 执行流程

### 9.1 完整执行流程

```
用户查询: "打开空调，温度24度"
    |
    v
Intent Agent 提取意图
    |
    v
Planner Agent 创建 Goal
    |
    v
Executor Agent 执行 Goal
    |
    v
BindingExecutor.execute(
    goal_type="climate_control",
    entities={"power": true, "temperature": 24},
    context={}
)
    |
    +-- BindingManager.get("climate_control")
    |         |
    |         v
    |    BindingConfig (from JSON)
    |
    +-- ConditionEvaluator 求值 action_selector
    |         |
    |         v
    |    action = "set_temp" (匹配到第二个条件)
    |
    +-- ParamMapper 映射参数
    |         |
    |         v
    |    params = {"temperature": 24, "mode": "auto"}
    |
    +-- ToolRegistry.call_tool("climate_control", "set_temp", **params)
    |         |
    |         v
    |    ToolResult(success=True, description="已调节温度至24°C")
    |
    v
返回执行结果
```

### 9.2 降级流程

```
Primary 执行失败
    |
    v
检查 error_strategy
    |
    +-- "fallback_only" 或 "fallback_then_error"
    |         |
    |         v
    |    遍历 secondary 列表
    |         |
    |         v
    |    Secondary[0]: tool="climate_control", action="get_status"
    |         |
    |         v
    |    执行成功 -> 返回结果
    |
    +-- "error_only"
    |         |
    |         v
    |    直接返回错误
    |
    v
重试逻辑 (如果 enabled)
    |
    v
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
python -m tools.validate_binding configs/bindings/vehicle/climate_control.json

# 验证所有 binding 文件
python -m tools.validate_binding --all
```

**2. 从硬编码提取：**

```bash
# 从 executor_agent.py 提取现有映射
python -m tools.extract_bindings \
    --source=agents/executor_agent.py \
    --output=configs/bindings/

# 生成 binding 文件草稿
python -m tools.extract_bindings \
    --source=agents/executor_agent.py \
    --output=configs/bindings/ \
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
| `configs/bindings/_schema.json` | Schema 定义文件 |

### 11.2 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `agents/executor_agent.py` | 移除硬编码，改用 BindingExecutor |

### 11.3 Binding 配置文件

```
configs/bindings/vehicle/
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
    context = {
        "entities": {"power": True, "temperature": 25},
        "session": {},
        "query": {},
        "custom": {},
        "runtime": {}
    }
    condition = {
        "and": [
            {"exists": {"var": "entities.power"}},
            {"or": [
                {"exists": {"var": "entities.temperature"}},
                {"exists": {"var": "entities.mode"}}
            ]}
        ]
    }
    evaluator = ConditionEvaluator()
    assert evaluator.evaluate(condition, context) == True

# tests/unit/test_param_mapper.py
def test_param_mapping_with_transform():
    param_defs = {
        "temperature": {"type": "int", "default": 24}
    }
    context = {"entities": {"temperature": "25"}, ...}
    mapper = ParamMapper()
    result = mapper.map_params(param_defs, context)
    assert result["temperature"] == 25
```

### 12.2 集成测试

```python
# tests/integration/test_binding_execution.py
def test_climate_control_binding():
    executor = BindingExecutor(binding_manager, registry)
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
| `action_selector` | 决定使用哪个 action 的条件列表 |
| `action` | 具体要执行的工具动作 |
| `param_mapping` | 参数如何从 entities 映射到工具参数 |
| `primary` | 主要执行目标 |
| `secondary` | 降级执行目标 |

### 15.2 参考资料

- `agents/executor_agent.py` - 当前硬编码实现
- `backend/tools.py` - ToolRegistry 实现
- `prompts/system/executor_agent.md` - Executor Agent 提示词
