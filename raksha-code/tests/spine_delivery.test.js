/* CITIZEN SPINE — PART FOUR: Delivery & Offline.
 *
 * The four invariants from `specs/01c_citizen_spine_four_parts.md` §Part Four:
 *
 *   1. Never lies     a report is reported sent only when the server accepted it
 *   2. Loses nothing  a failed flush keeps the backlog
 *   3. Offline-first  panic works with no network, no queue space and no server
 *   4. No stale shell a version bump invalidates every old cache
 *
 * Part Four is the only part that touches the network, so it is the only part
 * where "did it send?" is a question. Every test here is about that question
 * being answered correctly.
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const Q = require("../citizen/app/queue.js");
const S = require("../citizen/app/send-state.js");

const APP = path.join(__dirname, "..", "citizen", "app");

function memStore() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
  };
}

/* Load a browser script into a sandbox that looks enough like a window. */
function loadInPage(file, extraGlobals) {
  const sandbox = Object.assign(
    { window: {}, document: { addEventListener() {}, getElementById: () => null },
      navigator: {}, console },
    extraGlobals || {}
  );
  sandbox.window.addEventListener = () => {};
  sandbox.window.localStorage = memStore();
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(APP, file), "utf8"), sandbox,
                  { filename: file });
  return sandbox;
}

/* ------------------------------------------------------------------ */
/* 1. Never lies                                                      */
/* ------------------------------------------------------------------ */
test("a Response for a 500 is NOT accepted as a successful send", async () => {
  /* The defect this test was written for. `flush` treated any truthy return as
   * success, so the most natural call site — flush(store, e => fetch(...)) —
   * passed a Response, which is truthy for a 500. The report was deleted and
   * reported as sent. */
  const store = memStore();
  Q.enqueue(store, { category: "voice", severity: 0.9 });
  const out = await Q.flush(store, async () => ({ status: 500 }));
  assert.strictEqual(out.sent, 0);
  assert.strictEqual(out.remaining, 1);
  assert.strictEqual(Q.size(store), 1, "a 500 must not delete a report");
});

test("a Response for a 200 is accepted", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "voice" });
  const out = await Q.flush(store, async () => ({ status: 200 }));
  assert.strictEqual(out.sent, 1);
  assert.strictEqual(Q.size(store), 0);
});

test("a 4xx is kept but not retried forever in one pass", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "voice" });
  const out = await Q.flush(store, async () => ({ status: 422 }));
  assert.strictEqual(out.sent, 0);
  assert.strictEqual(out.rejected, 1);
  assert.strictEqual(Q.size(store), 1, "a refused report must stay visible");
});

test("the boolean contract still works unchanged", async () => {
  /* 8 pre-existing tests assert exact {sent, remaining} objects. The fix had to
   * preserve that shape or it would have rewritten the whole suite. */
  const store = memStore();
  Q.enqueue(store, { category: "voice" });
  const ok = await Q.flush(store, async () => true);
  assert.deepStrictEqual(ok, { sent: 1, remaining: 0 });
});

test("classifySend tells a refusal apart from a dead network", () => {
  assert.strictEqual(S.classifySend(null), "sent");
  assert.strictEqual(S.classifySend({ status: 200 }), "sent");
  assert.strictEqual(S.classifySend({ status: 500 }), "retry");
  assert.strictEqual(S.classifySend({ status: 503 }), "retry");
  assert.strictEqual(S.classifySend({ status: 404 }), "rejected");
  assert.strictEqual(S.classifySend({ status: 422 }), "rejected");
  assert.strictEqual(S.classifySend(new TypeError("Failed to fetch")), "retry");
});

test("429 means slow down, not give up", () => {
  /* The one 4xx that IS worth retrying. A naive `>= 400 -> rejected` rule
   * would tell a user their report was refused when they are merely being
   * rate-limited, which is a lie in the opposite direction. */
  assert.strictEqual(S.classifySend({ status: 429 }), "retry");
  assert.strictEqual(S.classifySend({ status: 408 }), "retry");
});

