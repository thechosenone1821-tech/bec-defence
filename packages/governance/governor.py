"""Compatibility facade for the shipped Governor."""
from spine.governor import *  # noqa: F401,F403
from spine.governor import PolicyEngine as PolicyEngine

__all__ = ["PolicyEngine"]
