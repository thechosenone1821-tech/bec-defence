"use client";

/**
 * Primary mode switcher — Consumer ↔ Organization.
 *
 * Built on the Nimbus UI LiquidToggle (liquid-glass-toggle.tsx): a real water
 * drop that drags, stretches, snaps across the track and splashes into place.
 * The binary toggle maps directly onto the two primary modes, with the mode
 * word glowing phosphor on the active side. Keyboard: focus + Space/Enter/
 * arrows on the switch, or click the mode words themselves.
 */

import * as React from "react";
import { LiquidToggle } from "@/components/ui/liquid-glass-toggle";
import { UserRound, Building2 } from "lucide-react";
import { useModeStore } from "@/lib/mode-store";
import type { AppMode } from "@/lib/apps";
import { cn } from "@/lib/utils";

const ICON = (d: React.ReactNode) => (
  <svg
    viewBox="0 0 24 24"
    width="100%"
    height="100%"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {d}
  </svg>
);

export const ModeToggleIcons = {
  consumer: ICON(
    <>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M5 20c.8-3.6 3.6-5.6 7-5.6s6.2 2 7 5.6" />
    </>,
  ),
  organization: ICON(
    <>
      <path d="M4 20h16M6 20V9l6-4 6 4v11" />
      <path d="M10 20v-4h4v4M9.5 12h.01M14.5 12h.01" />
    </>,
  ),
};

function ModeWord({
  mode,
  label,
  active,
  onSelect,
  className,
}: {
  mode: AppMode;
  label: string;
  active: boolean;
  onSelect: (m: AppMode) => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(mode)}
      aria-pressed={active}
      className={cn(
        "min-h-11 rounded-full px-2 font-mono text-[11px] tracking-[0.24em] uppercase transition-all duration-500 focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 sm:px-3",
        active
          ? "text-phosphor-bright ph-glow-text"
          : "text-muted-foreground hover:text-foreground",
        className,
      )}
    >
      {label}
    </button>
  );
}

export function ModeSwitcher({
  size = 56,
  compact = false,
  className,
}: {
  /** track height in px — width is 2.1× (LiquidToggle geometry) */
  size?: number;
  compact?: boolean;
  className?: string;
}) {
  const mode = useModeStore((s) => s.mode);
  const setMode = useModeStore((s) => s.setMode);
  const checked = mode === "organization";

  return (
    <div
      className={cn("inline-flex items-center gap-1 sm:gap-2", className)}
      role="group"
      aria-label="Primary mode"
    >
      <ModeWord
        mode="consumer"
        label={compact ? "Consumer" : "Consumer"}
        active={mode === "consumer"}
        onSelect={setMode}
      />
      <LiquidToggle
        size={size}
        tone="dark"
        checked={checked}
        onCheckedChange={(on) => setMode(on ? "organization" : "consumer")}
        icons={{
          off: ModeToggleIcons.consumer,
          on: ModeToggleIcons.organization,
        }}
        label={`Switch primary mode, currently ${mode}`}
      />
      <ModeWord
        mode="organization"
        label="Organization"
        active={mode === "organization"}
        onSelect={setMode}
      />
    </div>
  );
}
