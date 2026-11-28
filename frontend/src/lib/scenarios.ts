/**
 * Simulated attack-scenario client for the Infrastructure console.
 *
 * The script itself lives in the backend (`apps/infra/demo/scenarios.py`, served
 * at `GET /api/infra/scenarios` through the same-origin gateway) because the
 * payloads are the detector registry's own fixtures and must not be re-typed
 * here. This module only knows how to:
 *
 *   1. load the catalogue,
 *   2. mint a fresh run tag so every `event_id` is new (the runtime refuses a
 *      repeated id, so a repeatable demo needs a new tag per run),
 *   3. post each step through the same ingest paths a real organ uses — signed
 *      events via the gateway's HMAC signer, unsigned and forged ones exactly as
 *      built so the runtime has to refuse them,
 *   4. classify the runtime's own answer against the step's declared
 *      expectation, so drift shows up on the console instead of in the demo.
 *
 * Nothing here talks to a real host, and no number in the UI is invented by the
 * browser: every count the page renders is read back from the runtime.
 */

import { spine, spineSigned, type SpineSignedAck } from "@/lib/gateway";

export const SCENARIO_CATALOGUE_PATH = "/api/infra/scenarios";
export const SIMULATED_LABEL = "SIMULATED";

export type ScenarioEnvelope = "signed" | "unsigned" | "forged";
export type ScenarioFixture = "firing" | "silent" | "missing";
export type ScenarioExpectation = "finding" | "no_detection" | "quarantine";

export type IngestBody = {
  event_id?: string;
  accepted?: boolean;
  verified?: string;
  reason?: string;
  quarantined?: boolean;
  quarantine?: { state?: string; reason?: string };
  detections?: { organ?: string; rule_id?: string; reason?: string; severity?: number }[];
  decisions?: { verdict?: string; reason?: string; status?: string }[];
  proposals?: { status?: string; reason?: string }[];
  executions?: { status?: string; detail?: string; simulated?: boolean }[];
  campaign?: { campaign_id?: string; fused?: boolean; legs?: string[] };
  ledger_height?: number;
};

export type IngestAck = SpineSignedAck<IngestBody>;

export type ScenarioRule = { rule_id: string; reason: string };

export type ScenarioOrgan = {
  name: string;
  ring: string;
  rules: ScenarioRule[];
  fixtures: Partial<Record<ScenarioFixture, Record<string, number>>>;
};

export type ScenarioStepSpec = {
  index: number;
  key: string;
  title: string;
  narrative: string;
  organ: string;
  ring: string;
  leg: "citizen" | "infra" | string;
  entity: string;
  severity: number;
  fixture: ScenarioFixture;
  envelope: ScenarioEnvelope;
  expects: ScenarioExpectation;
  expects_rule: string;
  rule_reason: string;
  summary: string;
  payload: Record<string, number>;
  event: Record<string, unknown>;
};

export type ScenarioSpec = {
  id: string;
  name: string;
  tactic: string;
  story: string;
  watch_for: string;
  severity: number;
  simulated: boolean;
  label: string;
  organs: string[];
  rings: string[];
  campaign_id: string;
  case_id: string;
  step_count: number;
  steps: ScenarioStepSpec[];
};

export type ScenarioCatalogue = {
  contract: string;
  status: string;
  simulated: boolean;
  label: string;
  notes: string[];
  claims_not_made: string[];
  totals: {
    scenarios: number;
    steps: number;
    organs: number;
    firing_steps: number;
    quiet_steps: number;
    held_steps: number;
  };
  organs: ScenarioOrgan[];
  scenarios: ScenarioSpec[];
};

export type StepStatus = "pending" | "fired" | "quiet" | "held" | "skipped" | "error";

