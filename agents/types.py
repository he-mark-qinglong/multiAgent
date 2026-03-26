"""Input/Output types for agents."""

from dataclasses import dataclass
from typing import Any


@dataclass
class UserQuery:
    """User query input."""
    query_id: str
    text: str
    timestamp: int


@dataclass
class ExecutionResult:
    """Executor Agent output."""
    goal_id: str
    status: str  # completed | failed
    result: Any
    logs: list[dict]
    duration_ms: int


@dataclass
class FinalResponse:
    """Synthesizer Agent output."""
    response: str
    metadata: dict[str, Any]
    goals_achieved: list[str]
    goals_failed: list[str]
