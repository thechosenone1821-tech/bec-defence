/**
 * Platform gateway client. All browser requests are same-origin and are served
 * by the shared Python gateway in packages/frontend/gateway.py. The gateway
 * injects scoped tokens, maps compatibility paths to active RAKSHA endpoints,
 * signs sandbox telemetry and never exposes backend credentials to the browser.
 */

export type GatewayError = {
  ok: false;
  status: number;
  error: string;
  detail?: string;
};

export type GatewayResult<T> = { ok: true; data: T } | GatewayError;

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<GatewayResult<T>> {
  const { timeoutMs = 20000, ...rest } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(path, {
      ...rest,
      signal: rest.signal ?? controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Gateway-Client": "phosphor-console",
        ...(rest.headers ?? {}),
      },
      cache: "no-store",
    });
    const text = await res.text();
    let payload: unknown = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = { raw: text };
    }
    if (!res.ok) {
      const p = payload as Record<string, unknown> | null;
      return {
        ok: false,
        status: res.status,
        error:
          (typeof p?.detail === "string" && p.detail) ||
          (typeof p?.reason === "string" && p.reason) ||
          (typeof p?.error === "string" && p.error) ||
          `gateway request failed (${res.status})`,
        detail: text.slice(0, 400),
      };
    }
    return { ok: true, data: payload as T };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      ok: false,
      status: 0,
      error:
        msg.toLowerCase().includes("abort")
          ? "backend did not answer in time"
          : "backend unreachable — check the defence services are running",
    };
  } finally {
    clearTimeout(timer);
  }
}

export const citizen = <T>(path: string, init?: RequestInit) =>
  request<T>(`/api/gateway/citizen${path}`, init);

export const spine = <T>(path: string, init?: RequestInit) =>
  request<T>(`/api/gateway/spine${path}`, init);

/** Per-event reply from the gateway batch: one runtime result per event. */
export type SpineSignedAck<TBody = Record<string, unknown>> = {
  accepted: number;
  received: number;
  unverified: number;
  results?: { status?: number; body?: TBody }[];
};

/**
 * Ask the Python gateway to sign events and ingest them through /api/ingest.
 * Signing stays server-side: the browser never holds the sensor key.
 */
export const spineSigned = <TBody = Record<string, unknown>>(events: unknown[]) =>
  request<SpineSignedAck<TBody>>("/api/gateway/spine-signed", {
    method: "POST",
    body: JSON.stringify(events),
    timeoutMs: 30000,
  });

export type GatewayStatus = {
  citizen: { ok: boolean; detail?: string; info?: Record<string, unknown> | null };
  spine: { ok: boolean; detail?: string; info?: Record<string, unknown> | null };
};

export const gatewayStatus = () => request<GatewayStatus>("/api/gateway/status");

export type SeverityBand = "LOW_CONFIDENCE" | "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export function bandFromVerdict(verdict?: string): SeverityBand {
  switch ((verdict ?? "").toUpperCase()) {
    case "LIKELY_SYNTHETIC":
    case "CRITICAL":
      return "CRITICAL";
    case "SUSPICIOUS":
    case "HIGH":
      return "HIGH";
    case "ELEVATED":
    case "MODERATE":
      return "MODERATE";
    case "SILENT":
    case "LOW":
      return "LOW";
    default:
      return "LOW_CONFIDENCE";
  }
}

export const BAND_META: Record<
  SeverityBand,
  { label: string; tone: string; icon: string; colorVar: string }
> = {
  LOW_CONFIDENCE: {
    label: "LOW CONFIDENCE",
    tone: "Not enough signal to judge — treated as unknown, never as safe.",
    icon: "◌",
    colorVar: "var(--muted-foreground)",
  },
  LOW: {
    label: "LOW",
    tone: "No known scam signal present.",
    icon: "·",
    colorVar: "var(--sev-mild)",
  },
  MODERATE: {
    label: "MODERATE",
    tone: "Some scam-script signals present. Stay cautious.",
    icon: "◆",
    colorVar: "var(--sev-moderate)",
  },
  HIGH: {
    label: "HIGH",
    tone: "Strong scam signals. Do not act before verifying.",
    icon: "▲",
    colorVar: "var(--sev-high)",
  },
  CRITICAL: {
    label: "CRITICAL",
    tone: "This matches a known fraud script. Stop and call 1930.",
    icon: "◼",
    colorVar: "var(--sev-critical)",
  },
};
