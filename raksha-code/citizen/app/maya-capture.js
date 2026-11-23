/* MAYA / VoiceGuard — capture core (Phase 2)
 *
 * A 3-second ring buffer with a hard privacy contract. This file is the
 * *testable* half: it has no DOM, no permissions and no network, so the Node
 * test suite can drive it directly. The browser glue lives in
 * maya-capture-worklet.js + the voice tab in app.js.
 *
 * PRIVACY CONTRACT (enforced by tests, not by good intentions):
 *   1. Audio lives in one Float32Array and nowhere else. It is never persisted
 *      (no web storage of any kind), never fetched, never wrapped in a Blob or
 *      File, and never encoded. A grep test scans this file for those APIs.
 *   2. The buffer is zero-filled on stop(), on blur and on teardown.
 *   3. At most RING_SECONDS of audio is ever retained; older samples are
 *      overwritten in place, never appended to a growing list.
 *   4. Reading returns a *copy*, so a caller cannot hold a reference to the
 *      live buffer and keep audio alive after zeroing.
 */

"use strict";

const TARGET_SR = 16000;
const RING_SECONDS = 3;
const RING_SAMPLES = TARGET_SR * RING_SECONDS;
const DECIMATE = 3; // 48 kHz -> 16 kHz

/**
 * Clip a float sample safely. Never let NaN/Infinity into the buffer: a single
 * NaN would poison every downstream feature and break JSON serialisation.
 */
function sanitizeSample(v) {
  const x = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(x)) return 0;
  if (x > 1) return 1;
  if (x < -1) return -1;
  return x;
}

/**
 * Decimate 48 kHz frames to 16 kHz by averaging each group of 3 samples.
 *
 * Averaging (not dropping) is a crude anti-alias filter. It is honest about
 * what it is: a 3-tap box filter, not a windowed-sinc resampler. Above ~8 kHz
 * it will alias, which is acceptable because that band carries little
 * speaker-identity information — and the model is trained on this same
 * decimator (features are computed from what the phone actually captures).
 */
function decimate3(input) {
  const out = [];
  for (let i = 0; i + DECIMATE <= input.length; i += DECIMATE) {
    // Average FIRST, clamp after. Clamping each sample before averaging
    // would distort the mean of any loud block (a 3-sample [0,3,6] group
    // must average to 3, not to 0.67).
    let acc = 0;
    for (let k = 0; k < DECIMATE; k += 1) {
      const v = Number(input[i + k]);
      acc += Number.isFinite(v) ? v : 0;
    }
    const mean = acc / DECIMATE;
    out.push(mean > 1 ? 1 : (mean < -1 ? -1 : mean));
  }
  return out;
}

class RingBuffer {
  /**
   * @param {number} sr  capture sample rate (declared, not detected)
   * @param {number} len capacity in samples (default: 3 s at 16 kHz)
   */
  constructor(sr = TARGET_SR, len = RING_SAMPLES) {
    this.sr = sr;
    this.buf = new Float32Array(len);
    this.len = len;
    this.writeIndex = 0;
    this.filled = 0;      // 0..len — samples currently held
    this.wrapped = false; // true once writeIndex has lapped the buffer
    this.stopped = false;
    this.zeroedCount = 0;
  }

  /** Push one already-16 kHz sample. Overwrites the oldest in place. */
  push(sample) {
    if (this.stopped) return;
    this.buf[this.writeIndex] = sanitizeSample(sample);
    this.writeIndex = (this.writeIndex + 1) % this.len;
    if (this.filled < this.len) {
      this.filled += 1;
      if (this.filled === this.len) this.wrapped = false; // exactly full
    } else {
      this.wrapped = true;                                 // oldest overwritten
    }
  }

  /** Push a block of 48 kHz samples (raw mic frames). */
  pushRaw(block) {
    if (this.stopped) return;
    const dec = decimate3(block);
    for (let i = 0; i < dec.length; i += 1) this.push(dec[i]);
  }

  /**
   * Return the buffer contents in chronological order as a NEW array.
   * Callers never receive the live viewport.
   */
  read() {
    if (this.filled === 0) return [];
    if (!this.wrapped) return Array.from(this.buf.subarray(0, this.filled));
    const tail = Array.from(this.buf.subarray(this.writeIndex));
    const head = Array.from(this.buf.subarray(0, this.writeIndex));
    return tail.concat(head);
  }

  /** Seconds of audio currently held. */
  seconds() {
    return this.filled / this.sr;
  }

  /** Fill with zeros. Idempotent. Called on stop, blur and teardown. */
  zero() {
    this.buf.fill(0);
    this.zeroedCount += 1;
  }

  /** Stop capture and destroy the contents. Irreversible by design. */
  stop() {
    this.stopped = true;
    this.filled = 0;
    this.writeIndex = 0;
    this.wrapped = false;
    this.zero();
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { RingBuffer, decimate3, sanitizeSample,
                     TARGET_SR, RING_SECONDS, RING_SAMPLES, DECIMATE };
}