export type StepOutcome = {
  runTag: string;
  scenarioId: string;
  scenarioName: string;
  stepIndex: number;
  stepKey: string;
  title: string;
  narrative: string;
  organ: string;
  ring: string;
  leg: string;
  entity: string;
  severity: number;
  envelope: ScenarioEnvelope;
  expects: ScenarioExpectation;
  rule: string;
  ruleReason: string;
  eventId: string;
  /** the stamp the event carried — the runtime keeps it verbatim */
  ts: string;
  /** when this browser saw the reply, for the live rail */
  observedAt: string;
  status: StepStatus;
  verified: string;
  detail: string;
  firedRules: string[];
  decisions: number;
  contained: string;
  ledgerSeq: number | null;
  /** the runtime's answer matched the scripted expectation */
  asExpected: boolean;
};

export type RunSummary = {
  runTag: string;
  scenarioId: string;
  fired: number;
  quiet: number;
  held: number;
  skipped: number;
  errors: number;
  drift: number;
  finishedAt: string;
};

export const STATUS_META: Record<StepStatus, { label: string; colorVar: string }> = {
  pending: { label: "ARMED", colorVar: "var(--muted-foreground)" },
  fired: { label: "DETECTED", colorVar: "var(--sev-critical)" },
  quiet: { label: "NO FINDING", colorVar: "var(--sev-mild)" },
  held: { label: "HELD UNVERIFIED", colorVar: "var(--sev-moderate)" },
  skipped: { label: "REFUSED", colorVar: "var(--sev-moderate)" },
  error: { label: "BACKEND ERROR", colorVar: "var(--sev-critical)" },
};

export const EXPECTATION_META: Record<ScenarioExpectation, string> = {
  finding: "a rule fires and the finding is sealed",
  no_detection: "verified telemetry, no rule fires, nothing is accused",
  quarantine: "held before detection and never allowed to steer a decision",
};

/** Wall-clock UTC to the second, matching the `ts` format the I1 contract uses. */
function stamp(): string {
  return `${new Date().toISOString().slice(0, 19)}Z`;
}

/** Short, URL-safe and unique per run: the runtime refuses a repeated event id. */
export function newRunTag(): string {
  return `${Date.now().toString(36).slice(-4)}${Math.random().toString(36).slice(2, 6)}`;
}

/**
 * Fill the two tokens the backend leaves in every scripted event.
 *
 * The event body itself is exactly what the catalogue served — this function
 * does not add, rename or invent a field.
 */
export function materialize(event: Record<string, unknown>, tag: string, ts: string): Record<string, unknown> {
  const text = JSON.stringify(event);
  return JSON.parse(text.replaceAll("{tag}", tag).replaceAll("{ts}", ts)) as Record<string, unknown>;
}

export async function loadCatalogue(): Promise<
  { ok: true; data: ScenarioCatalogue } | { ok: false; error: string; detail?: string }
> {
  // the path is written literally so tools/check_frontend_integration.py can
  // resolve it against the Infra app's own routes; SCENARIO_CATALOGUE_PATH is
  // asserted to equal apps/infra/features.py's constant by that same gate
  const res = await spine<ScenarioCatalogue>("/api/infra/scenarios");
  if (!res.ok) {
    return { ok: false, error: res.error, detail: "detail" in res ? res.detail : undefined };
  }
  if (!Array.isArray(res.data?.scenarios)) {
    return { ok: false, error: "the scenario catalogue came back without a scenario list" };
  }
  return { ok: true, data: res.data };
}

export type Classified = {
  status: StepStatus;
  verified: string;
  detail: string;
  firedRules: string[];
  decisions: number;
  contained: string;
  ledgerSeq: number | null;
};

function classify(body: IngestBody | undefined, transportError?: string): Classified {
  const detections = body?.detections ?? [];
  const firedRules = detections.map((d) => String(d.rule_id ?? "finding"));
  const base = {
    verified: String(body?.verified ?? ""),
    firedRules,
    decisions: (body?.decisions ?? []).length,
    contained: (body?.executions ?? []).map((e) => String(e.status ?? "simulated")).join(" · ") || "—",
    ledgerSeq: typeof body?.ledger_height === "number" ? body.ledger_height : null,
  };
  if (transportError) {
    return { status: "error", detail: transportError, ...base };
  }
  if (!body) {
    return { status: "error", detail: "the ingest reply carried no result body", ...base };
  }
  if (body.quarantined) {
    // `accepted` is still true for a held event: the runtime ingests it as
    // evidence, it just refuses to let it become a finding or a decision
    return {
      status: "held",
      detail: body.reason ?? body.quarantine?.reason ?? "held before detection",
      ...base,
    };
  }
  if (firedRules.length) {
    const reason = detections[0]?.reason ?? body.reason ?? "";
    return { status: "fired", detail: `${firedRules.join(", ")} — ${reason}`, ...base };
  }
  const reason = String(body.reason ?? "");
  if (reason.toLowerCase().includes("duplicate") || reason.toLowerCase().includes("rate limit")) {
    return { status: "skipped", detail: reason, ...base };
  }
  return { status: "quiet", detail: reason || "verified; no rule fired", ...base };
}

