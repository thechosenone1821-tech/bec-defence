"""PLANE 3 — Local SLM client (llama.cpp / Ollama) with JSON grammar lock.

If no local model is reachable the client degrades to a deterministic
rule-based commander so the pipeline never blocks on AI availability. The
degradation is explicit: every response carries ``commander_mode``.

Environment:
    OLLAMA_HOST         default http://localhost:11434
    EIGENSHIELD_MODEL   default qwen3.5:4b
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from typing import Any, Dict, Optional

DEFAULT_MODEL = "qwen3.5:4b"


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


class SLMClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = 20.0):
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("EIGENSHIELD_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self._available: Optional[bool] = None
        self._checked_at = 0.0

    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        now = time.time()
        if self._available is not None and now - self._checked_at < 30:
            return self._available
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                self._available = resp.status == 200
        except Exception:
            self._available = False
        self._checked_at = now
        return self._available

    def mode(self) -> str:
        return "slm" if self.is_available() else "fallback_rules"

    # ------------------------------------------------------------------ #
    def complete_json(self, prompt: str, system: str = "") -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 700},
        }
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
            content = (body.get("message") or {}).get("content", "")
            return _extract_json(content)
        except Exception:
            return None
