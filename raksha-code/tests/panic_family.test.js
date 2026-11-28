/* PART 1 — Phase 2: panic flow + family mode.
 *
 * The panic tests are mostly about ORDER. "Lock then dial" and "dial then lock"
 * produce the same set of side effects and a completely different experience for
 * the person using it, so a set-equality test would pass while the product was
 * wrong.
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const P = require(path.join(__dirname, "..", "citizen", "app", "panic.js"));
const F = require(path.join(__dirname, "..", "citizen", "app", "family.js"));

/* ------------------------------------------------------------------ */
/* 1. Panic — the order is the safety property                        */
/* ------------------------------------------------------------------ */
test("panic runs LOCK, then CLOSE_IMAGE_SESSION, then DIAL", () => {
  const trace = [];
  const out = P.runPanic({
    lock: () => trace.push("lock"),
    closeImageSession: () => trace.push("stop"),
    dial: () => trace.push("dial"),
  });
  assert.deepStrictEqual(trace, ["lock", "stop", "dial"]);
  assert.deepStrictEqual(out.done, ["LOCK", "CLOSE_IMAGE_SESSION", "DIAL"]);
  assert.deepStrictEqual(out.failed, []);
});

test("the lock always precedes the dial", () => {
  const trace = [];
  P.runPanic({
    lock: () => trace.push("lock"),
    closeImageSession: () => trace.push("stop"),
    dial: () => trace.push("dial"),
  });
  assert.ok(trace.indexOf("lock") < trace.indexOf("dial"),
    "dialling before locking leaves the scam screen visible underneath");
});

test("image session is closed before the dialler opens", () => {
  const trace = [];
  P.runPanic({
    lock: () => trace.push("lock"),
    closeImageSession: () => trace.push("stop"),
    dial: () => trace.push("dial"),
  });
  assert.ok(trace.indexOf("stop") < trace.indexOf("dial"),
    "image must not still be image buffer when the call starts");
});

test("a broken overlay does not prevent the call to 1930", () => {
  const trace = [];
  const out = P.runPanic({
    lock: () => { throw new Error("render failed"); },
    closeImageSession: () => trace.push("stop"),
    dial: () => trace.push("dial"),
  });
  assert.deepStrictEqual(trace, ["stop", "dial"]);
  assert.ok(out.failed.includes("LOCK"));
});

test("a broken buffer clear does not prevent the call either", () => {
  const trace = [];
  const out = P.runPanic({
    lock: () => trace.push("lock"),
    closeImageSession: () => { throw new Error("buffer gone"); },
    dial: () => trace.push("dial"),
  });
  assert.deepStrictEqual(trace, ["lock", "dial"]);
  assert.ok(out.failed.includes("CLOSE_IMAGE_SESSION"));
});

test("every missing effect is reported, none is silently skipped", () => {
  const out = P.runPanic({ dial: () => {} });
  assert.deepStrictEqual(out.failed, ["LOCK", "CLOSE_IMAGE_SESSION"]);
  assert.deepStrictEqual(out.done, ["DIAL"]);
});

test("runPanic never throws, whatever it is handed", () => {
  assert.doesNotThrow(() => P.runPanic());
  assert.doesNotThrow(() => P.runPanic({}));
  assert.doesNotThrow(() => P.runPanic({ lock: 42, closeImageSession: null, dial: "x" }));
});

test("state is LOCKED only when the lock actually succeeded", () => {
  assert.strictEqual(P.runPanic({ dial: () => {} }).state, P.PANIC_STATE.IDLE);
  assert.strictEqual(
    P.runPanic({ lock: () => {}, dial: () => {} }).state, P.PANIC_STATE.LOCKED);
});

/* ------------------------------------------------------------------ */
/* 2. Panic copy — three languages, no promises it cannot keep        */
/* ------------------------------------------------------------------ */
test("panic copy exists in en, hi and te", () => {
  for (const lang of ["en", "hi", "te"]) {
    const c = P.panicCopy(lang);
    assert.ok(c.title.length > 3, lang);
    assert.ok(c.body.length > 10, lang);
    assert.ok(c.cancel.length > 3, lang);
  }
});