const MATCHES: Record<ScenarioExpectation, StepStatus[]> = {
  finding: ["fired"],
  no_detection: ["quiet"],
  quarantine: ["held"],
};

function outcomeFor(scenario: ScenarioSpec, step: ScenarioStepSpec, tag: string, ts: string,
  classified: Classified): StepOutcome {
  return {
    runTag: tag,
    scenarioId: scenario.id,
    scenarioName: scenario.name,
    stepIndex: step.index,
    stepKey: step.key,
    title: step.title,
    narrative: step.narrative,
    organ: step.organ,
    ring: step.ring,
    leg: step.leg,
    entity: step.entity,
    severity: step.severity,
    envelope: step.envelope,
    expects: step.expects,
    rule: step.expects_rule,
    ruleReason: step.rule_reason,
    eventId: String(step.event.event_id ?? "").replaceAll("{tag}", tag),
    ts,
    observedAt: new Date().toISOString().slice(11, 19),
    status: classified.status,
    verified: classified.verified,
    detail: classified.detail,
    firedRules: classified.firedRules,
    decisions: classified.decisions,
    contained: classified.contained,
    ledgerSeq: classified.ledgerSeq,
    asExpected: MATCHES[step.expects]?.includes(classified.status) ?? false,
  };
}

/**
 * Post one scripted step and return the runtime's own answer.
 *
 * Signed steps go through the gateway signer — the same verification path a real
 * organ uses. Unsigned and forged steps are sent exactly as scripted so the
 * runtime has to refuse them: that refusal is part of the demonstration.
 */
async function postStep(step: ScenarioStepSpec, event: Record<string, unknown>):
  Promise<{ body?: IngestBody; error?: string }> {
  if (step.envelope === "signed") {
    const ack = await spineSigned<IngestBody>([event]);
    if (!ack.ok) return { error: ack.error };
    return { body: ack.data.results?.[0]?.body };
  }
  const ack = await spine<IngestAck>("/api/ingest", {
    method: "POST",
    body: JSON.stringify(event),
  });
  if (!ack.ok) return { error: ack.error };
  return { body: ack.data.results?.[0]?.body };
}

export type StepListener = (outcome: StepOutcome) => void;

/** Run every step of one scenario in script order, reporting each result as it lands. */
export async function runScenario(scenario: ScenarioSpec, tag: string, onStep?: StepListener):
  Promise<StepOutcome[]> {
  const outcomes: StepOutcome[] = [];
  for (const step of scenario.steps) {
    const ts = stamp();
    const event = materialize(step.event, tag, ts);
    const { body, error } = await postStep(step, event);
    const classified = classify(body, error);
    const outcome = outcomeFor(scenario, step, tag, ts, classified);
    outcomes.push(outcome);
    onStep?.(outcome);
  }
  return outcomes;
}

/** Run the whole library, scenario by scenario, keeping one tag per scenario run. */
export async function runLibrary(scenarios: ScenarioSpec[], onStep?: StepListener):
  Promise<StepOutcome[]> {
  const all: StepOutcome[] = [];
  for (const scenario of scenarios) {
    all.push(...(await runScenario(scenario, newRunTag(), onStep)));
  }
  return all;
}

