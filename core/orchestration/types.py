"""Orchestration Engine 类型定义."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class QueryPriority(Enum):
    """Query 优先级."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class QueryType(Enum):
    """Query 类型."""
    NORMAL = "normal"      # 普通请求
    URGENT = "urgent"     # 紧急请求
    SPAWN = "spawn"       # 产卵请求（创建新 team）
    CANCEL = "cancel"     # 取消请求


class QueryStatus(Enum):
    """Query 状态."""
    PENDING = "pending"    # 等待中
    RUNNING = "running"    # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled" # 已取消


@dataclass
class QueryRequest:
    """查询请求."""

    id: str
    content: str
    query_type: QueryType = QueryType.NORMAL
    priority: QueryPriority = QueryPriority.NORMAL
    team_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: QueryStatus = QueryStatus.PENDING
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class RunResult:
    """Agent Team 运行结果."""

    team_id: str
    query_id: str
    status: QueryStatus
    final_response: str = ""
    goals: dict[str, Any] = field(default_factory=dict)
    execution_results: dict[str, Any] = field(default_factory=dict)
    iterations: int = 0
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class TeamConfig:
    """Agent Team 配置."""

    team_id: str
    max_iterations: int = 50
    timeout_seconds: float = 300.0
    enable_tracing: bool = False


@dataclass
class EngineConfig:
    """Orchestration Engine 配置."""

    max_concurrent_teams: int = 10
    max_queue_size: int = 1000
    loop_interval_seconds: float = 0.1
    default_team_id: str = "default"


EventHandler = Callable[[str, Any], None]


@dataclass
class QueueStats:
    """队列统计."""

    pending_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
