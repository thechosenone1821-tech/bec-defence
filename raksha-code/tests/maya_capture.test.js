/* MAYA / VoiceGuard — Phase 2 JS tests for the capture core.
 *
 * Run:  node --test tests/maya_capture.test.js
 *       (also invoked from pytest via test_maya_phase2.py so a Python-only
 *        CI run still catches a broken worklet)
 *
 * These are the tests that make "we keep nothing" a verifiable claim.
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const fs = require("node:fs");

const MOD = path.join(__dirname, "..", "citizen", "app", "maya-capture.js");
const { RingBuffer, decimate3, sanitizeSample,
        TARGET_SR, RING_SECONDS, RING_SAMPLES } = require(MOD);

const SAMPLES = path.join(__dirname, "..", "citizen", "app", "maya-capture-worklet.js");

/* ------------------------------------------------------------------ */
test("declared constants match the documented policy", () => {
  assert.strictEqual(TARGET_SR, 16000);
  assert.strictEqual(RING_SECONDS, 3);
  assert.strictEqual(RING_SAMPLES, 48000);
});

/* ------------------------------------------------------------------ */
test("ring buffer never grows past its capacity", () => {
  const r = new RingBuffer(SAMPLES_QTY());
  assert.strictEqual(r.buf.length, r.len);
  for (let i = 0; i < r.len * 3; i += 1) r.push(0.5);
  assert.strictEqual(r.buf.length, r.len, "buffer grew — retention violated");
  assert.strictEqual(r.filled, r.len);
});

function SAMPLES_QTY() { return 48000; }

test("ring buffer holds at most 3 seconds", () => {
  const r = new RingBuffer(16000, 16000 * 3);
  for (let i = 0; i < 16000 * 10; i += 1) r.push(Math.sin(i / 10));
  assert.ok(r.seconds() <= 3.0 + 1e-9, `held ${r.seconds()}s`);
});

/* ------------------------------------------------------------------ */
test("oldest samples are overwritten, newest retained", () => {
  const r = new RingBuffer(1000, 4);
  // Values stay inside [-1, 1]: clamping is correct behaviour for audio, so
  // pushing 2..6 would legitimately all become 1 and prove nothing.
  [0.1, 0.2, 0.3, 0.4, 0.5, 0.6].forEach((v) => r.push(v));
  assert.deepStrictEqual(r.read().map((x) => +x.toFixed(4)),
                         [0.3, 0.4, 0.5, 0.6]);
});

test("a partially filled ring reads back in order", () => {
  const r = new RingBuffer(1000, 4);
  [0.1, 0.2].forEach((v) => r.push(v));
  assert.deepStrictEqual(r.read().map((x) => +x.toFixed(4)), [0.1, 0.2]);
});

test("an exactly full ring reads back in order without wrapping", () => {
  const r = new RingBuffer(1000, 4);
  [0.1, 0.2, 0.3, 0.4].forEach((v) => r.push(v));
  assert.deepStrictEqual(r.read().map((x) => +x.toFixed(4)),
                         [0.1, 0.2, 0.3, 0.4]);
});

test("read returns a copy, not the live buffer", () => {
  const r = new RingBuffer(1000, 4);
  [0.1, 0.2, 0.3, 0.4].forEach((v) => r.push(v));
  const out = r.read();
  out[0] = 0.9;
  assert.deepStrictEqual(r.read().map((x) => +x.toFixed(4)),
                         [0.1, 0.2, 0.3, 0.4], "caller mutated the ring");
});

/* ------------------------------------------------------------------ */
test("stop() zeroes the buffer and refuses further writes", () => {
  const r = new RingBuffer(16000, 1600);
  for (let i = 0; i < 800; i += 1) r.push(0.7);
  r.stop();
  assert.ok(r.buf.every((v) => v === 0), "audio survived stop()");
  r.push(0.9);
  assert.ok(r.buf.every((v) => v === 0), "write accepted after stop");
  assert.strictEqual(r.read().length, 0);
  assert.ok(r.zeroedCount >= 1);
});

test("zero() is idempotent and counted", () => {
  const r = new RingBuffer(16000, 100);
  r.push(0.3);
  r.zero();
  const n = r.zeroedCount;
  r.zero();
  assert.strictEqual(r.zeroedCount, n + 1);
  assert.ok(r.buf.every((v) => v === 0));
});

