"use client";

import { create } from "zustand";
import type { SeverityBand } from "@/lib/gateway";

/**
 * Cross-application session signals. Call Screen and Message Guard publish their
 * latest verdicts here; VIGIL fuses them into one risk verdict. In-memory
 * only — verdicts belong to the current console session, never persisted.
 */
export type SessionVerdict = {
  app: "call-screen" | "message-guard";
  band: SeverityBand;
  verdict: string;
  at: number;
  raw: Record<string, unknown>;
};

type SignalsState = {
  call: SessionVerdict | null;
  message: SessionVerdict | null;
  setCall: (v: SessionVerdict | null) => void;
  setMessage: (v: SessionVerdict | null) => void;
};

export const useSessionSignals = create<SignalsState>()((set) => ({
  call: null,
  message: null,
  setCall: (call) => set({ call }),
  setMessage: (message) => set({ message }),
}));
