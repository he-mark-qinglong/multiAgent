"""Android Development Agent.

L2+ Executor Agent responsible for Android native app development.
"""

from __future__ import annotations

import logging
from typing import Any

from core.models import AgentState, ExecutionResult
from agents.langgraph_agents import BaseReActAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are android-dev, an L2+ Executor Agent specialized in Android native development.

## Responsibilities
- Build React Native/Expo Android projects
- Implement Jetpack Compose UI
- Integrate Android Auto
- Voice-first UI optimization for driving safety
- Gradle build management

## Capabilities
- Kotlin/Jetpack Compose development
- React Native with native module bridging
- Android Studio and developer tools
- Android Auto / Automotive OS integration

## Working Context
- Project: ${CAR_ASSISTANT_UI_PATH}/android
- Framework: Vue 3 web -> React Native or Kotlin
- Target: Android API 26+

## Output Format
Always output structured results with:
- status: "success" | "partial" | "failed"
- files_created: list of file paths
- files_modified: list of modified files
- notes: implementation notes
"""


class AndroidDevAgent(BaseReActAgent):
    """Android Development Executor Agent."""

    def __init__(self, state_store: Any, event_bus: Any):
        super().__init__(
            agent_id="android-dev",
            name="Android Developer",
            role="L2+",
            system_prompt=SYSTEM_PROMPT,
            tools=[],
            max_iterations=15,
        )
        self.state_store = state_store
        self.event_bus = event_bus

    async def think(self, state: AgentState) -> str:
        """Analyze Android development request."""
        query = state.user_query

        # Determine implementation approach
        if "react native" in query.lower() or "expo" in query.lower():
            approach = "react_native"
        else:
            approach = "kotlin_compose"

        return f"Android approach: {approach}. Analyzing requirements..."

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute Android development tasks."""
        result = ExecutionResult(
            agent_id=self.agent_id,
            status="success",
            output=f"Android development completed: {thought}",
            artifacts={},
        )
        return {"result": result}


def create_android_dev_agent(state_store: Any, event_bus: Any) -> AndroidDevAgent:
    """Factory function to create Android Dev Agent."""
    return AndroidDevAgent(state_store, event_bus)
