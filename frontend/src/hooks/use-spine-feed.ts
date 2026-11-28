"use client";

import * as React from "react";
import { usePoll } from "@/hooks/use-poll";

/**
 * Live infrastructure feed for the Phosphor console.
 *
 * The uploaded prototype opened a cross-origin WebSocket to the bus and
 * quietly fell back to polling. The active Python gateway is same-origin,
 * read-only and already authenticates the backend call for the browser, so
 * this hook only polls the gateway's `/api/gateway/spine/api/state`
 * compatibility view. There is no socket to keep alive and no token in the
 * page — `source` therefore reports how fresh the data is, not a transport.
 */

export type SpineEvent = Record<string, unknown> & {
  event_id?: string;
  organ?: string;
  signal_type?: string;
  severity?: number;
  verified?: boolean;
  timestamp_utc?: string;
};

export type SpineFeedSource = "poll" | "off" | "connecting";

const MAX_EVENTS = 60;

export function useSpineFeed(pollMs = 4000) {
  const [events, setEvents] = React.useState<SpineEvent[]>([]);
  const [source, setSource] = React.useState<SpineFeedSource>("connecting");

  const load = React.useCallback(async () => {
    try {
      const res = await fetch("/api/gateway/spine/api/state", { cache: "no-store" });
      if (!res.ok) throw new Error(`state view returned ${res.status}`);
      const data = (await res.json()) as { recent_events?: SpineEvent[] };
      const recent = Array.isArray(data?.recent_events) ? data.recent_events : [];
      setEvents(recent.slice(-MAX_EVENTS));
      setSource("poll");
    } catch {
      setSource("off");
    }
  }, []);

  const { pending, refresh } = usePoll(load, { everyMs: pollMs });

  return { events, source, pending, refresh };
}
