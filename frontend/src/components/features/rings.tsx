"use client";

import * as React from "react";
import { Orbit, RefreshCw } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { spine } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";
import { useSpineFeed, type SpineEvent } from "@/hooks/use-spine-feed";

/**
 * Per-organ view. The active Infra backend exposes one deterministic detector
 * registry, not a fleet supervisor: there is no process to watch, so the
 * gateway reports what it can actually see — the rules registered for the
 * organ and whether that organ produced a detection or a quarantine in this
 * runtime window. Anything else is reported as unobserved rather than invented.
 */
type OrganHealth = {
  state: string;
  ring?: string;
  rules?: number;
  detections?: number;
  held?: number;
  last_event?: string | null;
  note?: string;
};

type FleetSnapshot = {
  available: boolean;
  reason?: string;
  executor_mode?: string;
  live_control?: boolean;
  organs?: Record<string, OrganHealth>;
  counts?: Record<string, number>;
  total?: number;
  halted?: string[];
  silent?: string[];
  unobserved?: string[];
  canary?: {
    available?: boolean;
    ran?: boolean;
    reason?: string;
    results?: Record<string, { verdict?: string; detail?: string }>;
  };
};

type SpineState = {
  buffered_events?: number;
  executor_mode?: string;
  entity_graph?: { node_count?: number; edge_count?: number; window_sec?: number; window_note?: string };
  campaigns?: { campaign_id?: string; size?: number; risk_score?: number; legs?: string[] }[];
  governor?: {
    planner?: string;
    governor_id?: string;
    executor_id?: string;
    decisions_allowed?: number;
    decisions_refused?: number;
    live_action_paths?: number;
  };
  fortress?: {
    telemetry_mac?: boolean;
    unverified_held?: number;
    replay_dropped?: number;
    rate_limited?: number;
  };
  organs_observed?: string[];
  recent_events?: SpineEvent[];
};

const RING_LABELS: Record<string, string> = {
  RING_1_PERIMETER_IDENTITY: "Ring 1 · Perimeter & Identity",
  RING_2_AI_DEFENSE: "Ring 2 · Corporate AI & Agent Defence",
  RING_2_AI_AGENT_DEFENSE: "Ring 2 · Corporate AI & Agent Defence",
  RING_3_ENDPOINT_SILICON: "Ring 3 · Endpoint, Kernel & Silicon",
  RING_4_NETWORK_HEALING: "Ring 4 · Network Fabric & Self-Healing",
};

/**
 * Colour by what the runtime actually saw for this organ. "QUIET" is not an
 * alarm — an organ with no signed telemetry in the window has nothing to say.
 */
function stateColor(state: string): string {
  switch (state) {
    case "OBSERVED":
      return "var(--sev-mild)";
    case "HELD_ONLY":
      return "var(--sev-moderate)";
    case "QUIET":
    default:
      return "var(--muted-foreground)";
  }
}

