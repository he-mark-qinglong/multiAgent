"""Agent implementations for the Multi-Agent Collaboration System."""

from core.base_agent import BaseAgent, AgentRole, ContextAssembler, ScopedContext

from agents.intent_agent import IntentAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.types import UserQuery, ExecutionResult, FinalResponse

__all__ = [
    "BaseAgent",
    "AgentRole",
    "ContextAssembler",
    "ScopedContext",
    "IntentAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "SynthesizerAgent",
    "UserQuery",
    "ExecutionResult",
    "FinalResponse",
]
