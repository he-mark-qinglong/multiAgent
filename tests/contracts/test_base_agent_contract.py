"""BaseReActAgent contract tests."""

import sys
sys.path.insert(0, '.')

import pytest
from core.models import AgentState
from agents.langgraph_agents import BaseReActAgent


class EchoAgent(BaseReActAgent):
    """Test agent that echoes the query."""

    def __init__(self):
        super().__init__(
            agent_id="echo",
            name="Echo",
            role="L1",
            system_prompt="Echo agent",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return f"thinking about: {state.user_query}"

    async def act(self, state: AgentState, thought: str) -> dict:
        return {
            "final_response": f"Echo: {state.user_query}",
            "metadata": {"_finished": True},
        }


class TestBaseReActAgentContract:
    """BaseReActAgent public API contract tests."""

    @pytest.fixture
    def agent(self):
        return EchoAgent()

    def test_run_returns_dict(self, agent):
        """run() returns dict."""
        import asyncio
        result = asyncio.run(agent.run("hello"))
        assert isinstance(result, dict)

    def test_run_returns_final_response(self, agent):
        """run() result contains final_response."""
        import asyncio
        result = asyncio.run(agent.run("hello"))
        assert "final_response" in result

    def test_stream_yields_chunks(self, agent):
        """stream() yields generator of dicts."""
        chunks = list(agent.stream("hello"))
        assert isinstance(chunks, list)
        assert all(isinstance(c, dict) for c in chunks)

    def test_stream_has_type_complete(self, agent):
        """stream() yields chunk with type='complete'."""
        chunks = list(agent.stream("hello"))
        types = [c.get("type") for c in chunks]
        assert "complete" in types

    def test_stream_chunk_has_agent_id(self, agent):
        """stream() chunks contain agent_id."""
        chunks = list(agent.stream("hello"))
        for chunk in chunks:
            assert "agent_id" in chunk

    def test_interrupt_and_wait_returns_dict(self, agent):
        """interrupt_and_wait() returns dict."""
        state = AgentState(user_query="test", needs_approval=True)
        result = agent.interrupt_and_wait("confirm?", state)
        assert isinstance(result, dict)

    def test_agent_has_agent_id(self, agent):
        """Agent has agent_id attribute."""
        assert agent.agent_id == "echo"

    def test_agent_has_name(self, agent):
        """Agent has name attribute."""
        assert agent.name == "Echo"

    def test_agent_has_role(self, agent):
        """Agent has role attribute."""
        assert agent.role == "L1"

    def test_agent_has_system_prompt(self, agent):
        """Agent has system_prompt attribute."""
        assert agent.system_prompt == "Echo agent"

    def test_agent_has_max_iterations(self, agent):
        """Agent has max_iterations attribute."""
        assert agent.max_iterations == 2
