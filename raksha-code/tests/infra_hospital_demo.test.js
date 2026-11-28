/* Functional fake-hospital Infra demo — UI/asset contract.

   These tests are deliberately static/sandbox-only. The Python HTTP smoke is
   the runtime proof; here we prove the UI has real controls, same-origin
   relative endpoints, injected read auth, no external host calls, and that
   POST controls never carry a query token.
*/

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..", "..");
const HTML_PATH = path.join(ROOT, "apps", "infra", "console", "hospital.html");
const JS_PATH = path.join(ROOT, "apps", "infra", "console", "hospital.js");
const TOPOLOGY_PATH = path.join(ROOT, "apps", "infra", "demo", "hospital_topology.json");

function read(relPath) {
  return fs.readFileSync(relPath, "utf8");
}

function fakeElement() {
  return {
    textContent: "", innerHTML: "", className: "", disabled: false,
    addEventListener() {}, classList: { toggle() {} },
  };
}

function loadDemoJS() {
  const source = read(JS_PATH)
    .replace("__RAKSHA_DEMO_TOKEN__", JSON.stringify("unit-read-token"));
  const listeners = {};
  const sandbox = {
    console, URL, JSON, Promise, Object, Array, String, Number, Boolean,
    fetch: async () => ({ ok: true, json: async () => ({}) }),
    location: { origin: "https://preview.invalid" },
    navigator: {},
    document: {
      readyState: "loading",
      addEventListener: (name, fn) => { listeners[name] = fn; },
      getElementById: () => fakeElement(),
      querySelectorAll: () => [],
    },
    window: {
      setInterval: () => 1,
      clearInterval: () => {},
      setTimeout: () => 1,
      clearTimeout: () => {},
    },
  };
  sandbox.window.document = sandbox.document;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: "hospital.js" });
  return { sandbox, listeners };
}

test("fake-hospital UI exposes real start, step, play, pause and reset controls", () => {
  const html = read(HTML_PATH);
  for (const id of ["btn-start", "btn-step", "btn-play", "btn-pause", "btn-reset"]) {
    assert.ok(html.includes(`id="${id}"`), `missing control: ${id}`);
  }
  assert.ok(html.includes("Attack series on a fake hospital system"));
  assert.ok(html.includes("no real patient data"));
  assert.ok(html.includes('src="hospital.js"'), "demo script must be same-origin relative");
  assert.ok(!/https?:\/\//i.test(html), "hospital UI references an external URL");
  assert.ok(!/localhost|127\.0\.0\.1/i.test(html), "hospital UI references a sandbox-local URL");
});

test("fake-hospital demo JS uses same-origin API paths and read-only auth", () => {
  const js = read(JS_PATH);
  assert.ok(js.includes('"/api/infra/demo/hospital/state"'));
  assert.ok(js.includes('"/api/infra/demo/hospital/start"'));
  assert.ok(js.includes('"/api/infra/demo/hospital/step"'));
  assert.ok(js.includes('"/api/infra/demo/hospital/reset"'));
  assert.ok(js.includes('"Authorization": "Bearer " + READ_TOKEN'));
  assert.ok(js.includes('"X-API-Token": READ_TOKEN'));
  assert.ok(!/https?:\/\//i.test(js), "demo JS references an external URL");
  assert.ok(!/localhost|127\.0\.0\.1/i.test(js), "demo JS references a sandbox-local URL");
  assert.ok(!js.includes("/v1/telemetry"), "demo JS must not write live telemetry");
  assert.ok(!js.includes("override"), "demo JS must not call an override path");
});

test("query read tokens are GET-only; POST controls use header or cookie auth", () => {
  const { sandbox } = loadDemoJS();
  const getURL = vm.runInContext("readURL(PATHS.state, 'GET')", sandbox);
  const postURL = vm.runInContext("readURL(PATHS.step, 'POST')", sandbox);
  assert.ok(getURL.includes("access_token=unit-read-token"),
            "GET state should support the read-query preview fallback");
  assert.strictEqual(postURL, "/api/infra/demo/hospital/step",
                     "POST controls must not carry a query token");
  assert.strictEqual(
    vm.runInContext("AUTH_HEADERS.Authorization", sandbox),
    "Bearer unit-read-token",
  );
});

test("fake-hospital topology is explicitly synthetic and non-trivial", () => {
  const topology = JSON.parse(read(TOPOLOGY_PATH));
  assert.strictEqual(topology.meta.synthetic, true);
  assert.strictEqual(topology.meta.name.includes("synthetic"), true);
  assert.ok(topology.vlans.length >= 6, "demo VLAN set is too small");
  assert.ok(topology.hosts.length >= 8, "demo host set is too small");
  assert.ok(topology.edges.length >= 8, "demo edge set is too small");
  assert.ok(topology.vlans.some(v => v.tier === 0), "crown clinical tier is missing");
});
