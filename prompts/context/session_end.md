# Session End Context

## Session Summary Template

```
## 本次会话总结

总请求数: {turn_count}
完成任务: {completed_count}
失败任务: {failed_count}
平均响应时间: {avg_response_time}ms

关键决策:
{key_decisions}

用户偏好:
{user_preferences}
```

## Cleanup Actions

- Release pending approvals
- Flush execution logs
- Archive conversation to cold storage
- Update user preference profile