test("hindi and telugu panic copy are in their own scripts", () => {
  assert.match(P.panicCopy("hi").title, /[\u0900-\u097f]/);
  assert.match(P.panicCopy("te").title, /[\u0c00-\u0c7f]/);
});

test("unknown language falls back to English", () => {
  assert.strictEqual(P.panicCopy("fr").title, P.panicCopy("en").title);
  assert.strictEqual(P.panicCopy().title, P.panicCopy("en").title);
});

test("panic copy tells the truth about the image buffer and pixels", () => {
  const c = P.panicCopy("en");
  assert.match((c.body + c.calling).toLowerCase(), /image|pixels|buffer/);
});

test("panic copy never claims it killed other apps", () => {
  for (const lang of ["en", "hi", "te"]) {
    const blob = JSON.stringify(P.panicCopy(lang)).toLowerCase();
    assert.ok(!blob.includes("other apps"), `${lang} claims control of other apps`);
    assert.ok(!blob.includes("lock the screen"));
  }
});

/* ------------------------------------------------------------------ */
/* 3. Family mode — presentation only, never re-scoring               */
/* ------------------------------------------------------------------ */
test("family mode defaults to off", () => {
  assert.strictEqual(F.familyDefaults().enabled, false);
});

test("family mode is off when storage is missing or broken", () => {
  assert.strictEqual(F.readFamily(null).enabled, false);
  assert.strictEqual(F.readFamily({ getItem() { throw new Error("x"); } }).enabled, false);
  assert.strictEqual(F.readFamily({ getItem: () => "garbage" }).enabled, false);
});

test("family mode round-trips through storage", () => {
  const store = {};
  const fake = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = v; },
  };
  assert.strictEqual(F.writeFamily(fake, true), true);
  assert.strictEqual(F.readFamily(fake).enabled, true);
  F.writeFamily(fake, false);
  assert.strictEqual(F.readFamily(fake).enabled, false);
});

test("family mode never changes the verdict itself", () => {
  for (const verdict of ["LOW", "MODERATE", "HIGH", "CRITICAL"]) {
    for (const enabled of [false, true]) {
      const out = F.presentVerdict(verdict, { enabled, escalateModerate: true, largerType: true });
      assert.strictEqual(out.band, verdict, "the verdict must never be rewritten");
      assert.strictEqual(out.verdictUnchanged, true);
    }
  }
});

test("family mode escalates MODERATE to actionable", () => {
  const off = F.presentVerdict("MODERATE", { enabled: false });
  const on = F.presentVerdict("MODERATE", { enabled: true, escalateModerate: true });
  assert.strictEqual(off.actionable, false);
  assert.strictEqual(on.actionable, true);
  assert.strictEqual(on.escalated, true);
});

test("family mode does not escalate a LOW band into an accusation", () => {
  const on = F.presentVerdict("LOW", { enabled: true, escalateModerate: true });
  assert.strictEqual(on.actionable, false);
  assert.strictEqual(on.escalated, false);
});

test("HIGH and CRITICAL are actionable regardless of family mode", () => {
  for (const on of [false, true]) {
    for (const v of ["HIGH", "CRITICAL"]) {
      assert.strictEqual(F.presentVerdict(v, { enabled: on }).actionable, true);
    }
  }
});

test("family mode adds larger type and marks the escalation visibly", () => {
  const on = F.presentVerdict("MODERATE", { enabled: true, escalateModerate: true, largerType: true });
  assert.ok(on.cssClasses.includes("family-type"));
  assert.ok(on.cssClasses.includes("family-escalated"));
});

test("family mode hides the severity slider on the report screen", () => {
  assert.strictEqual(F.hideSeveritySlider({ enabled: false }), false);
  assert.strictEqual(F.hideSeveritySlider({ enabled: true, hideSeveritySlider: true }), true);
  assert.strictEqual(F.hideSeveritySlider({ enabled: true, hideSeveritySlider: false }), false);
});

test("presentVerdict tolerates a missing verdict", () => {
  const out = F.presentVerdict(undefined, F.familyDefaults());
  assert.strictEqual(out.band, "MODERATE");
  assert.strictEqual(out.verdictUnchanged, true);
});
