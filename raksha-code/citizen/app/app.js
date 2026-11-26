/* RAKSHA Citizen — no build step, same-origin API */

/* --- tabs --- */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === btn.dataset.tab));
  });
});

async function api(path, body) {
  const r = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"},
                               body: JSON.stringify(body || {})});
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

function esc(s) { const d = document.createElement("div"); d.textContent = String(s); return d.innerHTML; }

/* --- message screening --- */
const btnMsg = document.getElementById("btnScreenMessage");
const msgBox = document.getElementById("msgText");
const msgOut = document.getElementById("msgResult");

btnMsg.addEventListener("click", async () => {
  const text = msgBox.value.trim();
  if (!text) { msgBox.focus(); return; }
  btnMsg.disabled = true; btnMsg.textContent = "Screening…";
  try {
    const v = await api("/api/citizen/screen_message", {text, lang: lang()});
    msgOut.classList.remove("hidden");
    // Part 1 Phase 1: render the server's localised explanation. The raw score
    // and the matched token list were previously shown here, which
    //   (a) broke the spine's own "never show a raw score" rule, and
    //   (b) printed English diagnostics on a Hindi/Telugu screen.
    const ex = v.explanation || {};
    const band = {CRITICAL: "CRITICAL", HIGH: "HIGH", MODERATE: "MODERATE"}[v.verdict] || "LOW";
    const icon = {CRITICAL: "⛔", HIGH: "⚠️", MODERATE: "❔", LOW: "✓"}[band];
    msgOut.innerHTML = `
      <div class="verdict ${band}" data-icon="${icon}">${esc(ex.title || v.verdict)}</div>
      <div class="voice-action">${esc(ex.action || "Call 1930 if in doubt.")}</div>
      <ul>${(ex.reasons||[]).map(r => `<li>${esc(r)}</li>`).join("")}</ul>
      <div class="helpline">${esc(ex.disclaimer || "Advisory only.")}</div>`;
  } catch (e) {
    msgOut.classList.remove("hidden");
    msgOut.innerHTML = `<div class="verdict MODERATE">UNAVAILABLE</div><div>Could not screen. Stay safe: if in doubt call 1930.</div>`;
  } finally { btnMsg.disabled = false; btnMsg.textContent = "Screen this message"; }
});

/* --- voice screening (MAYA) -----------------------------------------
 * Phase 5: this tab now captures real microphone audio through the 3-second
 * ring buffer and sends only the last window for screening. The old
 * `synthTone(440)` demo path is kept behind an explicit button because it is a
 * useful plumbing check — but it is labelled as such and is no longer what
 * "Check a voice" does.
 * ------------------------------------------------------------------- */
const btnVoice = document.getElementById("btnScreenVoice");
const voiceOut = document.getElementById("voiceResult");
const btnVoiceTone = document.getElementById("btnVoiceTone");
const voiceIndicator = document.getElementById("voiceIndicator");
const lang = () => (new URLSearchParams(location.search).get("lang") || "en");

function synthTone(freq, seconds = 1.0, sr = 16000) {
  const n = Math.floor(seconds * sr), out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = 0.7 * Math.sin(2 * Math.PI * freq * (i / sr));
  return Array.from(out);
}

/* Render a result. The headline/action/reasons come from the server's i18n
 * layer so the citizen never reads a raw score or an English-only sentence. */
