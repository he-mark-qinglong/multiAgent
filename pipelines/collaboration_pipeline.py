"""Collaboration Pipeline - LangGraph orchestration with stream() + HITL.

This module provides the primary entry point for the multi-agent pipeline.

Core Design (from 04-architecture-principles.md):
- ReAct 循环 (内部) → 结构化输出 → Streaming (外层展示)
- interrupt() 用于需要人工审批的操作
- Checkpointer 保存中断点状态

Usage:
    from pipelines.collaboration_pipeline import CollaborationPipeline

    # Simple usage
    pipeline = CollaborationPipeline()
    result = pipeline.invoke("Search for AI news")

    # With streaming
    for chunk in pipeline.stream("Search for AI news"):
        if chunk["type"] == "result":
            print(chunk["data"]["final_response"])

    # With HITL
    pipeline.request_approval(thread_id, "delete", "将删除文件...")
    # ... show approval UI ...
    pipeline.submit_approval(thread_id, approved=True)
"""

from __future__ import annotations

import logging
from typing import Any, Generator

from core.models import UserQuery, FinalResponse
from core.langgraph_integration import PipelineStateGraph, HumanApprovalManager
from core.langsmith_integration import setup_langsmith, LangSmithTracer

logger = logging.getLogger(__name__)


class CollaborationPipeline:
    """Main pipeline for multi-agent collaboration.

    Features:
    - LangGraph StateGraph orchestration
    - ReAct agents (internal reasoning loop)
    - stream() outputs final structured results only
    - interrupt() + HITL for human approval
    - Checkpointer for state persistence
    - LangSmith tracing integration
    """

    def __init__(
        self,
        langsmith_project: str = "multi-agent",
        enable_tracing: bool = True,
    ):
        """Initialize the pipeline.

        Args:
            langsmith_project: LangSmith project name.
            enable_tracing: Enable LangSmith tracing.
        """
        self.tracer = LangSmithTracer(project_name=langsmith_project)

        if enable_tracing:
            setup_langsmith(project_name=langsmith_project)

        self.graph = PipelineStateGraph()
        self.approval_manager = HumanApprovalManager(self.graph)

        logger.info("CollaborationPipeline initialized")

    def invoke(
        self,
        query: str | UserQuery,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous invoke.

        Args:
            query: User query string or UserQuery object.
            thread_id: Thread ID for persistence.

        Returns:
            Final state with final_response.
        """
        if isinstance(query, str):
            query = UserQuery(query=query)

        thread_id = thread_id or query.session_id
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.graph.invoke(query, config=config)
            return result
        except Exception as e:
            logger.error("Pipeline invoke error: %s", e)
            raise

    def stream(
        self,
        query: str | UserQuery,
        thread_id: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Streaming invoke.

        IMPORTANT: This streams the FINAL structured result,
        NOT intermediate ReAct steps.

        ReAct loop runs fully internally for consistency,
        then final result is streamed to the client.

        Args:
            query: User query.
            thread_id: Thread ID for persistence.

        Yields:
            Stream chunks with final result.
        """
        if isinstance(query, str):
            query = UserQuery(query=query)

        thread_id = thread_id or query.session_id

        try:
            result = self.invoke(query, thread_id)

            # Stream structured output (not tokens)
            yield {
                "type": "result",
                "data": {
                    "final_response": result.get("final_response", ""),
                    "intent_chain": result.get("intent_chain"),
                    "execution_results": result.get("execution_results", {}),
                }
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    def request_approval(
        self,
        thread_id: str,
        action: str,
        details: str,
    ) -> str:
        """Request human approval.

        Args:
            thread_id: Thread identifier.
            action: Action to approve.
            details: Action details.

        Returns:
            Approval ID.
        """
        return self.approval_manager.request_approval(thread_id, action, details)

    def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
        """Get pending approval for thread.

        Args:
            thread_id: Thread identifier.

        Returns:
            Pending approval details or None.
        """
        return self.approval_manager.get_pending(thread_id)

    def submit_approval(
        self,
        thread_id: str,
        approved: bool,
        reason: str = "",
    ) -> dict[str, Any]:
        """Submit approval and resume pipeline execution.

        Args:
            thread_id: Thread identifier.
            approved: True to approve, False to reject.
            reason: Approval/rejection reason.

        Returns:
            Updated state after resume.
        """
        return self.approval_manager.submit_approval(thread_id, approved, reason)

    def get_checkpointer(self) -> Any:
        """Get the checkpointer for persistence."""
        return self.graph.checkpointer

    def get_state_history(self, thread_id: str) -> list[dict[str, Any]]:
        """Get conversation history for a thread.

        Args:
            thread_id: Thread identifier.

        Returns:
            List of checkpoint states.
        """
        if not hasattr(self.graph, '_graph') or not self.graph._graph:
            return []

        try:
            config = {"configurable": {"thread_id": thread_id}}
            history = list(self.graph._graph.get_state_history(config))
            return [
                {
                    "config": str(h.config),
                    "next_nodes": list(h.next) if h.next else [],
                }
                for h in history
            ]
        except Exception as e:
            logger.error("Failed to get state history: %s", e)
            return []


# Usage Example:
"""
from pipelines.collaboration_pipeline import CollaborationPipeline

# Create pipeline
pipeline = CollaborationPipeline()

# Simple invoke
result = pipeline.invoke("帮我搜索AI最新进展")
print(result["final_response"])

# Streaming
for chunk in pipeline.stream("搜索天气"):
    if chunk["type"] == "result":
        print(chunk["data"]["final_response"])
    elif chunk["type"] == "error":
        print(f"Error: {chunk['error']}")

# With HITL
approval_id = pipeline.request_approval(
    thread_id="session_123",
    action="execute_code",
    details="将执行: rm -rf /tmp/test"
)
# ... show approval UI to user ...

# User approves or rejects
result = pipeline.submit_approval(
    thread_id="session_123",
    approved=True,
    reason="确认执行"
)
"""
