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
    const v = await api("/api/citizen/screen_message", {text});
    msgOut.classList.remove("hidden");
    msgOut.innerHTML = `
      <div class="verdict ${esc(v.verdict)}">${esc(v.verdict)}</div>
      <div>Score ${esc(v.score)} · ${esc((v.families_hit||[]).join(", ") || "no signal families")}</div>
      <ul>${(v.reasons||[]).map(r => `<li>${esc(r)}</li>`).join("")}</ul>
      <div class="helpline">Advisory only — if unsure, don't act. ${esc(v.disclaimer || "Call 1930.")}</div>`;
  } catch (e) {
    msgOut.classList.remove("hidden");
    msgOut.innerHTML = `<div class="verdict MODERATE">UNAVAILABLE</div><div>Could not screen. Stay safe: if in doubt call 1930.</div>`;
  } finally { btnMsg.disabled = false; btnMsg.textContent = "Screen this message"; }
});

/* --- voice screening (demo-grade heuristic) --- */
const btnVoice = document.getElementById("btnScreenVoice");
const voiceOut = document.getElementById("voiceResult");

function synthTone(freq, seconds = 1.0, sr = 16000) {
  const n = Math.floor(seconds * sr), out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = 0.7 * Math.sin(2 * Math.PI * freq * (i / sr));
  return Array.from(out);
}

btnVoice.addEventListener("click", async () => {
  btnVoice.disabled = true; btnVoice.textContent = "Analysing…";
  try {
    const v = await api("/api/citizen/screen_voice", {samples: synthTone(440)});
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = `
      <div class="verdict ${v.verdict === "SUSPICIOUS" ? "HIGH" : "MODERATE"}">${esc(v.verdict)}</div>
      <div>${esc(v.reason || "")}</div>
      <div>Engine: ${esc(v.engine)}</div>
      <div class="helpline">Advisory only — voice verdicts here are heuristic. Call 1930 if pressured.</div>`;
  } catch (e) {
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = `<div class="verdict MODERATE">UNAVAILABLE</div><div>Voice engine unavailable — call 1930 if in doubt.</div>`;
  } finally { btnVoice.disabled = false; btnVoice.textContent = "Analyse sample tone A (synthetic)"; }
});

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
    const v = await api("/api/citizen/report", body);
    repOut.classList.remove("hidden");
    const fw = v.forwarded && v.forwarded.forwarded ? "✓ reached Raksha response network" : "✓ noted (offline mode — will sync)";
    repOut.innerHTML = `<div class="verdict LOW">REPORTED</div>
      <div>${esc(fw)}</div>
      <div>Event ${esc(v.event_id)} · severity ${esc(v.severity)}</div>
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
