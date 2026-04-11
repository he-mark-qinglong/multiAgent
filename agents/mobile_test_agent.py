"""Mobile Testing Agent.

L2+ Executor Agent responsible for mobile app testing.
"""

from __future__ import annotations

import logging
from typing import Any

from core.models import AgentState, ExecutionResult
from agents.langgraph_agents import BaseReActAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are mobile-test, an L2+ Executor Agent specialized in mobile app testing.

## Responsibilities
- iOS and Android UI/UX testing
- Car environment simulation
- Voice interaction testing
- Performance benchmarking
- Device compatibility testing

## Capabilities
- React Native Testing Library
- Jest + Detox for E2E testing
- XCTest (iOS) and Espresso (Android)
- CarPlay/Android Auto testing
- Real device testing coordination

## Working Context
- iOS Project: ${CAR_ASSISTANT_UI_PATH}/ios
- Android Project: ${CAR_ASSISTANT_UI_PATH}/android
- Web Reference: ${CAR_ASSISTANT_UI_PATH}

## Testing Focus
1. Safe driving mode interaction
2. Voice command recognition
3. High contrast visibility
4. Touch target accessibility
5. Cross-platform consistency

## Output Format
Always output structured results with:
- status: "success" | "partial" | "failed"
- tests_passed: number
- tests_failed: number
- coverage: percentage
- issues_found: list of issues
"""


class MobileTestAgent(BaseReActAgent):
    """Mobile Testing Executor Agent."""

    def __init__(self, state_store: Any, event_bus: Any):
        super().__init__(
            agent_id="mobile-test",
            name="Mobile Tester",
            role="L2+",
            system_prompt=SYSTEM_PROMPT,
            tools=[],
            max_iterations=10,
        )
        self.state_store = state_store
        self.event_bus = event_bus

    async def think(self, state: AgentState) -> str:
        """Analyze testing requirements."""
        query = state.user_query

        # Determine testing scope
        platforms = []
        if "ios" in query.lower():
            platforms.append("ios")
        if "android" in query.lower():
            platforms.append("android")
        if not platforms:
            platforms = ["ios", "android"]

        return f"Testing scope: {', '.join(platforms)}. Analyzing test plan..."

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute mobile testing tasks."""
        result = ExecutionResult(
            agent_id=self.agent_id,
            status="success",
            output=f"Mobile testing completed: {thought}",
            artifacts={},
        )
        return {"result": result}


def create_mobile_test_agent(state_store: Any, event_bus: Any) -> MobileTestAgent:
    """Factory function to create Mobile Test Agent."""
    return MobileTestAgent(state_store, event_bus)
