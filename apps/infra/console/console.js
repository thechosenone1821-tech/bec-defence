/* Completed read-only SOC console.

   No write route, decision-change route, model endpoint or mutation control is
   present. All URLs are same-origin and relative. The backend injects one
   read-scoped token, sets a same-origin read cookie, and accepts a read-only
   query token on GET routes when a preview proxy strips auth headers.
*/
const READ_TOKEN = __RAKSHA_READ_TOKEN__;
const AUTH_HEADERS = {
  "Authorization": "Bearer " + READ_TOKEN,
  "X-API-Token": READ_TOKEN
};

let lastSnapshot = null;
let toastTimer = null;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function readURL(path, extra) {
  const url = new URL(path, location.origin);
  url.searchParams.set("access_token", READ_TOKEN);
  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.pathname + url.search + url.hash;
}

async function getJSON(path, options) {
  const opts = options || {};
  const needsAuth = opts.auth !== false;
  const target = needsAuth ? readURL(path, opts.extra) : path;
  const response = await fetch(target, {
    headers: needsAuth ? AUTH_HEADERS : {},
    cache: "no-store"
  });
  if (!response.ok) throw new Error(path + " returned " + response.status);
  return response.json();
}

function showToast(message, bad) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show" + (bad ? " bad" : "");
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toast.className = "toast"; }, 2800);
}

function statusItem(label, value) {
  return `<div class="status-item"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function renderStatus(payload) {
  const box = document.getElementById("infra-status");
  const detectors = payload.detectors || {};
  box.innerHTML = [
    statusItem("ready", payload.ready ? "yes" : "no"),
    statusItem("model backed", payload.model_backed ? "yes" : "no"),
    statusItem("deterministic", payload.deterministic ? "yes" : "no"),
    statusItem("executor", payload.executor_mode || "unknown"),
    statusItem("Commander", payload.commander_enabled ? "enabled" : "disabled"),
    statusItem("console", payload.console_read_only ? "read-only" : "unexpected"),
    statusItem("organ registry", (detectors.organ_count ?? "unknown") + " organs / " + (detectors.registry_count ?? "unknown") + " registry"),
    statusItem("status path", payload.status_path || "unknown")
  ].join("");
  document.getElementById("auth-mode").textContent =
    (payload.read_auth_fallbacks || []).join(" · ") || "header + read cookie + read-only query fallback";
}

function renderTimeline(entries) {
  const body = document.getElementById("timeline");
  if (!entries.length) {
    body.innerHTML = '<tr><td colspan="6">No timeline yet.</td></tr>';
    return;
  }
  body.innerHTML = entries.map(row => {
    const cls = row.kind === "refusal" ? "refusal"
      : row.kind === "containment" ? "allowed"
      : row.stage === "ledger" ? "ledger" : "";
    return `<tr><td>${esc(row.step)}</td><td>${esc(row.stage)}</td>` +
      `<td class="${cls}">${esc(row.kind)}</td><td><code>${esc(row.ref)}</code></td>` +
      `<td>${row.ledger_seq ? "#" + esc(row.ledger_seq) : "—"}</td>` +
      `<td>${esc(row.detail)}</td></tr>`;
  }).join("");
  applyFilter();
}

function renderDecisions(payload) {
  const body = document.getElementById("decisions");
  document.getElementById("decision-count").textContent = payload.count ?? 0;
  if (!payload.decisions.length) {
    body.innerHTML = '<tr><td colspan="5">No sealed decisions yet.</td></tr>';
    applyFilter();
    return;
  }
  body.innerHTML = payload.decisions.map(row =>
    `<tr><td>#${esc(row.seq)}</td><td class="${row.kind === "refusal" ? "refusal" : "allowed"}">${esc(row.kind)}</td>` +
    `<td>${esc(row.verdict)}</td><td>${esc(row.rule_id)}</td><td><code>${esc(row.ref)}</code></td></tr>`
  ).join("");
  applyFilter();
}

function renderQuarantine(payload) {
  const body = document.getElementById("quarantine");
  if (!payload.items.length) {
    body.innerHTML = '<tr><td colspan="4">No quarantined events.</td></tr>';
    applyFilter();
    return;
  }
  body.innerHTML = payload.items.map(row =>
    `<tr><td><code>${esc(row.event_id)}</code></td><td class="refusal">${esc(row.state)}</td>` +
    `<td>${esc(row.organ)}</td><td>${esc(row.reason)}</td></tr>`
  ).join("");
  applyFilter();
}

function applyFilter() {
  const needle = (document.getElementById("filter").value || "").trim().toLowerCase();
  for (const id of ["timeline", "decisions", "quarantine"]) {
    const rows = document.getElementById(id).querySelectorAll("tr");
    rows.forEach(row => {
      row.hidden = Boolean(needle) && !row.textContent.toLowerCase().includes(needle);
    });
  }
}

function renderOrgans(card) {
  const body = document.getElementById("organ-list");
  const details = card.organ_details || [];
  if (!details.length) {
    body.innerHTML = '<tr><td colspan="5">No organ details in the detector card.</td></tr>';
    return;
  }
  body.innerHTML = details.map(spec =>
    `<tr><td><code>${esc(spec.name)}</code></td><td>${esc(spec.ring)}</td>` +
    `<td>${esc(spec.legacy_organ)}</td><td>${esc((spec.rule_ids || []).join(", "))}</td>` +
    `<td>${esc((spec.fixtures || []).join(", "))}</td></tr>`
  ).join("");
}

