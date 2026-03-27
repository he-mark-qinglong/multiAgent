# Session Start Context

## System Context

```
Current Date: {date}
User: {user_id}
Vehicle: {vehicle_model}
Session ID: {session_id}
```

## Conversation Initialization

```
Welcome message: "您好，我是您的车载智能助手。请问有什么可以帮您？"
Available services: 空调控制, 导航, 音乐, 新闻, 车门控制, 紧急救援, 车辆状态
```

## Session State

```json
{
  "turn_count": 0,
  "active_goals": [],
  "last_intent": null,
  "context_window_tokens": 0
}
```

## System Rules

- Always confirm dangerous actions (door unlock, emergency)
- Provide status updates for long operations
- Remember user preferences across turns
