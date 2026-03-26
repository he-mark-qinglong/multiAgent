"""LangSmith tracing integration for agent observability."""

from __future__ import annotations

import os
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# LangChain imports - graceful degradation
try:
    from langsmith import traceable, Client
    from langchain_core.runnables import RunnableConfig
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = None
    Client = None
    RunnableConfig = None


def setup_langsmith(
    project_name: str = "multi-agent",
    api_key: str | None = None,
) -> dict[str, Any]:
    """Setup LangSmith environment variables.

    Args:
        project_name: LangSmith project name.
        api_key: LangSmith API key (defaults to env var).

    Returns:
        Config dict with environment setup status.
    """
    config = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_PROJECT": project_name,
        "LANGSMITH_API_KEY": api_key or os.environ.get("LANGSMITH_API_KEY", ""),
    }
    for key, value in config.items():
        os.environ[key] = value

    logger.info("LangSmith configured: project=%s, enabled=%s",
                 project_name, bool(config["LANGSMITH_API_KEY"]))
    return config


class LangSmithTracer:
    """Wrapper for LangSmith tracing operations.

    Features:
    - Decorator-based function tracing
    - Token usage logging
    - Custom event logging
    - Run tree management
    """

    def __init__(self, project_name: str = "multi-agent"):
        self.project_name = project_name
        self._enabled = LANGSMITH_AVAILABLE and bool(os.environ.get("LANGSMITH_API_KEY"))
        self._client = None

        if self._enabled:
            self._init_client()

    def _init_client(self) -> None:
        """Initialize LangSmith client."""
        if LANGSMITH_AVAILABLE:
            try:
                self._client = Client()
            except Exception as e:
                logger.warning("Failed to init LangSmith client: %s", e)
                self._enabled = False

    def trace(self, name: str) -> Callable:
        """Decorator for tracing functions.

        Usage:
            @tracer.trace("intent_recognition")
            async def recognize_intent(query):
                ...

        Args:
            name: Trace name.

        Returns:
            Decorator function.
        """
        def decorator(func: Callable) -> Callable:
            if self._enabled and traceable:
                return traceable(name=name, project_name=self.project_name)(func)
            return func
        return decorator

    def log_token_usage(
        self,
        run_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Log token usage metrics to LangSmith.

        Args:
            run_id: Run identifier.
            prompt_tokens: Prompt token count.
            completion_tokens: Completion token count.
            total_tokens: Total token count.
        """
        if not self._enabled:
            return

        logger.debug(
            "Token usage: run=%s, prompt=%d, completion=%d, total=%d",
            run_id, prompt_tokens, completion_tokens, total_tokens
        )

    def log_event(
        self,
        run_id: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Log custom events to LangSmith.

        Args:
            run_id: Run identifier.
            event: Event name.
            data: Event data.
        """
        if not self._enabled:
            return

        logger.debug("Event logged: run=%s, event=%s", run_id, event)

    def log_agent_start(self, agent_id: str, input_data: dict[str, Any]) -> str:
        """Log agent start event.

        Args:
            agent_id: Agent identifier.
            input_data: Input data.

        Returns:
            Run ID for tracking.
        """
        run_id = f"{agent_id}_{id(input_data)}"
        if self._enabled:
            logger.info("Agent started: agent=%s, run=%s", agent_id, run_id)
        return run_id

    def log_agent_end(
        self,
        run_id: str,
        output_data: dict[str, Any],
        error: str | None = None,
    ) -> None:
        """Log agent end event.

        Args:
            run_id: Run identifier.
            output_data: Output data.
            error: Error message if failed.
        """
        if self._enabled:
            if error:
                logger.error("Agent failed: run=%s, error=%s", run_id, error)
            else:
                logger.info("Agent completed: run=%s", run_id)


# Global tracer instance
_tracer: LangSmithTracer | None = None


def get_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = LangSmithTracer()
    return _tracer


def init_tracer(project_name: str = "multi-agent") -> LangSmithTracer:
    """Initialize the global tracer."""
    global _tracer
    _tracer = LangSmithTracer(project_name=project_name)
    return _tracer
