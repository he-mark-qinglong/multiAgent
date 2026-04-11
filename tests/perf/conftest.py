"""Shared fixtures for performance tests."""

import sys
sys.path.insert(0, '.')

import pytest
from pipelines.collaboration_pipeline import CollaborationPipeline
from core.event_bus import EventBus


@pytest.fixture(scope="session")
def shared_pipeline():
    """Shared pipeline instance for perf tests."""
    return CollaborationPipeline(enable_tracing=False)


@pytest.fixture(scope="session")
def shared_event_bus():
    """Shared event bus for perf tests."""
    return EventBus()


@pytest.fixture
def perf_pipeline(shared_pipeline):
    """Fresh pipeline per test."""
    return shared_pipeline


@pytest.fixture
def perf_event_bus(shared_event_bus):
    """Fresh event bus per test."""
    return shared_event_bus