test("a rejected report never claims it will be sent later", () => {
  assert.ok(!/will be sent/i.test(S.SEND_COPY.rejected));
  assert.ok(/1930/.test(S.SEND_COPY.rejected), "must offer the alternative route");
  assert.ok(/kept on this device/i.test(S.SEND_COPY.retry));
});

/* ------------------------------------------------------------------ */
/* 2. Loses nothing                                                   */
/* ------------------------------------------------------------------ */
test("a network failure mid-flush keeps the unsent remainder in order", async () => {
  const store = memStore();
  for (const id of ["A", "B", "C"]) {
    Q.enqueue(store, { category: "voice", case_id: id });
  }
  let n = 0;
  const out = await Q.flush(store, async () => {
    n += 1;
    if (n <= 2) return { status: 200 };
    throw new TypeError("Failed to fetch");
  });
  assert.strictEqual(out.sent, 2);
  assert.strictEqual(out.remaining, 1);
  const left = Q.readQueue(store);
  assert.deepStrictEqual(left.map((e) => e.case_id), ["C"], "order must be preserved");
});

test("a sender that throws does not lose the backlog", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "voice" });
  await Q.flush(store, async () => { throw new Error("boom"); });
  assert.strictEqual(Q.size(store), 1);
});

test("nothing from a queued entry ever leaks into storage", async () => {
  const store = memStore();
  Q.enqueue(store, {
    category: "voice", severity: 0.8, lang: "te", case_id: "abc123",
    text: "my OTP is 123456", samples: [0.1, 0.2], phone: "9876543210",
  });
  const raw = store.getItem(Q.QUEUE_KEY);
  assert.ok(!raw.includes("OTP"), "message content reached storage");
  assert.ok(!raw.includes("9876543210"), "a phone number reached storage");
  assert.ok(!raw.includes("samples"), "audio reached storage");
  assert.deepStrictEqual(Object.keys(JSON.parse(raw)[0]).sort(),
                         ["case_id", "category", "lang", "severity"]);
});

/* ------------------------------------------------------------------ */
/* 3. Offline-first: panic                                            */
/* ------------------------------------------------------------------ */
test("the panic path issues no network request at all", () => {
  /* Proving a negative, which is the only kind of proof that matters for the
   * one control that must work when everything else does not. */
  let fetched = 0;
  const page = loadInPage("panic.js", {
    fetch: () => { fetched += 1; throw new Error("offline"); },
  });
  const P = page.window.RakshaPanic;
  const order = [];
  const res = P.runPanic({
    lock: () => order.push("LOCK"),
    stopCapture: () => order.push("STOP_CAPTURE"),
    dial: () => order.push("DIAL"),
  });
  assert.strictEqual(fetched, 0, "panic touched the network");
  assert.deepStrictEqual(order, ["LOCK", "STOP_CAPTURE", "DIAL"],
                         "safety order must be lock -> stop -> dial");
  assert.strictEqual(res.failed.length, 0);
});

test("panic completes with a full queue and a dead network", async () => {
  const store = memStore();
  for (let i = 0; i < Q.QUEUE_MAX; i += 1) {
    Q.enqueue(store, { category: "voice", case_id: "c" + i });
  }
  assert.strictEqual(Q.size(store), Q.QUEUE_MAX);

  const page = loadInPage("panic.js", {
    fetch: () => { throw new TypeError("Failed to fetch"); },
    localStorage: store,
  });
  const P = page.window.RakshaPanic;
  const order = [];
  const res = P.runPanic({
    lock: () => order.push("LOCK"),
    stopCapture: () => order.push("STOP_CAPTURE"),
    dial: () => order.push("DIAL"),
  });
  assert.deepStrictEqual(order, ["LOCK", "STOP_CAPTURE", "DIAL"]);
  assert.strictEqual(res.state, P.PANIC_STATE.LOCKED);
});

test("panic still dials when the overlay throws", () => {
  /* In a panic, a broken overlay must not stop the call. */
  const page = loadInPage("panic.js", {});
  const P = page.window.RakshaPanic;
  const order = [];
  const res = P.runPanic({
    lock: () => { throw new Error("DOM is gone"); },
    stopCapture: () => order.push("STOP_CAPTURE"),
    dial: () => order.push("DIAL"),
  });
  assert.deepStrictEqual(order, ["STOP_CAPTURE", "DIAL"]);
  assert.ok(res.failed.includes("LOCK"));
});

