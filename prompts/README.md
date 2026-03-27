# Prompts Directory

All Agent prompts are defined here. Loaded as templates at runtime.

## Structure

```
prompts/
├── system/        # Agent 角色定义 (加载到 system prompt)
├── context/       # 会话上下文模板
├── tools/        # 工具/MCP/Skill 定义
└── teams/        # Team 协作协议
```

## Loading

```python
def load_prompt(category: str, name: str) -> str:
    """Load prompt from prompts/{category}/{name}.md"""
    path = Path(f"prompts/{category}/{name}.md")
    return path.read_text()
```
