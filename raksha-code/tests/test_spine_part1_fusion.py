"""CITIZEN SPINE — PART ONE: the Signal Fusion Core.

The six invariants from `specs/01c_citizen_spine_four_parts.md` §Part One, each
as executable property tests:

  1. Monotone        adding evidence never lowers the score
  2. Bounded         the score is always in [0, 1]
  3. Order-free      input order cannot change the score
  4. Total           nothing raises; every input yields a band and a reason
  5. Conservative    absence of evidence never produces a band above LOW_CONFIDENCE
  6. Traceable       every band names the rules that produced it

These are properties, not examples. An example test says "this clip gives 0.65";
a property test says "no arrangement of these inputs can produce 1.4", and the
second one is what a fraud screen actually needs.
"""

import itertools
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.risk import assess
from citizen.risk import fusion as FU
from citizen.risk.fusion import (BAND_CRITICAL, BAND_ELEVATED, BAND_HIGH,
                                 BAND_LOW, BAND_LOW_CONFIDENCE, BANDS, band_for,
                                 clamp01, evaluate, noisy_or, safe_bool, safe_float,
                                 safe_int)
from citizen.voiceguard import i18n


# --------------------------------------------------------------------------- #
# 0. Part One must not contain presentation
# --------------------------------------------------------------------------- #
class TestSeparation:
    def test_fusion_module_contains_no_citizen_facing_sentences(self):
        """Part 1 decides how much evidence there is; Part 2 decides what to say.
        A stray English sentence here means the boundary has leaked, and the next
        person to translate the app will not find it."""
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "risk", "fusion.py"), encoding="utf-8").read()
        # The only allowed prose is in comments/docstrings and skip reasons, which
        # are developer diagnostics. A verdict sentence would contain these words.
        for banned in ("hang up", "OTP, PIN", "1930 पर", "డబ్బు ఇవ్వద్దు"):
            assert banned not in src, f"presentation leaked into Part One: {banned}"

    def test_fusion_module_has_no_io(self):
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "risk", "fusion.py"), encoding="utf-8").read()
        for banned in ("open(", "requests.", "urllib", "fetch", "sqlite"):
            assert banned not in src, f"I/O in the fusion core: {banned}"

    def test_evaluate_takes_no_language_argument(self):
        """If it needs a language, it is doing Part Two's job."""
        import inspect
        assert "lang" not in inspect.signature(evaluate).parameters


# --------------------------------------------------------------------------- #
# 1. Monotone
# --------------------------------------------------------------------------- #
class TestMonotone:
    def test_adding_any_signal_never_lowers_the_score(self):
        sources = [
            {"voice": {"verdict": "SUSPICIOUS"}},
            {"voice": {"verdict": "LIKELY_SYNTHETIC"}},
            {"message": {"verdict": "HIGH"}},
            {"message": {"verdict": "CRITICAL"}},
            {"campaign_linked": True},
            {"repeat_contacts": 4},
            {"user_doubt": True},
        ]
        base = {k: v for k, v in
                (("voice", None), ("message", None), ("campaign_linked", False),
                 ("repeat_contacts", 0), ("user_doubt", False))}

        for r in range(1, len(sources) + 1):
            for combo in itertools.combinations(sources, r):
                kwargs = dict(base)
                kwargs.update({k: v for d in combo for k, v in d.items()})
                score = evaluate(**kwargs)["score"]
                # Every subset must be at most the full-set score.
                full = dict(base)
                for d in sources:
                    full.update(d)
                assert score <= evaluate(**full)["score"] + 1e-9

    def test_strictly_increases_when_a_real_signal_is_added(self):
        a = evaluate()["score"]
        b = evaluate(campaign_linked=True)["score"]
        assert b > a

    def test_upgrading_a_verdict_never_lowers_the_score(self):
        sus = evaluate(voice={"verdict": "SUSPICIOUS"})["score"]
        syn = evaluate(voice={"verdict": "LIKELY_SYNTHETIC"})["score"]
        assert syn > sus


