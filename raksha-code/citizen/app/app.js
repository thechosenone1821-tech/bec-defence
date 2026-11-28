/* RAKSHA Citizen — no build step, same-origin API */

/* --- tabs --- */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === btn.dataset.tab));
  });
});

const lang = () => (new URLSearchParams(location.search).get("lang") || "en");

async function api(path, body) {
  const r = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"},
                               body: JSON.stringify(body || {})});
  if (!r.ok) {
    const err = new Error("HTTP " + r.status);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

const classifySend = (window.RakshaSend && window.RakshaSend.classifySend)
  || function (err) { return err ? "retry" : "sent"; };

function esc(s) { const d = document.createElement("div"); d.textContent = String(s); return d.innerHTML; }

/* --- family mode: presentation only, never a verdict --- */
const family = window.RakshaFamily || null;
let familyState = family ? family.readFamily(window.localStorage) : {enabled: false};

function applyFamilyClass() {
  document.body.classList.toggle("family-mode", Boolean(familyState.enabled));
  const chk = document.getElementById("chkFamily");
  if (chk) chk.checked = Boolean(familyState.enabled);
  const sev = document.querySelector(".sev");
  if (sev && family) sev.classList.toggle("hidden", family.hideSeveritySlider(familyState));
}

function present(verdict) {
  if (!family) return {cssClasses: ["verdict", String(verdict)], actionable: false};
  return family.presentVerdict(verdict, familyState);
}

/* --- VIGIL image session and panic safety order --- */
let activeVigilSession = null;

function closeImageSession() {
  activeVigilSession = null;
  window.RakshaVigilSessionId = null;
  const status = document.getElementById("vigilStatus");
  if (status) {
    status.textContent = "VIGIL image buffer closed.";
    status.classList.remove("live");
  }
}

function wirePanic() {
  const btn = document.getElementById("btnPanic");
  if (!btn || !window.RakshaPanic) return;
  btn.addEventListener("click", () => {
    window.RakshaPanic.runPanic({
      lock: () => window.RakshaPanic.showOverlay(
        document, lang(),
        () => { /* Cancel: the overlay removes itself. */ }),
      closeImageSession: closeImageSession,
      dial: () => { window.location.href = "tel:1930"; },
    });
  });
}

const btnVigil = document.getElementById("btnOpenVigil");
if (btnVigil) {
  btnVigil.addEventListener("click", () => {
    const status = document.getElementById("vigilStatus");
    if (status) status.textContent = "Opening VIGIL image privacy…";
  });
}

document.addEventListener("DOMContentLoaded", applyFamilyClass);
document.addEventListener("DOMContentLoaded", wirePanic);

/* --- offline report queue flush --- */
async function flushQueue() {
  const q = window.RakshaQueue;
  if (!q || q.size(window.localStorage) === 0) return;
  await q.flush(window.localStorage, async (entry) => {
    try {
      await api("/api/citizen/report", entry);
      return true;
    } catch (err) {
      return false;
    }
  });
}

document.addEventListener("DOMContentLoaded", flushQueue);
window.addEventListener("online", flushQueue);
{
  const chk = document.getElementById("chkFamily");
  if (chk) {
    chk.addEventListener("change", () => {
      familyState = {...familyState, enabled: chk.checked};
      if (family) family.writeFamily(window.localStorage, chk.checked);
      applyFamilyClass();
    });
  }
}

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
    const ex = v.explanation || {};
    const band = v.verdict || "LOW";
    const pres = present(band);
    const icon = {CRITICAL: "⛔", HIGH: "⚠️", MODERATE: "❔", LOW: "✓"}[band] || "❔";
    msgOut.innerHTML = `
      <div class="${pres.cssClasses.join(" ")}" data-icon="${icon}">${esc(ex.title || v.verdict)}</div>
      <div class="action-copy">${esc(ex.action || "Call 1930 if in doubt.")}</div>
      <ul>${(ex.reasons||[]).map(r => `<li>${esc(r)}</li>`).join("")}</ul>
      <div class="helpline">${esc(ex.disclaimer || "Advisory only.")}</div>`;
  } catch (e) {
    msgOut.classList.remove("hidden");
    msgOut.innerHTML = `<div class="verdict MODERATE">UNAVAILABLE</div><div>Could not screen. Stay safe: if in doubt call 1930.</div>`;
  } finally { btnMsg.disabled = false; btnMsg.textContent = "Screen this message"; }
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
  const body = {category: selectedCategory, severity: sevRange.value / 100};
  try {
    const cref = (caseRef && caseRef.value.trim()) || "";
    if (cref) body.case_id = cref;
    const v = await api("/api/citizen/report", {...body, lang: lang()});
    repOut.classList.remove("hidden");
    const ex = v.explanation || {};
    repOut.innerHTML = `<div class="verdict LOW" data-icon="✓">${esc(ex.title || "Report sent")}</div>
      <div class="action-copy">${esc(ex.detail || "")}</div>
      <div class="helpline">If you lost money already, call 1930 NOW and freeze the transaction.</div>`;
  } catch (e) {
    repOut.classList.remove("hidden");
    const q = window.RakshaQueue;
    let saved = false, pending = 0;
    if (q) {
      const r = q.enqueue(window.localStorage, body);
      saved = r.ok;
      pending = r.size;
    }
    const outcome = classifySend(e);
    const sendCopy = (window.RakshaSend && window.RakshaSend.SEND_COPY) || {};
    if (outcome === "rejected") {
      repOut.innerHTML = `<div class="verdict MODERATE" data-icon="❔">Report not accepted</div>
         <div class="action-copy">${sendCopy.rejected || "The service refused this report. Call 1930 instead."}</div>
         <div class="helpline">If you lost money, call 1930 NOW — do not wait for the report.</div>`;
    } else {
      repOut.innerHTML = saved
        ? `<div class="verdict MODERATE" data-icon="❔">Saved on this phone</div>
           <div class="action-copy">No signal. Your report is kept on this device and will be sent automatically when you are back online.</div>
           <div class="helpline">If you lost money, call 1930 NOW — do not wait for the report.</div>`
        : `<div class="verdict MODERATE" data-icon="❔">Report not sent</div>
           <div class="action-copy">Call 1930 instead. Your data did not leave this phone.</div>`;
    }
  } finally { btnReport.disabled = false; btnReport.textContent = "Send report"; }
});

/* --- service worker (offline shell) --- */
const recoveryParams = new URLSearchParams(location.search);
if (recoveryParams.has("nosw")) {
  /* Presentation / proxy recovery: forget the old offline shell so broken
     cached scripts cannot keep the buttons dead after a redeploy. */
  if ("serviceWorker" in navigator &&
      typeof navigator.serviceWorker.getRegistrations === "function") {
    navigator.serviceWorker.getRegistrations()
      .then(regs => regs.forEach(reg => reg.unregister()))
      .catch(() => {});
  }
  if ("caches" in window) {
    caches.keys()
      .then(keys => keys.filter(k => k.startsWith("raksha-citizen-"))
        .forEach(k => caches.delete(k)))
      .catch(() => {});
  }
} else if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}
