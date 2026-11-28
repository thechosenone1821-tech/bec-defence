/* Functional fake-hospital attack demo.

   All endpoints are same-origin and relative. The injected token is a
   read-scoped console token; query fallback exists for preview proxies that
   strip Authorization headers. The controls mutate only an isolated synthetic
   scenario, never the live deterministic campaign or a real host.
*/
const READ_TOKEN = __RAKSHA_DEMO_TOKEN__;
const AUTH_HEADERS = {
  "Authorization": "Bearer " + READ_TOKEN,
  "X-API-Token": READ_TOKEN
};
const PATHS = {
  state: "/api/infra/demo/hospital/state",
  start: "/api/infra/demo/hospital/start",
  step: "/api/infra/demo/hospital/step",
  reset: "/api/infra/demo/hospital/reset"
};

let lastState = null;
let playTimer = null;
let toastTimer = null;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function readURL(path, verb) {
  if (verb && verb !== "GET") return path;
  const url = new URL(path, location.origin);
  url.searchParams.set("access_token", READ_TOKEN);
  return url.pathname + url.search + url.hash;
}

async function api(path, method) {
  const verb = method || "GET";
  const options = {
    method: verb,
    headers: Object.assign({}, AUTH_HEADERS),
    cache: "no-store"
  };
  if (verb !== "GET") {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify({});
  }
  const response = await fetch(readURL(path, verb), options);
  if (!response.ok) throw new Error(path + " returned " + response.status);
  return response.json();
}

function showToast(message, bad) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show" + (bad ? " bad" : "");
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toast.className = "toast"; }, 2600);
}

function statusLabel(status) {
  return ({
    normal: "normal",
    observed: "observed",
    detected: "finding",
    quarantined: "quarantined",
    dry_run_contained: "dry-run contained"
  })[status] || status;
}

function renderAssets(assets) {
  const box = document.getElementById("asset-map");
  if (!assets.length) {
    box.innerHTML = '<div class="empty">No synthetic assets loaded.</div>';
    return;
  }
  box.innerHTML = assets.map(asset => {
    const status = String(asset.status || "normal");
    return `<div class="asset ${esc(status)}">
      <div class="role">${esc(asset.role || asset.kind || "asset")}${asset.crown ? " · crown" : ""}</div>
      <div class="name">${esc(asset.id)}</div>
      <div class="status status-${esc(status)}">${esc(statusLabel(status))}</div>
      ${asset.last_event ? `<div class="muted">last: ${esc(asset.last_event)}</div>` : ""}
    </div>`;
  }).join("");
}

function renderAttackFeed(attacks) {
  const feed = document.getElementById("attack-feed");
  if (!attacks.length) {
    feed.innerHTML = '<div class="empty">No attacks shown yet. Press Start scenario or Play all.</div>';
    return;
  }
  feed.innerHTML = attacks.slice().reverse().map(entry => {
    const step = entry.step || {};
    const cls = entry.outcome === "quarantined" ? "quarantined"
      : entry.outcome === "finding" ? "finding" : "no_detection";
    const tagCls = entry.outcome === "quarantined" ? "bad" : (entry.outcome === "finding" ? "ok" : "");
    const result = entry.result || {};
    const rules = (entry.detector_rules || []).join(", ") || "none";
    const verdicts = (entry.verdicts || []).join(", ") || "none";
    const actions = (entry.dry_run_actions || []).join(", ") || "none";
    return `<article class="attack ${cls}">
      <div class="attack-head">
        <strong>${esc(entry.index)}. ${esc(step.title || entry.event_id)}</strong>
        <span class="tag ${tagCls}">${esc(entry.outcome)}</span>
      </div>
      <p>${esc(step.narrative || result.reason || "")}</p>
      <div class="kv">
        <div><span>Phase</span><b>${esc(step.phase || "")}</b></div>
        <div><span>Technique</span><b>${esc(step.technique || "")}</b></div>
        <div><span>Target</span><b>${esc(step.target || "")}</b></div>
        <div><span>Detector rule</span><code>${esc(rules)}</code></div>
        <div><span>Verdicts</span><code>${esc(verdicts)}</code></div>
        <div><span>Dry-run actions</span><code>${esc(actions)}</code></div>
        <div><span>Ledger</span><b>#${esc(entry.ledger_height)}</b></div>
        <div><span>Real actions</span><b>${esc(entry.real_actions)}</b></div>
      </div>
    </article>`;
  }).join("");
}

