"use client";

import * as React from "react";
import { MessageSquareLock, ShieldAlert } from "lucide-react";
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
import { useSessionSignals } from "@/lib/session-signals";

type TranscriptVerdict = {
  verdict: string;
  score?: number;
  engine?: string;
  view?: string;
  reasons?: string[];
  reason_codes?: string[];
  families_hit?: string[];
  legacy_band?: string;
  lang?: string;
  features?: Record<string, number>;
  explanation?: { title?: string; action?: string; reasons?: string[]; disclaimer?: string };
  helpline?: string;
  disclaimer?: string;
};

const LANGS = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिंदी" },
  { id: "te", label: "తెలుగు" },
];

const SAMPLES: { label: string; lang: string; text: string }[] = [
  {
    label: "Benign · en",
    lang: "en",
    text: "Hi, this is your neighbour. The water tanker will arrive at eight in the evening.",
  },
  {
    label: "UPI pressure · en",
    lang: "en",
    text: "Your bank account will be blocked today. Share the OTP and pay the verification fee by UPI immediately.",
  },
  {
    label: "Authority script · hi",
    lang: "hi",
    text: "सीबीआई अधिकारी बोल रहे हैं। तुरंत क्लियरेंस राशि ट्रांसफर करें और इस कॉल की जानकारी किसी को न दें।",
  },
];

export function CallScreenApp() {
  const [text, setText] = React.useState("");
  const [lang, setLang] = React.useState("en");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<TranscriptVerdict | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const setCall = useSessionSignals((s) => s.setCall);

  const screen = async (payload: string) => {
    setBusy(true);
    setError(null);
    const res = await citizen<TranscriptVerdict>("/api/citizen/screen_transcript", {
      method: "POST",
      body: JSON.stringify({ text: payload, lang }),
    });
    if (!res.ok) {
      setError(res.error);
    } else {
      setResult(res.data);
      setCall({
        app: "call-screen",
        band: bandFromVerdict(res.data.verdict),
        verdict: res.data.verdict,
        at: Date.now(),
        raw: res.data as unknown as Record<string, unknown>,
      });
    }
    setBusy(false);
  };

  const band = result ? bandFromVerdict(result.verdict) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <PhosphorPanel className="p-6" glow>
        <Kicker phosphor>CALL TRANSCRIPT SCREEN · DETERMINISTIC RULES</Kicker>
        <h2 className="mt-2 text-xl font-semibold">Check what a caller said</h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Paste the words a caller used. The active Citizen MessageGuard rules
          screen that transcript for known fraud scripts. This is a transcript
          check only: no recording is made, no audio leaves the browser, and no
          synthetic-speech claim is made.
        </p>

        <div className="mt-6 space-y-4">
          <Field label="Call transcript" hint={`${text.length}/4000`}>
            <textarea
              rows={6}
              maxLength={4000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the caller's words here…"
              className="w-full resize-y rounded-md border border-input bg-secondary/70 px-3 py-2.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Call transcript to screen"
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Explanation language">
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="h-11 w-full rounded-md border border-input bg-secondary/70 px-3 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                aria-label="Explanation language"
              >
                {LANGS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex items-end">
              <PhosphorButton
                className="w-full"
                disabled={busy || text.trim().length === 0}
                onClick={() => screen(text)}
              >
                <MessageSquareLock className="size-4" aria-hidden="true" />
                {busy ? "Screening…" : "Screen transcript"}
              </PhosphorButton>
            </div>
          </div>

          <div>
            <Kicker className="mb-2">Sample transcripts</Kicker>
            <div className="flex flex-wrap gap-2">
              {SAMPLES.map((sample) => (
                <PhosphorButton
                  key={sample.label}
                  variant="ghost"
                  className="min-h-9 px-3"
                  disabled={busy}
                  onClick={() => {
                    setText(sample.text);
                    setLang(sample.lang);
                  }}
                >
                  {sample.label}
                </PhosphorButton>
              ))}
            </div>
          </div>

          {error ? (
            <div className="rounded-md border border-sev-critical/50 bg-sev-critical/10 p-4 text-sm text-sev-critical">
              {error}
            </div>
          ) : null}

          {result && band ? (
            <div className="space-y-4">
              <VerdictCard
                band={band}
                title={result.explanation?.title ?? result.verdict}
                reasons={result.explanation?.reasons}
                action={result.explanation?.action ?? "If unsure, do not act — call 1930."}
                disclaimer={result.disclaimer ?? "Advisory only — not an accusation."}
              />
              <details className="rounded-md border border-border bg-secondary/40 p-4">
                <summary className="cursor-pointer font-mono text-xs tracking-[0.18em] uppercase text-muted-foreground">
                  Signal diagnostics
                </summary>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {Object.entries(result.features ?? {}).map(([key, value]) => (
                    <StatTile key={key} label={key} value={typeof value === "number" ? value.toFixed(3) : String(value)} />
                  ))}
                </div>
                <p className="mt-3 font-mono text-[11px] text-muted-foreground">
                  engine: {result.engine ?? "unknown"} · helpline: {result.helpline ?? "1930"}
                  {result.view ? ` · ${result.view}` : ""}
                </p>
                {(result.families_hit ?? []).length ? (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(result.families_hit ?? []).map((family) => (
                      <span
                        key={family}
                        className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                      >
                        {family}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                    no scam family matched this transcript
                  </p>
                )}
              </details>
            </div>
          ) : null}
        </div>
      </PhosphorPanel>

      <aside className="space-y-6">
        <PhosphorPanel className="p-6">
          <Kicker>RETENTION CONTRACT</Kicker>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Only pasted transcript text is sent to the Citizen rule scorer.
            </li>
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              No recording, microphone access or persistent transcript store is used.
            </li>
            <li className="flex gap-2">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Verdicts are advisory and always end with a human next step.
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
