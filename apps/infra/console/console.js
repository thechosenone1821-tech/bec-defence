/* Read-only SOC console. No write route, decision-change route, model endpoint
   or mutation control is present. All URLs are same-origin and relative. */
const READ_TOKEN = __RAKSHA_READ_TOKEN__;
const AUTH_HEADERS = { "Authorization": "Bearer " + READ_TOKEN };

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

async function getJSON(path) {
  const response = await fetch(path, { headers: AUTH_HEADERS });
  if (!response.ok) throw new Error(path + " returned " + response.status);
  return response.json();
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
}

function renderDecisions(payload) {
  const body = document.getElementById("decisions");
  document.getElementById("decision-count").textContent = payload.count ?? 0;
  if (!payload.decisions.length) {
    body.innerHTML = '<tr><td colspan="5">No sealed decisions yet.</td></tr>';
    return;
  }
  body.innerHTML = payload.decisions.map(row =>
    `<tr><td>#${esc(row.seq)}</td><td class="${row.kind === "refusal" ? "refusal" : "allowed"}">${esc(row.kind)}</td>` +
    `<td>${esc(row.verdict)}</td><td>${esc(row.rule_id)}</td><td><code>${esc(row.ref)}</code></td></tr>`
  ).join("");
}

function renderQuarantine(payload) {
  const body = document.getElementById("quarantine");
  document.getElementById("quarantine-count").textContent = payload.count ?? 0;
  if (!payload.items.length) {
    body.innerHTML = '<tr><td colspan="4">No quarantined events.</td></tr>';
    return;
  }
  body.innerHTML = payload.items.map(row =>
    `<tr><td><code>${esc(row.event_id)}</code></td><td class="refusal">${esc(row.state)}</td>` +
    `<td>${esc(row.organ)}</td><td>${esc(row.reason)}</td></tr>`
  ).join("");
}

async function refresh() {
  try {
    const [state, decisions, quarantine, verify, metrics] = await Promise.all([
      getJSON("/v1/state"),
      getJSON("/v1/decisions"),
      getJSON("/v1/quarantine"),
      getJSON("/v1/ledger/verify"),
      getJSON("/v1/metrics")
    ]);
    document.getElementById("ledger-height").textContent = state.ledger_height ?? 0;
    document.getElementById("detection-count").textContent = state.detections.length ?? 0;
    document.getElementById("quarantine-count").textContent = state.quarantine_count ?? 0;
    document.getElementById("ledger-verify").textContent =
      `${verify.ok ? "OK" : "FAILED"} · height ${verify.height} · ${verify.reason}\nhead ${verify.head}`;
    document.getElementById("commander").textContent =
      `enabled: ${state.commander.enabled}\nmode: ${state.commander.mode}\n` +
      `model_invoked: ${state.commander.model_invoked}\nfallback_only: ${state.commander.fallback_only}\n` +
      `reason: ${state.commander.reason}`;
    document.getElementById("metrics").textContent =
      JSON.stringify(metrics.counters || {}, null, 2);
    renderTimeline(state.timeline || []);
    renderDecisions(decisions);
    renderQuarantine(quarantine);
  } catch (error) {
    document.getElementById("ledger-verify").textContent = "Read failed: " + error.message;
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

document.getElementById("refresh").addEventListener("click", refresh);
refresh();
connectStream();
setInterval(refresh, 5000);
