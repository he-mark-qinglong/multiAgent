# Git 提交规范

**版本: 1.0 | 2026-03-27**

## 1. Commit Message 格式

```
<type>(<scope>): <description>

[可选 body]
```

### Types
| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复bug |
| refactor | 重构 |
| docs | 文档 |
| test | 测试 |
| chore | 杂项 |

### 示例
```
feat(state): add DeltaUpdate subscription model
fix(agent): resolve intent chain circular reference
docs(rules): add delta sync specification
```

## 2. Phase 提交规则

每个 Phase 完成后必须提交一次 git，记录:
- Phase 完成状态
- 主要变更
- 待解决问题

## 3. 决策记录

所有 ADR 记录到 `docs/decisions/`

```markdown
# ADR-XXX: <Title>

## Status
Accepted | Deprecated | Superseded

## Context
<问题描述>

## Decision
<决策内容>

## Consequences
<影响>
```
