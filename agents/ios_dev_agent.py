"""iOS Development Agent.

L2+ Executor Agent responsible for iOS native app development.
"""

from __future__ import annotations

import logging
from typing import Any

from core.models import AgentState, ExecutionResult
from agents.langgraph_agents import BaseReActAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are iOS-dev, an L2+ Executor Agent specialized in iOS native development.

## Responsibilities
- Build React Native/Expo iOS projects
- Implement SwiftUI native modules
- Integrate Apple CarPlay
- Voice-first UI optimization for driving safety
- Xcode project management

## Capabilities
- Swift/SwiftUI development
- React Native with native module bridging
- Apple developer tools (Xcode, Instruments)
- CarPlay framework integration

## Working Context
- Project: ${CAR_ASSISTANT_UI_PATH}/ios
- Framework: Vue 3 web -> React Native or SwiftUI
- Target: iOS 15.0+

## Output Format
Always output structured results with:
- status: "success" | "partial" | "failed"
- files_created: list of file paths
- files_modified: list of modified files
- notes: implementation notes
"""


class IOSDevAgent(BaseReActAgent):
    """iOS Development Executor Agent."""

    def __init__(self, state_store: Any, event_bus: Any):
        super().__init__(
            agent_id="ios-dev",
            name="iOS Developer",
            role="L2+",
            system_prompt=SYSTEM_PROMPT,
            tools=[],
            max_iterations=15,
        )
        self.state_store = state_store
        self.event_bus = event_bus

    async def think(self, state: AgentState) -> str:
        """Analyze iOS development request."""
        query = state.user_query

        # Determine implementation approach
        if "react native" in query.lower() or "expo" in query.lower():
            approach = "react_native"
        else:
            approach = "swiftui"

        return f"iOS approach: {approach}. Analyzing requirements..."

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute iOS development tasks."""
        result = ExecutionResult(
            agent_id=self.agent_id,
            status="success",
            output=f"iOS development completed: {thought}",
            artifacts={},
        )
        return {"result": result}


def create_ios_dev_agent(state_store: Any, event_bus: Any) -> IOSDevAgent:
    """Factory function to create iOS Dev Agent."""
    return IOSDevAgent(state_store, event_bus)
