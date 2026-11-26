/* RAKSHA Citizen — panic flow (Part 1, Phase 2, task 2.1)
 *
 * A helpline link is not a panic button. This is the real sequence.
 *
 * THE ORDER IS THE SAFETY PROPERTY. Lock, then stop, then dial:
 *
 *   1. LOCK   — put a full-screen barrier over whatever scam screen the person
 *               was looking at. If we dial first, the phone app opens over it
 *               and the user comes back to an unchanged, still-convincing
 *               screen. Nothing was achieved.
 *   2. STOP   — end any active microphone capture and zero the ring buffer.
 *               A panic tap during a recorded call must not leave audio alive.
 *   3. DIAL   — hand off to the dialler with 1930.
 *
 * Confirmation is deliberately NOT required. In the situation this button
 * exists for, a "are you sure?" dialog is the last thing a frightened person
 * needs, and it costs the seconds that matter. The overlay instead offers a
 * single, large, obvious Cancel that returns to the home screen.
 *
 * What this module does NOT do, and why:
 *   * It cannot kill other apps or "end the scam session". That needs Android
 *     accessibility permissions, which Part 1 §8 forbids (no IME/keystroke
 *     access). The original spec claimed this behaviour; it was never
 *     implementable under this project's own privacy rules.
 *   * It does not block the dialler. The OS owns that.
 */

"use strict";

var PANIC_STEPS = Object.freeze(["LOCK", "STOP_CAPTURE", "DIAL"]);

var PANIC_STATE = Object.freeze({
  IDLE: "IDLE",
  LOCKED: "LOCKED",
  DIALED: "DIALED",
  CANCELLED: "CANCELLED",
});

/**
 * Run the panic sequence in the only safe order.
 *
 * All effects are injected so the sequence can be tested without a browser.
 * Every step is attempted even if an earlier one throws — a failure to zero the
 * buffer must not prevent the call to 1930.
 *
 * @param {object} effects
 * @param {function} effects.lock      render the blocking overlay
 * @param {function} effects.stopCapture end capture + zero buffer
 * @param {function} effects.dial      open the dialler
 * @returns {{done: string[], failed: string[], state: string}}
 */
function runPanic(effects) {
  var e = effects || {};
  var done = [];
  var failed = [];

  var table = {
    LOCK: e.lock,
    STOP_CAPTURE: e.stopCapture,
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
      // Swallow and continue. In a panic, a broken overlay must not stop the
      // call, and a broken buffer-zero must not stop the overlay.
      failed.push(step);
    }
  }

  return {
    done: done,
    failed: failed,
    state: done.indexOf("LOCK") >= 0 ? PANIC_STATE.LOCKED : PANIC_STATE.IDLE,
  };
}

/**
 * Build the overlay markup. Kept here (rather than in app.js) so the copy that a
 * frightened person reads is reviewable in one place, in three languages.
 */
var PANIC_COPY = Object.freeze({
  en: {
    title: "Scam screen closed",
    body: "Your microphone is off and the recording buffer is cleared.",
    calling: "Calling 1930 — the national cybercrime helpline.",
    cancel: "Cancel and go back",
  },
  hi: {
    title: "धोखाधड़ी की स्क्रीन बंद कर दी गई",
    body: "आपका माइक्रोफ़ोन बंद है और रिकॉर्डिंग बफ़र साफ़ कर दिया गया है।",
    calling: "1930 पर कॉल किया जा रहा है — राष्ट्रीय साइबर अपराध हेल्पलाइन।",
    cancel: "रद्द करें और वापस जाएँ",
  },
  te: {
    title: "మోసపు స్క్రీన్ మూసివేయబడింది",
    body: "మీ మైక్రోఫోన్ ఆఫ్‌లో ఉంది మరియు రికార్డింగ్ బఫర్ క్లియర్ చేయబడింది.",
    calling: "1930కి కాల్ చేస్తున్నాము — జాతీయ సైబర్ నేరాల హెల్ప్‌లైన్.",
    cancel: "రద్దు చేసి వెనక్కి వెళ్లండి",
  },
});

function panicCopy(lang) {
  var base = String(lang || "en").toLowerCase().replace("_", "-").split("-")[0];
  return PANIC_COPY[base] || PANIC_COPY.en;
}

/**
 * Render the blocking overlay into a document. Returns the overlay element so a
 * caller can dismiss it. Never throws — a rendering failure must not stop the
 * call, so the dialler is opened by `runPanic` separately.
 */
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
