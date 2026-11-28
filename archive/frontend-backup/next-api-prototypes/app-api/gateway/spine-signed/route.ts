import { NextRequest, NextResponse } from "next/server";
import { signEvent } from "@/lib/event-signer";

/**
 * Signed ingest — the verified path into the spine bus.
 *
 * The Red Team application replays multi-stage campaign telemetry exactly the
 * way a real organ would: events are HMAC-signed at birth with the bus key and
 * POSTed to /api/ingest, where the bus verifies them through the normal path.
 * This route performs that signing server-side (the key never reaches the
 * browser) and forwards the batch.
 *
 * POST body: [event, ...]  ->  bus ingest ack {accepted, received, unverified}
 */

const SPINE_BUS_URL = (process.env.SPINE_BUS_URL || "http://127.0.0.1:8080").replace(/\/$/, "");

export async function POST(req: NextRequest) {
  let events: unknown[];
  try {
    const parsed = await req.json();
    events = Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return NextResponse.json({ error: "body must be a JSON event array" }, { status: 400 });
  }

  const signed = events.map((e) =>
    e && typeof e === "object" && !Array.isArray(e)
      ? signEvent(e as Record<string, unknown>)
      : e,
  );

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const res = await fetch(`${SPINE_BUS_URL}/api/ingest`, {
      method: "POST",
      body: JSON.stringify(signed),
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": "application/json", "X-Gateway-Target": "spine-signed" },
    });
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { error: "spine bus unreachable", detail },
      { status: 502, headers: { "X-Gateway-Target": "spine-signed" } },
    );
  } finally {
    clearTimeout(timer);
  }
}