/* ------------------------------------------------------------------ */
test("sanitizeSample clamps and kills non-finite values", () => {
  assert.strictEqual(sanitizeSample(NaN), 0);
  assert.strictEqual(sanitizeSample(Infinity), 0);
  assert.strictEqual(sanitizeSample(-Infinity), 0);
  assert.strictEqual(sanitizeSample(5), 1);
  assert.strictEqual(sanitizeSample(-5), -1);
  assert.strictEqual(sanitizeSample("0.25"), 0.25);
});

test("a NaN in the stream cannot poison the ring", () => {
  const r = new RingBuffer(16000, 100);
  r.push(NaN);
  r.push(Infinity);
  r.push(0.5);
  assert.ok(r.read().every((v) => Number.isFinite(v)));
});

/* ------------------------------------------------------------------ */
test("decimate3 produces exactly one third the samples", () => {
  const input = new Array(4800).fill(0).map((_, i) => Math.sin(i / 7));
  const out = decimate3(input);
  assert.strictEqual(out.length, 1600);
});

test("decimate3 drops the partial tail rather than padding", () => {
  assert.strictEqual(decimate3([1, 2, 3, 4]).length, 1);
  assert.strictEqual(decimate3([1, 2]).length, 0);
});

test("decimate3 averages (anti-alias), it does not drop samples", () => {
  assert.deepStrictEqual(decimate3([0, 0.3, 0.6]).map((x) => +x.toFixed(4)), [0.3]);
});

test("decimate3 averages before clamping, so a loud block keeps its mean", () => {
  // Clamping each sample first would turn [0,3,6] into [0,1,1] -> 0.67.
  // The correct result is mean(0,3,6)=3, clamped to 1.
  assert.strictEqual(decimate3([0, 3, 6])[0], 1);
  assert.strictEqual(decimate3([0.2, 0.5, 0.8])[0], 0.5);
});

/* ------------------------------------------------------------------ */
function codeOnly(file) {
  return fs.readFileSync(file, "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")   // block comments
    .replace(/^\s*\/\/.*$/gm, "")        // line comments
    .replace(/\/\/.*$/gm, "");            // trailing comments
}

test("privacy: the capture module imports no storage or network API", () => {
  const src = codeOnly(MOD);
  const banned = [
    "localStorage", "sessionStorage", "indexedDB", "fetch(", "XMLHttpRequest",
    "new Blob", "FileReader", "navigator.sendBeacon", "document.cookie",
  ];
  for (const b of banned) {
    assert.ok(!src.includes(b), `capture core references ${b} — privacy contract broken`);
  }
});

test("privacy: no base64/audio encoding path in the capture core", () => {
  const src = codeOnly(MOD);
  for (const b of ["btoa", "atob", "toDataURL", "MediaRecorder"]) {
    assert.ok(!src.includes(b), `capture core references ${b}`);
  }
});

/* ------------------------------------------------------------------ */
test("worklet declares a 3-second ring and zeroes on stop", () => {
  const src = fs.readFileSync(SAMPLES, "utf8");
  assert.ok(src.includes("16000 * 3"), "worklet ring is not 3 s at 16 kHz");
  assert.ok(src.includes("ring.fill(0)"), "worklet does not zero its buffer");
  assert.ok(src.includes('type === "stop"'));
});

test("session state machine forbids illegal transitions", () => {
  const { CaptureSession, CAPTURE_STATES } = require(SAMPLES);
  const s = new CaptureSession({});
  assert.strictEqual(s.state, CAPTURE_STATES.IDLE);
  assert.throws(() => s._transition("STOPPED"), /illegal capture transition/);
});

test("indicator is derived from state, so it cannot stay on after stop", async () => {
  const { CaptureSession, CAPTURE_STATES } = require(SAMPLES);
  const seen = [];
  const s = new CaptureSession({
    getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }),
    onState: (st) => seen.push(st),
    screenEveryMs: 100000,
  });
  s.setConsent(true);
  await s.start();
  assert.strictEqual(s.indicatorVisible, true);
  s.stop();
  assert.strictEqual(s.indicatorVisible, false);
  assert.ok(seen.includes(CAPTURE_STATES.CAPTURING));
  assert.ok(seen.includes(CAPTURE_STATES.STOPPED));
});

test("capture refuses to start without consent", async () => {
  const { CaptureSession } = require(SAMPLES);
  const s = new CaptureSession({ getUserMedia: async () => ({ getTracks: () => [] }) });
  await assert.rejects(() => s.start(), /consent required/);
});