# --------------------------------------------------------------------------- #
# 2. Bounded
# --------------------------------------------------------------------------- #
class TestBounded:
    def test_score_is_always_within_zero_and_one(self):
        extreme = dict(voice={"verdict": "LIKELY_SYNTHETIC"},
                       message={"verdict": "CRITICAL"},
                       campaign_linked=True, repeat_contacts=999, user_doubt=True)
        r = evaluate(**extreme)
        assert 0.0 <= r["score"] <= 1.0

    def test_the_scale_is_reachable_not_just_bounded(self):
        """Bounded above is not the same as able to reach the top.

        A ceiling on the fused score (say, capping at 0.5) still satisfies
        0 <= score <= 1 and would keep every other test here green, while
        quietly making CRITICAL unreachable. A tool that cannot escalate to
        its own worst band is broken in the direction that hurts most, so
        pin the top of the scale from below.
        """
        extreme = dict(voice={"verdict": "LIKELY_SYNTHETIC"},
                       message={"verdict": "CRITICAL"},
                       campaign_linked=True, repeat_contacts=999, user_doubt=True)
        r = evaluate(**extreme)
        # The real floor of the worst band: `_BAND_TABLE` maps (upper_limit, band),
        # so a band's floor is the previous row's limit. Derived rather than
        # hard-coded so this still means something if the bands are retuned.
        limits = [lim for lim, _ in FU._BAND_TABLE]
        names = [b for _, b in FU._BAND_TABLE]
        critical_floor = limits[names.index(BAND_CRITICAL) - 1]
        assert r["score"] >= critical_floor, (
            f"worst-case evidence fused to {r['score']}, below the "
            f"{BAND_CRITICAL} floor of {critical_floor}")
        assert r["band"] == BAND_CRITICAL

    @pytest.mark.xfail(strict=True, reason=(
        "KNOWN DEFECT (Part One, found by mutation testing): band LOW is "
        "provably unreachable. The input space is finite - 5 sources with "
        "fixed weights - so the score set can be enumerated exactly. The "
        "cheapest corroborated evidence is user_doubt(0.15) + "
        "repeat_contact(0.20), which noisy-or fuses to 0.32, already above "
        "LOW's ceiling of 0.20. So the ladder jumps LOW_CONFIDENCE -> "
        "ELEVATED and no citizen ever sees a mild warning. Fixing it means "
        "retuning _BAND_TABLE, which reclassifies citizen-facing severity, "
        "so it needs an explicit decision rather than a silent edit. "
        "Recommended: ceilings 0.40 / 0.60 / 0.80 / 1.01. strict=True so "
        "this flips to a failure the moment the thresholds are retuned, "
        "forcing the marker to be removed rather than forgotten."))
    def test_every_declared_band_is_reachable(self):
        """Every declared band must be attainable by some real evidence set.

        Otherwise the band list is decoration: a band no input can select
        would never appear in production, and nobody would notice.
        """
        seen = set()
        for voice in (None, {"verdict": "SUSPICIOUS"}, {"verdict": "LIKELY_SYNTHETIC"}):
            for message in (None, {"verdict": "HIGH"}, {"verdict": "CRITICAL"}):
                for camp in (False, True):
                    for rep in (0, 3):
                        for doubt in (False, True):
                            seen.add(evaluate(voice=voice, message=message,
                                              campaign_linked=camp,
                                              repeat_contacts=rep,
                                              user_doubt=doubt)["band"])
        assert seen == set(BANDS), f"unreachable bands: {sorted(set(BANDS) - seen)}"

    @pytest.mark.parametrize("weights", [
        [], [0.0], [1.0], [0.9, 0.9, 0.9, 0.9, 0.9], [-5.0], [2.0], [1e9],
        [float("nan")], [float("inf")], [None], ["x"],
    ])
    def test_noisy_or_is_bounded_for_any_input(self, weights):
        v = noisy_or(weights)
        assert 0.0 <= v <= 1.0
        assert v == v          # never NaN

    def test_clamp_handles_junk(self):
        for junk in (None, "x", float("nan"), float("inf"), -1e9, 1e9):
            assert 0.0 <= clamp01(junk) <= 1.0


