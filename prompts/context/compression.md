# Context Compression Prompt

## When to Compress

Triggered when token count exceeds 80% of context window.

## Compression Strategy

### Step 1: Identify Key Events

```
Keep:
- Intent chain decisions
- Goal completions/failures
- User preferences expressed
- Critical system events

Discard:
- Intermediate ReAct reasoning
- Raw tool call details
- Redundant confirmations
```

### Step 2: Generate Summary

```
压缩摘要生成提示:

将以下对话历史压缩为摘要，保留关键意图和决策:

{conversation_history}

摘要要求:
- 保留所有意图识别结果
- 保留所有完成/失败的目标
- 保留用户偏好变化
- 压缩后保留最多10个关键事件
- 输出为结构化 JSON
```

### Step 3: Replace History

```
Old history (N turns) → Compressed summary
Turn count: N → {compressed_turn_count}
Token count: {old_tokens} → {new_tokens}
```

## Safety Checks

- Never compress during active HITL interrupt
- Never compress mid-execution goal
- Preserve all user consent records
