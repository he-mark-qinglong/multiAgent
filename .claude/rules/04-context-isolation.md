# 上下文隔离与权限规范

**版本: 1.0 | 2026-03-27**

## 1. 数据分类

### 1.1 分类定义

| 类型 | 说明 | 可见范围 |
|------|------|----------|
| **PUBLIC** | 共享数据 | 所有Agent可见 |
| **PROTECTED** | 受限数据 | 指定Agent组可见 |
| **PRIVATE** | 隐私数据 | 仅创建者可见 |

### 1.2 数据类型映射

```python
class DataVisibility(str, Enum):
    PUBLIC = "public"       # 所有Agent可见
    PROTECTED = "protected" # 指定Agent可见
    PRIVATE = "private"     # 仅创建者可见

class DataCategory(str, Enum):
    # PUBLIC - 全局共享
    INTENT_CHAIN = "intent_chain"      # 意图链
    GOAL_TREE = "goal_tree"           # 目标树
    PLAN = "plan"                     # 执行计划
    EXECUTION_STATUS = "status"       # 执行状态

    # PRIVATE - 仅创建者
    LLM_PROMPT = "llm_prompt"         # LLM调用记录
    INTERNAL_REASONING = "reasoning"  # 内部推理
    CONFIDENCE_SCORES = "scores"      # 置信度评分
```

## 2. 隔离机制

### 2.1 ScopedContext 增强

```python
@dataclass
class ScopedContext:
    agent_id: str
    visibility: DataVisibility

    # PUBLIC 字段 - 所有Agent可见
    intent_chain: IntentChain | None
    goal_tree: GoalTree | None
    plan: Plan | None

    # PRIVATE 字段 - 仅创建者可见
    _private_data: dict[str, Any]  # 加密存储
```

### 2.2 读取权限检查

```python
class ContextPermission:
    @staticmethod
    def can_read(
        data_category: DataCategory,
        requesting_agent: str,
        data_owner: str | None,
        authorized_agents: list[str] | None,
    ) -> bool:
        # PUBLIC - 全部可读
        if data_category.is_public():
            return True

        # PRIVATE - 仅创建者可读
        if data_category.is_private():
            return requesting_agent == data_owner

        # PROTECTED - 授权列表检查
        if data_category.is_protected():
            return requesting_agent in (authorized_agents or [])

        return False
```

## 3. 各Agent权限矩阵

| 数据类型 | IntentAgent | PlannerAgent | Executor | Synthesizer | Monitor |
|----------|-------------|--------------|----------|-------------|---------|
| **INTENT_CHAIN** | R/W | R | - | R | R |
| **GOAL_TREE** | - | R/W | R | R/W | R |
| **PLAN** | - | R/W | R | R | R |
| **EXECUTION_STATUS** | - | - | W | R | R/W |
| **LLM_PROMPT** | R/W | R/W | - | R | - |
| **INTERNAL_REASONING** | R/W | R/W | - | - | - |
| **SUBGOAL_RESULT** | - | - | W | R | R |

> R=读取, W=写入, -=无权限

## 4. StateStore 权限增强

```python
class SecureStateStore:
    def set(
        self,
        entity_type: EntityType,
        entity_id: str,
        value: Any,
        source_agent: str,
        visibility: DataVisibility = DataVisibility.PUBLIC,
        authorized_agents: list[str] | None = None,
    ) -> DeltaUpdate:
        """写入数据，自动设置权限标记"""
        metadata = {
            "visibility": visibility.value,
            "owner": source_agent,
            "authorized": authorized_agents,
        }
        return self._store_with_metadata(...)

    def get(
        self,
        entity_type: EntityType,
        entity_id: str,
        requesting_agent: str,
    ) -> Any | None:
        """读取数据，权限检查"""
        if not self._check_permission(entity_type, entity_id, requesting_agent):
            raise PermissionError(f"{requesting_agent} cannot access {entity_id}")
        return self._read(...)

    def _check_permission(
        self,
        entity_type: EntityType,
        entity_id: str,
        agent_id: str,
    ) -> bool:
        """权限检查"""
        metadata = self._get_metadata(entity_type, entity_id)
        return ContextPermission.can_read(
            metadata.category,
            agent_id,
            metadata.owner,
            metadata.authorized_agents,
        )
```

## 5. Agent 作用域限制

```
Intent Agent (L0):
  输出: PUBLIC(IntentChain) + PRIVATE(LLM_Prompt, Reasoning)
  可读取: PUBLIC(IntentChain, History)

Planner Agent (L1):
  输出: PUBLIC(GOAL_TREE, PLAN) + PRIVATE(Reasoning)
  可读取: PUBLIC(IntentChain, GOAL_TREE, PLAN)

Executor Agent (L2+):
  输出: PUBLIC(SUBGOAL_RESULT, STATUS) + PRIVATE(Step_Details)
  可读取: PUBLIC(分配的Goal, PLAN)

Synthesizer Agent (L1):
  输出: PUBLIC(FinalResponse)
  可读取: PUBLIC(GoalTree, SubGoalResults, IntentChain)

Monitor Agent (XL):
  输出: PUBLIC(Status_Summary, Alerts)
  可读取: PUBLIC(Status) + PROTECTED(详细日志)
```

## 6. 实现清单

- [ ] DataVisibility enum
- [ ] ContextPermission.can_read()
- [ ] SecureStateStore.get() with permission check
- [ ] SecureStateStore.set() with visibility metadata
- [ ] Agent run() 返回值过滤（移除PRIVATE数据）
- [ ] 单元测试：权限检查边界情况
