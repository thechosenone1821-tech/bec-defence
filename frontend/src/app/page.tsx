"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ConsoleHeader } from "@/components/shell/console-header";
import { ModeSwitcher } from "@/components/shell/mode-switcher";
import { CurvedCarousel } from "@/components/shell/curved-carousel";
import { Kicker } from "@/components/phosphor/primitives";
import { appsForMode, MODES } from "@/lib/apps";
import { useModeStore } from "@/lib/mode-store";

export default function Home() {
  const router = useRouter();
  const mode = useModeStore((s) => s.mode);
  const setLastApp = useModeStore((s) => s.setLastApp);
  const items = appsForMode(mode);

  const openApp = (app: (typeof items)[number]) => {
    setLastApp(mode, app.id);
    router.push(app.route);
  };

  return (
    <div className="flex min-h-screen flex-col ph-backdrop">
      <ConsoleHeader />

      <main className="flex flex-1 flex-col">
        {/* hero */}
        <section className="mx-auto flex w-full max-w-7xl flex-col items-center px-4 pt-10 text-center sm:pt-16">
          <Kicker phosphor>ARK OMNITEK · UNIFIED DEFENCE OPERATIONS</Kicker>
          <h1 className="mt-4 max-w-3xl text-balance text-3xl font-semibold leading-tight tracking-tight text-foreground sm:text-5xl">
            One phosphor console.
            <br />
            <span className="text-phosphor ph-glow-text">Every line of defence.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
            Choose your primary mode, then ride the carousel into the subapplication
            you need. Consumer applications guard the person; organization
            applications guard the network. Mode and context travel with you.
          </p>

          {/* the liquid glass primary mode switcher */}
          <div className="mt-10 flex flex-col items-center gap-4">
            <ModeSwitcher size={60} />
            <p
              className="max-w-md font-mono text-[11px] tracking-[0.18em] uppercase text-muted-foreground"
              aria-live="polite"
            >
              {MODES[mode].label} mode · {MODES[mode].blurb}
            </p>
          </div>
        </section>

        {/* 3D curved carousel */}
        <section aria-label="Subapplication carousel" className="mt-8 pb-8 sm:mt-10">
          {/* key={mode} swaps the whole arc when the mode changes, which is
              also what resets it to its head card */}
          <CurvedCarousel key={mode} items={items} mode={mode} onOpen={openApp} />
        </section>

        <p className="mx-auto max-w-7xl px-6 pb-10 text-center font-mono text-[11px] tracking-[0.16em] uppercase text-muted-foreground">
          Drag · trackpad swipe · arrow keys — Enter opens the selected application
        </p>
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