export function summariseRun(scenarioId: string, outcomes: StepOutcome[]): RunSummary {
  const rows = outcomes.filter((o) => o.scenarioId === scenarioId);
  return {
    runTag: rows[rows.length - 1]?.runTag ?? "",
    scenarioId,
    fired: rows.filter((o) => o.status === "fired").length,
    quiet: rows.filter((o) => o.status === "quiet").length,
    held: rows.filter((o) => o.status === "held").length,
    skipped: rows.filter((o) => o.status === "skipped").length,
    errors: rows.filter((o) => o.status === "error").length,
    drift: rows.filter((o) => !o.asExpected && o.status !== "pending").length,
    finishedAt: rows.length ? rows[rows.length - 1].observedAt : "",
  };
}

/**
 * One row as the shared state view renders it.
 *
 * `recent_events` carries `ts`, `campaign_id` and a detection COUNT; `timeline`
 * carries `stage`, `ledger_seq` and `detail` but no wall clock. The rail reads the
 * first for stamps and the second for ledger facts — neither is invented here.
 */
export type RuntimeRow = {
  event_id?: string;
  kind?: string;
  /** `timeline` rows name their event `ref`, not `event_id` */
  ref?: string;
  campaign_id?: string;
  organ?: string;
  signal_type?: string;
  severity?: number;
  verified?: boolean;
  stage?: string;
  detail?: string;
  ts?: string;
  timestamp_utc?: string;
  detections?: number | { rule_id?: string }[];
  ledger_seq?: number | null;
  step?: number;
};

/** `timeline` rows joined onto `recent_events` rows by event id. */
export type RailRow = RuntimeRow & {
  ts?: string;
  stage?: string;
};

/** A row may report its detection count as a number or as the list itself. */
export function detectionCount(row?: RuntimeRow): number {
  if (!row) return 0;
  const value = row.detections;
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return value.length;
  return 0;
}

/** Rows from the runtime's own feed that belong to one simulated campaign run. */
export function runtimeRowsFor(campaignId: string, eventPrefix: string, rows?: RuntimeRow[]): RuntimeRow[] {
  return (rows ?? []).filter((row) => {
    const id = String(row.event_id ?? "");
    return row.campaign_id === campaignId || id.startsWith(eventPrefix);
  });
}

/**
 * The live rail for one run: `recent_events` rows of this campaign, joined with the
 * timeline row of the same event id so each line carries a stage and a ledger
 * sequence. Sorted newest first, so the newest thing a trigger did sits on top.
 */
export function buildRail(campaignId: string, eventPrefix: string, state?: {
  recent_events?: RuntimeRow[]; timeline?: RuntimeRow[];
}): RailRow[] {
  const timeline = state?.timeline ?? [];
  const rows = runtimeRowsFor(campaignId, eventPrefix, state?.recent_events ?? []).map((row) => {
    const twin = timeline.find(
      (entry) => entry.ref === row.event_id || entry.event_id === row.event_id,
    );
    return {
      ...row,
      ts: row.ts || row.timestamp_utc || twin?.ts || "",
      stage: twin?.stage ?? "",
      detail: twin?.detail ?? "",
      ledger_seq: typeof twin?.ledger_seq === "number" ? twin.ledger_seq : null,
    };
  });
  return rows.reverse();
}

/**
 * Colour one rail row by what the state view actually reported for it.
 *
 * The compat view labels each row with a stage (and a kind for the rows appended
 * from sealed detections) and carries no severity of its own for quiet events, so
 * the tint follows the label instead of guessing from the text.
 */
export function railTone(row: RailRow): string {
  const label = `${row.stage ?? ""} ${row.kind ?? ""} ${row.signal_type ?? ""}`.toLowerCase();
  if (label.includes("quarantine") || row.verified === false) return "var(--sev-moderate)";
  if (label.includes("detect") || detectionCount(row) > 0) return "var(--sev-critical)";
  return "var(--sev-mild)";
}

export function simEventPrefix(scenarioId: string, tag: string): string {
  return `evt_sim_${scenarioId}_${tag}_`;
}

export function campaignFor(scenarioId: string, tag: string): string {
  return `${SIMULATED_LABEL}-${scenarioId}-${tag}`;
}
