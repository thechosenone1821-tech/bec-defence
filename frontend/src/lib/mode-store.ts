"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AppMode } from "@/lib/apps";

/**
 * Primary-mode store. The selected mode (and the last subapplication opened
 * in each mode) survives navigation between subapplications and full page
 * loads — the mode is a property of the operator session, not of one page.
 */
type ModeState = {
  mode: AppMode;
  lastApp: Record<AppMode, string>;
  setMode: (mode: AppMode) => void;
  setLastApp: (mode: AppMode, id: string) => void;
};

export const useModeStore = create<ModeState>()(
  persist(
    (set) => ({
      mode: "consumer",
      lastApp: { consumer: "", organization: "" },
      setMode: (mode) => set({ mode }),
      setLastApp: (mode, id) =>
        set((s) => ({ lastApp: { ...s.lastApp, [mode]: id } })),
    }),
    {
      name: "ark-omnitek-mode",
      version: 1,
    },
  ),
);