# --------------------------------------------------------------------------- #
# 3. Order-free
# --------------------------------------------------------------------------- #
class TestOrderFree:
    def test_kwarg_order_is_meaningless_and_not_worth_testing(self):
        """Kept only to record why the obvious version of this test is useless.

        `evaluate(**{"a": 1, "b": 2})` and `evaluate(**{"b": 2, "a": 1})` build
        the same dict in CPython, so asserting they agree is a tautology - it
        cannot fail on any implementation. The order that genuinely matters is
        the iteration order of `RULES`, which `evaluate` does depend on. That
        is what `test_shuffling_the_rule_table_cannot_change_verdicts` pins.
        """
        a = evaluate(voice={"verdict": "SUSPICIOUS"}, campaign_linked=True)
        b = evaluate(**{"campaign_linked": True, "voice": {"verdict": "SUSPICIOUS"}})
        assert a == b

    def test_shuffling_the_rule_table_cannot_change_verdicts(self, monkeypatch):
        """The verdict must not depend on the order rules happen to be listed.

        `evaluate` walks `RULES` in insertion order. Reordering that dict is a
        natural thing for someone to do (alphabetical, "most important first"),
        and it must be a cosmetic change. A fusion that took the first strong
        signal, or short-circuited, would silently change every verdict.
        """
        args = dict(voice={"verdict": "SUSPICIOUS"}, message={"verdict": "HIGH"},
                    campaign_linked=True, repeat_contacts=3, user_doubt=True)
        baseline = evaluate(**args)
        original = list(FU.RULES.items())

        for perm in itertools.permutations(original):
            monkeypatch.setattr(FU, "RULES", dict(perm))
            r = evaluate(**args)
            order = [s for s, _ in perm]
            assert r["score"] == baseline["score"], f"score moved for rule order {order}"
            assert r["band"] == baseline["band"], f"band moved for rule order {order}"
            assert r["sources_fired"] == baseline["sources_fired"]
            assert {s["source"] for s in r["signals"]} == \
                   {s["source"] for s in baseline["signals"]}
            assert sorted(r["weights_used"]) == sorted(baseline["weights_used"])

    def test_noisy_or_is_permutation_invariant(self):
        ws = [0.15, 0.45, 0.65]
        values = {round(noisy_or(list(p)), 12) for p in itertools.permutations(ws)}
        assert len(values) == 1


# --------------------------------------------------------------------------- #
# 4. Total — nothing raises
# --------------------------------------------------------------------------- #
_JUNK = [None, "", " ", "abc", 0, -1, 1, 3.9, float("nan"), float("inf"),
         [], [1, 2], {}, {"a": 1}, object(), True, False]


