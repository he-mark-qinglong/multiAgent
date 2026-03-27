# 上下文隔离与权限规范

**版本: 1.0 | 2026-03-27**

> 完整权限矩阵待实现 (见下方 TODO)

---

## 1. 可见性级别

```
PUBLIC:     所有 Agent 可读
PROTECTED:  仅父子 Agent 可读
PRIVATE:    仅自身 Agent 可读
```

## 2. 权限矩阵 (简化版)

| 数据类型 | Intent | Planner | Executor | Synthesizer | Monitor |
|----------|--------|---------|----------|-------------|---------|
| **IntentChain** | W | R | - | R | R |
| **GoalTree** | - | W | R | R | R |
| **Plan** | - | W | R | - | R |
| **ExecutionStatus** | - | - | W | R | R/W |
| **SubGoalResult** | - | - | W | R | R |
| **FinalResponse** | - | - | - | W | R |

> W=可写, R=可读, -=无权限

## 3. 上下文隔离原则

```
✅ 每个 Agent 只接收必要最小上下文
✅ EventBus 发布前检查可见性
✅ DeltaUpdate 只包含变更字段
❌ 禁止: Agent 间直接状态共享
❌ 禁止: 全量状态广播
```

---

## TODO: 完整权限实现

以下为计划实现，待优先级确认:

- [ ] `PermissionGuard` 类 (can_read/can_write)
- [ ] `SecureStateStore` (权限检查包装)
- [ ] Agent 配置 YAML 支持
- [ ] 单元测试: 权限边界情况

当前默认行为: 所有 Agent 可读可写全部数据类型。
