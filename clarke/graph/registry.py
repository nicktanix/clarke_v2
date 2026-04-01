"""Graph compilation and registry with checkpointing."""

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from clarke.graph.workflow import build_graph


@lru_cache
def get_compiled_workflow() -> CompiledStateGraph:
    """Build and compile the broker workflow graph with checkpointing.

    Uses MemorySaver for in-process checkpointing (spec §7.2).
    Enables deterministic resume and replay via thread_id.
    """
    graph = build_graph()
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
