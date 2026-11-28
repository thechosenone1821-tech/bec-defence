"""Compatibility facade for the shared sanitizer rules."""
from spine.sanitizer import *  # noqa: F401,F403
from spine.sanitizer import (  # noqa: F401
    DEFAULT_SALT,
    clean_reason,
    digest,
    get_salt,
    looks_like_injection,
    opaque_token,
    sanitize_batch,
    sanitize_event,
)

__all__ = [
    "DEFAULT_SALT", "clean_reason", "digest", "get_salt",
    "looks_like_injection", "opaque_token", "sanitize_batch", "sanitize_event",
]
