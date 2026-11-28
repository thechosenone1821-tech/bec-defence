import { NextRequest, NextResponse } from "next/server";

/**
 * Citizen defence service gateway.
 *   /api/gateway/citizen/api/citizen/*  ->  {CITIZEN_API_URL}/api/citizen/*
 *
 * Same-origin for the browser, so the citizen service's CORS-disabled,
 * same-origin PWA posture is preserved without touching the backend.
 */

const CITIZEN_API_URL = (process.env.CITIZEN_API_URL || "http://127.0.0.1:8095").replace(/\/$/, "");

type Ctx = { params: Promise<{ path: string[] }> };

async function forward(req: NextRequest, ctx: Ctx, method: "GET" | "POST") {
  const { path } = await ctx.params;
  const target = `${CITIZEN_API_URL}/${path.join("/")}${req.nextUrl.search}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const body = method === "POST" ? await req.text() : undefined;
    const res = await fetch(target, {
      method,
      body,
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": "application/json", "X-Gateway-Target": "citizen" },
    });
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { error: "citizen service unreachable", detail },
      { status: 502, headers: { "X-Gateway-Target": "citizen" } },
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(req: NextRequest, ctx: Ctx) {
  return forward(req, ctx, "GET");
}

export async function POST(req: NextRequest, ctx: Ctx) {
  return forward(req, ctx, "POST");
}
