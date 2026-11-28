"use client";

import * as React from "react";
import { Radar, Trash2 } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  VerdictCard,
  Field,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { citizen, bandFromVerdict, type SeverityBand } from "@/lib/gateway";
import { useSessionSignals } from "@/lib/session-signals";

type AssessResult = {
  score?: number;
  band?: string;
  verdict?: string;
  reasons?: string[];
  signals?: string[];
  signals_used?: string[];
  action?: string;
  advice?: string;
  headline?: string;
  advisory?: string;
};

function minutesSince(at: number): string {
  const m = Math.max(0, Math.round((Date.now() - at) / 60000));
  return m === 0 ? "just now" : `${m} min ago`;
}

export function VigilApp() {
  const call = useSessionSignals((s) => s.call);
  const message = useSessionSignals((s) => s.message);
  const setCall = useSessionSignals((s) => s.setCall);
  const setMessage = useSessionSignals((s) => s.setMessage);

  const [campaignLinked, setCampaignLinked] = React.useState(false);
  const [repeatContacts, setRepeatContacts] = React.useState(0);
  const [userDoubt, setUserDoubt] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<AssessResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const assess = async () => {
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      campaign_linked: campaignLinked,
      repeat_contacts: repeatContacts,
      user_doubt: userDoubt,
    };
    const primary = message ?? call;
    if (primary) body.message = { verdict: primary.raw.verdict ?? primary.verdict };
    const res = await citizen<AssessResult>("/api/citizen/assess", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (!res.ok) setError(res.error);
    else setResult(res.data);
    setBusy(false);
  };

  const band: SeverityBand | null = result
    ? bandFromVerdict(result.band ?? result.verdict)
    : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      {/* fusion console */}
      <PhosphorPanel className="p-6" glow>
        <Kicker phosphor>RISK FUSION · BOUNDED NOISY-OR</Kicker>
        <h2 className="mt-2 text-xl font-semibold">One verdict from every signal</h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          VIGIL combines the verdicts captured in this session — from Call Screen and
          Message Guard — with linkage and behaviour signals. The weighting is a
          plain, inspectable rule set, and an empty result is reported as
          LOW_CONFIDENCE, never as "safe".
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {/* call signal card */}
          <div className="rounded-md border border-border bg-secondary/50 p-4">
            <div className="flex items-center justify-between">
              <Kicker>CALL SCREEN · transcript</Kicker>
              {call ? (
                <button
                  type="button"
                  onClick={() => setCall(null)}
                  aria-label="Clear call signal"
                  className="text-muted-foreground hover:text-sev-critical"
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </button>
              ) : null}
            </div>
            {call ? (
              <>
                <p className="mt-2 font-mono text-sm text-phosphor-bright">{call.verdict}</p>
                <p className="text-xs text-muted-foreground">captured {minutesSince(call.at)}</p>
              </>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">
                No transcript verdict this session — open Call Screen and run a screen.
              </p>
            )}
          </div>

          {/* message signal card */}
          <div className="rounded-md border border-border bg-secondary/50 p-4">
            <div className="flex items-center justify-between">
              <Kicker>MESSAGE GUARD · text</Kicker>
              {message ? (
                <button
                  type="button"
                  onClick={() => setMessage(null)}
                  aria-label="Clear message signal"
                  className="text-muted-foreground hover:text-sev-critical"
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </button>
              ) : null}
            </div>
            {message ? (
              <>
                <p className="mt-2 font-mono text-sm text-phosphor-bright">{message.verdict}</p>
                <p className="text-xs text-muted-foreground">captured {minutesSince(message.at)}</p>
              </>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">
                No message verdict this session — open Message Guard and run a screen.
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-md border border-border bg-secondary/50 px-4 py-3">
            <label className="flex min-h-8 cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={campaignLinked}
                onChange={(e) => setCampaignLinked(e.target.checked)}
                className="size-4 accent-[#79c4b7]"
              />
              <span className="text-muted-foreground">Campaign-linked case ref</span>
            </label>
          </div>
          <div className="rounded-md border border-border bg-secondary/50 px-4 py-3">
            <label className="flex min-h-8 cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={userDoubt}
                onChange={(e) => setUserDoubt(e.target.checked)}
                className="size-4 accent-[#79c4b7]"
              />
              <span className="text-muted-foreground">You feel something is off</span>
            </label>
          </div>
          <Field label="Repeat contacts" hint={`${repeatContacts}`}>
            <input
              type="range"
              min={0}
              max={10}
              value={repeatContacts}
              onChange={(e) => setRepeatContacts(Number(e.target.value))}
              className="mt-2 w-full accent-[#79c4b7]"
              aria-label="Repeat contact attempts"
            />
          </Field>
        </div>

        <div className="mt-6">
          <PhosphorButton onClick={assess} disabled={busy}>
            <Radar className="size-4" aria-hidden="true" />
            {busy ? "Fusing…" : "Run risk fusion"}
          </PhosphorButton>
        </div>

        {error ? (
          <div className="mt-6 rounded-md border border-sev-critical/50 bg-sev-critical/10 p-4 text-sm text-sev-critical">
            {error}
          </div>
        ) : null}

        {result && band ? (
          <div className="mt-6 space-y-4">
            <VerdictCard
              band={band}
              title={result.headline ?? `${result.band ?? band} · score ${typeof result.score === "number" ? result.score.toFixed(2) : "n/a"}`}
              reasons={result.reasons}
              action={result.action ?? result.advice}
              disclaimer={result.advisory}
            />
            {(result.signals ?? result.signals_used)?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {(result.signals ?? result.signals_used ?? []).map((s) => (
                  <span
                    key={s}
                    className="rounded-full border border-border bg-secondary/70 px-2.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </PhosphorPanel>

      <aside className="space-y-6">
        <PhosphorPanel className="p-6">
          <Kicker>DOCTRINE</Kicker>
          <div className="mt-3 grid gap-3">
            <StatTile label="Empty input" value="LOW_CONFIDENCE" valueClass="text-sm" hint={'never "safe"'} />
            <StatTile label="Reasons are" value="sentences" valueClass="text-sm" hint="no raw scores shown to citizens" />
            <StatTile label="Signals fused" value="5" valueClass="text-sm" hint="transcript · message · linkage · repeats · doubt" />
          </div>
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