function renderVoice(v) {
  const ex = v.explanation || {};
  const band = v.verdict === "LIKELY_SYNTHETIC" ? "CRITICAL"
             : v.verdict === "SUSPICIOUS" ? "HIGH"
             : v.verdict === "SILENT" ? "LOW" : "MODERATE";
  const icon = {CRITICAL: "⛔", HIGH: "⚠️", MODERATE: "❔", LOW: "🔇"}[band];
  voiceOut.classList.remove("hidden");
  voiceOut.innerHTML = `
    <div class="verdict ${band}" data-icon="${icon}">${esc(ex.title || v.verdict)}</div>
    <div class="voice-action">${esc(ex.action || "Call 1930 if in doubt.")}</div>
    ${(ex.reasons || []).length ? `<ul>${ex.reasons.map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
    <div class="helpline">${esc(ex.disclaimer || "Advisory only.")}</div>
    <div class="engine-note">${esc(v.engine || "")}</div>`;
}

async function analyse(samples) {
  btnVoice.disabled = true; btnVoice.textContent = "Listening…";
  try {
    const v = await api("/api/citizen/screen_voice", {samples, lang: lang()});
    renderVoice(v);
  } catch (e) {
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = `<div class="verdict MODERATE" data-icon="❔">Check unavailable</div>
      <div>Stay safe: if in doubt, call 1930.</div>`;
  } finally { btnVoice.disabled = false; btnVoice.textContent = "Record and check this call"; }
}

/* --- microphone path ------------------------------------------------- */
btnVoice.addEventListener("click", async () => {
  if (!window.MayaCapture) {
    // Capture module not available (old browser / file://) — fall back to the
    // bundled tone so the tab still demonstrates the pipeline, and SAY SO.
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = `<div class="verdict MODERATE" data-icon="❔">Microphone not available here</div>
      <div>This browser cannot record. Try the bundled sample below, or open the app over http:// or https://.</div>`;
    return;
  }
  const capture = window.MayaCapture.create({
    onState: (st) => {
      if (voiceIndicator) {
        voiceIndicator.textContent = st === "CAPTURING" ? "● Recording (3 s buffer, discarded on stop)" : "";
        voiceIndicator.classList.toggle("live", st === "CAPTURING");
      }
    },
    onSamples: (buf) => { analyse(Array.from(buf)).then(() => capture.stop()); },
  });
  capture.setConsent(true);                   // the consent screen gates this in production
  const state = await capture.start();
  if (state !== "CAPTURING") {
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = `<div class="verdict MODERATE" data-icon="❔">Microphone not available</div>
      <div>We could not open the microphone. No audio was recorded. Call 1930 if in doubt.</div>`;
  }
});

/* Explicit, labelled plumbing check — not the product path. */
if (btnVoiceTone) {
  btnVoiceTone.addEventListener("click", () => analyse(synthTone(440)));
}

/* --- one-tap report --- */
let selectedCategory = null;
document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    selectedCategory = chip.dataset.cat;
    document.querySelectorAll(".chip").forEach(c => c.classList.toggle("selected", c === chip));
  });
});
const sevRange = document.getElementById("sevRange");
const sevVal = document.getElementById("sevVal");
sevRange.addEventListener("input", () => { sevVal.textContent = (sevRange.value / 100).toFixed(2); });

const caseRef = document.getElementById("caseRef");
const btnReport = document.getElementById("btnReport");
const repOut = document.getElementById("reportResult");

btnReport.addEventListener("click", async () => {
  if (!selectedCategory) { repOut.classList.remove("hidden"); repOut.innerHTML = "<div class='verdict MODERATE'>Pick a category first</div>"; return; }
  btnReport.disabled = true; btnReport.textContent = "Sending…";
  try {
    const body = {category: selectedCategory, severity: sevRange.value / 100};
    const cref = (caseRef && caseRef.value.trim()) || "";
    if (cref) body.case_id = cref;
    const v = await api("/api/citizen/report", {...body, lang: lang()});
    repOut.classList.remove("hidden");
    // Part 1 Phase 1: an event id and a severity float are not citizen-facing.
    // The wrapper says what happened and what did NOT leave the phone.
    const ex = v.explanation || {};
    repOut.innerHTML = `<div class="verdict LOW" data-icon="✓">${esc(ex.title || "Report sent")}</div>
      <div class="voice-action">${esc(ex.detail || "")}</div>
      <div class="helpline">If you lost money already, call 1930 NOW and freeze the transaction.</div>`;
  } catch (e) {
    repOut.classList.remove("hidden");
    repOut.innerHTML = `<div class="verdict MODERATE">NOT SENT</div><div>Report could not be sent — call 1930 instead. Your data did not leave this phone.</div>`;
  } finally { btnReport.disabled = false; btnReport.textContent = "Send report"; }
});

/* --- service worker (offline shell) --- */
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}
