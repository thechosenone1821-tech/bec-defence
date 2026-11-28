import type { LucideIcon } from "lucide-react";
import {
  Radar,
  FlaskConical,
  Landmark,
  MessageSquareLock,
  Orbit,
  Swords,
  Scale,
} from "lucide-react";

/**
 * ARK OMNITEK — subapplication registry.
 *
 * Two primary modes, eight subapplications. Every entry is a real destination
 * backed by the shared Python gateway in packages/frontend/gateway.py — no placeholders.
 */

export type AppMode = "consumer" | "organization";

export type SubApp = {
  id: string;
  /** display name, exactly as specified by the product */
  name: string;
  /** mono kicker shown above the name */
  kicker: string;
  /** one-line caption under the name on the carousel card */
  caption: string;
  /** longer description used on the app pages */
  description: string;
  mode: AppMode;
  route: string;
  icon: LucideIcon;
  /** capability chips rendered on the card */
  capabilities: string[];
};

export const MODES: Record<
  AppMode,
  { label: string; blurb: string }
> = {
  consumer: {
    label: "Consumer",
    blurb: "Personal defence applications for citizens on the network edge.",
  },
  organization: {
    label: "Organization",
    blurb: "Ring-level defence, red-team replay and deterministic governance.",
  },
};

export const SUBAPPS: SubApp[] = [
  {
    id: "call-screen",
    name: "CALL SCREEN",
    kicker: "CONSUMER · 01",
    caption: "Fraud-script screen for pasted call transcripts.",
    description:
      "Paste the words a caller used. The deterministic MessageGuard screen checks the transcript for known fraud scripts and returns a plain-language, advisory verdict. No recording is made and no audio leaves this browser.",
    mode: "consumer",
    route: "/console/call-screen",
    icon: MessageSquareLock,
    capabilities: ["Pasted transcript", "en / hi / te", "Advisory only", "No recording"],
  },
  {
    id: "vigil",
    name: "VIGIL",
    kicker: "CONSUMER · 02",
    caption: "Fused risk verdict from every citizen signal.",
    description:
      "VIGIL fuses independent signals — transcript verdicts, message verdicts, campaign linkage, repeat contacts and your own doubt — into one bounded, inspectable risk verdict with plain-language reasons. It can say \"I don't know\": no signal is a LOW_CONFIDENCE band, never a reassuring \"safe\".",
    mode: "consumer",
    route: "/console/vigil",
    icon: Radar,
    capabilities: ["Noisy-OR fusion", "Plain-language reasons", "LOW_CONFIDENCE honest band"],
  },
  {
    id: "citizen-spine",
    name: "Citizen Spine",
    kicker: "CONSUMER · 03",
    caption: "One-tap signed reports into the shared spine.",
    description:
      "Citizen Spine is the report rail that files signed, tokenized incident reports into the shared defence spine — category and severity band only, never raw content — where they fuse with infrastructure evidence into a single campaign view.",
    mode: "consumer",
    route: "/console/citizen-spine",
    icon: Landmark,
    capabilities: ["HMAC-signed events", "No PII", "Campaign fusion", "1930 linkage"],
  },
  {
    id: "attack-lab",
    name: "Attack Lab",
    kicker: "SIMULATED SCENARIOS",
    caption: "Trigger scripted attacks · watch detection and response",
    description:
      "Eight scripted attack scenarios — suspicious logins, a ransomware sweep, a coordinated agent flood, a hostile document, an infrastructure anomaly, a kernel tamper, a staged exfiltration and one benign control. Every step is one synthetic event sent through the same signed ingest path a real organ uses, so the findings, quarantines, fusion, Governor decisions and ledger entries that follow are the runtime's own answers. Trigger one, watch the timeline move, reset and repeat.",
    mode: "organization",
    route: "/console/attack-lab",
    icon: FlaskConical,
    capabilities: [
      "Simulated telemetry",
      "Per-scenario trigger",
      "Live timeline",
      "Resettable runs",
      "Dry-run response",
    ],
  },
  {
    id: "message-guard",
    name: "Message Guard",
    kicker: "CONSUMER · 04",
    caption: "Scam-script screen for SMS and chat text.",
    description:
      "Message Guard scores suspicious messages against known scam-script families across English, Hindi and Telugu. Every verdict ships with an explanation and the 1930 helpline — and honest LOW_CONFIDENCE when there is too little text to judge.",
    mode: "consumer",
    route: "/console/message-guard",
    icon: MessageSquareLock,
    capabilities: ["en / hi / te", "Scam families", "Explanations", "Advisory only"],
  },
  {
    id: "rings",
    name: "Rings",
    kicker: "ORGANIZATION · 01",
    caption: "Organ liveness across the four defence rings.",
    description:
      "Rings is the fleet console for the four paired defence rings — perimeter & identity, AI & agent defence, endpoint & silicon, network fabric & self-healing. Watch organ liveness, run positive-control canaries, and use operator kill switches with Governor-approved tokens.",
    mode: "organization",
    route: "/console/rings",
    icon: Orbit,
    capabilities: ["8 organs · 4 rings", "Liveness states", "Canary sweep", "Halt / resume"],
  },
  {
    id: "red-team",
    name: "Red Team",
    kicker: "ORGANIZATION · 02",
    caption: "Sandbox-only multi-stage campaign replay.",
    description:
      "Red Team replays a sandbox campaign — from a scripted call report through document injection to ransomware — as signed organ telemetry through the same verification path real sensors use. A forged probe is submitted first to prove the bus holds unsigned evidence out of the AI path.",
    mode: "organization",
    route: "/console/red-team",
    icon: Swords,
    capabilities: ["Signed replay", "Forge probe first", "Campaign fusion", "Sandbox only"],
  },
  {
    id: "governance",
    name: "Governance",
    kicker: "ORGANIZATION · 03",
    caption: "Deterministic Governor, planner and ledger.",
    description:
      "Governance is the zero-AI policy plane: propose a minimum-disruption containment cut, watch the deterministic Governor approve or refuse it against budgets and Tier-0 locks, and read the hash-chained evidence ledger that seals every decision.",
    mode: "organization",
    route: "/console/governance",
    icon: Scale,
    capabilities: ["Blast-radius budgets", "Tier-0 locks", "Containment planner", "Hash-chained ledger"],
  },
];

export function appsForMode(mode: AppMode): SubApp[] {
  return SUBAPPS.filter((a) => a.mode === mode);
}

export function defaultAppForMode(mode: AppMode): SubApp {
  return appsForMode(mode)[0];
}

export function findApp(id: string): SubApp | undefined {
  return SUBAPPS.find((a) => a.id === id);
}