class TestTotal:
    @pytest.mark.parametrize("junk", _JUNK)
    def test_evaluate_never_raises_for_junk_voice(self, junk):
        json.dumps(evaluate(voice=junk), allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_evaluate_never_raises_for_junk_message(self, junk):
        json.dumps(evaluate(message=junk), allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_evaluate_never_raises_for_junk_counters(self, junk):
        json.dumps(evaluate(repeat_contacts=junk, campaign_linked=junk,
                            user_doubt=junk), allow_nan=False)

    def test_every_result_carries_a_band_and_a_reason(self):
        r = evaluate()
        assert r["band"] in BANDS
        assert r["band_reason"]

    def test_a_broken_rule_cannot_break_the_screen(self, monkeypatch):
        """A rule that raises must be skipped and reported, not propagated."""
        def boom(_payload):
            raise RuntimeError("rule exploded")
        monkeypatch.setitem(FU.RULES, "voice", boom)
        r = evaluate(voice={"verdict": "LIKELY_SYNTHETIC"})
        assert r["band"] in BANDS
        skip = [s for s in r["skipped"] if s["source"] == "voice"][0]
        assert "error" in skip["reason"].lower()


class TestCoercion:
    def test_safe_bool_rejects_truthy_strings(self):
        assert safe_bool("nope") is False
        assert safe_bool("false") is False
        assert safe_bool("") is False
        assert safe_bool([]) is False
        assert safe_bool({"a": 1}) is False

    def test_safe_bool_accepts_explicit_truth(self):
        for v in (True, 1, "true", "1", "yes", "TRUE"):
            assert safe_bool(v) is True

    def test_safe_int_and_float_never_raise(self):
        for junk in _JUNK:
            assert isinstance(safe_int(junk), int)
            assert isinstance(safe_float(junk), float)


# --------------------------------------------------------------------------- #
# 5. Conservative
# --------------------------------------------------------------------------- #
class TestConservative:
    def test_no_input_is_low_confidence(self):
        assert evaluate()["band"] == BAND_LOW_CONFIDENCE

    def test_single_weak_signal_stays_undecided(self):
        assert evaluate(user_doubt=True)["band"] == BAND_LOW_CONFIDENCE
        assert evaluate(repeat_contacts=3)["band"] == BAND_LOW_CONFIDENCE

    def test_inconclusive_and_silent_voice_contribute_nothing(self):
        for v in ("INCONCLUSIVE", "SILENT"):
            r = evaluate(voice={"verdict": v})
            assert r["signals"] == []
            assert r["band"] == BAND_LOW_CONFIDENCE

    def test_unknown_message_verdict_contributes_nothing(self):
        assert evaluate(message={"verdict": "WHATEVER"})["signals"] == []

    def test_junk_boolean_is_not_evidence(self):
        """The bug this encodes: `campaign_linked="nope"` once produced HIGH."""
        assert evaluate(campaign_linked="nope")["signals"] == []
        assert evaluate(campaign_linked="nope")["band"] == BAND_LOW_CONFIDENCE

    def test_two_weak_signals_corroborate(self):
        assert evaluate(user_doubt=True, repeat_contacts=4)["band"] != BAND_LOW_CONFIDENCE

    def test_one_standalone_source_is_enough(self):
        assert evaluate(voice={"verdict": "LIKELY_SYNTHETIC"})["band"] != BAND_LOW_CONFIDENCE

    def test_band_for_explains_a_conservative_downgrade(self):
        band, why = band_for(0.30, 1, ["user_doubt"])
        assert band == BAND_LOW_CONFIDENCE
        assert "corroboration" in why.lower()


# --------------------------------------------------------------------------- #
# 6. Traceable
# --------------------------------------------------------------------------- #
class TestTraceable:
    def test_every_fired_signal_is_listed_with_its_weight(self):
        r = evaluate(voice={"verdict": "LIKELY_SYNTHETIC"}, campaign_linked=True)
        assert {s["source"] for s in r["signals"]} == {"voice", "campaign"}
        for s in r["signals"]:
            assert s["weight"] > 0

    def test_every_skipped_source_says_why(self):
        r = evaluate(voice={"verdict": "INCONCLUSIVE"}, message={"verdict": "LOW"})
        for s in r["skipped"]:
            assert s["reason"], f"{s['source']} was skipped without a reason"
        voice_skip = [s for s in r["skipped"] if s["source"] == "voice"][0]
        assert "absence of evidence" in voice_skip["reason"].lower()

    def test_the_payload_says_which_rules_ran(self):
        r = evaluate()
        assert r["sources_evaluated"] == len(FU.RULES)
        assert r["sources_fired"] == 0

    def test_band_carries_its_reason(self):
        for kwargs in ({}, {"voice": {"verdict": "LIKELY_SYNTHETIC"}},
                       {"campaign_linked": True},
                       {"voice": {"verdict": "LIKELY_SYNTHETIC"},
                        "message": {"verdict": "CRITICAL"}, "campaign_linked": True,
                        "repeat_contacts": 5, "user_doubt": True}):
            assert evaluate(**kwargs)["band_reason"]


# --------------------------------------------------------------------------- #
# 7. The rule table is the arithmetic, and it is pinned
# --------------------------------------------------------------------------- #
class TestRuleTable:
    def test_declared_weights_are_the_ones_applied(self):
        """If someone edits a weight, this fails — that is the point."""
        assert FU.SOURCE_WEIGHTS["voice"]["LIKELY_SYNTHETIC"] == 0.65
        assert FU.SOURCE_WEIGHTS["voice"]["SUSPICIOUS"] == 0.40
        assert FU.SOURCE_WEIGHTS["message"]["CRITICAL"] == 0.60
        assert FU.SOURCE_WEIGHTS["message"]["HIGH"] == 0.35
        assert FU.SOURCE_WEIGHTS["campaign"]["linked"] == 0.45
        assert FU.SOURCE_WEIGHTS["repeat_contact"]["three_or_more"] == 0.20
        assert FU.SOURCE_WEIGHTS["user_doubt"]["reported"] == 0.15

    def test_applied_weights_match_the_declared_table(self):
        r = evaluate(voice={"verdict": "LIKELY_SYNTHETIC"},
                     message={"verdict": "CRITICAL"}, campaign_linked=True,
                     repeat_contacts=5, user_doubt=True)
        expected = [0.65, 0.60, 0.45, 0.20, 0.15]
        assert sorted(r["weights_used"]) == sorted(expected)

    def test_each_rule_is_a_callable_in_the_table(self):
        for name, fn in FU.RULES.items():
            assert callable(fn), name
            assert name in FU.SOURCE_WEIGHTS, f"{name} has no declared weight"

    def test_all_bands_have_a_bounded_upper_edge(self):
        assert BANDS[-1] == BAND_CRITICAL
        assert BANDS.index(BAND_LOW_CONFIDENCE) < BANDS.index(BAND_LOW)
        assert BANDS.index(BAND_LOW) < BANDS.index(BAND_ELEVATED)
        assert BANDS.index(BAND_ELEVATED) < BANDS.index(BAND_HIGH)
        assert BANDS.index(BAND_HIGH) < BANDS.index(BAND_CRITICAL)


# --------------------------------------------------------------------------- #
# 8. The adapter keeps the old contract, in real sentences
# --------------------------------------------------------------------------- #
class TestAdapter:
    def test_engine_still_returns_the_documented_keys(self):
        r = assess()
        for key in ("band", "score", "signals", "headline", "action", "reasons",
                    "helpline", "lang", "degraded", "advisory", "band_reason"):
            assert key in r, key

    def test_reasons_are_sentences_not_internal_codes(self):
        """The gap Part One closed: `reasons` used to carry raw values like
        'LIKELY_SYNTHETIC' and 'same pattern already reported'."""
        r = assess(voice={"verdict": "LIKELY_SYNTHETIC"}, campaign_linked=True,
                   lang="en")
        for sentence in r["reasons"]:
            assert sentence.endswith("."), sentence
            assert "_" not in sentence, f"code leaked: {sentence}"
            assert len(sentence) > 20, sentence

    def test_reasons_are_localised(self):
        for lang, script in (("hi", "\u0900"), ("te", "\u0c00")):
            r = assess(voice={"verdict": "LIKELY_SYNTHETIC"}, lang=lang)
            assert any(ord(ch) >= ord(script) and ord(ch) <= ord(script) + 0x7f
                       for ch in r["reasons"][0]), lang

    def test_existing_callers_are_unaffected(self):
        assert assess()["band"] == BAND_LOW_CONFIDENCE
        assert assess(voice={"verdict": "LIKELY_SYNTHETIC"})["band"] == BAND_HIGH

    def test_render_source_never_leaks_a_code(self):
        for sig in ({"source": "voice", "detail": "LIKELY_SYNTHETIC"},
                    {"source": "campaign", "detail": "same pattern already reported"},
                    {"source": "mystery", "detail": "???"}):
            for lang in ("en", "hi", "te"):
                sentence = i18n.render_source(sig, lang)
                assert "same pattern already reported" not in sentence
                assert "LIKELY_SYNTHETIC" not in sentence
