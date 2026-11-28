"""Structured JSON logging.

One line per event, machine-parseable, no multi-line stack traces inline
(exc_info is folded into the record). Levels follow RAKSHA_LOG_LEVEL.
"""

from __future__ import annotations

import json
import logging
import sys
import time

_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_text", "stack_info", "lineno", "funcName", "created",
    "msecs", "relativeCreated", "thread", "threadName", "processName",
    "process", "taskName", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                out[key] = value
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=True, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    try:
        root.setLevel(getattr(logging, level.upper()))
    except AttributeError:
        root.setLevel(logging.INFO)
    # Uvicorn's loggers otherwise double-log through their own handlers.
    for noisy in ("uvicorn.access", "uvicorn", "uvicorn.error"):
        lg = logging.getLogger(noisy)
        lg.handlers[:] = []
        lg.propagate = True
