"use client";

import * as React from "react";
import { Scale, ShieldCheck, ShieldX, RefreshCw } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  BackendNotice,
  StatTile,
} from "@/components/phosphor/primitives";
import { spine } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";

type GovernorStatus = {
  config_integrity?: string;
  autonomy_mode?: string;
  frozen_categories?: Record<string, number>;
  budget_window_usage?: Record<string, number>;
};

type SpineState = {
  governor?: GovernorStatus | null;
  executor_mode?: string;
  orchestration_count?: number;
  last_containment?: Record<string, unknown> | null;
  last_plan?: Record<string, unknown> | null;
};

type ContainmentBundle = {
  status?: string;
  brief?: string;
  plan_source?: string;
  containment?: {
    plan_id?: string;
    status?: string;
    reason?: string;
    seeds?: string[];
    cut_size?: number;
    cut_edges?: { a: string; b: string }[];
    severed_fixture_flow_pct?: number;
    preserved_critical_weight_pct?: number;
    preserved_fixture_flow_pct?: number;
    icu_status?: string;
  };
  governor?: { decision?: string; reason?: string } | null;
  executor_result?: Record<string, unknown> | null;
};

type OrchestrateBundle = {
  status?: string;
  reason?: string;
  plan_id?: string;
  commander_mode?: string;
  brief?: string;
  actions?: { tool?: string; rationale?: string }[];
  decisions?: { tool?: string; decision?: string; reason?: string }[];
  results?: { tool?: string; result?: Record<string, unknown> }[];
};

