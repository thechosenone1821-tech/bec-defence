"use client";

import * as React from "react";
import { Swords, ShieldCheck, ShieldX, Play } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { spine, spineSigned, type SpineSignedAck } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";
import type { SpineEvent } from "@/hooks/use-spine-feed";

/**
 * Red Team — sandbox-only campaign replay.
 *
 * The five techniques below are the active detector registry's own firing
 * fixtures (`apps/infra/detectors/registry.py`), sent in the enterprise `I1`
 * wire envelope that `packages/contracts/envelope.py` validates: `event_id`,
 * `ts`, `organ`, `campaign_id`, `case_id`, `leg`, integer `severity`,
 * `entity`, `summary` and a `payload` holding exactly the features the rule
 * requires. That matters: an event that carries features the detector does not
 * read is skipped as `no_detection`, so this page mirrors the registry rather
 * than inventing numbers. If a rule changes, the fixture values here change
 * with it (and `tools/check_frontend_integration.py` asserts they still
 * match).
 *
 * The events are minted in the browser and signed by the same-origin Python
 * gateway with the shared sensor key — the identical path a real organ uses, so
 * nothing here bypasses verification. A forged, unsigned probe and a
 * wrongly-signed probe are submitted FIRST; both must be quarantined and must
 * not steer the decision path. That refusal is the point of the exercise.
 */

const CAMPAIGN_ID = "CAMP_PHOSPHOR_REPLAY";
const CASE_ID = "CASE_PHOSPHOR_SANDBOX";

type CampaignStep = {
  name: string;
  organ: string;
  leg: "citizen" | "infra";
  entity: string;
  summary: string;
  /** registry scale: integer 1-5 */
  severity: number;
  payload: Record<string, number>;
  rule: string;
};

/** Firing fixtures copied from the registry — see the note above. */
const STEPS: CampaignStep[] = [
  {
    name: "T01 · replayed visitor session on the consumer leg",
    organ: "cookie_fluid_turbulence",
    leg: "citizen",
    entity: "HOST_CONSUMER_01",
    summary: "Turbulent cookie replay cadence above the laminar boundary",
    severity: 4,
    payload: { reynolds_number: 3100, cookie_replay_count: 3 },
    rule: "COOKIE-TURBULENT-REPLAY",
  },
  {
    name: "T02 · adversarial suffix inside a vendor document",
    organ: "bragg_fft_firewall",
    leg: "infra",
    entity: "DOC_VENDOR_INVOICE",
    summary: "Periodic adversarial suffix energy in the token spectrum",
    severity: 5,
    payload: { fft_peak_ratio: 0.88, fiedler_value: 0.04 },
    rule: "BRAGG-FFT-PEAK",
  },
  {
    name: "T03 · rank-1 session condensation on the projector edge",
    organ: "bec_spectral_filter",
    leg: "infra",
    entity: "HOST_EDGE_07",
    summary: "Rank-1 condensation with a sufficient sample window",
    severity: 4,
    payload: { condensation_ratio: 0.91, session_count: 12 },
    rule: "BEC-RANK1-CONDENSATION",
  },
  {
    name: "T04 · ransomware parity break on a honey page",
    organ: "page_curve_trap",
    leg: "infra",
    entity: "HOST_FINANCE_22",
    summary: "4 KB honey-block XOR invariant broken on first write",
    severity: 5,
    payload: { parity_break: 1, encrypt_events_per_min: 512 },
    rule: "PAGECURVE-PARITY-BREAK",
  },
  {
    name: "T05 · unattributed package-power residual",
    organ: "landauer_thermal_audit",
    leg: "infra",
    entity: "HOST_EDGE_07",
    summary: "Macroscopic power residual not explained by instruction rate",
    severity: 3,
    payload: { power_residual_w: 18.5 },
    rule: "LANDAUER-POWER-RESIDUAL",
  },
];

/**
 * One wire event per step. `salt` + `nonce` keep ids unique per run because the
 * runtime refuses a repeated `event_id` — so the unsigned probes and the signed
 * campaign deliberately use different ids, and re-running the replay is
 * possible without tripping the duplicate guard.
 */