async function loadOrgans() {
  try {
    const card = await getJSON("/api/infra/detectors", {auth: false});
    renderOrgans(card);
    showToast("Organ card loaded");
  } catch (error) {
    showToast("Organ card failed: " + error.message, true);
  }
}

async function refresh() {
  try {
    const [status, capabilities, state, decisions, quarantine, verify, metrics, ledgerHead, campaigns] = await Promise.all([
      getJSON("/api/infra/status", {auth: false}),
      getJSON("/api/infra/capabilities", {auth: false}),
      getJSON("/v1/state"),
      getJSON("/v1/decisions"),
      getJSON("/v1/quarantine"),
      getJSON("/v1/ledger/verify"),
      getJSON("/v1/metrics"),
      getJSON("/v1/ledger/head"),
      getJSON("/v1/campaigns")
    ]);
    lastSnapshot = {
      status: status,
      capabilities: capabilities,
      state: state,
      decisions: decisions,
      quarantine: quarantine,
      ledger_verify: verify,
      metrics: metrics,
      ledger_head: ledgerHead,
      campaigns: campaigns
    };
    renderStatus(status);
    document.getElementById("ledger-height").textContent = state.ledger_height ?? 0;
    document.getElementById("detection-count").textContent = state.detections.length ?? 0;
    document.getElementById("quarantine-count").textContent = state.quarantine_count ?? 0;
    document.getElementById("ledger-head").textContent =
      `height ${ledgerHead.height} · seq ${ledgerHead.seq} · head ${ledgerHead.head}`;
    document.getElementById("ledger-verify").textContent =
      `${verify.ok ? "OK" : "FAILED"} · height ${verify.height} · ${verify.reason}\nhead ${verify.head}`;
    document.getElementById("campaigns").textContent = JSON.stringify(campaigns, null, 2);
    document.getElementById("commander").textContent =
      `enabled: ${state.commander.enabled}\nmode: ${state.commander.mode}\n` +
      `model_invoked: ${state.commander.model_invoked}\nfallback_only: ${state.commander.fallback_only}\n` +
      `reason: ${state.commander.reason}`;
    document.getElementById("metrics").textContent = JSON.stringify(metrics.counters || {}, null, 2);
    renderTimeline(state.timeline || []);
    renderDecisions(decisions);
    renderQuarantine(quarantine);
  } catch (error) {
    document.getElementById("infra-status").textContent = "Read failed: " + error.message;
    showToast("Refresh failed: " + error.message, true);
  }
}

function connectStream() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${location.host}/v1/telemetry/stream?token=${encodeURIComponent(READ_TOKEN)}`;
  const ws = new WebSocket(url);
  const badge = document.getElementById("ws-state");
  ws.onopen = () => { badge.textContent = "WS live · read scope"; badge.className = "badge ok"; };
  ws.onmessage = event => { void event; refresh(); };
  ws.onclose = () => { badge.textContent = "WS closed · polling"; badge.className = "badge warn"; };
  ws.onerror = () => { badge.textContent = "WS unavailable · polling"; badge.className = "badge warn"; };
}

function activatePanel(name) {
  document.querySelectorAll(".tab").forEach(button => {
    button.classList.toggle("active", button.dataset.panel === name);
  });
  document.querySelectorAll("main > section[data-panel]").forEach(section => {
    section.classList.toggle("active", section.dataset.panel === name);
  });
}

function downloadSnapshot() {
  if (!lastSnapshot) {
    showToast("No snapshot loaded yet", true);
    return;
  }
  const blob = new Blob([JSON.stringify(lastSnapshot, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "raksha-infra-snapshot.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("Snapshot downloaded");
}

async function copyStatus() {
  if (!lastSnapshot) {
    showToast("No status loaded yet", true);
    return;
  }
  const text = JSON.stringify(lastSnapshot.status, null, 2);
  try {
    if (!navigator.clipboard) throw new Error("clipboard unavailable");
    await navigator.clipboard.writeText(text);
    showToast("Status JSON copied");
  } catch (error) {
    showToast("Clipboard unavailable; use Download snapshot", true);
  }
}

async function tryApi(path) {
  const output = document.getElementById("api-output");
  output.textContent = "Loading " + path + "…";
  try {
    const payload = await getJSON(path, {auth: path.startsWith("/v1/")});
    output.textContent = JSON.stringify(payload, null, 2);
    showToast("Endpoint responded");
  } catch (error) {
    output.textContent = "Request failed: " + error.message;
    showToast("Endpoint failed: " + error.message, true);
  }
}

function wireUI() {
  document.querySelectorAll(".tab").forEach(button => {
    button.addEventListener("click", () => activatePanel(button.dataset.panel));
  });
  document.getElementById("refresh").addEventListener("click", refresh);
  document.getElementById("export").addEventListener("click", downloadSnapshot);
  document.getElementById("copy-status").addEventListener("click", copyStatus);
  document.getElementById("load-organs").addEventListener("click", loadOrgans);
  document.getElementById("filter").addEventListener("input", applyFilter);
  document.querySelectorAll("[data-api-path]").forEach(button => {
    button.addEventListener("click", () => tryApi(button.dataset.apiPath));
  });
}

function init() {
  wireUI();
  refresh();
  loadOrgans();
  connectStream();
  window.setInterval(refresh, 5000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
