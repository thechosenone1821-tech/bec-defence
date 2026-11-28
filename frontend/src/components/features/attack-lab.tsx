"use client";

import * as React from "react";
import { FlaskConical, RotateCcw, ShieldAlert, ShieldCheck, Zap } from "lucide-react";
import {
  Kicker,
  PhosphorPanel,
  PhosphorButton,
  BackendNotice,
  StatTile,
  StatusPill,
} from "@/components/phosphor/primitives";
import { spine } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";
import {
  EXPECTATION_META,
  SIMULATED_LABEL,
  STATUS_META,
  buildRail,
  campaignFor,
  loadCatalogue,
  newRunTag,
  railTone,
  runScenario,
  simEventPrefix,
  summariseRun,
  type RailRow,
  type RunSummary,
  type ScenarioCatalogue,
  type ScenarioSpec,
  type ScenarioStepSpec,
  type StepOutcome,
} from "@/lib/scenarios";

/**
 * Attack Lab — simulated attack scenarios, triggered from the console.
 *
 * The script lives in the backend (`apps/infra/demo/scenarios.py`) and is served
 * at `GET /api/infra/scenarios`; each step's payload is the active detector
 * registry's own fixture, so a step that claims a rule fires fires exactly that
 * rule. The browser posts every step through the same signed ingest path a real
 * organ uses, and every number on this page is read back from the runtime —
 * nothing here fabricates a detection, a containment action or an outcome.
 *
 * What is simulated is the TELEMETRY, and every step says so in its own summary,
 * campaign id and case id. No host, network, account or file is touched. The
 * executor is dry-run: organ control and admin override are refused by design,
 * and efficacy against real attack traffic remains UNMEASURED.
 *
 * The backend contract constants live in `apps/infra/features.py`.
 */

type PhosphorState = {
  status?: string;
  dry_run?: boolean;
  recent_events?: RailRow[];
  timeline?: RailRow[];
  detections?: Record<string, unknown>[];
  campaigns?: {
    campaign_id?: string;
    case_id?: string;
    /** sealed detections in the campaign — the runtime's own count */
    size?: number;
    risk_score?: number;
    severity_max?: number;
    fused?: boolean;
  }[];
  organs_observed?: string[];
  quarantine_count?: number;
  decision_count?: number;
  ledger_height?: number;
  fortress?: {
    telemetry_mac?: boolean;
    unverified_held?: number;
    replay_dropped?: number;
    rate_limited?: number;
    quarantine_states?: Record<string, number>;
  };
  governor?: {
    decisions_allowed?: number;
    decisions_refused?: number;
    executor_simulated?: number;
    executor_skipped_refusal?: number;
    live_action_paths?: number;
  };
  entity_graph?: { node_count?: number; edge_count?: number };
};

type RunState = {
  scenarioId: string;
  tag: string;
  stepKey: string;
  outcomes: StepOutcome[];
  summary: RunSummary;
};

/** The console's severity ramp: the I1 scale is what the registry event carries. */
function severityVar(value: number): string {
  if (value >= 5) return "var(--sev-critical)";
  if (value >= 4) return "var(--sev-high)";
  if (value >= 3) return "var(--sev-moderate)";
  return "var(--sev-mild)";
}

/** Rail rows belonging to one run — the runtime's own record, not a replay. */
function railFor(state: PhosphorState | null, scenario: ScenarioSpec, tag: string): RailRow[] {
  if (!state) return [];
  const campaign = campaignFor(scenario.id, tag);
  return buildRail(campaign, simEventPrefix(scenario.id, tag), state);
}

/**
 * What the runtime's own campaign row says about this run.
 *
 * `size` is sealed detections for the campaign id, so a run scripted to stay quiet
 * correctly reports zero here — that is the result, not a gap in the demo.
 */
function campaignFindings(
  state: PhosphorState | null,
  scenarioId: string,
  tag: string,
): { findings: number; fused: boolean; riskScore: number } | null {
  const match = (state?.campaigns ?? []).find(
    (c) => c.campaign_id === campaignFor(scenarioId, tag),
  );
  if (!match) return null;
  return {
    findings: typeof match.size === "number" ? match.size : 0,
    fused: Boolean(match.fused),
    riskScore: typeof match.risk_score === "number" ? match.risk_score : 0,
  };
}

