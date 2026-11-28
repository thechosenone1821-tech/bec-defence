"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { BAND_META, type SeverityBand } from "@/lib/gateway";

/** Mono uppercase kicker — the section label voice of the theme. */
export function Kicker({
  children,
  className,
  phosphor = false,
}: {
  children: React.ReactNode;
  className?: string;
  phosphor?: boolean;
}) {
  return (
    <p
      className={cn(
        "font-mono text-[11px] tracking-[0.22em] uppercase",
        phosphor ? "text-phosphor ph-glow-text" : "text-muted-foreground",
        className,
      )}
    >
      {children}
    </p>
  );
}

/** Layered surface panel with hairline border and corner ticks. */
export function PhosphorPanel({
  children,
  className,
  ticks = true,
  glow = false,
  as: Tag = "section",
}: {
  children: React.ReactNode;
  className?: string;
  ticks?: boolean;
  glow?: boolean;
  as?: "section" | "div" | "aside";
}) {
  return (
    <Tag
      className={cn(
        "rounded-lg border border-border bg-card/90 backdrop-blur-sm",
        ticks && "ph-ticks",
        glow && "ph-glow",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

/** Small live status pill with a phosphor dot. */
export function StatusPill({
  label,
  state,
  className,
}: {
  label: string;
  state: "ok" | "warn" | "down" | "idle";
  className?: string;
}) {
  const color =
    state === "ok"
      ? "bg-phosphor"
      : state === "warn"
        ? "bg-sev-moderate"
        : state === "down"
          ? "bg-sev-critical"
          : "bg-muted-foreground";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-border bg-secondary/80 px-3 py-1 font-mono text-[11px] tracking-[0.14em] uppercase text-muted-foreground",
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", color, state !== "idle" && "animate-pulse")} />
      {label}
    </span>
  );
}

/** Bordered metric tile. */
export function StatTile({
  label,
  value,
  hint,
  className,
  valueClass,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  className?: string;
  valueClass?: string;
}) {
  return (
    <div className={cn("rounded-md border border-border bg-secondary/60 px-4 py-3", className)}>
      <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-muted-foreground">
        {label}
      </p>
      <p className={cn("mt-1 font-mono text-xl text-phosphor ph-glow-text", valueClass)}>
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** Severity verdict card — band + word + icon, never colour alone. */
export function VerdictCard({
  band,
  title,
  reasons,
  action,
  disclaimer,
  className,
}: {
  band: SeverityBand;
  title?: string;
  reasons?: string[];
  action?: string;
  disclaimer?: string;
  className?: string;
}) {
  const meta = BAND_META[band];
  return (
    <div
      className={cn("rounded-md border border-border bg-secondary/50 p-5", className)}
      style={{ borderLeft: `4px solid ${meta.colorVar}` }}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="grid size-9 place-items-center rounded-md border font-mono text-lg"
          style={{ color: meta.colorVar, borderColor: meta.colorVar }}
        >
          {meta.icon}
        </span>
        <div className="min-w-0">
          <p className="font-mono text-sm tracking-[0.18em] uppercase" style={{ color: meta.colorVar }}>
            {title ? title : meta.label}
          </p>
          <p className="text-xs text-muted-foreground">{meta.tone}</p>
        </div>
      </div>
      {reasons && reasons.length > 0 ? (
        <ul className="mt-3 space-y-1.5 text-sm text-foreground/90">
          {reasons.map((r, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden="true" className="text-phosphor">›</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {action ? (
        <p className="mt-3 border-t border-border pt-3 font-mono text-xs tracking-wide text-phosphor">
          {action}
        </p>
      ) : null}
      {disclaimer ? <p className="mt-2 text-xs text-muted-foreground">{disclaimer}</p> : null}
    </div>
  );
}

/** Themed primary action — phosphor rim, not neon. */
export function PhosphorButton({
  children,
  className,
  variant = "solid",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "solid" | "ghost" | "danger";
}) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 font-mono text-xs font-medium tracking-[0.16em] uppercase transition-all duration-200 focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        variant === "solid" &&
          "border border-phosphor/60 bg-phosphor/10 text-phosphor-bright hover:bg-phosphor/20 hover:ph-glow active:translate-y-px",
        variant === "ghost" &&
          "border border-border bg-secondary/60 text-foreground/85 hover:border-phosphor/50 hover:text-phosphor-bright",
        variant === "danger" &&
          "border border-sev-critical/60 bg-sev-critical/10 text-sev-critical hover:bg-sev-critical/20",
        className,
      )}
    >
      {children}
    </button>
  );
}

/** Labelled control row used across the subapplications. */
export function Field({
  label,
  children,
  hint,
  className,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="font-mono text-[11px] tracking-[0.18em] uppercase text-muted-foreground">
          {label}
        </span>
        {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
      </span>
      {children}
    </label>
  );
}

/** Offline / unreachable notice — honest state, no fake data. */
export function BackendNotice({ detail, onRetry }: { detail?: string; onRetry?: () => void }) {
  return (
    <PhosphorPanel className="p-6" glow={false}>
      <div className="flex items-start gap-4">
        <span aria-hidden="true" className="mt-1 grid size-9 shrink-0 place-items-center rounded-md border border-sev-critical/50 font-mono text-sev-critical">
          ◌
        </span>
        <div className="min-w-0 flex-1">
          <Kicker phosphor>Service offline</Kicker>
          <p className="mt-1 text-sm text-foreground/85">
            The defence backend is not answering. Nothing is being faked while it is
            away — run the service and retry to see live verdicts.
          </p>
          {detail ? (
            <p className="mt-2 break-words font-mono text-xs text-muted-foreground">{detail}</p>
          ) : null}
          {onRetry ? (
            <PhosphorButton variant="ghost" className="mt-4" onClick={onRetry}>
              Retry connection
            </PhosphorButton>
          ) : null}
        </div>
      </div>
    </PhosphorPanel>
  );
}
