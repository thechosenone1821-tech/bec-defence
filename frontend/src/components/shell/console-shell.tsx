"use client";

/**
 * Console shell for subapplication pages: header + mode dock + footer.
 * The dock lets operators jump between the current mode's subapplications
 * without returning to the home carousel (client-side navigation only).
 */
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConsoleHeader } from "@/components/shell/console-header";
import { appsForMode, findApp, MODES } from "@/lib/apps";
import { useModeStore } from "@/lib/mode-store";
import { cn } from "@/lib/utils";

export function ConsoleShell({
  appId,
  children,
}: {
  appId: string;
  children: React.ReactNode;
}) {
  const mode = useModeStore((s) => s.mode);
  const setMode = useModeStore((s) => s.setMode);
  const setLastApp = useModeStore((s) => s.setLastApp);
  const pathname = usePathname();
  const app = findApp(appId);
  const apps = appsForMode(mode);

  /* deep links win: the page you are on defines the primary mode, so the
     dock always matches the open subapplication */
  React.useEffect(() => {
    if (app && app.mode !== mode) setMode(app.mode);
    if (app) setLastApp(app.mode, app.id);
  }, [appId, pathname]);

  return (
    <div className="flex min-h-screen flex-col ph-backdrop">
      <ConsoleHeader />
      <nav
        aria-label="Subapplications in this mode"
        className="border-b border-border bg-panel/70"
      >
        <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2 ph-scroller sm:px-6">
          <span className="mr-2 hidden font-mono text-[10px] tracking-[0.28em] uppercase text-muted-foreground sm:block">
            {MODES[mode].label}
          </span>
          {apps.map((app) => {
            const Icon = app.icon;
            const active = app.id === appId;
            return (
              <Link
                key={app.id}
                href={app.route}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex min-h-9 shrink-0 items-center gap-2 rounded-md border px-3 font-mono text-[11px] tracking-[0.14em] uppercase transition-all duration-200",
                  active
                    ? "border-phosphor/60 bg-phosphor/10 text-phosphor-bright ph-glow"
                    : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {app.name}
              </Link>
            );
          })}
        </div>
      </nav>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        {children}
      </main>

      <footer className="mt-auto border-t border-border bg-panel/80">
        <div
          className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-2 px-4 py-4 font-mono text-[11px] tracking-wide text-muted-foreground sm:flex-row sm:items-center sm:px-6"
          style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
        >
          <span>ARK OMNITEK · PHOSPHOR CONSOLE</span>
          <span>
            Verdicts are advisory — in a live emergency call the national cybercrime
            helpline <a href="tel:1930" className="text-phosphor underline-offset-4 hover:underline">1930</a>
          </span>
        </div>
      </footer>
    </div>
  );
}