function renderNext(next) {
  const box = document.getElementById("next-card");
  if (!next) {
    box.innerHTML = '<div class="empty">Exercise complete. Reset to run it again.</div>';
    return;
  }
  box.innerHTML = `<div class="attack finding">
    <div class="attack-head"><strong>${esc(next.title)}</strong><span class="tag">${esc(next.phase)}</span></div>
    <p>${esc(next.narrative)}</p>
    <div class="kv">
      <div><span>Technique</span><b>${esc(next.technique)}</b></div>
      <div><span>Target</span><b>${esc(next.target)}</b></div>
      <div><span>Expected</span><b>${esc(next.expected)}</b></div>
    </div>
  </div>`;
}

function renderDecisions(payload) {
  const box = document.getElementById("decision-list");
  const decisions = payload.decisions || [];
  if (!decisions.length) {
    box.innerHTML = '<div class="empty">No sealed decisions yet.</div>';
    return;
  }
  box.innerHTML = `<table><thead><tr><th>Seq</th><th>Kind</th><th>Verdict</th><th>Rule</th></tr></thead><tbody>${
    decisions.slice(-8).reverse().map(row =>
      `<tr><td>#${esc(row.seq)}</td><td>${esc(row.kind)}</td><td>${esc(row.verdict)}</td><td>${esc(row.rule_id)}</td></tr>`
    ).join("")
  }</tbody></table>`;
}

function renderQuarantine(payload) {
  const box = document.getElementById("quarantine-list");
  const items = payload.items || [];
  if (!items.length) {
    box.innerHTML = '<div class="empty">No quarantined events yet.</div>';
    return;
  }
  box.innerHTML = `<table><thead><tr><th>Event</th><th>State</th><th>Reason</th></tr></thead><tbody>${
    items.slice(-8).reverse().map(row =>
      `<tr><td><code>${esc(row.event_id)}</code></td><td>${esc(row.state)}</td><td>${esc(row.reason)}</td></tr>`
    ).join("")
  }</tbody></table>`;
}

function renderState(state) {
  lastState = state;
  const scenario = state.scenario || {};
  const runtime = state.runtime || {};
  document.getElementById("kpi-steps").textContent =
    `${scenario.steps_completed ?? 0} / ${scenario.steps_total ?? 0}`;
  document.getElementById("kpi-findings").textContent = runtime.finding_count ?? 0;
  document.getElementById("kpi-quarantine").textContent = runtime.quarantine_count ?? 0;
  document.getElementById("kpi-decisions").textContent = runtime.decision_count ?? 0;
  document.getElementById("kpi-ledger").textContent = runtime.ledger_height ?? 0;
  document.getElementById("kpi-real-actions").textContent = scenario.real_action_count ?? 0;

  const statePill = document.getElementById("scenario-state");
  statePill.textContent = scenario.done ? "complete" : (scenario.started ? "running" : "ready");
  statePill.className = "pill" + (scenario.done ? " live" : "");
  document.getElementById("campaign-fused").textContent =
    scenario.campaign_fused ? "campaign fused" : "campaign not fused";
  document.getElementById("executor-mode").textContent = scenario.executor_mode || "dry-run";
  document.getElementById("next-attack").textContent =
    state.next_step ? "next: " + state.next_step.title : "no next attack";

  renderAssets(state.assets || []);
  renderAttackFeed(state.attacks || []);
  renderNext(state.next_step);
  renderDecisions(runtime.decisions || {});
  renderQuarantine(runtime.quarantine || {});
  const verify = runtime.ledger_verify || {};
  document.getElementById("ledger-verify").textContent =
    `${verify.ok ? "OK" : "FAILED"} · height ${verify.height ?? 0} · ${verify.reason || "no reason"}\nhead ${verify.head || ""}`;
  document.getElementById("runtime-timeline").textContent =
    JSON.stringify((runtime.timeline || []).slice(-12), null, 2);
  setButtons();
}

function setButtons() {
  const done = Boolean(lastState && lastState.scenario && lastState.scenario.done);
  document.getElementById("btn-start").disabled = Boolean(playTimer);
  document.getElementById("btn-step").disabled = done || Boolean(playTimer);
  document.getElementById("btn-play").disabled = done || Boolean(playTimer);
  document.getElementById("btn-pause").disabled = !playTimer;
  document.getElementById("btn-reset").disabled = Boolean(playTimer);
  document.getElementById("auth-badge").textContent = playTimer ? "playing · read scope" : "read scope";
}

function stopPlay() {
  if (playTimer) {
    window.clearInterval(playTimer);
    playTimer = null;
  }
  setButtons();
}

async function refresh() {
  try {
    const state = await api(PATHS.state, "GET");
    renderState(state);
  } catch (error) {
    document.getElementById("demo-message").textContent = "State load failed: " + error.message;
    showToast("State load failed: " + error.message, true);
  }
}

async function start() {
  stopPlay();
  document.getElementById("demo-message").textContent = "Starting synthetic attack series…";
  try {
    const payload = await api(PATHS.start, "POST");
    renderState(payload.state);
    document.getElementById("demo-message").textContent =
      `Attack ${payload.step ? payload.step.index : 1} shown. Use Next attack or Play all.`;
    showToast("Scenario started");
  } catch (error) {
    document.getElementById("demo-message").textContent = "Start failed: " + error.message;
    showToast("Start failed: " + error.message, true);
  }
}

async function step() {
  if (lastState && lastState.scenario && lastState.scenario.done) return;
  try {
    const payload = await api(PATHS.step, "POST");
    renderState(payload.state);
    if (payload.step) {
      document.getElementById("demo-message").textContent =
        `Attack ${payload.step.index}: ${payload.step.step.title} · ${payload.step.outcome}.`;
    } else {
      document.getElementById("demo-message").textContent = "Exercise complete.";
    }
  } catch (error) {
    document.getElementById("demo-message").textContent = "Step failed: " + error.message;
    showToast("Step failed: " + error.message, true);
  }
}

async function playAll() {
  if (playTimer) return;
  if (!lastState || !lastState.scenario.started || lastState.scenario.done) {
    await start();
  }
  playTimer = window.setInterval(async () => {
    if (!lastState || lastState.scenario.done) {
      stopPlay();
      document.getElementById("demo-message").textContent = "Exercise complete.";
      showToast("Attack series complete");
      return;
    }
    await step();
  }, 900);
  setButtons();
  document.getElementById("demo-message").textContent = "Playing synthetic attack series…";
  showToast("Playing all attacks");
}

async function reset() {
  stopPlay();
  try {
    const state = await api(PATHS.reset, "POST");
    renderState(state);
    document.getElementById("demo-message").textContent = "Reset. Press Start scenario.";
    showToast("Scenario reset");
  } catch (error) {
    document.getElementById("demo-message").textContent = "Reset failed: " + error.message;
    showToast("Reset failed: " + error.message, true);
  }
}

function wireUI() {
  document.getElementById("btn-start").addEventListener("click", start);
  document.getElementById("btn-step").addEventListener("click", step);
  document.getElementById("btn-play").addEventListener("click", playAll);
  document.getElementById("btn-pause").addEventListener("click", () => {
    stopPlay();
    document.getElementById("demo-message").textContent = "Paused.";
    showToast("Playback paused");
  });
  document.getElementById("btn-reset").addEventListener("click", reset);
}

function init() {
  wireUI();
  refresh();
  window.setInterval(() => { if (!playTimer) refresh(); }, 10000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