function buildEvents(salt: string, nonce: string, forged = false): Record<string, unknown>[] {
  const ts = `${new Date().toISOString().slice(0, 19)}Z`;
  return STEPS.map((s, i) => {
    const event: Record<string, unknown> = {
      event_id: `evt_${salt}_${nonce}_${String(i + 1).padStart(2, "0")}`,
      ts,
      organ: s.organ,
      campaign_id: CAMPAIGN_ID,
      case_id: CASE_ID,
      leg: s.leg,
      severity: s.severity,
      entity: s.entity,
      summary: s.summary,
      payload: s.payload,
    };
    if (forged) {
      // a signature that was never minted with the sensor key
      event.sig = "0".repeat(64);
      event.sig_alg = "HMAC-SHA256";
    }
    return event;
  });
}

type IngestBody = {
    event_id?: string;
    accepted?: boolean;
    verified?: string;
    quarantined?: boolean;
    reason?: string;
    detections?: { organ?: string; rule_id?: string; reason?: string }[];
    decisions?: { verdict?: string; reason?: string }[];
    campaign?: { campaign_id?: string; fused?: boolean; legs?: string[] };
};

type IngestResult = { status?: number; body?: IngestBody };

/** The gateway answers the same shape for signed and unsigned batches. */
type IngestAck = SpineSignedAck<IngestBody>;

type OrchestrateBundle = {
  status?: string;
  reason?: string;
  commander_mode?: string;
  brief?: string;
  unverified_events?: number;
  ledger_height?: number;
  actions?: { tool?: string; proposal_id?: string; rationale?: string }[];
  decisions?: { tool?: string; decision?: string; reason?: string; dry_run?: boolean }[];
  results?: { tool?: string; result?: { status?: string; detail?: string } }[];
};

type SpineState = {
  campaigns?: {
    campaign_id?: string;
    size?: number;
    risk_score?: number;
    legs?: string[];
    organs?: string[];
  }[];
  governor?: {
    live_action_paths?: number;
    decisions_allowed?: number;
    decisions_refused?: number;
    executor_simulated?: number;
  };
  fortress?: {
    unverified_held?: number;
    replay_dropped?: number;
    quarantine_states?: Record<string, number>;
  };
  organs_observed?: string[];
  recent_events?: SpineEvent[];
};

type LogLine = {
  kind: "forge" | "hold" | "signed" | "plan" | "state" | "error";
  text: string;
};

const HOLD_STATUSES = new Set([
  "HELD_UNVERIFIED_EVIDENCE",
  "PARTIAL_HOLD",
  "NO_EVENTS",
]);

