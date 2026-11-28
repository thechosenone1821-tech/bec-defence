/* PART 1 — Phase 3, task 3.6: the offline report queue.
 *
 * The property under test is not "does it store things". It is:
 *   a report is never lost, is never claimed as sent, and never carries content.
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const Q = require(path.join(__dirname, "..", "citizen", "app", "queue.js"));

function memStore() {
  const data = {};
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
    _raw: data,
  };
}

/* ------------------------------------------------------------------ */
/* 1. What may be stored                                              */
/* ------------------------------------------------------------------ */
test("only category, severity, lang and case_id are persisted", () => {
  const store = memStore();
  Q.enqueue(store, {
    category: "call", severity: 0.8, lang: "hi", case_id: "CASE_1",
    text: "secret message", pixels: [1, 2, 3], phone: "9999999999",
  });
  const raw = store._raw[Q.QUEUE_KEY];
  for (const banned of ["secret message", "9999999999", "pixels"]) {
    assert.ok(!raw.includes(banned), `queue stored forbidden content: ${banned}`);
  }
  assert.deepStrictEqual(Object.keys(JSON.parse(raw)[0]).sort(),
    ["case_id", "category", "lang", "severity"]);
});

test("an entry with no category is refused", () => {
  const store = memStore();
  const r = Q.enqueue(store, { severity: 0.9 });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(Q.size(store), 0);
});

test("severity is clamped and non-finite values are replaced", () => {
  const store = memStore();
  Q.enqueue(store, { category: "call", severity: 99 });
  Q.enqueue(store, { category: "call", severity: NaN });
  Q.enqueue(store, { category: "call", severity: -3 });
  const items = Q.readQueue(store);
  assert.deepStrictEqual(items.map((i) => i.severity), [1, 0.5, 0]);
});

test("strings are truncated so a huge field cannot fill storage", () => {
  const store = memStore();
  Q.enqueue(store, { category: "call", case_id: "x".repeat(5000) });
  assert.ok(Q.readQueue(store)[0].case_id.length <= 64);
});

/* ------------------------------------------------------------------ */
/* 2. Bounds and resilience                                           */
/* ------------------------------------------------------------------ */
test("the queue is bounded", () => {
  const store = memStore();
  for (let i = 0; i < Q.QUEUE_MAX + 25; i++) {
    Q.enqueue(store, { category: "call", severity: 0.5 });
  }
  assert.strictEqual(Q.size(store), Q.QUEUE_MAX);
});

test("the oldest entries are dropped first when full", () => {
  const store = memStore();
  for (let i = 0; i < Q.QUEUE_MAX + 1; i++) {
    Q.enqueue(store, { category: "call", case_id: `C${i}` });
  }
  const ids = Q.readQueue(store).map((i) => i.case_id);
  assert.strictEqual(ids[0], "C1", "the newest writes must survive, not the oldest");
});

test("corrupt storage reads as empty rather than throwing", () => {
  const store = memStore();
  store.setItem(Q.QUEUE_KEY, "{not json");
  assert.deepStrictEqual(Q.readQueue(store), []);
  assert.strictEqual(Q.size(store), 0);
});

test("non-array storage reads as empty", () => {
  const store = memStore();
  store.setItem(Q.QUEUE_KEY, '{"a":1}');
  assert.deepStrictEqual(Q.readQueue(store), []);
});

test("a missing store degrades quietly", () => {
  assert.strictEqual(Q.enqueue(null, { category: "call" }).ok, false);
  assert.deepStrictEqual(Q.readQueue(null), []);
  assert.strictEqual(Q.size(null), 0);
});

test("javascript: scheme inside a stored field is inert data, not markup", () => {
  const store = memStore();
  Q.enqueue(store, { category: "call", case_id: "javascript:alert(1)" });
  // Stored verbatim as a string; the UI must escape it on render (checked in
  // the Python suite via esc()). Assert it is not interpreted anywhere here.
  assert.strictEqual(Q.readQueue(store)[0].case_id, "javascript:alert(1)");
});

/* ------------------------------------------------------------------ */
/* 3. Flushing                                                        */
/* ------------------------------------------------------------------ */
test("a successful flush empties the queue", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "call" });
  Q.enqueue(store, { category: "message" });
  const out = await Q.flush(store, async () => true);
  assert.deepStrictEqual(out, {sent: 2, remaining: 0});
  assert.strictEqual(Q.size(store), 0);
});

test("a failed flush keeps every entry", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "call" });
  Q.enqueue(store, { category: "message" });
  const out = await Q.flush(store, async () => false);
  assert.deepStrictEqual(out, {sent: 0, remaining: 2});
  assert.strictEqual(Q.size(store), 2);
});

test("a partial flush keeps only the unsent remainder", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "call", case_id: "A" });
  Q.enqueue(store, { category: "call", case_id: "B" });
  Q.enqueue(store, { category: "call", case_id: "C" });
  let n = 0;
  const out = await Q.flush(store, async () => { n += 1; return n <= 2; });
  assert.deepStrictEqual(out, {sent: 2, remaining: 1});
  assert.deepStrictEqual(Q.readQueue(store).map((i) => i.case_id), ["C"]);
});

test("a sender that throws does not lose the backlog", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "call" });
  const out = await Q.flush(store, async () => { throw new Error("network"); });
  assert.deepStrictEqual(out, {sent: 0, remaining: 1});
  assert.strictEqual(Q.size(store), 1);
});

test("flushing an empty queue is a no-op", async () => {
  const store = memStore();
  const out = await Q.flush(store, async () => true);
  assert.deepStrictEqual(out, {sent: 0, remaining: 0});
});

test("entries are sent in the order they were queued", async () => {
  const store = memStore();
  Q.enqueue(store, { category: "call", case_id: "first" });
  Q.enqueue(store, { category: "call", case_id: "second" });
  const seen = [];
  await Q.flush(store, async (e) => { seen.push(e.case_id); return true; });
  assert.deepStrictEqual(seen, ["first", "second"]);
});

test("flush stops at the first failure rather than hammering a dead network", async () => {
  const store = memStore();
  for (const id of ["A", "B", "C"]) Q.enqueue(store, { category: "call", case_id: id });
  let calls = 0;
  await Q.flush(store, async () => { calls += 1; return false; });
  assert.strictEqual(calls, 1);
});

test("clear purges everything", () => {
  const store = memStore();
  Q.enqueue(store, { category: "call" });
  assert.strictEqual(Q.clear(store), true);
  assert.strictEqual(Q.size(store), 0);
});
