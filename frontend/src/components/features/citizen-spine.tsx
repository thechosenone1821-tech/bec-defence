"use client";

import * as React from "react";
import { Landmark, Send } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  VerdictCard,
  Field,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { citizen, spine } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";

type ReportResult = {
  status?: string;
  event_id?: string;
  category?: string;
  severity?: number;
  forwarded?: { forwarded?: boolean; reason?: string; error?: string; bus_reply?: unknown };
  explanation?: { delivered?: boolean; title?: string; body?: string; reasons?: string[] };
  delivered?: boolean;
  helpline?: string;
};

type SpineHealth = {
  status?: string;
  commander_mode?: string;
  executor_mode?: string;
  planes_3_4?: boolean;
};

type SpineState = {
  buffered_events?: number;
  campaigns?: { campaign_id?: string; size?: number; severity_max?: number }[];
  fortress?: { telemetry_mac?: boolean; unverified_held?: number; replay_dropped?: number };
  orchestration_count?: number;
};

const CATEGORIES = [
  { id: "call", label: "Call / message scam" },
  { id: "message", label: "Message scam" },
  { id: "financial", label: "Money / UPI fraud" },
  { id: "other", label: "Other" },
];

export function CitizenSpineApp() {
  const [category, setCategory] = React.useState<string>("message");
  const [severity, setSeverity] = React.useState(0.8);
  const [caseRef, setCaseRef] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<ReportResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [log, setLog] = React.useState<ReportResult[]>([]);

  const [spineHealth, setSpineHealth] = React.useState<SpineHealth | null>(null);
  const [spineState, setSpineState] = React.useState<SpineState | null>(null);
  const [spineError, setSpineError] = React.useState<string | null>(null);

  const loadSpine = React.useCallback(async () => {
    const h = await spine<SpineHealth>("/api/health");
    const s = await spine<SpineState>("/api/state");
    if (h.ok) setSpineHealth(h.data);
    if (s.ok) setSpineState(s.data);
    setSpineError(h.ok || s.ok ? null : h.error ?? s.error ?? "gateway unreachable");
  }, []);

  /* a report can fuse into a campaign on the bus, so the view re-reads */
  const { refresh: refreshSpine } = usePoll(loadSpine, { everyMs: 15000 });

  const sendReport = async () => {
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = { category, severity, lang: "en" };
    if (caseRef.trim()) body.case_id = caseRef.trim().toUpperCase();
    const res = await citizen<ReportResult>("/api/citizen/report", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      setError(res.error);
    } else {
      setResult(res.data);
      setLog((prev) => [res.data, ...prev].slice(0, 12));
      // a report may have fused on the bus — re-read the spine view
      await refreshSpine();
    }
    setBusy(false);
  };

  const delivered = result?.delivered ?? result?.explanation?.delivered;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      {/* report rail */}
      <PhosphorPanel className="p-6" glow>
        <Kicker phosphor>REPORT RAIL · SIGNED & TOKENIZED</Kicker>
        <h2 className="mt-2 text-xl font-semibold">File an incident report</h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          One tap files a signed event into the shared spine. Only the category
          and a severity band leave this console — no phone numbers, no message
          content, no personal data. An opaque case reference optionally links
          your report to a live campaign.
        </p>

        <div className="mt-6 space-y-5">
          <div>
            <Kicker className="mb-2">Category</Kicker>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Report category">
              {CATEGORIES.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  role="radio"
                  aria-checked={category === c.id}
                  onClick={() => setCategory(c.id)}
                  className={`min-h-11 rounded-md border px-3 text-xs transition-all duration-200 ${
                    category === c.id
                      ? "border-phosphor/60 bg-phosphor/10 text-phosphor-bright ph-glow"
                      : "border-border bg-secondary/60 text-muted-foreground hover:border-phosphor/40"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <Field label="Severity band" hint={severity.toFixed(2)}>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(severity * 100)}
              onChange={(e) => setSeverity(Number(e.target.value) / 100)}
              className="mt-2 w-full accent-[#79c4b7]"
              aria-label="Severity"
            />
          </Field>

          <Field
            label="Case reference (optional)"
            hint="opaque linkage token — letters, digits, underscore"
          >
            <input
              value={caseRef}
              onChange={(e) => setCaseRef(e.target.value)}
              maxLength={40}
              placeholder="e.g. CASE_RAAVAN_1930_0001 (demo kits only)"
              className="h-11 w-full rounded-md border border-input bg-secondary/70 px-3 font-mono text-sm text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Case reference"
            />
          </Field>

          <PhosphorButton onClick={sendReport} disabled={busy}>
            <Send className="size-4" aria-hidden="true" />
            {busy ? "Signing…" : "Send signed report"}
          </PhosphorButton>

          {error ? (
            <div className="rounded-md border border-sev-critical/50 bg-sev-critical/10 p-4 text-sm text-sev-critical">
              {error}
            </div>
          ) : null}

          {result ? (
            <VerdictCard
              band={delivered ? "LOW" : "MODERATE"}
              title={delivered ? "REPORTED · DELIVERED" : "NOT DELIVERED"}
              reasons={[
                `event ${result.event_id ?? "n/a"} · category ${result.category ?? category} · band ${result.severity ?? severity}`,
                result.explanation?.body ??
                  (delivered
                    ? "Received by the spine bus."
                    : result.forwarded?.reason ??
                      "The bus was not configured — nothing was stored or synced. If money has moved, call 1930 now."),
              ]}
              action="If you lost money, call 1930 and freeze the transaction."
            />
          ) : null}

          {log.length ? (
            <details className="rounded-md border border-border bg-secondary/40 p-4">
              <summary className="cursor-pointer font-mono text-xs tracking-[0.18em] uppercase text-muted-foreground">
                Session report log ({log.length})
              </summary>
              <ul className="mt-3 space-y-1.5 font-mono text-xs text-muted-foreground">
                {log.map((r, i) => (
                  <li key={i} className="flex justify-between gap-3">
                    <span>{r.event_id}</span>
                    <span className={r.delivered ? "text-phosphor" : "text-sev-moderate"}>
                      {r.delivered ? "delivered" : "held"}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      </PhosphorPanel>

      {/* spine status */}
      <aside className="space-y-6">
        <PhosphorPanel className="p-6">
          <div className="flex items-center justify-between">
            <Kicker>SHARED SPINE STATUS</Kicker>
            <button
              type="button"
              onClick={refreshSpine}
              aria-label="Refresh spine status"
              className="font-mono text-xs text-muted-foreground hover:text-phosphor"
            >
              ↻
            </button>
          </div>
          {spineError ? (
            <div className="mt-4">
              <BackendNotice detail={spineError} onRetry={refreshSpine} />
            </div>
          ) : spineHealth ? (
            <div className="mt-4 grid gap-3">
              <StatTile
                label="bus"
                value={spineHealth.status === "ok" ? "ONLINE" : "OFFLINE"}
                hint={`executor: ${spineHealth.executor_mode ?? "?"} · commander: ${spineHealth.commander_mode ?? "?"}`}
              />
              <StatTile
                label="campaigns in window"
                value={spineState?.campaigns?.length ?? 0}
                hint={
                  spineState?.campaigns?.[0]
                    ? `largest: ${spineState.campaigns[0].campaign_id} (${spineState.campaigns[0].size} events)`
                    : "no fused campaigns yet"
                }
              />
              <StatTile
                label="quarantine"
                value={`${spineState?.fortress?.unverified_held ?? 0} held · ${spineState?.fortress?.replay_dropped ?? 0} replayed`}
                valueClass="text-sm"
                hint="unsigned or replayed events never steer the AI path"
              />
            </div>
          ) : null}
        </PhosphorPanel>

        <PhosphorPanel className="p-6">
          <Kicker>WHAT LEAVES THIS PAGE</Kicker>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li className="flex gap-2">
              <Landmark className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Category + severity band + a language digest, HMAC-signed.
            </li>
            <li className="flex gap-2">
              <Landmark className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              An optional opaque case ref — never PII — fuses your leg with
              infrastructure evidence into one campaign.
            </li>
            <li className="flex gap-2">
              <Landmark className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              If the bus is away, the console says NOT DELIVERED. It will never
              claim a report was stored when it was not.
            </li>
          </ul>
        </PhosphorPanel>
      </aside>
    </div>
  );
}