export function RedTeamApp() {
  const [running, setRunning] = React.useState(false);
  const [log, setLog] = React.useState<LogLine[]>([]);
  const [state, setState] = React.useState<SpineState | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    const res = await spine<SpineState>("/api/state");
    if (res.ok) {
      setState(res.data);
      setError(null);
    } else {
      setError(res.error);
    }
  }, []);

  const { refresh: refreshState } = usePoll(load, { everyMs: 10000 });

  const push = (line: LogLine) => setLog((prev) => [...prev, line]);

  const runReplay = async () => {
    setRunning(true);
    setLog([]);
    setError(null);
    try {
      const nonce = Math.random().toString(16).slice(2, 8);
      const unsigned = buildEvents("u", nonce);
      const signed = buildEvents("s", nonce);

      // ACT 1 — unsigned probes must be held before any detection runs
      push({ kind: "forge", text: "Submitting unsigned probes (no signature field)…" });
      const forge = await spine<IngestAck>("/api/ingest", {
        method: "POST",
        body: JSON.stringify(unsigned),
      });
      if (!forge.ok) {
        push({ kind: "error", text: forge.error });
        return;
      }
      push({
        kind: "forge",
        text: `unsigned batch → received ${forge.data.received ?? 0}, held ${forge.data.unverified ?? 0}`,
      });
      for (const item of forge.data.results ?? []) {
        const body = item.body ?? {};
        push({
          kind: "forge",
          text: `  ${body.event_id ?? "?"} → ${body.quarantined ? `quarantined as ${body.verified}` : "ACCEPTED — FAIL"}`,
        });
      }

      // ACT 2 — a forged signature is a different failure and must read as one
      const forged = await spine<IngestAck>("/api/ingest", {
        method: "POST",
        body: JSON.stringify(buildEvents("f", nonce, true)),
      });
      if (forged.ok) {
        const body = forged.data.results?.[0]?.body ?? {};
        push({
          kind: "forge",
          text: `forged signature → ${body.quarantined ? `quarantined as ${body.verified} (${body.reason ?? ""})` : "ACCEPTED — FAIL"}`,
        });
      } else {
        push({ kind: "error", text: forged.error });
      }

      // ACT 3 — the decision path must refuse to steer on held evidence
      const held = await spine<OrchestrateBundle>("/api/orchestrate", {
        method: "POST",
        body: "{}",
      });
      push(
        held.ok
          ? {
              kind: "hold",
              text: `orchestrate → ${held.data.status}${held.data.reason ? ` (${held.data.reason})` : ""}`,
            }
          : { kind: "error", text: held.error },
      );
      if (held.ok && !HOLD_STATUSES.has(held.data.status ?? "")) {
        push({ kind: "error", text: "held evidence steered the decision path — FAIL" });
        return;
      }

      // ACT 4 — the same campaign, signed by the gateway with the sensor key
      push({ kind: "signed", text: "Ingesting the signed campaign (gateway mints HMAC-SHA256)…" });
      const ack = await spineSigned<IngestBody>(signed);
      if (!ack.ok) {
        push({ kind: "error", text: ack.error });
        return;
      }
      const bodies = (ack.data.results ?? []).map((item) => item.body ?? {});
      const fired = bodies.flatMap((body) => body.detections ?? []);
      const heldCount = bodies.filter((body) => body.quarantined).length;
      push({
        kind: "signed",
        text: `signed batch → accepted ${ack.data.accepted ?? 0}, rules fired ${fired.length}, held ${heldCount}`,
      });
      for (const d of fired) {
        push({ kind: "plan", text: `  ${d.organ} fired ${d.rule_id} — ${d.reason}` });
      }
      const fused = bodies.map((body) => body.campaign).find((c) => c?.fused);
      push({
        kind: "plan",
        text: fused
          ? `campaign ${fused.campaign_id} fused across legs: ${(fused.legs ?? []).join(" + ")}`
          : "no fused campaign — fusion needs findings on both the citizen and the infra leg",
      });

      // ACT 5 — what the Governor decided, and what was actually executed
      const bundle = await spine<OrchestrateBundle>("/api/orchestrate", {
        method: "POST",
        body: "{}",
      });
      if (bundle.ok) {
        push({
          kind: "plan",
          text: `orchestrate → ${bundle.data.status} · commander=${bundle.data.commander_mode ?? "?"} · ledger=${bundle.data.ledger_height ?? "?"}`,
        });
        for (const d of bundle.data.decisions ?? []) {
          push({
            kind: "plan",
            text: `  ${d.tool ?? "proposal"} → ${d.decision}${d.reason ? ` (${d.reason})` : ""}`,
          });
        }
        for (const r of bundle.data.results ?? []) {
          push({ kind: "plan", text: `  executor → ${r.result?.status ?? "?"} — ${r.result?.detail ?? ""}` });
        }
        if (bundle.data.brief) push({ kind: "plan", text: `brief: ${bundle.data.brief}` });
      } else {
        push({ kind: "error", text: bundle.error });
      }

      await refreshState();
      push({ kind: "state", text: "state refreshed — fused campaign and quarantine counters below" });
    } finally {
      setRunning(false);
    }
  };

  const top = state?.campaigns?.find((c) => c.campaign_id === CAMPAIGN_ID) ?? state?.campaigns?.[0];
  const heldStates = state?.fortress?.quarantine_states ?? {};

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
      {/* campaign */}
      <PhosphorPanel className="p-6" glow>
        <Kicker phosphor>CAMPAIGN REPLAY · SANDBOX ONLY</Kicker>
        <h2 className="mt-2 flex items-center gap-2 text-xl font-semibold">
          <Swords className="size-5 text-phosphor" aria-hidden="true" />
          Multi-stage campaign against the active detector
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Five techniques across two legs, all sharing one opaque case token so the bus fuses them
          into a single campaign. The payloads are the detector registry&apos;s own firing fixtures,
          so a rule listed here is a rule that really fires. Pointed only at this sandbox — never at
          a system you do not own.
        </p>

        <ol className="mt-6 space-y-2">
          {STEPS.map((s, i) => (
            <li
              key={s.name}
              className="rounded-md border border-border bg-secondary/50 px-4 py-3"
              style={{
                borderLeft: `3px solid var(--sev-${s.severity >= 5 ? "critical" : s.severity >= 4 ? "high" : "moderate"})`,
              }}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-mono text-sm text-foreground">{s.name}</p>
                <span className="font-mono text-[10px] tracking-[0.14em] text-muted-foreground">
                  sev {s.severity}/5 · {s.leg} leg
                </span>
              </div>
              <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                {s.organ} · {s.entity} → expect {s.rule}
              </p>
              <p className="sr-only">step {i + 1} of {STEPS.length}</p>
            </li>
          ))}
        </ol>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <PhosphorButton onClick={runReplay} disabled={running}>
            <Play className="size-4" aria-hidden="true" />
            {running ? "Replaying…" : "Run campaign replay"}
          </PhosphorButton>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            fresh event ids per run — a repeated id is refused as a duplicate
          </span>
        </div>

        {log.length ? (
          <div className="mt-6 max-h-64 space-y-1 overflow-y-auto rounded-md border border-border bg-panel p-4 font-mono text-xs ph-scroller" aria-live="polite">
            {log.map((l, i) => (
              <p
                key={i}
                className={
                  l.kind === "error"
                    ? "text-sev-critical"
                    : l.kind === "hold"
                      ? "text-sev-moderate"
                      : l.kind === "signed" || l.kind === "plan"
                        ? "text-phosphor"
                        : "text-muted-foreground"
                }
              >
                {l.text}
              </p>
            ))}
          </div>
        ) : null}

        {error ? (
          <div className="mt-6">
            <BackendNotice detail={error} onRetry={refreshState} />
          </div>
        ) : null}
      </PhosphorPanel>

      <aside className="space-y-6">
        {/* fused campaign */}
        <PhosphorPanel className="p-6">
          <div className="flex items-center justify-between">
            <Kicker>FUSED CAMPAIGN VIEW</Kicker>
            <button
              type="button"
              onClick={refreshState}
              aria-label="Refresh campaign state"
              className="font-mono text-xs text-muted-foreground hover:text-phosphor"
            >
              ↻
            </button>
          </div>
          {top ? (
            <div className="mt-4 grid gap-3">
              <StatTile
                label="campaign"
                value={top.campaign_id ?? "—"}
                valueClass="text-sm"
                hint={`${top.size ?? "?"} sealed detections · legs ${(top.legs ?? []).join(" + ") || "—"}`}
              />
              <StatTile
                label="risk score"
                value={top.risk_score ?? "—"}
                hint="runtime rule: 10 points per sealed detection"
              />
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              No fused campaign in the runtime window yet — run the replay.
            </p>
          )}
          <div className="mt-4 grid grid-cols-2 gap-3">
            <StatTile
              label="unverified held"
              value={state?.fortress?.unverified_held ?? 0}
              hint={`unsigned ${heldStates.unsigned ?? 0} · tampered ${heldStates.tampered ?? 0}`}
            />
            <StatTile
              label="replay dropped"
              value={state?.fortress?.replay_dropped ?? 0}
              hint="same event id refused a second time"
            />
            <StatTile
              label="real actions"
              value={state?.governor?.live_action_paths ?? 0}
              hint="no live containment path is wired"
            />
            <StatTile
              label="governor"
              value={`${state?.governor?.decisions_allowed ?? 0}/${
                (state?.governor?.decisions_allowed ?? 0) + (state?.governor?.decisions_refused ?? 0)
              }`}
              hint="allowed / ruled (refusals are first-class)"
            />
          </div>
        </PhosphorPanel>

        <PhosphorPanel className="p-6">
          <Kicker>WHY THE FORGE MATTERS</Kicker>
          <div className="mt-3 space-y-3 text-sm text-muted-foreground">
            <p className="flex gap-2">
              <ShieldX className="mt-0.5 size-4 shrink-0 text-sev-moderate" aria-hidden="true" />
              Unsigned and tampered telemetry stay visible as evidence but can never steer the
              decision path or back a disruptive action — the runtime quarantines them before
              detection runs.
            </p>
            <p className="flex gap-2">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-phosphor" aria-hidden="true" />
              Signed telemetry traverses the same public endpoint and is verified by HMAC — only
              then may the Governor rule, and the executor simulates. Efficacy against real
              traffic is UNMEASURED.
            </p>
          </div>
        </PhosphorPanel>
      </aside>
    </div>
  );
}
