# 上下文隔离与权限规范 v2

**版本: 2.0 | 2026-03-27**

## 1. Agent 权限配置

### 1.1 权限配置文件

```python
@dataclass
class AgentPermissionConfig:
    """单个Agent的权限配置"""

    # 可读取哪些Agent的数据
    can_read_from: set[str]  # e.g., {"intent_agent", "planner_agent"}

    # 可写入哪些共享数据
    can_write_to: set[str]   # e.g., {"goal_status", "execution_result"}

    # 隐私配置
    is_public: bool          # 是否将自己的结论公开到共享上下文
    publish_to_shared: bool  # 是否发布中间状态到共享列表

    # 可见的数据类型
    allowed_data_types: set[str]  # e.g., {"intent_chain", "goal", "plan"}


@dataclass
class SystemPermissionConfig:
    """系统级权限配置"""
    agents: dict[str, AgentPermissionConfig]

    # 默认配置
    default: AgentPermissionConfig
```

### 1.2 配置示例

```python
# 系统权限配置
SYSTEM_PERMISSIONS = {
    "intent_agent": AgentPermissionConfig(
        can_read_from={"*"},              # 可读取所有Agent
        can_write_to={"intent_chain"},   # 只写意图链
        is_public=True,                   # 结论公开
        publish_to_shared=True,           # 发布中间状态
        allowed_data_types={"intent_chain", "history"},
    ),

    "planner_agent": AgentPermissionConfig(
        can_read_from={"intent_agent"},   # 只读IntentAgent
        can_write_to={"goal_tree", "plan"},
        is_public=True,
        publish_to_shared=True,
        allowed_data_types={"intent_chain", "goal_tree", "plan"},
    ),

    "executor_agent": AgentPermissionConfig(
        can_read_from={"planner_agent"}, # 只读PlannerAgent
        can_write_to={"execution_status", "subgoal_result"},
        is_public=False,                  # 执行细节不公开
        publish_to_shared=True,           # 但会发布状态到列表
        allowed_data_types={"goal", "plan"},
    ),

    "synthesizer_agent": AgentPermissionConfig(
        can_read_from={"executor_agent", "planner_agent"},  # 读执行器和规划器
        can_write_to={"final_response"},
        is_public=True,
        publish_to_shared=False,          # 不需要发布中间状态
        allowed_data_types={"goal_tree", "subgoal_result"},
    ),
}
```

## 2. 读写权限检查

### 2.1 读取权限

```python
class PermissionGuard:
    """Agent读写权限守卫"""

    def __init__(self, config: SystemPermissionConfig):
        self.config = config

    def can_read(
        self,
        reader: str,      # 请求读取的Agent
        writer: str,      # 数据来源Agent
        data_type: str,   # 数据类型
    ) -> bool:
        """检查读取权限"""
        reader_config = self.config.agents.get(
            reader,
            self.config.default
        )

        # 检查可读来源
        if "*" not in reader_config.can_read_from:
            if writer not in reader_config.can_read_from:
                return False

        # 检查数据类型
        if data_type not in reader_config.allowed_data_types:
            return False

        return True

    def can_write(
        self,
        writer: str,
        data_type: str,
    ) -> bool:
        """检查写入权限"""
        writer_config = self.config.agents.get(
            writer,
            self.config.default
        )

        if data_type not in writer_config.can_write_to:
            return False

        return True
```

### 2.2 写入控制

