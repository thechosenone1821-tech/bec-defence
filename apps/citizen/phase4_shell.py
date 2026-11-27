"""Runtime-only shell overlay for the VIGIL-integrated Citizen PWA.

The physical PWA files are served from one directory. This module injects one
small same-origin script and an honest manifest description so the one shell
advertises the active model-backed image-privacy route without creating a second
app or a second PWA.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

SHELL_VERSION = "citizen-shell-vigil-v1"
INJECT_MARKER = "<!-- RAKSHA VIGIL image-privacy overlay -->"

PHASE4_SHELL_JS = r"""
(function () {
  "use strict";
  var title = "Image privacy — VIGIL";
  var detail = "VIGIL is a model-backed image-privacy tool. It changes selected pixels and reports local metrics; it does not claim deepfake prevention, modern facial recognition defeat or anonymity. Call 1930 if in doubt.";
  window.RakshaPhase4VigilStatus = {
    enabled: true,
    status: "active",
    title: title,
    detail: detail,
    route: "/vigil/",
    modelBacked: true,
    privacyEfficacy: "UNMEASURED"
  };
  function apply() {
    var tab = document.querySelector('.tab[data-tab="privacy"]');
    if (tab) tab.textContent = title;
    var hint = document.querySelector('#privacy .hint');
    if (hint) hint.textContent = detail;
    var status = document.getElementById("vigilStatus");
    if (status) status.textContent = "VIGIL is active at /vigil/.";
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
"""


def inject_index_html(app_dir: str | Path) -> str:
    html = (Path(app_dir) / "index.html").read_text(encoding="utf-8")
    injection = (INJECT_MARKER + "\n"
                 "<noscript><p class=\"hint\">VIGIL image privacy is available at /vigil/. "
                 "Call 1930 if in doubt.</p></noscript>\n"
                 "<meta name=\"raksha-vigil-status\" content=\"active\">\n"
                 "<script src=\"phase4.js\"></script>\n"
                 "<script>window.RakshaPhase4VigilStatus && "
                 "console.info('RAKSHA VIGIL:', window.RakshaPhase4VigilStatus.status);</script>\n")
    marker = "</body>"
    assert marker in html, "Citizen shell has no </body> anchor"
    return html.replace(marker, injection + marker, 1)


def honest_manifest(app_dir: str | Path) -> Dict[str, Any]:
    manifest = json.loads((Path(app_dir) / "manifest.json").read_text(encoding="utf-8"))
    manifest["description"] = (
        "Offline-first RAKSHA Citizen: message screening, risk advice, one-tap "
        "reporting, the 1930 helpline and VIGIL image privacy."
    )
    manifest["phase4"] = {
        "shell": SHELL_VERSION,
        "vigil_enabled": True,
        "vigil_route": "/vigil/",
        "model_backed": True,
        "active_model": "VIGIL PrivacyNet TorchScript",
        "privacy_efficacy": "UNMEASURED",
    }
    return manifest


__all__ = ["INJECT_MARKER", "PHASE4_SHELL_JS", "SHELL_VERSION",
           "honest_manifest", "inject_index_html"]