/* ------------------------------------------------------------------ */
/* 4. No stale shell                                                  */
/* ------------------------------------------------------------------ */
function loadSw(clientsControlled) {
  const listeners = {};
  const calls = { claim: 0, skipWaiting: 0, deleted: [], added: null };
  const sandbox = {
    self: null,
    caches: {
      open: async () => ({ addAll: async (a) => { calls.added = a; } }),
      keys: async () => ["raksha-citizen-v0.4.0", "raksha-citizen-v0.4.1"],
      delete: async (k) => { calls.deleted.push(k); },
      match: async () => undefined,
    },
    Promise,
    URL,
    Response,
    console,
  };
  sandbox.self = {
    addEventListener: (ev, fn) => { listeners[ev] = fn; },
    skipWaiting: () => { calls.skipWaiting += 1; },
    clients: {
      claim: () => { calls.claim += 1; return Promise.resolve(); },
      matchAll: async () => clientsControlled.map((c) => ({ controller: c })),
    },
    location: { origin: "https://example.test" },
  };
  sandbox.self.self = sandbox.self;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(APP, "sw.js"), "utf8"), sandbox,
                  { filename: "sw.js" });
  return { listeners, calls, sandbox };
}

test("the worker never caches an /api/ response", () => {
  const src = fs.readFileSync(path.join(APP, "sw.js"), "utf8");
  assert.ok(src.includes('url.pathname.startsWith("/api/")'),
            "the /api/ bypass is the rule that keeps verdicts out of the cache");
  const assets = src.match(/const ASSETS = \[([\s\S]*?)\]/)[1];
  assert.ok(!/\/api\//.test(assets), "an API path in the asset list would poison the cache");
});

test("a version bump invalidates every previous cache", async () => {
  const { listeners, calls, sandbox } = loadSw([true]);
  let waited;
  listeners.activate({ waitUntil: (p) => { waited = p; } });
  await waited;
  assert.deepStrictEqual(calls.deleted, ["raksha-citizen-v0.4.0"],
                         "the old version must be deleted");
});

test("an open page is not claimed mid-session", async () => {
  /* The defect this test was written for. install() skips waiting and activate()
   * used to claim unconditionally, so a new worker took over a page that was
   * still running the old scripts — whose caches had just been deleted. */
  const { listeners, calls } = loadSw([/* already controlled */ true]);
  let waited;
  listeners.activate({ waitUntil: (p) => { waited = p; } });
  await waited;
  assert.strictEqual(calls.claim, 0, "an open, controlled page must keep its worker");
});

test("a first install is claimed immediately", async () => {
  /* No controller means nothing to disrupt: the page has no old scripts. */
  const { listeners, calls } = loadSw([/* not controlled */ false]);
  let waited;
  listeners.activate({ waitUntil: (p) => { waited = p; } });
  await waited;
  assert.strictEqual(calls.claim, 1);
});

test("every script index.html loads is in the offline cache", () => {
  /* This is the Phase 3 bug that made the panic button dead offline, and the
   * reason a new file (send-state.js) cannot be added without also being
   * cached. Derived from index.html so the list cannot drift again. */
  const html = fs.readFileSync(path.join(APP, "index.html"), "utf8");
  const srcs = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(srcs.length > 0, "index.html stopped loading any scripts?");
  const sw = fs.readFileSync(path.join(APP, "sw.js"), "utf8");
  for (const s of srcs) {
    assert.ok(sw.includes('"./' + s + '"'), `${s} is loaded but not cached offline`);
  }
});

test("the cache version is bumped when the asset list changes", () => {
  const sw = fs.readFileSync(path.join(APP, "sw.js"), "utf8");
  const version = sw.match(/const CACHE = "raksha-citizen-(v[\d.]+)"/);
  assert.ok(version, "the cache version disappeared");
  assert.ok(version[1] !== "v0.4.0",
            "send-state.js was added, so the cache version had to move");
});
