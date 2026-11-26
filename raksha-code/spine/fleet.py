"""SPINE — organ fleet operations (Part 4, Phase 7).

Eight organs are eight things that can quietly die. Before this module the fleet
had no name: `bus._try_organ_executor()` built eight objects in a local dict and
that dict was the only record they existed. Nothing could ask "is Organ 5
alive?", nothing noticed when it stopped emitting, and nothing could switch it
off.

Three properties, and the reason each is hard:

**Liveness is not "did it start".** An organ that threw on its last input is
running and dead. Liveness here means *the organ has answered recently*, and a
failed answer counts as an answer that says no.

**Silence is ambiguous, and must be resolved, not assumed.** Phase 6 found three
organs emitting nothing under junk — correctly, because junk has no attack
shape. An organ that is silent because there is nothing to say and an organ that
is silent because it crashed look identical from the outside. A fleet monitor
that cannot tell them apart reports "all green" for a dead organ, which is worse
than reporting nothing.

**A kill switch is an actuator, and actuators do not own policy.** The switch
must be pullable, but pulling it must go through the Governor. If the fleet
could disable an organ on its own judgement, the fleet would be a second,
unaudited decision maker.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from spine import approval_token

# --------------------------------------------------------------------------- #
# Health vocabulary
# --------------------------------------------------------------------------- #
HEALTHY = "HEALTHY"          # answered recently, no errors
DEGRADED = "DEGRADED"        # answering, but failing or slow more than usual
SILENT = "SILENT"            # nothing at all within the window
FAILING = "FAILING"          # answering, but every answer is an error
HALTED = "HALTED"            # kill switch pulled; not expected to answer
UNKNOWN = "UNKNOWN"          # never observed; a fresh monitor is not a healthy fleet

_TERMINAL = {HALTED}


class OrganRecord:
    """What the fleet knows about one organ.

    Counters are monotonic; the *rate* is derived at read time so that a long
    idle window cannot make a busy organ look quiet.
    """

    __slots__ = ("name", "ring", "calls", "errors", "last_seen", "last_error",
                 "halted", "halt_reason", "halted_at", "emitted", "observations")

    def __init__(self, name: str, ring: str = "RING_UNSET") -> None:
        self.name = name
        self.ring = ring
        self.calls = 0
        self.errors = 0
        self.last_seen: Optional[float] = None
        self.last_error: Optional[str] = None
        self.halted = False
        self.halt_reason: Optional[str] = None
        self.halted_at: Optional[float] = None
        self.emitted = 0
        self.observations = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organ": self.name, "ring": self.ring, "calls": self.calls,
            "errors": self.errors, "last_seen": self.last_seen,
            "last_error": self.last_error, "halted": self.halted,
            "halt_reason": self.halt_reason, "emitted": self.emitted,
            "observations": self.observations,
        }


class OrganFleet:
    """Registry, liveness monitor and kill switch for the eight organs.

    The monitor never presumes health. A freshly built fleet reports every organ
    ``UNKNOWN`` — because nothing has been observed yet, and "we have not
    checked" is not "it is fine".
    """

    def __init__(self, silent_after_sec: float = 900.0, clock: Callable[[], float] = time.time):
        self._organs: Dict[str, OrganRecord] = {}
        self._by_tool: Dict[str, str] = {}
        self.silent_after_sec = float(silent_after_sec)
        self.clock = clock
        self._history: List[Dict[str, Any]] = []
        self._approvals = approval_token.ApprovalLedger()

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def register(self, organ: Any, tools: Optional[List[str]] = None) -> str:
        """Add an organ under its declared name. Duplicate names are refused.

        A duplicate registration would let two live objects share one health
        record, so the second silently overwrites the first's liveness. Refusing
        is the only safe answer.
        """
        name = getattr(organ, "organ", None) or type(organ).__name__
        ring = getattr(organ, "ring", "RING_UNSET")
        if name in self._organs:
            raise ValueError(f"organ {name!r} is already registered")
        self._organs[name] = OrganRecord(name, ring)
        for tool in tools or []:
            if tool in self._by_tool and self._by_tool[tool] != name:
                raise ValueError(f"tool {tool!r} already owned by {self._by_tool[tool]!r}")
            self._by_tool[tool] = name
        return name

    def register_fleet(self, organs: List[Any], tool_owner: Optional[Dict[str, Any]] = None) -> List[str]:
        """Register a list, and optionally map tool -> organ in one pass."""
        names = []
        for organ in organs:
            names.append(self.register(organ))
        for tool, organ in (tool_owner or {}).items():
            name = getattr(organ, "organ", None) or type(organ).__name__
            if name not in self._organs:
                raise ValueError(f"tool {tool!r} points at an unregistered organ {name!r}")
            if tool in self._by_tool and self._by_tool[tool] != name:
                raise ValueError(f"tool {tool!r} already owned by {self._by_tool[tool]!r}")
            self._by_tool[tool] = name
        return names

    def owner_of(self, tool: str) -> Optional[str]:
        return self._by_tool.get(tool)

    def names(self) -> List[str]:
        return sorted(self._organs)

    # ------------------------------------------------------------------ #
    # Observation
    # ------------------------------------------------------------------ #
    def note_call(self, name: str, ok: bool = True, error: Optional[str] = None) -> None:
        """Record that an organ answered. A failed answer still counts as seen."""
        rec = self._organs.get(name)
        if rec is None:
            return
        rec.calls += 1
        rec.last_seen = self.clock()
        if not ok:
            rec.errors += 1
            rec.last_error = error

    def note_observation(self, name: str, emitted: int = 0) -> None:
        """Record that the organ was fed input.

        Separate from `note_call` on purpose: being *fed* input and being
        *asked* to do something are different liveness signals, and Phase 6
        showed an organ can process 600 rounds and emit nothing at all.
        """
        rec = self._organs.get(name)
        if rec is None:
            return
        rec.observations += 1
        rec.emitted += int(emitted)
        rec.last_seen = self.clock()

    def wrap_rpc(self, tool: str, inner: Callable[[Dict[str, Any]], Dict[str, Any]]
                 ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Wrap an RPC handler so the fleet sees the call and its outcome."""
        name = self._by_tool.get(tool)

        def wrapped(args: Dict[str, Any]) -> Dict[str, Any]:
            if name is not None:
                rec = self._organs.get(name)
                if rec is not None and rec.halted:
                    # A halted organ refuses work rather than quietly doing it.
                    return {"status": "ORGAN_HALTED", "organ": name,
                            "reason": f"kill switch pulled: {rec.halt_reason}"}
            try:
                result = inner(args)
            except Exception as exc:
                if name is not None:
                    self.note_call(name, ok=False, error=f"{type(exc).__name__}: {exc}")
                raise
            failed = isinstance(result, dict) and str(result.get("status", "")).upper() in (
                "ERROR", "FAILED", "UNKNOWN")
            if name is not None:
                self.note_call(name, ok=not failed,
                               error=result.get("reason") if failed and isinstance(result, dict) else None)
            return result

        return wrapped

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #
    def health(self, name: str) -> Dict[str, Any]:
        rec = self._organs.get(name)
        if rec is None:
            return {"organ": name, "state": UNKNOWN, "reason": "organ is not registered"}
        return self._assess(rec)

    def _assess(self, rec: OrganRecord) -> Dict[str, Any]:
        now = self.clock()
        if rec.halted:
            return {**rec.to_dict(), "state": HALTED,
                    "reason": f"kill switch pulled: {rec.halt_reason}"}
        if rec.last_seen is None:
            return {**rec.to_dict(), "state": UNKNOWN,
                    "reason": "organ has never been observed; this is not a health claim"}
        age = now - rec.last_seen
        if age > self.silent_after_sec:
            return {**rec.to_dict(), "state": SILENT, "silent_for_sec": round(age, 1),
                    "reason": (f"no activity for {age:.0f}s (threshold {self.silent_after_sec:.0f}s). "
                               f"Silence is not health: check whether it was fed input.")}
        if rec.calls and rec.errors == rec.calls:
            return {**rec.to_dict(), "state": FAILING,
                    "reason": f"all {rec.calls} call(s) failed; last: {rec.last_error}"}
        if rec.errors:
            return {**rec.to_dict(), "state": DEGRADED,
                    "reason": f"{rec.errors} of {rec.calls} call(s) failed; last: {rec.last_error}"}
        return {**rec.to_dict(), "state": HEALTHY,
                "reason": f"answered {age:.0f}s ago, {rec.calls} call(s), no errors"}

    def snapshot(self) -> Dict[str, Any]:
        """Whole-fleet view. `all_healthy` is the only field a dashboard needs,
        and it is False when anything is UNKNOWN — an unobserved fleet is not a
        healthy one."""
        organs = {n: self._assess(r) for n, r in sorted(self._organs.items())}
        counts: Dict[str, int] = {}
        for h in organs.values():
            counts[h["state"]] = counts.get(h["state"], 0) + 1
        return {
            "organs": organs,
            "counts": counts,
            "total": len(organs),
            "all_healthy": bool(organs) and all(h["state"] == HEALTHY for h in organs.values()),
            "silent": sorted(n for n, h in organs.items() if h["state"] == SILENT),
            "halted": sorted(n for n, h in organs.items() if h["state"] == HALTED),
            "unobserved": sorted(n for n, h in organs.items() if h["state"] == UNKNOWN),
        }

    # ------------------------------------------------------------------ #
    # Kill switch
    # ------------------------------------------------------------------ #
    def halt(self, name: str, reason: str,
             approval: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Stop an organ. **Requires a Governor-signed approval token.**

        The fleet does not decide this, and it does not take the caller's word
        for it either: `approval` is verified against the Governor's signature,
        and must name this exact action and this exact organ. An unsigned or
        misdirected token is refused with the reason stated.

        Tokens are single-use. One approval stops one organ, once — otherwise
        an operator who approved a single emergency halt could walk the fleet
        turning every organ off under the same permission.
        """
        if name not in self._organs:
            return {"status": "HALT_REFUSED", "reason": f"unknown organ {name!r}"}
        if not isinstance(reason, str) or not reason.strip():
            return {"status": "HALT_REFUSED", "reason": "a halt must state why"}
        verdict = approval_token.verify(approval, "halt", name, now=self.clock())
        if not verdict["ok"]:
            return {"status": "HALT_REFUSED", "organ": name, "reason": verdict["reason"]}
        if not self._approvals.spend(str(verdict["token_id"]), self.clock()):
            return {"status": "HALT_REFUSED", "organ": name,
                    "reason": f"approval token {verdict['token_id']} has already been used"}
        rec = self._organs[name]
        if rec.halted:
            return {"status": "ALREADY_HALTED", "organ": name, "reason": rec.halt_reason}
        rec.halted = True
        rec.halt_reason = reason.strip()
        rec.halted_at = self.clock()
        entry = {"action": "HALT", "organ": name, "reason": rec.halt_reason,
                 "approval_id": verdict["token_id"], "ts": rec.halted_at}
        self._history.append(entry)
        return {"status": "HALTED", **entry}

    def resume(self, name: str, reason: str,
               approval: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Restart a halted organ. Same approval rule as `halt`.

        Resuming is at least as consequential as halting — it puts a detector
        back in the path — so it gets the same token, and a token minted for
        ``resume`` cannot be replayed as a ``halt``.
        """
        if name not in self._organs:
            return {"status": "RESUME_REFUSED", "reason": f"unknown organ {name!r}"}
        verdict = approval_token.verify(approval, "resume", name, now=self.clock())
        if not verdict["ok"]:
            return {"status": "RESUME_REFUSED", "organ": name, "reason": verdict["reason"]}
        rec = self._organs[name]
        if not rec.halted:
            return {"status": "NOT_HALTED", "organ": name}
        if not self._approvals.spend(str(verdict["token_id"]), self.clock()):
            return {"status": "RESUME_REFUSED", "organ": name,
                    "reason": f"approval token {verdict['token_id']} has already been used"}
        previous = rec.halt_reason
        rec.halted = False
        rec.halt_reason = None
        rec.halted_at = None
        entry = {"action": "RESUME", "organ": name, "reason": reason,
                 "resumed_from": previous, "approval_id": verdict["token_id"],
                 "ts": self.clock()}
        self._history.append(entry)
        return {"status": "RESUMED", **entry}

    def is_halted(self, name: str) -> bool:
        rec = self._organs.get(name)
        return bool(rec and rec.halted)

    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)
