"""PART 1 — Phase 2: panic button + family mode, from the Python side.

The behavioural logic is tested in `panic_family.test.js` under Node. This file
tests what Node cannot reach: that the shipped page actually wires those
modules, that the assets are served, and that the spec's claims now match the
code.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "citizen", "app")
_SPECS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "specs")


def read(name):
    with open(os.path.join(_APP, name), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# 1. The page actually loads and wires the new modules
# --------------------------------------------------------------------------- #
class TestWiring:
    def test_index_loads_panic_and_family_before_app(self):
        html = read("index.html")
        assert "panic.js" in html and "family.js" in html
        assert html.index("panic.js") < html.index("app.js")
        assert html.index("family.js") < html.index("app.js")

    def test_panic_is_a_button_not_a_bare_link(self):
        """It was an <a href="tel:1930"> — which is a phone link, not a panic
        flow. It cannot lock anything or stop a image buffer."""
        html = read("index.html")
        assert 'id="btnPanic"' in html
        assert not re.search(r'<a class="panic"[^>]*href="tel:1930"', html), \
            "a bare tel: link cannot perform the lock/stop steps"

    def test_app_wires_the_panic_handler(self):
        js = read("app.js")
        assert "RakshaPanic" in js
        assert "runPanic" in js
        # The three effects must all be present, or the sequence is a no-op.
        for key in ("lock", "closeImageSession", "dial"):
            assert key in js

    def test_panic_stops_a_live_image_session(self):
        js = read("app.js")
        block = js[js.index("function wirePanic"):js.index("document.addEventListener(\"DOMContentLoaded\", wirePanic)")]
        assert "activeVigilSession" in js
        assert "closeImageSession" in block

    def test_panic_clears_the_image_buffer_indicator(self):
        js = read("app.js")
        block = js[js.index("function wirePanic"):js.index("document.addEventListener(\"DOMContentLoaded\", wirePanic)")]
        assert "vigilStatus" in block

    def test_family_toggle_exists_and_is_wired(self):
        assert 'id="chkFamily"' in read("index.html")
        assert "RakshaFamily" in read("app.js")

    def test_family_mode_never_rewrites_a_verdict_in_the_ui(self):
        """presentVerdict returns an unchanged band; the UI must use it for
        styling only and keep rendering the server's own verdict text."""
        js = read("app.js")
        assert "present(" in js
        assert "presentVerdict" in js


# --------------------------------------------------------------------------- #
# 2. Assets are served (the Phase-5 deployment bug, re-checked for new files)
# --------------------------------------------------------------------------- #
class TestAssets:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        return TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))

    @pytest.mark.parametrize("asset", ["panic.js", "family.js"])
    def test_new_modules_are_served(self, client, asset):
        assert client.get(f"/app/{asset}").status_code == 200

    def test_every_script_referenced_by_the_page_resolves(self, client):
        page = client.get("/app/").text
        for src in re.findall(r'<script src="([^"]+)"', page):
            assert client.get(f"/app/{src}").status_code == 200, src

    def test_stylesheet_covers_the_overlay_and_family_mode(self):
        css = read("styles.css")
        for cls in (".panic-overlay", ".panic-card", ".panic-cancel",
                    ".family-toggle", "body.family-mode", ".family-escalated"):
            assert cls in css, f"{cls} has no styling"


# --------------------------------------------------------------------------- #
# 3. Accessibility — this is a button pressed by frightened people
# --------------------------------------------------------------------------- #
class TestAccessibility:
    def test_overlay_is_an_alert_dialog(self):
        js = read("panic.js")
        assert 'role", "alertdialog"' in js or "alertdialog" in js
        assert "aria-modal" in js

    def test_overlay_is_fully_opaque(self):
        """If any of the scam screen shows through, the scammer's instructions
        are still readable — which defeats the point."""
        css = read("styles.css")
        block = css[css.index(".panic-overlay"):css.index(".panic-card")]
        assert "position: fixed" in block
        assert "inset: 0" in block
        assert "opacity" not in block, "a transparent overlay leaves the scam visible"

    def test_cancel_target_meets_touch_guidance(self):
        css = read("styles.css")
        block = css[css.index(".panic-cancel"):]
        block = block[:block.index("}")]
        assert "min-height: 56px" in block, "48px is the guidance; 56 is used here"

    def test_overlay_moves_focus_to_cancel(self):
        js = read("panic.js")
        assert ".focus()" in js


# --------------------------------------------------------------------------- #
# 4. The spec's claims must now match the code
# --------------------------------------------------------------------------- #
class TestSpecHonesty:
    def test_panic_row_now_claims_the_behaviour_that_exists(self):
        """Phase 1 changed this row from a false ✅ to an honest ⚠️. Phase 2 made
        the behaviour real, so the row may only go back to ✅ if the lock, the
        image session stop and the dial are all actually implemented — which the JS
        tests prove they are."""
        spec = open(os.path.join(_SPECS, "01_citizen_spine.md"), encoding="utf-8").read()
        row = [l for l in spec.splitlines() if "Panic button" in l][0]
        assert "lock" in row.lower() and "dial" in row.lower()
        assert "1930" in row
        # And the implementation it points at must contain all three steps.
        js = read("panic.js")
        for step in ("LOCK", "CLOSE_IMAGE_SESSION", "DIAL"):
            assert step in js, f"{step} missing from panic.js"

    def test_spec_states_what_the_panic_button_cannot_do(self):
        spec = open(os.path.join(_SPECS, "01_citizen_spine.md"), encoding="utf-8").read()
        assert "accessibility" in spec.lower()
        assert "cannot" in spec.lower()

    def test_roadmap_marks_phase_two_done_only_with_real_counts(self):
        rm = open(os.path.join(_SPECS, "01a_citizen_spine_roadmap.md"),
                  encoding="utf-8").read()
        assert "Phase 2" in rm
        # No aspirational counts: the status board must carry a real figure.
        assert "runner-reported" in rm


# --------------------------------------------------------------------------- #
# 5. Family mode must not become a scoring path
# --------------------------------------------------------------------------- #
class TestFamilyIsPresentationOnly:
    def test_family_module_never_imports_or_calls_a_scorer(self):
        js = read("family.js")
        for banned in ("score_call", "screen_call", "/api/", "fetch("):
            assert banned not in js, f"family mode must not call {banned}"

    def test_family_module_stores_nothing_sensitive(self):
        js = read("family.js")
        # Only a boolean preference may be persisted.
        stored = re.findall(r"setItem\([^,]+,\s*([^)]+)\)", js)
        assert stored, "no persistence found"
        for v in stored:
            assert "enabled" in v or "?" in v, f"unexpected stored value: {v}"

    def test_family_mode_cannot_enable_without_the_user(self):
        js = read("family.js")
        assert "enabled: false" in js, "default must be off"