test("permission denial lands in DENIED, not CAPTURING", async () => {
  const { CaptureSession } = require(SAMPLES);
  const s = new CaptureSession({
    getUserMedia: async () => { throw new Error("NotAllowedError"); },
  });
  s.setConsent(true);
  const st = await s.start();
  assert.strictEqual(st, "DENIED");
  assert.strictEqual(s.indicatorVisible, false);
});

test("no microphone available degrades honestly to UNSUPPORTED", async () => {
  const { CaptureSession } = require(SAMPLES);
  const s = new CaptureSession({ getUserMedia: null });
  s.setConsent(true);
  assert.strictEqual(await s.start(), "UNSUPPORTED");
});

test("blur destroys audio even mid-capture", async () => {
  const { CaptureSession } = require(SAMPLES);
  const tracks = [{ stopped: false, stop() { this.stopped = true; } }];
  const s = new CaptureSession({
    getUserMedia: async () => ({ getTracks: () => tracks }),
    screenEveryMs: 100000,
  });
  s.setConsent(true);
  const { RingBuffer } = require(MOD);
  const ring = new RingBuffer(16000, 1600);
  s.attachRing(ring);
  await s.start();
  for (let i = 0; i < 500; i += 1) ring.push(0.4);
  s.onBlur();
  assert.ok(ring.buf.every((v) => v === 0), "blur did not destroy audio");
  assert.strictEqual(tracks[0].stopped, true, "mic track left open");
});

/* ------------------------------------------------------------------ */
/* Phase 5: the shipping page must actually load the capture code, and */
/* the verdict bands must not be distinguishable by colour alone.      */
/* ------------------------------------------------------------------ */
const _appDir = require("node:path").join(__dirname, "..", "citizen", "app");
const read = (f) => require("node:fs").readFileSync(_appDir + "/" + f, "utf8");

test("index.html loads both capture scripts before app.js", () => {
  const html = read("index.html");
  const cap = html.indexOf("maya-capture.js");
  const worklet = html.indexOf("maya-capture-worklet.js");
  const app = html.indexOf("app.js");
  assert.ok(cap > -1, "maya-capture.js is not referenced by the page");
  assert.ok(worklet > -1, "maya-capture-worklet.js is not referenced by the page");
  assert.ok(cap < app && worklet < app, "capture scripts must load before app.js");
});

test("index.html offers a microphone button distinct from the sample tone", () => {
  const html = read("index.html");
  assert.match(html, /id="btnScreenVoice"[^>]*>Record and check/);
  assert.match(html, /id="btnVoiceTone"/);
  // The old copy claimed only bundled tones were possible.
  assert.doesNotMatch(html, /Only bundled sample tones are analysed here/);
  assert.doesNotMatch(html, /heuristic fallback<\/b> in this demo/);
});

test("verdict bands are not colour-only (BUG-3)", () => {
  const css = read("styles.css");
  for (const band of ["LOW", "MODERATE", "HIGH", "CRITICAL"]) {
    const rule = new RegExp(`\\.${band}\\s*\\{[^}]*\\}`);
    const m = css.match(rule);
    assert.ok(m, `.${band} has no rule`);
    // Every band must carry at least one non-colour cue.
    assert.ok(/border-left/.test(m[0]),
      `.${band} has no border cue — colour-blind users cannot distinguish it`);
  }
  assert.match(css, /\.verdict::before/, "bands need an icon, not just a hue");
  assert.match(css, /data-icon/, "bands must render a shape/icon marker");
});

test("the voice UI renders an icon and never a raw score", () => {
  const js = read("app.js");
  assert.match(js, /data-icon/);
  // Scope the "no raw score" rule to the VOICE renderer. The message panel
  // legitimately shows a score — it is a different surface with different
  // copy, and a blanket ban would be a false requirement.
  const voice = js.slice(js.indexOf("function renderVoice"), js.indexOf("async function analyse"));
  assert.ok(voice.length > 100, "renderVoice not found");
  assert.doesNotMatch(voice, /v\.score|v\["score"\]/, "voice UI must not show a raw score");
  assert.match(voice, /explanation/, "voice UI must use the localised explanation");
});

test("app.js degrades honestly when the microphone is unavailable", () => {
  const js = read("app.js");
  assert.match(js, /Microphone not available/);
  assert.match(js, /No audio was recorded/);
});

test("worklet exports a browser entry point for app.js", () => {
  const src = read("maya-capture-worklet.js");
  assert.match(src, /window\.MayaCapture/);
  assert.match(src, /create\s*\(/);
  assert.match(src, /sys\.exit|module\.exports/);
});
