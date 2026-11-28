"use client";

import * as React from "react";
import { Mic, Square, Play, ShieldAlert } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  VerdictCard,
  Field,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { citizen, bandFromVerdict } from "@/lib/gateway";
import { runCapture, synthTone, MayaCaptureError } from "@/lib/maya-capture";
import { useSessionSignals } from "@/lib/session-signals";

type VoiceVerdict = {
  verdict: string;
  score?: number;
  engine?: string;
  reason?: string;
  features?: Record<string, number>;
  explanation?: { title?: string; action?: string; reasons?: string[]; disclaimer?: string };
  helpline?: string;
};

const LANGS = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिंदी" },
  { id: "te", label: "తెలుగు" },
];

export function MayaApp() {
  const [consent, setConsent] = React.useState(false);
  const [lang, setLang] = React.useState("en");
  const [phase, setPhase] = React.useState<"idle" | "capturing" | "screening">("idle");
  const [seconds, setSeconds] = React.useState(0);
  const [level, setLevel] = React.useState(0);
  const [result, setResult] = React.useState<VoiceVerdict | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const setVoiceSignal = useSessionSignals((s) => s.setVoice);

  const screen = async (samples: number[], consented: boolean, how: string) => {
    setPhase("screening");
    setError(null);
    const res = await citizen<VoiceVerdict>("/api/citizen/screen_voice", {
      method: "POST",
      body: JSON.stringify({ samples, consent: consented, lang }),
    });
    if (!res.ok) {
      setError(res.error);
      setNotice(
        res.status === 403
          ? "The screen was refused because consent was not recorded. Review the consent note and try again."
          : null,
      );
    } else {
      setResult(res.data);
      setNotice(
        how === "tone"
          ? "Screened the bundled reference tone — a plumbing check, not a real call."
          : null,
      );
      setVoiceSignal({
        app: "maya",
        band: bandFromVerdict(res.data.verdict),
        verdict: res.data.verdict,
        at: Date.now(),
        raw: res.data as unknown as Record<string, unknown>,
      });
    }
    setPhase("idle");
  };

  const record = async () => {
    setError(null);
    setNotice(null);
    setResult(null);
    setSeconds(0);
    setPhase("capturing");
    try {
      const { samples } = await runCapture({
        onSeconds: setSeconds,
        onLevel: setLevel,
        maxSeconds: 3,
      });
      if (!samples.length) {
        setError("No audio was captured from the microphone window.");
        setPhase("idle");
        return;
      }
      await screen(samples, true, "mic");
    } catch (e) {
      setError(e instanceof MayaCaptureError ? e.message : "Capture failed unexpectedly.");
      setPhase("idle");
    }
  };

  const band = result ? bandFromVerdict(result.verdict) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      {/* ---------------- screener ---------------- */}
      <div className="space-y-6">
        <PhosphorPanel className="p-6" glow>
          <Kicker phosphor>VOICE SCREEN · ROLLING 3S WINDOW</Kicker>
          <h2 className="mt-2 text-xl font-semibold">Screen a suspicious call</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
            MAYA listens for at most three seconds, screens the window, and keeps
            nothing — the buffer is overwritten while listening and zeroed when the
            window is read. The microphone is open only while a check is running.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Field label="Explanation language">
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="h-11 w-full rounded-md border border-input bg-secondary/70 px-3 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                aria-label="Explanation language"
              >
                {LANGS.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            </Field>
            <div className="rounded-md border border-border bg-secondary/50 px-4 py-3">
              <label className="flex min-h-8 cursor-pointer items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-1 size-4 accent-[#79c4b7]"
                />
                <span className="text-muted-foreground">
                  <b className="text-foreground">Consent to screen this window.</b>{" "}
                  Required by the screen endpoint — without it the backend refuses
                  with 403 and processes nothing.
                </span>
              </label>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <PhosphorButton
              onClick={record}
              disabled={!consent || phase !== "idle"}
              aria-label="Record three seconds and screen"
            >
              {phase === "capturing" ? (
                <>
                  <Square className="size-4" aria-hidden="true" /> Listening · {seconds.toFixed(1)}s
                </>
              ) : phase === "screening" ? (
                <>Screening…</>
              ) : (
                <>
                  <Mic className="size-4" aria-hidden="true" /> Record and check this call
                </>
              )}
            </PhosphorButton>
            <PhosphorButton
              variant="ghost"
              disabled={phase !== "idle"}
              onClick={() => screen(synthTone(440), consent, "tone")}
            >
              <Play className="size-4" aria-hidden="true" /> Bundled tone (plumbing check)
            </PhosphorButton>
          </div>

          {!consent ? (
            <p className="mt-4 font-mono text-xs text-sev-moderate">
              Consent is off — recording stays disabled. No audio has been captured.
            </p>
          ) : null}

          {/* live indicator */}
          {phase === "capturing" ? (
            <div className="mt-6" role="status" aria-live="polite">
              <div className="flex items-center gap-3">
                <span className="size-2.5 animate-pulse rounded-full bg-sev-critical" aria-hidden="true" />
                <span className="font-mono text-xs tracking-[0.18em] uppercase text-muted-foreground">
                  Recording · {seconds.toFixed(1)}s / 3.0s · buffer overwrites continuously
                </span>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-phosphor transition-[width] duration-100"
                  style={{ width: `${Math.min(100, level * 220)}%` }}
                />
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="mt-6 rounded-md border border-sev-critical/50 bg-sev-critical/10 p-4 text-sm text-sev-critical">
              {error}
              {notice ? <p className="mt-2 text-muted-foreground">{notice}</p> : null}
            </div>
          ) : null}

          {result && band ? (
            <div className="mt-6 space-y-4">
              <VerdictCard
                band={band}
                title={result.explanation?.title ?? result.verdict}
                reasons={result.explanation?.reasons}
                action={result.explanation?.action ?? "If in doubt, hang up and call 1930."}
                disclaimer={result.explanation?.disclaimer ?? "Advisory only — not an accusation."}
              />
              {result.features ? (
                <details className="rounded-md border border-border bg-secondary/40 p-4">
                  <summary className="cursor-pointer font-mono text-xs tracking-[0.18em] uppercase text-muted-foreground">
                    Spectral features (diagnostics)
                  </summary>
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {Object.entries(result.features).map(([k, v]) => (
                      <StatTile key={k} label={k} value={typeof v === "number" ? v.toFixed(3) : String(v)} />
                    ))}
                  </div>
                </details>
              ) : null}
              <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
                engine: {result.engine ?? "unknown"} · helpline: {result.helpline ?? "1930"}
              </p>
            </div>
          ) : null}
        </PhosphorPanel>
      </div>

      {/* ---------------- side rail ---------------- */}
      <aside className="space-y-6">
        <PhosphorPanel className="p-6">
          <Kicker>RETENTION CONTRACT</Kicker>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Ring buffer ≤ 3 s, zeroed when the window is read.
            </li>
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Nothing is written to disk, storage, or the network.
            </li>
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              The engine is a spectral fallback, not a trained anti-spoof model — real
              speech may return INCONCLUSIVE, which is honest.
            </li>
          </ul>
        </PhosphorPanel>
        <BackendNoticeHolder />
      </aside>
    </div>
  );
}

function BackendNoticeHolder() {
  const [detail, setDetail] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    let alive = true;
    citizen("/api/citizen/health").then((r) => {
      if (alive) setDetail(r.ok ? null : r.error);
    });
    return () => {
      alive = false;
    };
  }, [tick]);
  if (!detail) return null;
  return <BackendNotice detail={detail} onRetry={() => setTick((t) => t + 1)} />;
}
