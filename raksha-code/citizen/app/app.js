/* RAKSHA Citizen — same-origin API; no build step */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === btn.dataset.tab));
  });
});
async function api(path, body) {
  const response = await fetch(path, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body || {})});
  if (!response.ok) {
    let detail = "HTTP " + response.status;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}
function esc(value) {
  const node = document.createElement("div");
  node.textContent = String(value);
  return node.innerHTML;
}

/* MessageGuard */
const btnMsg = document.getElementById("btnScreenMessage");
const msgBox = document.getElementById("msgText");
const msgOut = document.getElementById("msgResult");
btnMsg.addEventListener("click", async () => {
  const text = msgBox.value.trim();
  if (!text) { msgBox.focus(); return; }
  btnMsg.disabled = true;
  btnMsg.textContent = "Screening…";
  try {
    const v = await api("/api/citizen/screen_message", {text});
    msgOut.classList.remove("hidden");
    msgOut.innerHTML = '<div class="verdict ' + esc(v.verdict) + '">' + esc(v.verdict) + '</div>'
      + '<div>Score ' + esc(v.score) + ' · ' + esc((v.families_hit || []).join(", ") || "no signal families") + '</div>'
      + '<ul>' + (v.reasons || []).map(r => '<li>' + esc(r) + '</li>').join("") + '</ul>'
      + '<div class="helpline">Advisory only — if unsure, don\\'t act. ' + esc(v.disclaimer || "Call 1930.") + '</div>';
  } catch (_) {
    msgOut.classList.remove("hidden");
    msgOut.textContent = "Could not screen this message. If in doubt, call 1930.";
  } finally {
    btnMsg.disabled = false;
    btnMsg.textContent = "Screen this message";
  }
});

/* VoiceGuard: explicit consent, visible two-second mic capture, no storage */
const btnVoice = document.getElementById("btnScreenVoice");
const btnCancelVoice = document.getElementById("btnCancelVoice");
const consentVoice = document.getElementById("voiceConsent");
const voiceOut = document.getElementById("voiceResult");
const voiceStatus = document.getElementById("voiceStatus");
const voiceStatusText = document.getElementById("voiceStatusText");
const micIndicator = document.getElementById("micIndicator");
let activeRecorder = null;
let activeStream = null;
let cancelCapture = false;

