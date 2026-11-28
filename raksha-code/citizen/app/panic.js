/* RAKSHA Citizen — panic flow.
 *
 * A helpline link is not a panic button. This is the real sequence.
 *
 * THE ORDER IS THE SAFETY PROPERTY. Lock, then close, then dial:
 *
 *   1. LOCK   — put a full-screen barrier over whatever scam screen the person
 *               was looking at. If we dial first, the phone app opens over it
 *               and the user comes back to an unchanged, still-convincing
 *               screen.
 *   2. CLOSE  — clear any active VIGIL image buffer and its in-memory pixels.
 *               A panic tap must not leave an image session alive.
 *   3. DIAL   — hand off to the dialler with 1930.
 *
 * Confirmation is deliberately NOT required. In the situation this button
 * exists for, a "are you sure?" dialog costs seconds that matter. The overlay
 * offers one large Cancel that returns to the home screen.
 */

"use strict";

var PANIC_STEPS = Object.freeze(["LOCK", "CLOSE_IMAGE_SESSION", "DIAL"]);

var PANIC_STATE = Object.freeze({
  IDLE: "IDLE",
  LOCKED: "LOCKED",
  DIALED: "DIALED",
  CANCELLED: "CANCELLED",
});

/**
 * Run the panic sequence in the only safe order. All effects are injected so the
 * sequence can be tested without a browser. Every step is attempted even if an
 * earlier one throws — a failure to clear the image buffer must not prevent the
 * call to 1930.
 */
function runPanic(effects) {
  var e = effects || {};
  var done = [];
  var failed = [];
  var table = {
    LOCK: e.lock,
    CLOSE_IMAGE_SESSION: e.closeImageSession,
    DIAL: e.dial,
  };

  for (var i = 0; i < PANIC_STEPS.length; i++) {
    var step = PANIC_STEPS[i];
    var fn = table[step];
    if (typeof fn !== "function") {
      failed.push(step);
      continue;
    }
    try {
      fn();
      done.push(step);
    } catch (err) {
      failed.push(step);
    }
  }
  return {
    done: done,
    failed: failed,
    state: done.indexOf("LOCK") >= 0 ? PANIC_STATE.LOCKED : PANIC_STATE.IDLE,
  };
}

var PANIC_COPY = Object.freeze({
  en: {
    title: "Scam screen closed",
    body: "The image buffer is closed and in-memory pixels are purged.",
    calling: "Calling 1930 — the national cybercrime helpline.",
    cancel: "Cancel and go back",
  },
  hi: {
    title: "धोखाधड़ी की स्क्रीन बंद कर दी गई",
    body: "छवि बफ़र बंद कर दिया गया है और स्मृति में मौजूद पिक्सेल हटा दिए गए हैं।",
    calling: "1930 पर कॉल किया जा रहा है — राष्ट्रीय साइबर अपराध हेल्पलाइन।",
    cancel: "रद्द करें और वापस जाएँ",
  },
  te: {
    title: "మోసపు స్క్రీన్ మూసివేయబడింది",
    body: "చిత్ర బఫర్ మూసివేయబడింది మరియు మెమరీలోని పిక్సెల్\u200cలు తొలగించబడ్డాయి.",
    calling: "1930కి కాల్ చేస్తున్నాము — జాతీయ సైబర్ నేరాల హెల్ప్\u200cలైన్.",
    cancel: "రద్దు చేసి వెనక్కి వెళ్లండి",
  },
});

function panicCopy(lang) {
  var base = String(lang || "en").toLowerCase().replace("_", "-").split("-")[0];
  return PANIC_COPY[base] || PANIC_COPY.en;
}

function showOverlay(doc, lang, onCancel) {
  if (!doc || !doc.body) return null;
  var copy = panicCopy(lang);
  var wrap = doc.createElement("div");
  wrap.className = "panic-overlay";
  wrap.setAttribute("role", "alertdialog");
  wrap.setAttribute("aria-modal", "true");
  wrap.innerHTML =
    '<div class="panic-card">' +
    '<div class="panic-icon" aria-hidden="true">🛡️</div>' +
    '<h2>' + copy.title + "</h2>" +
    "<p>" + copy.body + "</p>" +
    '<p class="panic-calling">' + copy.calling + "</p>" +
    '<button class="panic-cancel" type="button">' + copy.cancel + "</button>" +
    "</div>";
  var btn = wrap.querySelector(".panic-cancel");
  if (btn && typeof onCancel === "function") {
    btn.addEventListener("click", function () {
      if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
      onCancel();
    });
  }
  doc.body.appendChild(wrap);
  if (btn && typeof btn.focus === "function") btn.focus();
  return wrap;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    PANIC_STEPS: PANIC_STEPS,
    PANIC_STATE: PANIC_STATE,
    PANIC_COPY: PANIC_COPY,
    runPanic: runPanic,
    panicCopy: panicCopy,
    showOverlay: showOverlay,
  };
}
if (typeof window !== "undefined") {
  window.RakshaPanic = {
    PANIC_STEPS: PANIC_STEPS,
    PANIC_STATE: PANIC_STATE,
    runPanic: runPanic,
    panicCopy: panicCopy,
    showOverlay: showOverlay,
  };
}