function ScenarioCard({
  scenario,
  index,
  total,
  runningId,
  disabled,
  run,
  rail,
  lastTriggered,
  onTrigger,
}: {
  scenario: ScenarioSpec;
  index: number;
  total: number;
  runningId: string | null;
  disabled: boolean;
  run: RunState | null;
  rail: RailRow[];
  /** the card the presenter triggered most recently, so the eye finds it fast */
  lastTriggered: boolean;
  onTrigger: (scenario: ScenarioSpec) => void;
}) {
  const busy = runningId === scenario.id;
  const summary = run?.summary ?? null;
  const done = Boolean(summary) && !busy;
  const drift = summary?.drift ?? 0;
  const byKey = new Map((run?.outcomes ?? []).map((o) => [o.stepKey, o]));
  const activeKey = run?.stepKey ?? "";
  const severity = scenario.steps[0]?.severity ?? 0;
  const sev = severityVar;

  return (
    <PhosphorPanel
      className="ph-no-corners p-0"
      glow={busy || lastTriggered}
      as="div"
    >
      <div
        className="flex h-full flex-col gap-3 border-l-2 p-4"
        style={{ borderLeftColor: sev(severity) }}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Kicker>
              Scenario {String(index).padStart(2, "0")} / {String(total).padStart(2, "0")}
            </Kicker>
            <h3 className="mt-1 text-sm font-semibold leading-snug text-foreground">
              {scenario.name}
            </h3>
            <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
              {scenario.tactic}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            {lastTriggered && !busy ? (
              <span className="font-mono text-[9px] tracking-[0.18em] text-phosphor">
                LAST TRIGGERED
              </span>
            ) : null}
            <StatusPill
              label={`${SIMULATED_LABEL} · ${scenario.step_count} STEPS`}
              state={busy ? "warn" : done ? (drift ? "warn" : "ok") : "idle"}
            />
            <PhosphorButton
              variant={busy ? "ghost" : "solid"}
              disabled={disabled || busy}
              onClick={() => onTrigger(scenario)}
              title={`Send the scripted events for “${scenario.name}” through the signed ingest path`}
            >
              {busy ? (
                <Zap aria-hidden="true" className="size-3.5 animate-pulse" />
              ) : (
                <FlaskConical aria-hidden="true" className="size-3.5" />
              )}
              {busy ? "Running" : done ? "Run again" : "Trigger"}
            </PhosphorButton>
          </div>
        </div>

        <p className="text-xs leading-relaxed text-muted-foreground">{scenario.story}</p>
        <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/85">
          <span className="text-phosphor">WATCH </span>
          {scenario.watch_for}
        </p>

        <div className="flex flex-wrap gap-1.5">
          {scenario.organs.map((organ) => (
            <span
              key={organ}
              className="ph-no-corners rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              title={`Detection organ this scenario reads: ${organ}`}
            >
              {organ}
            </span>
          ))}
        </div>

        {done && summary ? (
          <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px] sm:grid-cols-4">
            {[
              { label: "detected", value: summary.fired, tone: "var(--sev-critical)" },
              { label: "held", value: summary.held, tone: "var(--sev-moderate)" },
              { label: "no finding", value: summary.quiet, tone: "var(--sev-mild)" },
              { label: "drift", value: summary.drift, tone: drift ? "var(--sev-high)" : "var(--sev-mild)" },
            ].map((chip) => (
              <div key={chip.label} className="rounded border border-border px-1.5 py-1">
                <span className="text-muted-foreground">{chip.label} </span>
                <span style={{ color: chip.tone }}>{chip.value}</span>
              </div>
            ))}
          </div>
        ) : null}
        {done && summary && summary.errors ? (
          <p className="font-mono text-[11px] text-sev-critical">
            {summary.errors} of {scenario.step_count} steps did not reach the runtime — the
            backend may have refused the rate limit or be offline. Trigger again.
          </p>
        ) : null}

        <ol className="flex flex-col gap-1.5">
          {scenario.steps.map((step) => (
            <ScenarioStepRow
              key={step.key}
              step={step}
              outcome={byKey.get(step.key)}
              active={activeKey === step.key && busy}
            />
          ))}
        </ol>

        {done ? (
          <div className="ph-scroll ph-no-corners max-h-40 overflow-auto rounded border border-border">
            <table className="w-full border-collapse font-mono text-[11px]">
              <caption className="border-b border-border bg-secondary/50 px-2 py-1 text-left text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Runtime rail · {rail.length} event{rail.length === 1 ? "" : "s"} for this run
              </caption>
              <tbody>
                {rail.length === 0 ? (
                  <tr>
                    <td className="px-2 py-1.5 text-muted-foreground">
                      The runtime has not echoed this campaign into its state view yet —
                      refresh in a moment, or the run is still in flight.
                    </td>
                  </tr>
                ) : (
                  rail.map((row, i) => (
                    <tr
                      key={row.event_id ? `${row.event_id}-${i}` : `${row.stage}-${row.ts}-${i}`}
                      className="border-b border-border/60 last:border-b-0"
                    >
                      <td className="whitespace-nowrap px-2 py-1.5 align-top text-muted-foreground">
                        {String(row.ts || "").slice(11, 19) || "—"}
                      </td>
                      <td className="px-2 py-1.5 align-top">
                        <span className="text-foreground">{row.organ || "envelope"}</span>
                        <span className="block text-muted-foreground">
                          {row.stage || row.signal_type || "event"} · {row.detail || row.event_id}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-right align-top text-muted-foreground">
                        {typeof row.ledger_seq === "number" ? `seq ${row.ledger_seq}` : "no entry"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </PhosphorPanel>
  );
}

function ScenarioStepRow({
  step,
  outcome,
  active,
}: {
  step: ScenarioStepSpec;
  outcome?: StepOutcome;
  active: boolean;
}) {
  const status = outcome?.status ?? "pending";
  const meta = STATUS_META[status];
  const tone = outcome ? meta.colorVar : "var(--muted-foreground)";
  return (
    <li
      className="ph-no-corners rounded border border-border px-2 py-1.5"
      style={{
        borderLeft: `2px solid ${tone}`,
        boxShadow: active ? "0 0 0 1px var(--phosphor)" : undefined,
      }}
      title={`${step.narrative} — expected: ${EXPECTATION_META[step.expects]}`}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 font-mono text-[11px]">
        <span className="text-muted-foreground">
          {String(step.index).padStart(2, "0")}
        </span>
        <span className="font-semibold text-foreground">{step.title}</span>
        <span
          className="ml-auto shrink-0 tracking-[0.14em]"
          style={{ color: tone }}
          title={`expected: ${step.expects} · ${statusLabelReason(step)}`}
        >
          {meta.label}
          {outcome && !outcome.asExpected ? " ≠ EXPECTED" : ""}
        </span>
      </div>
      <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2 font-mono text-[10px] text-muted-foreground">
        <span>{step.organ}</span>
        <span>· {step.leg} leg</span>
        <span>· {step.envelope}</span>
        <span>· sev {step.severity}</span>
        {step.expects_rule ? <span>· {step.expects_rule}</span> : null}
        {outcome ? <span className="text-foreground/80">· {outcome.detail}</span> : null}
        {outcome && outcome.decisions > 0 ? (
          <span className="text-phosphor">
            · response: {outcome.decisions} governor decision{outcome.decisions === 1 ? "" : "s"} ·{" "}
            {outcome.contained} (dry-run)
          </span>
        ) : null}
        {outcome?.ts ? (
          <span className="ml-auto">
            {outcome.ts.slice(11, 19)}
            {typeof outcome.ledgerSeq === "number" ? ` · ledger ${outcome.ledgerSeq}` : ""}
          </span>
        ) : null}
      </div>
    </li>
  );
}

function statusLabelReason(step: ScenarioStepSpec): string {
  if (step.envelope === "unsigned") return "unsigned events are held before detection";
  if (step.envelope === "forged") return "a forged signature is held as unverified evidence";
  if (step.fixture === "silent") return "benign features — no rule may fire";
  if (step.fixture === "missing") return "no readable features — the detector degrades to no_detection";
  return `rule ${step.expects_rule || "expected"} fires and the finding is sealed`;
}

export function AttackLabApp() {
  const [catalogue, setCatalogue] = React.useState<ScenarioCatalogue | null>(null);
  const [offline, setOffline] = React.useState<string | null>(null);
  const [runs, setRuns] = React.useState<Record<string, RunState>>({});
  const [runningId, setRunningId] = React.useState<string | null>(null);
  const [runningAll, setRunningAll] = React.useState(false);
  const [selected, setSelected] = React.useState<string>("");
  const [state, setState] = React.useState<PhosphorState | null>(null);
  const cancelled = React.useRef(false);

  // no interval of our own: the page's freshness is the state view's poll, so a
  // row can never show a clock the runtime did not report
  React.useEffect(() => () => {
    cancelled.current = true;
  }, []);

  // The loader is inline on purpose — `usePoll` holds it in a ref, so a new
  // closure per render never re-subscribes the interval (see hooks/use-poll.ts).
  const { refresh: refreshCatalogue } = usePoll(
    async () => {
      const res = await loadCatalogue();
      if (!res.ok) {
        setOffline(res.error);
        return;
      }
      setOffline(null);
      setCatalogue(res.data);
    },
    { everyMs: 30000 },
  );

  // The state view is polled rather than subscribed: the platform gateway is
  // same-origin and read-only, and it is the surface the other console views
  // already trust. `spine/api/state` is the Infra compat view, so the campaign,
  // fortress and governor counters below are the runtime's own numbers.
  const { refresh: refreshState } = usePoll(
    async () => {
      const res = await spine<PhosphorState>("/api/state");
      setState(res.ok ? res.data : null);
    },
    { everyMs: 2500 },
  );

  const scenarios = catalogue?.scenarios ?? [];

  const trigger = async (scenario: ScenarioSpec) => {
    if (runningId) return;
    setRunningId(scenario.id);
    setSelected(scenario.id);
    const tag = newRunTag();
    setRuns((prev) => ({
      ...prev,
      [scenario.id]: {
        scenarioId: scenario.id,
        tag,
        stepKey: scenario.steps[0]?.key ?? "",
        outcomes: [],
        summary: {
          runTag: tag,
          scenarioId: scenario.id,
          fired: 0,
          quiet: 0,
          held: 0,
          skipped: 0,
          errors: 0,
          drift: 0,
          finishedAt: "",
        },
      },
    }));
    try {
      await runScenario(scenario, tag, (outcome) => {
        if (cancelled.current) return;
        setRuns((prev) => {
          const run = prev[scenario.id];
          if (!run) return prev;
          const outcomes = [...run.outcomes.filter((o) => o.stepKey !== outcome.stepKey), outcome];
          return {
            ...prev,
            [scenario.id]: {
              ...run,
              stepKey: outcome.stepKey,
              outcomes,
              summary: summariseRun(scenario.id, outcomes),
            },
          };
        });
      });
    } finally {
      if (!cancelled.current) {
        // refresh before clearing the busy flag, so the tiles and the rail settle
        // with the run still marked as in-flight instead of flickering
        await refreshState();
        setRunningId(null);
      }
    }
  };

  // the whole library, scenario by scenario, through the same trigger path a
  // button uses — one flag tracks the sweep, and each run keeps its own tag
  const runLibrary = async () => {
    if (runningId || runningAll) return;
    setRunningAll(true);
    try {
      for (const scenario of scenarios) {
        if (cancelled.current) break;
        await trigger(scenario);
      }
    } finally {
      setRunningAll(false);
    }
  };

  const reset = async () => {
    setRuns({});
    setSelected("");
    await Promise.all([refreshCatalogue(), refreshState()]);
  };

  const totals = React.useMemo(() => {
    const all = Object.values(runs).flatMap((run) => run.outcomes);
    const fired = all.filter((o) => o.status === "fired").length;
    const held = all.filter((o) => o.status === "held").length;
    const quiet = all.filter((o) => o.status === "quiet").length;
    const drift = all.filter((o) => !o.asExpected && o.status !== "pending").length;
    const runsCount = Object.values(runs).filter((run) => run.outcomes.length).length;
    const scenarioIds = new Set(all.map((o) => o.scenarioId));
    return {
      runs: runsCount,
      scenarios: scenarioIds.size,
      events: all.length,
      fired,
      held,
      quiet,
      drift,
      organs: new Set(all.map((o) => o.organ)).size,
      rings: new Set(scenarios.filter((s) => scenarioIds.has(s.id)).flatMap((s) => s.rings)).size,
      contained: all.filter((o) => o.contained !== "—").length,
      decisions: all.reduce((sum, o) => sum + (o.decisions || 0), 0),
    };
  }, [runs, scenarios]);

  const lastRun = React.useMemo(() => {
    const list = Object.values(runs).filter((run) => run.outcomes.length);
    if (!list.length) return null;
    return list.reduce((a, b) => (a.summary.finishedAt >= b.summary.finishedAt ? a : b));
  }, [runs]);

  // every run this page started knows its own event-id prefix, so a row of the
  // shared feed can be labelled SIMULATED from what was actually sent
  const simPrefixes = React.useMemo(
    () => Object.values(runs).map((run) => simEventPrefix(run.scenarioId, run.tag)),
    [runs],
  );
  // an attack demo that ends without a visible alert is not a demo: this strip is
  // the fired rows of the runs above, grouped by organ, with the rules the runtime
  // actually named
  const alerts = React.useMemo(() => {
    const fired = Object.values(runs)
      .flatMap((run) => run.outcomes)
      .filter((outcome) => outcome.status === "fired");
    const byOrgan = new Map<string, { rules: Set<string>; entities: Set<string>; severity: number }>();
    for (const row of fired) {
      const bucket =
        byOrgan.get(row.organ) ?? { rules: new Set<string>(), entities: new Set<string>(), severity: 0 };
      row.firedRules.forEach((rule) => bucket.rules.add(rule));
      bucket.entities.add(row.entity);
      bucket.severity = Math.max(bucket.severity, row.severity);
      byOrgan.set(row.organ, bucket);
    }
    return [...byOrgan.entries()].map(([organ, bucket]) => {
      const entities = [...bucket.entities];
      return {
        organ,
        rules: [...bucket.rules].filter(Boolean).join(", ") || "sealed finding",
        entities: entities.slice(0, 3).join(", "),
        more: Math.max(0, entities.length - 3),
        count: fired.filter((row) => row.organ === organ).length,
        severity: bucket.severity,
      };
    });
  }, [runs]);
  const lastOutcome = lastRun?.outcomes[lastRun.outcomes.length - 1] ?? null;  const lastRunScenario = lastRun ? scenarios.find((s) => s.id === lastRun.scenarioId) : null;
  const lastCampaign = lastRun ? campaignFindings(state, lastRun.scenarioId, lastRun.tag) : null;
  const lastRail = lastRun && lastRunScenario
    ? railFor(state, lastRunScenario, lastRun.tag)
    : [];

  if (offline && !catalogue) {
    return <BackendNotice detail={offline} onRetry={() => void refreshCatalogue()} />;
  }

  return (
    <div className="ph-flex flex-col gap-4">
      <PhosphorPanel className="p-4" glow>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Kicker phosphor>
              Attack lab · simulated · dry-run · {scenarios.length} scenarios
            </Kicker>
            <h2 className="mt-1 text-lg font-semibold leading-tight text-foreground">
              Trigger a scripted attack, watch the platform answer it
            </h2>
            <p className="mt-1 max-w-[92ch] text-xs leading-relaxed text-muted-foreground">
              Every event below is synthetic and labelled{" "}
              <span className="font-mono text-phosphor">{SIMULATED_LABEL}</span> in its own
              summary, campaign id and case id. The payloads are the detector registry&apos;s
              own fixtures, the ingest path is the one real organs use, and every count on
              this page is read back from the runtime — nothing is drawn from a storyboard.
              No host, network, account or file is touched; containment is simulated
              dry-run only, and real-world efficacy is unmeasured.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusPill
              label={runningId ? "RUNNING" : runningAll ? "RUNNING · LIBRARY" : "ARMED"}
              state={runningId || runningAll ? "warn" : "ok"}
            />
            <StatusPill
              label={`LEDGER ${state?.ledger_height ?? "—"}`}
              state={typeof state?.ledger_height === "number" ? "ok" : "down"}
            />
            <PhosphorButton
              variant="ghost"
              disabled={Boolean(runningId) || runningAll}
              onClick={() => void runLibrary()}
            >
              <Zap aria-hidden="true" className="size-3.5" />
              Run all
            </PhosphorButton>
            <PhosphorButton variant="danger" onClick={() => void reset()}>
              <RotateCcw aria-hidden="true" className="size-3.5" />
              Reset
            </PhosphorButton>
          </div>
        </div>
      </PhosphorPanel>

      {alerts.length ? (
        <PhosphorPanel className="p-4" glow>
          <div className="flex flex-wrap items-center gap-2">
            <Kicker phosphor>Alerts raised by this demonstration</Kicker>
            <span className="ml-auto font-mono text-[10px] text-muted-foreground">
              one line per organ the runtime flagged · severity is the event&apos;s own
            </span>
          </div>
          <ul className="mt-2 grid gap-1.5 lg:grid-cols-2">
            {alerts.map((alert) => (
              <li
                key={alert.organ}
                className="ph-no-corners rounded border border-border px-2 py-1.5"
                style={{ borderLeft: `2px solid ${severityVar(alert.severity)}` }}
              >
                <div className="flex flex-wrap items-baseline gap-x-2 font-mono text-[11px]">
                  <span className="rounded border border-phosphor/50 px-1 text-[9px] tracking-[0.16em] text-phosphor">
                    {SIMULATED_LABEL}
                  </span>
                  <span className="font-semibold text-foreground">ALERT · {alert.organ}</span>
                  <span className="ml-auto text-muted-foreground">
                    {alert.count} finding{alert.count === 1 ? "" : "s"} · sev {alert.severity}
                  </span>
                </div>
                <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                  {alert.rules} · {alert.entities}
                  {alert.more ? ` +${alert.more} more` : ""}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 font-mono text-[10px] leading-relaxed text-muted-foreground">
            Response taken by the platform: {totals.decisions} Governor decision(s) and{" "}
            {totals.contained} dry-run containment result(s) on this page&apos;s runs. Organ control
            and admin override stay refused, the executor is dry-run, and no real action was
            attempted against anything.
          </p>
        </PhosphorPanel>
      ) : null}

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <StatTile
          label="simulated events sent"
          value={totals.events}
          hint={`${totals.runs} run${totals.runs === 1 ? "" : "s"} across ${totals.scenarios} scenario${totals.scenarios === 1 ? "" : "s"}`}
        />
        <StatTile
          label="detected"
          value={totals.fired}
          hint="sealed findings the runtime accepted"
          valueClass="text-sev-critical"
        />
        <StatTile
          label="held unverified"
          value={totals.held}
          hint="quarantined before detection, kept as evidence"
          valueClass="text-sev-moderate"
        />
        <StatTile
          label="no finding"
          value={totals.quiet}
          hint="verified telemetry that correctly stayed quiet"
          valueClass="text-sev-mild"
        />
        <StatTile
          label="organs lit by this run"
          value={`${totals.organs} / ${catalogue?.totals.organs ?? 8}`}
          hint={`across ${totals.rings} detection ring${totals.rings === 1 ? "" : "s"}`}
        />
        <StatTile
          label="governor decisions"
          value={totals.decisions}
          hint="proposals this run had ruled on (dry-run)"
        />
        <StatTile
          label="runtime detections"
          value={state ? (state.detections ?? []).length : "—"}
          hint={`${state?.quarantine_count ?? "—"} held · ${state?.organs_observed?.length ?? 0} organs reporting`}
        />
        <StatTile
          label="executor mode"
          value={
            <span className={state?.dry_run === false ? "text-sev-critical" : "text-phosphor"}>
              {state?.dry_run === false ? "NOT DRY-RUN" : "DRY-RUN"}
            </span>
          }
          hint={`${state?.governor?.live_action_paths ?? 0} live action paths · override refused`}
        />
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(320px,440px)]">
        <div className="ph-flex flex-col gap-3">
          {scenarios.length === 0 ? (
            <PhosphorPanel className="p-6 text-sm text-muted-foreground">
              The scenario catalogue is loading from <code>/api/infra/scenarios</code>.
            </PhosphorPanel>
          ) : (
            scenarios.map((scenario, i) => (
              <ScenarioCard
                key={scenario.id}
                scenario={scenario}
                index={i + 1}
                total={scenarios.length}
                runningId={runningId}
                disabled={Boolean(runningId) || runningAll}
                run={runs[scenario.id] ?? null}
                rail={railFor(state, scenario, runs[scenario.id]?.tag ?? "")}
                lastTriggered={selected === scenario.id}
                onTrigger={(s) => void trigger(s)}
              />
            ))
          )}
        </div>

        <div className="ph-flex flex-col gap-3">
          <PhosphorPanel className="p-4">
            <Kicker phosphor>Last run · live runtime view</Kicker>
            <div className="mt-2 grid gap-1.5">
              <RunTile
                label="scenario"
                value={lastRunScenario ? lastRunScenario.name : "no run yet — trigger a card"}
              />
              <RunTile
                label="campaign id"
                value={lastRun ? campaignFor(lastRun.scenarioId, lastRun.tag) : "—"}
              />
              <RunTile
                label="run tag"
                value={lastRun ? lastRun.tag : "—"}
              />
              <RunTile
                label="last step"
                value={
                  lastOutcome
                    ? `${lastOutcome.title} · ${STATUS_META[lastOutcome.status].label}${
                        lastOutcome.ledgerSeq !== null ? ` · ledger ${lastOutcome.ledgerSeq}` : ""
                      }`
                    : "—"
                }
              />
              <RunTile
                label="campaign row in the runtime"
                value={
                  lastCampaign
                    ? `${lastCampaign.findings} sealed detection${lastCampaign.findings === 1 ? "" : "s"} · ${lastCampaign.fused ? "cross-leg campaign fused" : "single-leg, not fused"} · risk ${lastCampaign.riskScore}`
                    : lastRun
                      ? "no campaign row for this id yet — the state view refreshes every 2.5 s"
                      : "—"
                }
              />
              <RunTile
                label="fortress counters"
                value={`${state?.fortress?.unverified_held ?? "—"} held · ${state?.fortress?.replay_dropped ?? "—"} replay dropped · ${state?.fortress?.rate_limited ?? "—"} rate limited · MAC ${state?.fortress?.telemetry_mac ? "on" : "—"}`}
              />
              <RunTile
                label="governor"
                value={`${state?.governor?.decisions_allowed ?? "—"} allowed · ${state?.governor?.decisions_refused ?? "—"} refused · ${state?.governor?.executor_simulated ?? "—"} simulated · ${state?.governor?.executor_skipped_refusal ?? "—"} skipped on refusal`}
              />
            </div>
          </PhosphorPanel>

          <PhosphorPanel className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Kicker phosphor>Live timeline · runtime state view</Kicker>
              <StatusPill
                label={state ? `${(state.recent_events ?? []).length} RUNTIME EVENTS` : "STATE VIEW OFFLINE"}
                state={state ? "ok" : "down"}
              />
            </div>
            <div className="ph-scroll ph-no-corners mt-2 max-h-[460px] overflow-auto rounded border border-border">
              <ol className="flex flex-col">
                {(state?.recent_events ?? []).length === 0 ? (
                  <li className="px-2 py-2 font-mono text-[11px] text-muted-foreground">
                    The runtime state view is empty — trigger a scenario, or check that the
                    Infra backend is up.
                  </li>
                ) : (
                  (state?.recent_events ?? [])
                    .slice()
                    .reverse()
                    .map((row: RailRow, i: number) => {
                      const eventId = String(row.event_id ?? "");
                      // every run this page started knows its own event-id prefix,
                      // so a row from one of them is labelled without guessing
                      const simulated = simPrefixes.some((prefix) => eventId.startsWith(prefix));
                      const tone = railTone(row);
                      return (
                        <li
                          key={`${eventId}-${row.stage}-${i}`}
                          className="border-b border-border/60 px-2 py-1.5 last:border-b-0"
                          style={{ borderLeft: `2px solid ${tone}` }}
                        >
                          <div className="flex flex-wrap items-baseline gap-x-2 font-mono text-[11px]">
                            <span className="text-muted-foreground">
                              {String(row.ts || "").slice(11, 19) || "no stamp"}
                            </span>
                            <span className="font-semibold text-foreground">
                              {row.organ || "envelope"}
                            </span>
                            <span className="text-muted-foreground">{row.stage || row.signal_type}</span>
                            <span className="ml-auto flex items-center gap-1.5">
                              {simulated ? (
                                <span className="rounded border border-phosphor/50 px-1 text-[9px] tracking-[0.16em] text-phosphor">
                                  {SIMULATED_LABEL}
                                </span>
                              ) : null}
                              {typeof row.ledger_seq === "number" ? (
                                <span className="text-muted-foreground">seq {row.ledger_seq}</span>
                              ) : null}
                            </span>
                          </div>
                          <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                            {eventId || "—"} · {row.detail || "no detail"}
                          </div>
                        </li>
                      );
                    })
                )}
              </ol>
            </div>
          </PhosphorPanel>

          {lastRun && lastRunScenario ? (
            <PhosphorPanel className="p-4">
              <Kicker phosphor>This run in the runtime</Kicker>
              <table className="mt-2 w-full border-collapse font-mono text-[11px]">
                <tbody>
                  {lastRail.length === 0 ? (
                    <tr>
                      <td className="px-0 py-1.5 text-muted-foreground">
                        No campaign rows echoed yet for {campaignFor(lastRun.scenarioId, lastRun.tag)}.
                      </td>
                    </tr>
                  ) : (
                    lastRail.map((row, i) => (
                      <tr key={`${row.event_id}-${i}`} className="border-b border-border/60 last:border-b-0">
                        <td className="whitespace-nowrap px-0 py-1 text-muted-foreground">
                          {String(row.ts || "").slice(11, 19) || "—"}
                        </td>
                        <td className="px-2 py-1">{row.organ || "envelope"}</td>
                        <td className="px-2 py-1 text-muted-foreground">{row.stage || "event"}</td>
                        <td className="whitespace-nowrap px-0 py-1 text-right text-muted-foreground">
                          {typeof row.ledger_seq === "number" ? row.ledger_seq : "—"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </PhosphorPanel>
          ) : null}

          <PhosphorPanel className="p-4">
            <Kicker>What this page proves, and what it does not</Kicker>
            <ul className="mt-2 flex flex-col gap-1.5 text-xs leading-relaxed text-muted-foreground">
              {(catalogue?.notes ?? []).map((note) => (
                <li key={note} className="flex gap-2">
                  <ShieldCheck aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-phosphor" />
                  <span>{note}</span>
                </li>
              ))}
              {(catalogue?.claims_not_made ?? []).length ? (
                <li className="mt-1 flex gap-2">
                  <ShieldAlert aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-sev-moderate" />
                  <span>
                    Never claimed by these runs: {catalogue?.claims_not_made.join(", ")}.
                  </span>
                </li>
              ) : null}
            </ul>
            {offline ? (
              <p className="mt-2 font-mono text-[11px] text-sev-moderate">
                Catalogue read failed on the last refresh ({offline}) — the list above is the
                last one that loaded.
              </p>
            ) : null}
          </PhosphorPanel>
        </div>
      </div>
    </div>
  );
}

function RunTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="ph-no-corners rounded border border-border px-2 py-1.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <div className="mt-0.5 break-words font-mono text-[11px] text-foreground">{value}</div>
    </div>
  );
}
