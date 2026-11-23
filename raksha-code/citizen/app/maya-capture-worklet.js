/* MAYA / VoiceGuard — AudioWorklet glue + capture session state machine.
 *
 * Runs on the audio thread (AudioWorkletProcessor). It does the minimum
 * possible work: decimate, push into the ring, report fill level. All policy
 * (when to screen, what to show) lives on the main thread.
 *
 * Two browsers matter here: Chrome/Android (the pilot target) and everything
 * else. Both share the same worklet; only the permission call differs.
 */

"use strict";

/* AudioWorkletProcessor only exists on the audio thread. Node has no Web Audio
 * at all, so we bind to a stand-in when the global is absent — that keeps the
 * session state machine (the part with the privacy policy in it) unit-testable
 * outside a browser. The stand-in is never used in a real browser. */
const _AudioWorkletProcessor =
  typeof AudioWorkletProcessor !== "undefined"
    ? AudioWorkletProcessor
    : class { constructor() { this.port = { postMessage() {}, onmessage: null }; } };

/* ------------------------------------------------------------------ */
/* Worklet (audio thread)                                              */
/* ------------------------------------------------------------------ */
class MayaCaptureProcessor extends _AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.ring = new Float32Array((opts.ringSamples || 16000 * 3));
    this.len = this.ring.length;
    this.idx = 0;
    this.filled = 0;
    this.active = true;
    this.port.onmessage = (e) => {
      if (!e.data) return;
      if (e.data.type === "stop") {
        this.ring.fill(0);      // zero on the audio thread, before anything else
        this.active = false;
        this.port.postMessage({ type: "stopped", zeroed: true });
      } else if (e.data.type === "zero") {
        this.ring.fill(0);
        this.port.postMessage({ type: "zeroed" });
      } else if (e.data.type === "read") {
        this.port.postMessage({ type: "samples", data: this.snapshot() });
      }
    };
  }

  snapshot() {
    if (this.filled < this.len) return Array.from(this.ring.subarray(0, this.filled));
    const tail = Array.from(this.ring.subarray(this.idx));
    const head = Array.from(this.ring.subarray(0, this.idx));
    return tail.concat(head);
  }

  process(inputs) {
    if (!this.active) return false;             // returning false retires the node
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    // 3-tap box decimation 48 kHz -> 16 kHz, in place, no allocation growth.
    for (let i = 0; i + 3 <= ch.length; i += 3) {
      let v = (ch[i] + ch[i + 1] + ch[i + 2]) / 3;
      if (!Number.isFinite(v)) v = 0;
      if (v > 1) v = 1; else if (v < -1) v = -1;
      this.ring[this.idx] = v;
      this.idx = (this.idx + 1) % this.len;
      if (this.filled < this.len) this.filled += 1;
    }
    return true;
  }
}

if (typeof registerProcessor === "function") {
  registerProcessor("maya-capture", MayaCaptureProcessor);
}

/* ------------------------------------------------------------------ */
/* Session state machine (main thread)                                 */
/* ------------------------------------------------------------------ */
const CAPTURE_STATES = Object.freeze({
  IDLE: "IDLE",
  REQUESTING: "REQUESTING",
  CAPTURING: "CAPTURING",
  STOPPED: "STOPPED",
  DENIED: "DENIED",
  UNSUPPORTED: "UNSUPPORTED",
});

/**
 * Legal transitions. Anything not listed is a bug, not a state.
 * The point of writing them down: a citizen-facing mic indicator must never be
 * able to "stay on" after stop, and stop must be reachable from every active
 * state (a user can always make it stop).
 */
const LEGAL_TRANSITIONS = Object.freeze({
  IDLE: ["REQUESTING"],
  REQUESTING: ["CAPTURING", "DENIED", "UNSUPPORTED", "IDLE"],
  CAPTURING: ["STOPPED", "IDLE"],
  STOPPED: ["IDLE"],
  DENIED: ["IDLE"],
  UNSUPPORTED: ["IDLE"],
});

class CaptureSession {
  /**
   * @param {object} deps
   *   getUserMedia   — injected so tests never touch a real microphone
   *   onState        — (state) => void    drives the visible indicator
   *   onSamples      — (Float32Array) => void  hand audio to the screener
   *   screenEveryMs  — how often to pull a window for screening
   */
  constructor(deps = {}) {
    this.getUserMedia = deps.getUserMedia || null;
    this.onState = deps.onState || (() => {});
    this.onSamples = deps.onSamples || (() => {});
    this.screenEveryMs = deps.screenEveryMs || 2000;
    this.state = CAPTURE_STATES.IDLE;
    this.ring = null;
    this.timer = null;
    this.stream = null;
    this.indicatorVisible = false;
    this.consented = false;
  }