```python
class SecureStateStore:
    """带权限检查的状态存储"""

    def __init__(
        self,
        permissions: PermissionGuard,
        event_bus: EventBus,
    ):
        self._guard = permissions
        self._event_bus = event_bus

    def write(
        self,
        writer: str,
        data_type: str,
        entity_id: str,
        value: Any,
        visibility: Visibility = Visibility.PUBLIC,
    ) -> DeltaUpdate | None:
        """写入数据，带权限检查"""

        # 1. 权限检查
        if not self._guard.can_write(writer, data_type):
            raise PermissionError(
                f"{writer} cannot write {data_type}"
            )

        # 2. 检查是否发布到共享
        writer_config = self.config.agents.get(writer)
        if writer_config and not writer_config.publish_to_shared:
            # 不发布到共享，只存储到私有空间
            return self._write_private(writer, entity_id, value)

        # 3. 发布到共享上下文
        return self._publish_to_shared(
            writer=writer,
            data_type=data_type,
            entity_id=entity_id,
            value=value,
            visibility=visibility,
        )

    def _publish_to_shared(
        self,
        writer: str,
        data_type: str,
        entity_id: str,
        value: Any,
        visibility: Visibility,
    ) -> DeltaUpdate:
        """发布到共享上下文"""
        # 构建DeltaUpdate
        delta = DeltaUpdate.create(
            entity_type=EntityType(data_type),
            entity_id=entity_id,
            operation=DeltaOperation.CREATE,
            changed_keys=list(value.keys()) if isinstance(value, dict) else ["value"],
            delta={"value": value, "visibility": visibility.value},
            source_agent=writer,
        )

        # 发布事件
        self._event_bus.publish_delta(
            entity_type=data_type,
            entity_id=entity_id,
            operation="create",
            delta=delta.delta,
            source_agent=writer,
        )

        return delta
```

## 3. 中间状态管理

### 3.1 共享状态列表

```python
class SharedStateList:
    """Agent中间状态列表"""

    # 执行状态列表 - 各Executor的状态汇总
    EXECUTION_STATUS_LIST = "execution_status_list"

    # 结论列表 - 各Agent的公开结论
    CONCLUSIONS_LIST = "conclusions_list"

    # 依赖等待列表 - 等待某些条件满足
    WAITING_DEPENDENCIES = "waiting_dependencies"

    def append_status(
        self,
        agent_id: str,
        status: ExecutionStatus,
        publish: bool = True,
    ) -> None:
        """追加执行状态到列表"""
        if not publish:
            # 检查权限
            agent_config = get_config(agent_id)
            if not agent_config.publish_to_shared:
                return  # 不发布

        self._list_append(
            list_name=self.EXECUTION_STATUS_LIST,
            item={
                "agent_id": agent_id,
                "status": status,
                "timestamp": time.time(),
            }
        )

    def get_all_status(
        self,
        requester: str,
    ) -> list[dict]:
        """获取所有状态，带权限检查"""
        return self._list_get(
            list_name=self.EXECUTION_STATUS_LIST,
            filter_fn=lambda item: self._guard.can_read(
                reader=requester,
                writer=item["agent_id"],
                data_type="execution_status",
            )
        )
```

### 3.2 Agent间状态传递

```
┌─────────────────────────────────────────────────────────────┐
│                    状态传递流程                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Planner                                                   │
│    │                                                        │
│    ├──[写: goal]──→ SharedGoalTree ──→[读]──→ Executor     │
│    │                                                        │
│    │                                                        │
│    ▼                                                        │
│  Executor                                                   │
│    │                                                        │
│    ├──[状态列表]──→ ExecutionStatusList ──→[读]──→ Monitor │
│    │                                                        │
│    ├──[结论列表]──→ ConclusionsList (如果is_public=True)    │
│    │                                                        │
│    └──[私有存储]──→ Executor_Private (不共享)               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 4. 权限矩阵 (完整版)

| 数据类型 | Intent | Planner | Executor | Synthesizer | Monitor |
|----------|--------|---------|----------|-------------|---------|
| **IntentChain** | W | R | - | R | R |
| **GoalTree** | - | W | R | R | R |
| **Plan** | - | W | R | - | R |
| **ExecutionStatus** | - | - | W | R | R/W |
| **SubGoalResult** | - | - | W | R | R |
| **FinalResponse** | - | - | - | W | R |
| **LLM_Prompt** | R/W | R/W | - | - | - |
| **Internal_Reasoning** | R/W | R/W | - | - | - |
| **Step_Details** | - | - | PRIVATE | - | R |
| **Conclusions** | R/W | R/W | R/W | R/W | R |

> W=可写, R=可读, -=无权限, PRIVATE=私有存储

## 5. 实现清单

- [ ] `AgentPermissionConfig` dataclass
- [ ] `SystemPermissionConfig` with defaults
- [ ] `PermissionGuard.can_read()`
- [ ] `PermissionGuard.can_write()`
- [ ] `SecureStateStore` with permission checks
- [ ] `SharedStateList` for intermediate states
- [ ] Agent config in `agents/types.py`
- [ ] 权限配置YAML文件支持
- [ ] 单元测试：权限边界情况
