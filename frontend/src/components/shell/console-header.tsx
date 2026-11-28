"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { LiquidToggle } from "@/components/ui/liquid-glass-toggle";
import { ModeSwitcher, ModeToggleIcons } from "@/components/shell/mode-switcher";
import { StatusPill } from "@/components/phosphor/primitives";
import { gatewayStatus, type GatewayStatus } from "@/lib/gateway";
import { usePoll } from "@/hooks/use-poll";
import { useModeStore } from "@/lib/mode-store";
import { cn } from "@/lib/utils";

function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-6", className)} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#0A0B0C" stroke="#262626" />
      <path d="M16 6 25 21h-4.6L16 13.4 11.6 21H7L16 6Z" fill="#79C4B7" />
      <circle cx="16" cy="24" r="2" fill="#DAD1B9" />
    </svg>
  );
}

/**
 * Top chrome shared by the home shell and every subapplication. Carries the
 * compact Liquid Glass mode switcher (functional everywhere — switching from
 * a subapplication takes you into the new mode's default app, client-side)
 * and live backend status pills.
 */
export function ConsoleHeader({
  backLabel,
  className,
}: {
  backLabel?: string;
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const mode = useModeStore((s) => s.mode);
  const setMode = useModeStore((s) => s.setMode);
  const [status, setStatus] = React.useState<GatewayStatus | null>(null);
  const [checking, setChecking] = React.useState(false);

  const onAppPage = pathname?.startsWith("/console/");

  const load = React.useCallback(async () => {
    const res = await gatewayStatus();
    setStatus(res.ok ? res.data : null);
  }, []);

  /* the header only needs to know the services are up; 30s is plenty */
  const { pending: polling, refresh: reload } = usePoll(load, { everyMs: 30000 });

  const refresh = async () => {
    setChecking(true);
    try {
      await reload();
    } finally {
      setChecking(false);
    }
  };

  const switchModeAndGo = (on: boolean) => {
    const next = on ? "organization" : "consumer";
    if (next !== mode) {
      setMode(next);
      router.push(on ? "/console/rings" : "/console/call-screen");
    }
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md",
        className,
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:gap-5 sm:px-6">
        <Link
          href="/"
          className="group flex min-h-11 items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2"
        >
          <BrandMark />
          <span className="hidden flex-col leading-none sm:flex">
            <span className="font-mono text-[13px] font-semibold tracking-[0.3em] text-foreground">
              ARK OMNITEK
            </span>
            <span className="mt-1 font-mono text-[9px] tracking-[0.34em] text-muted-foreground">
              PHOSPHOR CONSOLE
            </span>
          </span>
        </Link>

        {onAppPage ? (
          <button
            type="button"
            onClick={() => router.push("/")}
            className="hidden min-h-9 items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 font-mono text-[11px] tracking-[0.14em] uppercase text-muted-foreground transition-colors hover:border-phosphor/50 hover:text-phosphor md:inline-flex"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            {backLabel ?? "Console"}
          </button>
        ) : null}

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden items-center gap-2 lg:flex">
            {status ? (
              <>
                <StatusPill
                  label={status.citizen.ok ? "citizen svc" : "citizen off"}
                  state={status.citizen.ok ? "ok" : "down"}
                />
                <StatusPill
                  label={status.spine.ok ? "spine bus" : "spine off"}
                  state={status.spine.ok ? "ok" : "down"}
                />
              </>
            ) : (
              <StatusPill label={polling ? "checking" : "no status"} state="idle" />
            )}
            <button
              type="button"
              onClick={refresh}
              aria-label="Re-check backend status"
              className="grid size-8 place-items-center rounded-full text-muted-foreground transition-colors hover:text-phosphor"
            >
              {checking ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <span aria-hidden="true" className="font-mono text-xs">↻</span>
              )}
            </button>
          </div>

          {/* compact liquid-glass switcher — same control, header scale */}
          <div className="hidden md:block">
            <LiquidToggle
              size={30}
              tone="dark"
              checked={mode === "organization"}
              onCheckedChange={switchModeAndGo}
              icons={{ off: ModeToggleIcons.consumer, on: ModeToggleIcons.organization }}
              label="Switch primary mode"
            />
          </div>
        </div>
      </div>
    </header>
  );
}

/** Re-exported for pages that want the labelled hero switcher instead. */
export { ModeSwitcher };