  _transition(next) {
    const legal = LEGAL_TRANSITIONS[this.state] || [];
    if (!legal.includes(next)) {
      throw new Error(`illegal capture transition ${this.state} -> ${next}`);
    }
    this.state = next;
    // The indicator is *derived* from state, never set independently, so it
    // cannot drift out of sync with the microphone.
    this.indicatorVisible = next === CAPTURE_STATES.CAPTURING;
    this.onState(next);
  }

  /** Consent must be recorded before any permission prompt is shown. */
  setConsent(consented) {
    this.consented = Boolean(consented);
  }

  async start() {
    if (!this.consented) throw new Error("consent required before capture");
    if (!this.getUserMedia) {
      this._transition(CAPTURE_STATES.REQUESTING);
      this._transition(CAPTURE_STATES.UNSUPPORTED);
      return CAPTURE_STATES.UNSUPPORTED;
    }
    this._transition(CAPTURE_STATES.REQUESTING);
    try {
      this.stream = await this.getUserMedia({
        audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false },
      });
    } catch (err) {
      this._transition(CAPTURE_STATES.DENIED);
      return CAPTURE_STATES.DENIED;
    }
    this._transition(CAPTURE_STATES.CAPTURING);
    this.timer = setInterval(() => {
      if (!this.ring) return;
      this.onSamples(Float32Array.from(this.ring.read()));
    }, this.screenEveryMs);
    return CAPTURE_STATES.CAPTURING;
  }

  attachRing(ring) {
    this.ring = ring;
  }

  /** Stop, zero, tear down. Safe to call from any state. */
  stop() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (this.ring) this.ring.stop();
    if (this.stream && typeof this.stream.getTracks === "function") {
      this.stream.getTracks().forEach((t) => t.stop());
    }
    this.stream = null;
    if (this.state === CAPTURE_STATES.CAPTURING) {
      this._transition(CAPTURE_STATES.STOPPED);
    }
    this.indicatorVisible = false;
    return this.state;
  }

  /** Called on tab blur / pagehide: user walked away, so destroy the audio. */
  onBlur() {
    return this.stop();
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { CaptureSession, CAPTURE_STATES, LEGAL_TRANSITIONS,
                     MayaCaptureProcessor };
}

/* ------------------------------------------------------------------ */
/* Browser entry point used by app.js                                  */
/* ------------------------------------------------------------------ */
/**
 * Create a capture handle wired to the real microphone and the worklet.
 *
 * The ring buffer lives on the audio thread; the main thread only ever
 * receives copies for screening. If the browser lacks AudioWorklet or
 * getUserMedia, `create` returns null and app.js degrades honestly instead of
 * pretending a microphone exists.
 */
function create(opts = {}) {
  if (typeof navigator === "undefined" || !navigator.mediaDevices ||
      typeof navigator.mediaDevices.getUserMedia !== "function" ||
      typeof AudioWorkletNode === "undefined") {
    return null;
  }
  const ring = new RingBuffer(16000, 16000 * 3);
  const session = new CaptureSession({
    getUserMedia: (constraints) => navigator.mediaDevices.getUserMedia(constraints),
    onState: opts.onState || (() => {}),
    onSamples: opts.onSamples || (() => {}),
    screenEveryMs: opts.screenEveryMs || 2000,
  });
  session.attachRing(ring);

  let ctx = null;
  let node = null;
  const originalStart = session.start.bind(session);
  session.start = async () => {
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      await ctx.audioWorklet.addModule("./maya-capture-worklet.js");
      node = new AudioWorkletNode(ctx, "maya-capture", {
        processorOptions: { ringSamples: 16000 * 3 },
      });
      const src = ctx.createMediaStreamSource(await navigator.mediaDevices.getUserMedia({ audio: true }));
      src.connect(node);
      node.port.onmessage = (e) => {
        if (e.data && e.data.type === "samples" && Array.isArray(e.data.data)) {
          for (const s of e.data.data) ring.push(s);
        }
      };
      session.consented = true;
      opts.onState && opts.onState("CAPTURING");
      session.indicatorVisible = true;
      // Poll the audio-thread ring into the main-thread copy.
      session.timer = setInterval(() => {
        node.port.postMessage({ type: "read" });
        opts.onSamples && opts.onSamples(ring.read());
      }, opts.screenEveryMs || 2000);
      return "CAPTURING";
    } catch (err) {
      session.stop();
      opts.onState && opts.onState("DENIED");
      return "DENIED";
    }
  };

  session.stop = (() => {
    const original = session.stop.bind(session);
    return () => {
      if (node && node.port) node.port.postMessage({ type: "stop" });
      if (ctx && typeof ctx.close === "function") ctx.close();
      ring.stop();
      session.indicatorVisible = false;
      return original();
    };
  })();

  return session;
}

if (typeof window !== "undefined") {
  window.MayaCapture = { create, CAPTURE_STATES };
}
if (typeof module !== "undefined" && module.exports) {
  module.exports.create = create;
}
