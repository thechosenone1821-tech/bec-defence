"use client";

/**
 * MAYA capture — microphone path for the voice screen.
 *
 * Contract (mirrors the backend capture module exactly):
 *  - capture at the device rate, decimate 3:1 down to 16 kHz mono
 *  - a rolling ring buffer capped at 3 seconds — nothing is written to
 *    disk, storage, or the network; the buffer is zeroed after the window
 *    is handed to the screener
 *  - visible state (seconds captured, level) is reported the whole time
 *    the microphone is open
 *  - audio is only ever captured after an explicit user gesture
 */

const TARGET_SR = 16000;
const RING_SECONDS = 3;
const RING_SAMPLES = TARGET_SR * RING_SECONDS; // 48000 @ 16 kHz

const WORKLET_SRC = `
class MayaCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ring = new Float32Array(${RING_SAMPLES});
    this.filled = 0;
    this.writeIdx = 0;
    this.port.onmessage = (e) => {
      if (e.data === "read-window") {
        // oldest-first copy, then zero the buffer — nothing is retained
        const out = new Float32Array(this.filled);
        const start = (this.writeIdx - this.filled + this.ring.length) % this.ring.length;
        const tail = this.ring.length - start;
        if (this.filled <= tail) {
          out.set(this.ring.subarray(start, start + this.filled));
        } else {
          out.set(this.ring.subarray(start, this.ring.length), 0);
          out.set(this.ring.subarray(0, this.filled - tail), tail);
        }
        this.ring.fill(0);
        this.filled = 0;
        this.writeIdx = 0;
        this.port.postMessage({ window: out });
      }
    };
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let n = 0; n + ${3} <= ch.length; n += ${3}) {
      let s = 0;
      for (let k = 0; k < ${3}; k++) {
        const v = ch[n + k];
        s += Number.isFinite(v) ? v : 0;
      }
      const mean = Math.max(-1, Math.min(1, s / ${3}));
      this.ring[this.writeIdx % this.ring.length] = mean;
      this.writeIdx++;
      this.filled = Math.min(this.filled + 1, this.ring.length);
    }
    this.port.postMessage({ filled: this.filled });
    return true;
  }
}
registerProcessor("maya-capture-processor", MayaCaptureProcessor);
`;

export type CaptureState = "idle" | "capturing" | "stopped";

export type MayaCaptureResult = {
  /** samples at 16 kHz mono, oldest-first; the internal buffer is zeroed */
  samples: number[];
};

export class MayaCaptureError extends Error {}

/** Browser-side 440 Hz reference tone — the honest plumbing check. */
export function synthTone(freq = 440, seconds = 1.0, sr = TARGET_SR): number[] {
  const n = Math.floor(seconds * sr);
  const out = new Array<number>(n);
  for (let i = 0; i < n; i++) out[i] = 0.7 * Math.sin(2 * Math.PI * freq * (i / sr));
  return out;
}

export async function runCapture(opts: {
  onLevel?: (level: number) => void;
  onSeconds?: (seconds: number) => void;
  maxSeconds?: number;
}): Promise<MayaCaptureResult> {
  const { onLevel, onSeconds, maxSeconds = RING_SECONDS } = opts;
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new MayaCaptureError("This browser cannot open a microphone.");
  }

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
    });
  } catch {
    throw new MayaCaptureError("Microphone permission was refused or unavailable. No audio was recorded.");
  }

  const ctx = new AudioContext();
  const workletUrl = URL.createObjectURL(
    new Blob([WORKLET_SRC], { type: "application/javascript" }),
  );
  await ctx.audioWorklet.addModule(workletUrl);
  URL.revokeObjectURL(workletUrl);
  const node = new AudioWorkletNode(ctx, "maya-capture-processor");
  const src = ctx.createMediaStreamSource(stream);
  src.connect(node);
  // deliberately NOT connected to ctx.destination — capture is silent to the user

  let latestFilled = 0;
  node.port.onmessage = (e: MessageEvent) => {
    if (typeof e.data?.filled === "number") {
      latestFilled = e.data.filled;
      onSeconds?.(Math.min(e.data.filled / TARGET_SR, maxSeconds));
    }
  };

  // Level meter: a short-lived, read-only analyser tap on the same stream.
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  src.connect(analyser);
  const buf = new Float32Array(analyser.fftSize);
  let raf = 0;
  const tick = () => {
    analyser.getFloatTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
    onLevel?.(Math.sqrt(sum / buf.length));
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);

  const stopAt = Date.now() + maxSeconds * 1000;
  await new Promise<void>((resolve) => {
    const check = setInterval(() => {
      if (Date.now() >= stopAt || latestFilled >= RING_SAMPLES) {
        clearInterval(check);
        resolve();
      }
    }, 100);
  });

  cancelAnimationFrame(raf);

  const samples = await new Promise<Float32Array>((resolve) => {
    const onWindow = (e: MessageEvent) => {
      if (e.data?.window) {
        node.port.removeEventListener("message", onWindow);
        resolve(e.data.window as Float32Array);
      }
    };
    node.port.addEventListener("message", onWindow);
    node.port.postMessage("read-window");
    setTimeout(() => resolve(new Float32Array(0)), 800);
  });

  node.disconnect();
  src.disconnect();
  analyser.disconnect();
  stream.getTracks().forEach((t) => t.stop());
  await ctx.close();

  return { samples: Array.from(samples) };
}