export function RingsApp() {
  const [fleet, setFleet] = React.useState<FleetSnapshot | null>(null);
  const [state, setState] = React.useState<SpineState | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [canary, setCanary] = React.useState<FleetSnapshot["canary"] | null>(null);
  const [haltOrgan, setHaltOrgan] = React.useState("");
  const [haltReason, setHaltReason] = React.useState("");
  const [approval, setApproval] = React.useState("");
  const [opResult, setOpResult] = React.useState<string | null>(null);
  const { events, source } = useSpineFeed();

  const load = React.useCallback(async () => {
    const [f, s] = await Promise.all([
      spine<FleetSnapshot>("/api/fleet"),
      spine<SpineState>("/api/state"),
    ]);
    if (!f.ok && !s.ok) setError(f.error || s.error || "gateway unreachable");
    else setError(null);
    if (f.ok) setFleet(f.data);
    if (s.ok) setState(s.data);
  }, []);

  /* one pass on mount, then every 20s; `refresh` is the manual button */
  const { pending: busy, refresh } = usePoll(load, { everyMs: 20000 });

  const runCanary = async () => {
    const res = await spine<FleetSnapshot>("/api/fleet/canary");
    if (res.ok) setCanary(res.data.canary ?? null);
    else setError(res.error);
  };

  const fleetOp = async (kind: "halt" | "resume") => {
    if (!haltOrgan) return;
    const body: Record<string, unknown> = { reason: haltReason };
    if (approval.trim()) body.approval = JSON.parse(approval);
    const res = await spine<{ status?: string; reason?: string }>(
      `/api/fleet/${encodeURIComponent(haltOrgan)}/${kind}`,
      { method: "POST", body: JSON.stringify(body) },
    );
    setOpResult(
      res.ok
        ? `${res.data.status}: ${res.data.reason ?? "done"}`
        : `${res.status === 403 ? "REFUSED" : "ERROR"}: ${res.error}`,
    );
    await refresh();
  };

  const organs = fleet?.organs ?? {};
  const byRing: Record<string, [string, OrganHealth][]> = {};
  for (const [name, h] of Object.entries(organs)) {
    const ring = h.ring ?? "RING_UNSET";
    (byRing[ring] ??= []).push([name, h]);
  }

  return (
    <div className="space-y-6">
      {/* summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="registry"
          value={`${state?.organs_observed?.length ?? 0}/${fleet?.total ?? 0} organs active`}
          hint={`${fleet?.counts?.HELD_ONLY ?? 0} held-only · ${fleet?.silent?.length ?? 0} quiet in this window`}
        />
        <StatTile
          label="topology"
          value={`${state?.entity_graph?.node_count ?? 0}n / ${state?.entity_graph?.edge_count ?? 0}e`}
          hint={`${state?.buffered_events ?? 0} timeline entries sealed in this runtime`}
        />
        <StatTile
          label="fused campaigns"
          value={state?.campaigns?.length ?? 0}
          hint={
            state?.campaigns?.[0]
              ? `${state.campaigns[0].campaign_id} · ${state.campaigns[0].size ?? 0} detections · legs ${(state.campaigns[0].legs ?? []).join("+")}`
              : "none fused in this runtime"
          }
        />
        <StatTile
          label="quarantine"
          value={`${state?.fortress?.unverified_held ?? 0}/${state?.fortress?.replay_dropped ?? 0}`}
          hint="unverified held / replay dropped — unsigned evidence never reaches detection"
        />
      </div>

      {/* rings */}
      {fleet && fleet.available && Object.keys(organs).length ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Object.entries(byRing).map(([ring, list]) => (
            <PhosphorPanel key={ring} className="p-6">
              <Kicker phosphor>{RING_LABELS[ring] ?? ring}</Kicker>
              <ul className="mt-4 space-y-2">
                {list.map(([name, h]) => (
                  <li
                    key={name}
                    className="flex items-center justify-between gap-3 rounded-md border border-border bg-secondary/50 px-4 py-3"
                    style={{ borderLeft: `3px solid ${stateColor(h.state)}` }}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-mono text-sm text-foreground">{name}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">
                        {h.rules ?? 0} rule{h.rules === 1 ? "" : "s"} · {h.detections ?? 0} detection
                        {h.detections === 1 ? "" : "s"} · {h.held ?? 0} held
                      </p>
                    </div>
                    <span
                      className="shrink-0 rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-[0.14em]"
                      style={{ color: stateColor(h.state), borderColor: stateColor(h.state) }}
                    >
                      {h.state}
                    </span>
                  </li>
                ))}
              </ul>
            </PhosphorPanel>
          ))}
        </div>
      ) : (
        <PhosphorPanel className="p-6">
          <Kicker phosphor>ORGAN FLEET</Kicker>
          <p className="mt-3 text-sm text-muted-foreground">
            {fleet?.available === false
              ? fleet.reason
              : "Fleet snapshot not available yet — the bus may be starting up."}
          </p>
        </PhosphorPanel>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* operator controls */}
        <PhosphorPanel className="p-6">
          <Kicker phosphor>ORGAN CONTROL — NOT WIRED</Kicker>
          <p className="mt-2 text-sm text-muted-foreground">
            The active build has no live organ supervisor to halt: detection organs are
            feature rules evaluated on signed telemetry, not processes. Any halt or resume
            request is answered <span className="font-mono">DRY_RUN_ONLY</span> with zero
            real actions, so the form below is a contract check, not a control panel.
          </p>
          <div className="mt-4 grid gap-3">
            <select
              value={haltOrgan}
              onChange={(e) => setHaltOrgan(e.target.value)}
              className="h-11 rounded-md border border-input bg-secondary/70 px-3 font-mono text-sm text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Organ"
            >
              <option value="">Select organ…</option>
              {Object.keys(organs).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <input
              value={haltReason}
              onChange={(e) => setHaltReason(e.target.value)}
              placeholder="Reason (shown in the ledger)"
              className="h-11 rounded-md border border-input bg-secondary/70 px-3 text-sm text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Reason"
            />
            <input
              value={approval}
              onChange={(e) => setApproval(e.target.value)}
              placeholder="Approval note (echoed only — nothing is executed)"
              className="h-11 rounded-md border border-input bg-secondary/70 px-3 font-mono text-xs text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="Approval note"
            />
            <div className="flex flex-wrap gap-3">
              <PhosphorButton variant="danger" disabled={!haltOrgan} onClick={() => fleetOp("halt")}>
                Probe halt (dry-run)
              </PhosphorButton>
              <PhosphorButton variant="ghost" disabled={!haltOrgan} onClick={() => fleetOp("resume")}>
                Probe resume (dry-run)
              </PhosphorButton>
              <PhosphorButton variant="ghost" onClick={runCanary}>
                Run canary sweep
              </PhosphorButton>
            </div>
            {opResult ? (
              <p className="break-words rounded-md border border-border bg-secondary/50 p-3 font-mono text-xs text-muted-foreground">
                {opResult}
              </p>
            ) : null}
            {canary ? (
              <p className="font-mono text-xs text-muted-foreground">
                canary: {canary.available === false ? canary.reason ?? "unavailable" : JSON.stringify(canary.results ?? {}).slice(0, 220)}
              </p>
            ) : null}
          </div>
        </PhosphorPanel>

        {/* live feed */}
        <PhosphorPanel className="p-6">
          <div className="flex items-center justify-between">
            <Kicker phosphor>LIVE TELEMETRY</Kicker>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              {source === "poll"
                ? "polling /v1/state"
                : source === "connecting"
                  ? "connecting…"
                  : "gateway unreachable"}
            </span>
          </div>
          <div className="mt-4 max-h-72 space-y-1.5 overflow-y-auto ph-scroller" aria-live="polite">
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Nothing sealed in the runtime window yet. Run the Red Team replay, the fake-hospital
                exercise, or send signed organ telemetry.
              </p>
            ) : (
              events.slice().reverse().map((e, i) => (
                <div
                  key={e.event_id ?? i}
                  className="flex items-center justify-between gap-3 rounded border border-border/60 bg-secondary/40 px-3 py-1.5 font-mono text-[11px]"
                >
                  <span className="truncate text-foreground/85">
                    {e.organ ?? "?"} · {e.signal_type ?? "?"}
                  </span>
                  <span className={e.verified ? "text-phosphor" : "text-sev-moderate"}>
                    {e.verified ? "✓" : "held"} sev {typeof e.severity === "number" ? e.severity.toFixed(2) : "?"}
                  </span>
                </div>
              ))
            )}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <PhosphorButton variant="ghost" onClick={refresh} disabled={busy}>
              <RefreshCw className={busy ? "size-4 animate-spin" : "size-4"} aria-hidden="true" />
              Refresh snapshot
            </PhosphorButton>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              {busy ? "reading gateway" : "idle"}
            </span>
          </div>
        </PhosphorPanel>
      </div>

      {error ? <BackendNotice detail={error} onRetry={refresh} /> : null}
    </div>
  );
}
