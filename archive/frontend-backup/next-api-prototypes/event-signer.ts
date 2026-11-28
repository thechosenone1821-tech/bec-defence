/**
 * Canonical JSON + HMAC-SHA256 event signing, server-side.
 *
 * Replicates the spine's telemetry MAC contract exactly:
 *   mac = HMAC-SHA256(key, canonical_json(event_without_mac))
 * where canonical_json is Python's
 *   json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
 * (sorted keys, compact separators, ensure_ascii escaping).
 *
 * Events signed here traverse the bus's public ingest endpoint through the
 * *same verification path* as real organ telemetry — signed events are
 * verified and enter the attack graph; anything unsigned is held unverified.
 */

import { createHmac } from "crypto";

export const DEFAULT_SPINE_KEY = "eigenshield-dev-bus-key-change-in-production";

export function spineKey(): string {
  return process.env.SPINE_BUS_KEY || DEFAULT_SPINE_KEY;
}

/** Python-json.dumps-compatible canonical serialization. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") {
    if (Number.isInteger(value)) return String(value);
    if (!Number.isFinite(value)) return "null";
    return String(value); // JS shortest round-trip matches Python repr for our payloads
  }
  if (typeof value === "string") {
    // JSON.stringify escapes controls/quotes identically to Python; upgrade it
    // to ensure_ascii by escaping every non-ASCII code point.
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (c) => {
      const code = c.codePointAt(0) as number;
      if (code > 0xffff) {
        // surrogate pair — JSON.stringify already emits the pair escaped? no:
        // it emits the literal astral char, so escape both halves.
        const h = Math.floor((code - 0x10000) / 0x400) + 0xd800;
        const l = ((code - 0x10000) % 0x400) + 0xdc00;
        return `\\u${h.toString(16).padStart(4, "0")}\\u${l.toString(16).padStart(4, "0")}`;
      }
      return `\\u${code.toString(16).padStart(4, "0")}`;
    });
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => canonicalJson(v)).join(",")}]`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>).sort();
    const body = keys
      .filter((k) => (value as Record<string, unknown>)[k] !== undefined)
      .map((k) => `${JSON.stringify(k)}:${canonicalJson((value as Record<string, unknown>)[k])}`)
      .join(",");
    return `{${body}}`;
  }
  return "null";
}

export function signEvent(event: Record<string, unknown>): Record<string, unknown> {
  const clean = { ...event };
  delete clean.mac;
  delete clean.verified;
  const mac = createHmac("sha256", spineKey()).update(canonicalJson(clean)).digest("hex");
  return { ...clean, mac };
}
