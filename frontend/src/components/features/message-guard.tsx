"use client";

import * as React from "react";
import { MessageSquareLock } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  VerdictCard,
  Field,
  BackendNotice,
} from "@/components/phosphor/primitives";
import { citizen, bandFromVerdict } from "@/lib/gateway";
import { useSessionSignals } from "@/lib/session-signals";

type MessageVerdict = {
  verdict: string;
  score?: number;
  hits?: Record<string, number>;
  families_hit?: string[];
  reasons?: string[];
  explanation?: { title?: string; action?: string; reasons?: string[]; disclaimer?: string };
  helpline?: string;
  lang?: string;
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
    text: "Hi mom, dinner at 8? I will bring the laundry back then.",
  },
  {
    label: "KYC/UPI scam · en",
    lang: "en",
    text:
      "Dear customer, your bank account will be blocked in 24 hours. Update KYC immediately by clicking this link and pay Rs 10 verification fee via UPI.",
  },
  {
    label: "Digital arrest · en",
    lang: "en",
    text:
      "This is CBI officer Sharma. An arrest warrant is issued in your name. Stay on the video call, do not tell anyone, and transfer the clearance amount now.",
  },
  {
    label: "OTP scam · hi",
    lang: "hi",
    text: "आपका OTP 448921 है। खाता बंद होने से बचाने के लिए तुरंत OTP साझा करें।",
  },
];

export function MessageGuardApp() {
  const [text, setText] = React.useState("");
  const [lang, setLang] = React.useState("en");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<MessageVerdict | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const setMessageSignal = useSessionSignals((s) => s.setMessage);

  const screen = async (payload: string) => {
    setBusy(true);
    setError(null);
    const res = await citizen<MessageVerdict>("/api/citizen/screen_message", {
      method: "POST",
      body: JSON.stringify({ text: payload, lang }),
    });
    if (!res.ok) setError(res.error);
    else {
      setResult(res.data);
      setMessageSignal({
        app: "message-guard",
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
        <Kicker phosphor>MESSAGE SCREEN · SMS / CHAT / SCRIPT</Kicker>
        <h2 className="mt-2 text-xl font-semibold">Check a suspicious message</h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Paste anything you doubt — an SMS, a WhatsApp forward, a call script.
          The screen is heuristic: it names the scam families it recognised and
          always ends with a human next step.
        </p>

        <div className="mt-6 space-y-4">
          <Field label="Message text" hint={`${text.length}/4000`}>
            <textarea
              rows={6}
              maxLength={4000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="e.g. Dear customer, your account will be blocked in 24 hours…"
              className="w-full resize-y rounded-md border border-input bg-secondary/70 px-3 py-2.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Message text to screen"
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
                {LANGS.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
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
                {busy ? "Screening…" : "Screen this message"}
              </PhosphorButton>
            </div>
          </div>

          <div>
            <Kicker className="mb-2">Sample fixtures</Kicker>
            <div className="flex flex-wrap gap-2">
              {SAMPLES.map((s) => (
                <PhosphorButton
                  key={s.label}
                  variant="ghost"
                  className="min-h-9 px-3"
                  disabled={busy}
                  onClick={() => {
                    setText(s.text);
                    setLang(s.lang);
                  }}
                >
                  {s.label}
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
                reasons={result.explanation?.reasons ?? result.reasons}
                action={result.explanation?.action ?? "If unsure, do not act — call 1930."}
                disclaimer={result.disclaimer}
              />
              <details className="rounded-md border border-border bg-secondary/40 p-4">
                <summary className="cursor-pointer font-mono text-xs tracking-[0.18em] uppercase text-muted-foreground">
                  Signal diagnostics
                </summary>
                <div className="mt-3 space-y-2 font-mono text-xs text-muted-foreground">
                  <p>score: {typeof result.score === "number" ? result.score.toFixed(3) : "n/a"}</p>
                  <p>families hit: {result.families_hit?.length ? result.families_hit.join(", ") : "none"}</p>
                  {result.hits && Object.keys(result.hits).length ? (
                    <ul className="space-y-1">
                      {Object.entries(result.hits).map(([k, v]) => (
                        <li key={k}>
                          {k}: {typeof v === "number" ? v.toFixed(2) : String(v)}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </details>
            </div>
          ) : null}
        </div>
      </PhosphorPanel>

      <aside className="space-y-6">
        <PhosphorPanel className="p-6">
          <Kicker>WHAT IT SEES</Kicker>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li>Scam-script families: credential harvesting, urgency, authority, payment pressure.</li>
            <li>Cross-language token set — en / hi / te screened with one pass.</li>
            <li>Too little text returns LOW_CONFIDENCE: an honest "I don't know", never a clean bill.</li>
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
