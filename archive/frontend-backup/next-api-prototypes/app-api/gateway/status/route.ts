import { NextResponse } from "next/server";

/**
 * Aggregated backend health for the console status pills.
 * Never throws — each backend reports ok/unreachable independently.
 */

const CITIZEN_API_URL = (process.env.CITIZEN_API_URL || "http://127.0.0.1:8095").replace(/\/$/, "");
const SPINE_BUS_URL = (process.env.SPINE_BUS_URL || "http://127.0.0.1:8080").replace(/\/$/, "");

async function probe(url: string, timeoutMs: number) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal, cache: "no-store" });
    const text = await res.text();
    let info: Record<string, unknown> | null = null;
    try {
      info = text ? JSON.parse(text) : null;
    } catch {
      info = null;
    }
    return { ok: res.ok, info };
  } catch (e) {
    return { ok: false, detail: e instanceof Error ? e.message : String(e), info: null };
  } finally {
    clearTimeout(timer);
  }
}

export async function GET() {
  const [citizen, spine] = await Promise.all([
    probe(`${CITIZEN_API_URL}/api/citizen/health`, 4000),
    probe(`${SPINE_BUS_URL}/api/health`, 4000),
  ]);
  return NextResponse.json(
    { citizen, spine },
    { headers: { "Cache-Control": "no-store" } },
  );
}
