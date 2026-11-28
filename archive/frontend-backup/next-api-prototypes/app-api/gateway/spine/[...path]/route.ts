import { NextRequest, NextResponse } from "next/server";

/**
 * Shared spine telemetry bus gateway.
 *   /api/gateway/spine/api/*  ->  {SPINE_BUS_URL}/api/*
 *
 * Carries state, fleet, ingest, containment, orchestrate and fleet
 * halt/resume through one same-origin surface for the organization apps.
 */

const SPINE_BUS_URL = (process.env.SPINE_BUS_URL || "http://127.0.0.1:8080").replace(/\/$/, "");

type Ctx = { params: Promise<{ path: string[] }> };

async function forward(req: NextRequest, ctx: Ctx, method: "GET" | "POST") {
  const { path } = await ctx.params;
  const target = `${SPINE_BUS_URL}/${path.join("/")}${req.nextUrl.search}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000); // orchestrate can think
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
      headers: { "Content-Type": "application/json", "X-Gateway-Target": "spine" },
    });
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { error: "spine bus unreachable", detail },
      { status: 502, headers: { "X-Gateway-Target": "spine" } },
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
