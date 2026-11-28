"""Compatibility facade for the shared entity graph."""
from spine.entity_graph import *  # noqa: F401,F403
from spine.entity_graph import EntityGraph as EntityGraph

__all__ = ["EntityGraph"]