export function GovernanceApp() {
  const [state, setState] = React.useState<SpineState | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);

  const [containment, setContainment] = React.useState<ContainmentBundle | null>(null);
  const [orchestration, setOrchestration] = React.useState<OrchestrateBundle | null>(null);

  const load = React.useCallback(async () => {
    const res = await spine<SpineState>("/api/state");
    if (res.ok) {
      setState(res.data);
      setError(null);
    } else {
      setError(res.error);
    }
  }, []);

  const { refresh } = usePoll(load, { everyMs: 20000 });

  const proposeContainment = async () => {
    setBusy("containment");
    const res = await spine<ContainmentBundle>("/api/containment", {
      method: "POST",
      body: JSON.stringify({}), // no seeds → derived from the live buffer
    });
    if (res.ok) setContainment(res.data);
    else setError(res.error);
    setBusy(null);
    refresh();
  };

  const orchestrate = async () => {
    setBusy("orchestrate");
    const res = await spine<OrchestrateBundle>("/api/orchestrate", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (res.ok) setOrchestration(res.data);
    else setError(res.error);
    setBusy(null);
    refresh();
  };

  const gov = state?.governor ?? null;
  const plan = containment?.containment;

  return (
    <div className="space-y-6">
      {/* governor summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="governor"
          value={gov ? "ARMED" : "UNWIRED"}
          hint={`autonomy: ${gov?.autonomy_mode ?? "?"} · executor: ${state?.executor_mode ?? "?"}`}
        />
        <StatTile
          label="config integrity"
          value={gov?.config_integrity ?? "?"}
          valueClass={gov?.config_integrity === "ok" ? "" : "text-sev-moderate"}
          hint="boot manifest verified at status read"
        />
        <StatTile
          label="budget window"
          value={
            gov?.budget_window_usage && Object.keys(gov.budget_window_usage).length
              ? Object.entries(gov.budget_window_usage).map(([k, v]) => `${k}:${v}`).join(" ")
              : "0 / 0"
          }
          valueClass="text-xs"
          hint="blast-radius counters in the current 5-min window"
        />
        <StatTile
          label="orchestrations"
          value={state?.orchestration_count ?? 0}
          hint="planner runs since bus boot"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* containment */}
        <PhosphorPanel className="p-6" glow>
          <Kicker phosphor>CONTAINMENT PLANNER · MIN-DISRUPTION CUT</Kicker>
          <h2 className="mt-2 text-xl font-semibold">Propose a containment cut</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Derives the apparent attack foothold from the live window, computes the
            minimal edge cut that severs it from Tier-0, then hands the plan to the
            deterministic Governor. Proposes only — the Governor disposes, the
            executor is a dry-run.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <PhosphorButton onClick={proposeContainment} disabled={busy === "containment"}>
              {busy === "containment" ? "Planning…" : "Propose cut from live window"}
            </PhosphorButton>
            <PhosphorButton variant="ghost" onClick={refresh} disabled={busy !== null}>
              <RefreshCw className="size-4" aria-hidden="true" /> Refresh state
            </PhosphorButton>
          </div>

          {containment ? (
            <div className="mt-5 space-y-4">
              <div
                className="rounded-md border p-4"
                style={{
                  borderColor:
                    containment.governor?.decision === "APPROVED"
                      ? "var(--sev-mild)"
                      : containment.governor?.decision
                        ? "var(--sev-moderate)"
                        : "var(--border)",
                }}
              >
                <div className="flex items-center gap-2">
                  {containment.governor?.decision === "APPROVED" ? (
                    <ShieldCheck className="size-4 text-phosphor" aria-hidden="true" />
                  ) : (
                    <ShieldX className="size-4 text-sev-moderate" aria-hidden="true" />
                  )}
                  <p className="font-mono text-sm tracking-[0.14em] uppercase text-foreground">
                    governor: {containment.governor?.decision ?? containment.status ?? "—"}
                  </p>
                </div>
                {containment.governor?.reason ? (
                  <p className="mt-2 font-mono text-xs text-muted-foreground">{containment.governor.reason}</p>
                ) : null}
                <p className="mt-2 text-sm text-muted-foreground">{containment.brief}</p>
              </div>

              {plan?.status === "PLAN_PROPOSED" ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label="cut size" value={plan.cut_size ?? 0} />
                  <StatTile
                    label="flow severed"
                    value={`${plan.severed_fixture_flow_pct ?? 0}%`}
                    hint="fixture window"
                  />
                  <StatTile
                    label="critical preserved"
                    value={`${plan.preserved_critical_weight_pct ?? 0}%`}
                  />
                  <StatTile label="tier-0" value={plan.icu_status ?? "INTACT"} />
                </div>
              ) : null}

              {plan?.cut_edges?.length ? (
                <div className="rounded-md border border-border bg-secondary/40 p-4">
                  <Kicker className="mb-2">cut edges</Kicker>
                  <ul className="space-y-1 font-mono text-xs text-muted-foreground">
                    {plan.cut_edges.map((e, i) => (
                      <li key={i}>
                        {e.a} ↔ {e.b}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </PhosphorPanel>

        {/* orchestration */}
        <PhosphorPanel className="p-6">
          <Kicker phosphor>COMMANDER · TOOL-LOCKED PLAN</Kicker>
          <h2 className="mt-2 text-xl font-semibold">Run an orchestration pass</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            The Commander (local model or deterministic fallback) proposes actions
            from the verified telemetry window. Every proposal must clear the
            Governor's five invariants before the executor may act — and only the
            fixed tool allowlist is reachable.
          </p>
          <div className="mt-4">
            <PhosphorButton onClick={orchestrate} disabled={busy === "orchestrate"}>
              {busy === "orchestrate" ? "Orchestrating…" : "Orchestrate now"}
            </PhosphorButton>
          </div>

          {orchestration ? (
            <div className="mt-5 space-y-3">
              <p className="font-mono text-xs text-muted-foreground">
                status:{" "}
                <span
                  className={
                    orchestration.status === "OK"
                      ? "text-phosphor"
                      : orchestration.status === "HELD_UNVERIFIED_EVIDENCE"
                        ? "text-sev-moderate"
                        : "text-foreground"
                  }
                >
                  {orchestration.status}
                </span>
                {orchestration.reason ? ` — ${orchestration.reason}` : ""} · commander:{" "}
                {orchestration.commander_mode ?? "?"}
              </p>
              {orchestration.brief ? (
                <p className="text-sm text-foreground/85">{orchestration.brief}</p>
              ) : null}
              {orchestration.decisions?.length ? (
                <div className="max-h-56 space-y-1.5 overflow-y-auto ph-scroller">
                  {orchestration.decisions.map((d, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-3 rounded border border-border/60 bg-secondary/40 px-3 py-1.5 font-mono text-[11px]"
                    >
                      <span className="truncate text-foreground/85">{d.tool}</span>
                      <span className={d.decision === "APPROVED" ? "text-phosphor" : "text-sev-moderate"}>
                        {d.decision}
                      </span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </PhosphorPanel>
      </div>

      {error ? <BackendNotice detail={error} onRetry={refresh} /> : null}
    </div>
  );
}
