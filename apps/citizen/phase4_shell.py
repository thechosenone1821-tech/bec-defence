"""Phase 4 — runtime-only honest shell overlay.

The frozen PWA files are never edited. The Citizen service injects one small
same-origin script into the single existing ``index.html`` and serves an honest
manifest description. The injected script disables the frozen voice controls;
no audio is captured, no model is called, and no second PWA shell is created.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

SHELL_VERSION = "citizen-shell-phase4-v1"
INJECT_MARKER = "<!-- RAKSHA Phase 4 voice-status overlay -->"

PHASE4_SHELL_JS = r"""
(function () {
  "use strict";
  var title = "Voice check — not integrated yet";
  var detail = "VoiceGuard/MAYA is frozen. No audio is recorded, no AI model is run, and no clone-detection claim is made. Call 1930 if in doubt.";
  window.RakshaPhase4VoiceStatus = {
    enabled: false,
    status: "not integrated yet",
    title: title,
    detail: detail,
    modelInvoked: false
  };
  function disableButton(id, label) {
    var el = document.getElementById(id);
    if (!el) return;
    var clone = el.cloneNode(true);
    clone.disabled = true;
    clone.textContent = label;
    el.parentNode.replaceChild(clone, el);
  }
  function apply() {
    var tab = document.querySelector('.tab[data-tab="voice"]');
    if (tab) tab.textContent = title;
    var hint = document.querySelector('#voice .hint');
    if (hint) hint.textContent = detail;
    var indicator = document.getElementById('voiceIndicator');
    if (indicator) { indicator.textContent = ''; indicator.classList.remove('live'); }
    var out = document.getElementById('voiceResult');
    if (out) {
      out.classList.remove('hidden');
      out.textContent = detail;
    }
    disableButton('btnScreenVoice', title);
    disableButton('btnVoiceTone', title);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply);
  } else {
    apply();
  }
})();
"""


def inject_index_html(app_dir: str | Path) -> str:
    html = (Path(app_dir) / "index.html").read_text(encoding="utf-8")
    injection = (INJECT_MARKER + "\n"
                 "<noscript><p class=\"hint\">Voice check — not integrated yet. "
                 "No audio is recorded or scored. Call 1930 if in doubt.</p></noscript>\n"
                 "<meta name=\"raksha-voice-status\" content=\"not integrated yet\">\n"
                 "<script src=\"phase4.js\"></script>\n"
                 "<script>window.RakshaPhase4VoiceStatus && "
                 "console.info('RAKSHA Phase 4:', window.RakshaPhase4VoiceStatus.status);</script>\n")
    marker = "</body>"
    assert marker in html, "frozen Citizen shell has no </body> anchor"
    return html.replace(marker, injection + marker, 1)


def honest_manifest(app_dir: str | Path) -> Dict[str, Any]:
    manifest = json.loads((Path(app_dir) / "manifest.json").read_text(encoding="utf-8"))
    manifest["description"] = (
        "Offline-first RAKSHA Citizen: message screening, risk advice, reporting "
        "and the 1930 helpline. Voice screening is not integrated yet."
    )
    manifest["phase4"] = {
        "shell": SHELL_VERSION,
        "voiceguard_enabled": False,
        "voice_status": "not integrated yet",
        "no_ai_models": True,
    }
    return manifest


__all__ = ["INJECT_MARKER", "PHASE4_SHELL_JS", "SHELL_VERSION",
           "honest_manifest", "inject_index_html"]