consentVoice.addEventListener("change", () => {
  if (!consentVoice.checked) {
    if (activeRecorder && activeRecorder.state !== "inactive") {
      cancelCapture = true;
      activeRecorder.stop();
      stopMicrophoneTracks();
      setVoiceState("inactive", "Consent withdrawn. Recording stopped; no sample will be sent.");
    } else {
      voiceStatusText.textContent = "Microphone inactive. Consent is required before access.";
    }
  }
  btnVoice.disabled = !consentVoice.checked || Boolean(activeRecorder);
});
function setVoiceState(state, message) {
  voiceStatus.dataset.state = state;
  micIndicator.classList.toggle("recording", state === "recording");
  voiceStatusText.textContent = message;
}
function stopMicrophoneTracks() {
  if (activeStream) {
    activeStream.getTracks().forEach(track => track.stop());
    activeStream = null;
  }
}
function captureBlobForTwoSeconds(stream) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let recorder;
    try { recorder = new MediaRecorder(stream); }
    catch (_) { reject(new Error("This browser cannot record microphone audio.")); return; }
    activeRecorder = recorder;
    cancelCapture = false;
    recorder.ondataavailable = event => { if (event.data && event.data.size > 0) chunks.push(event.data); };
    recorder.onerror = () => reject(new Error("Microphone recording failed."));
    recorder.onstop = () => {
      activeRecorder = null;
      btnCancelVoice.classList.add("hidden");
      if (cancelCapture) { chunks.length = 0; reject(new Error("Recording cancelled.")); return; }
      const recorded = new Blob(chunks, {type:recorder.mimeType || "audio/webm"});
      chunks.length = 0;
      resolve(recorded);
    };
    recorder.start();
    btnCancelVoice.classList.remove("hidden");
    setVoiceState("recording", "RECORDING — microphone active. This stops automatically after 2 seconds.");
    window.setTimeout(() => { if (recorder.state !== "inactive") recorder.stop(); }, 2000);
  });
}
async function blobToMono16k(recorded) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const OfflineContextClass = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  if (!AudioContextClass || !OfflineContextClass) throw new Error("This browser does not support the required audio processing.");
  const context = new AudioContextClass();
  try {
    const decoded = await context.decodeAudioData(await recorded.arrayBuffer());
    const offline = new OfflineContextClass(1, 32000, 16000);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination);
    source.start(0);
    const rendered = await offline.startRendering();
    return rendered.getChannelData(0).slice(0, 32000);
  } finally {
    if (context.state !== "closed") await context.close();
  }
}
async function captureTwoSecondWindow() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error("Microphone access is unavailable. Use HTTPS or localhost.");
  if (!window.MediaRecorder) throw new Error("This browser does not support microphone recording.");
  activeStream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
  let recorded = null;
  try {
    recorded = await captureBlobForTwoSeconds(activeStream);
    stopMicrophoneTracks();
    setVoiceState("processing", "Microphone off. Preparing the sample in memory…");
    const samples = await blobToMono16k(recorded);
    recorded = null;
    return samples;
  } finally {
    stopMicrophoneTracks();
    activeRecorder = null;
    btnCancelVoice.classList.add("hidden");
    recorded = null;
  }
}
btnCancelVoice.addEventListener("click", () => {
  if (activeRecorder && activeRecorder.state !== "inactive") {
    cancelCapture = true;
    activeRecorder.stop();
    setVoiceState("inactive", "Recording stopped. No sample was sent.");
  }
});
btnVoice.addEventListener("click", async () => {
  if (!consentVoice.checked) { setVoiceState("inactive", "Consent is required before microphone access."); return; }
  btnVoice.disabled = true;
  btnVoice.textContent = "Starting microphone…";
  voiceOut.classList.add("hidden");
  let samples = null;
  try {
    setVoiceState("requesting", "Waiting for microphone permission…");
    samples = await captureTwoSecondWindow();
    if (!consentVoice.checked) throw new Error("Consent was withdrawn. No sample was sent.");
    setVoiceState("processing", "Sending the consented sample to the configured RAKSHA service…");
    const v = await api("/api/citizen/screen_voice", {consent:true,sample_rate:16000,samples:Array.from(samples)});
    const toneClass = v.verdict === "SUSPICIOUS" ? "HIGH" : (v.verdict === "LIKELY_GENUINE" ? "LOW" : "MODERATE");
    voiceOut.classList.remove("hidden");
    voiceOut.innerHTML = '<div class="verdict ' + toneClass + '">' + esc(v.verdict) + '</div>'
      + '<p>' + esc(v.reason || "No further explanation returned.") + '</p>'
      + '<p>Engine: ' + esc(v.engine) + ' · Model: ' + esc(v.model_status || "unknown") + '</p>'
      + '<div class="helpline">' + esc(v.disclaimer || "Advisory screening only. A verdict does not verify a caller identity.") + ' Call 1930 if pressured or defrauded.</div>';
    setVoiceState("inactive", "Screening complete. Microphone is off and the temporary sample has been cleared.");
  } catch (error) {
    voiceOut.classList.remove("hidden");
    voiceOut.textContent = error.message || "Voice screening unavailable.";
    setVoiceState("inactive", "Microphone inactive. No audio is retained by the app.");
  } finally {
    if (samples) samples.fill(0);
    samples = null;
    stopMicrophoneTracks();
    activeRecorder = null;
    btnCancelVoice.classList.add("hidden");
    btnVoice.disabled = !consentVoice.checked;
    btnVoice.textContent = "Record 2-second sample and screen";
  }
});

/* Citizen incident reporting — audio is never included */
let selectedCategory = null;
document.querySelectorAll(".chip").forEach(chip => chip.addEventListener("click", () => {
  selectedCategory = chip.dataset.cat;
  document.querySelectorAll(".chip").forEach(item => item.classList.toggle("selected", item === chip));
}));
const sevRange = document.getElementById("sevRange");
const sevVal = document.getElementById("sevVal");
sevRange.addEventListener("input", () => { sevVal.textContent = (sevRange.value / 100).toFixed(2); });
const caseRef = document.getElementById("caseRef");
const btnReport = document.getElementById("btnReport");
const repOut = document.getElementById("reportResult");
btnReport.addEventListener("click", async () => {
  if (!selectedCategory) { repOut.classList.remove("hidden"); repOut.textContent = "Pick a category first."; return; }
  btnReport.disabled = true;
  btnReport.textContent = "Sending…";
  try {
    const body = {category:selectedCategory,severity:sevRange.value / 100};
    const caseValue = caseRef.value.trim();
    if (caseValue) body.case_id = caseValue;
    const v = await api("/api/citizen/report", body);
    repOut.classList.remove("hidden");
    const message = v.forwarded && v.forwarded.forwarded ? "Report reached the RAKSHA response network." : "Report noted in demo/offline mode.";
    repOut.innerHTML = '<div class="verdict LOW">REPORTED</div><div>' + esc(message) + '</div>'
      + '<div>Event ' + esc(v.event_id) + ' · severity ' + esc(v.severity) + '</div>'
      + '<div class="helpline">If money was lost, call 1930 promptly.</div>';
  } catch (_) {
    repOut.classList.remove("hidden");
    repOut.textContent = "Report could not be sent. Call 1930 if you need urgent help.";
  } finally {
    btnReport.disabled = false;
    btnReport.textContent = "Send report";
  }
});
window.addEventListener("pagehide", () => {
  cancelCapture = true;
  consentVoice.checked = false;
  if (activeRecorder && activeRecorder.state !== "inactive") activeRecorder.stop();
  stopMicrophoneTracks();
});
if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
