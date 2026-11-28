"use client";

/**
 * 3D Curved Carousel — subapplication navigation.
 *
 * Cards are positioned on a cylindrical arc with CSS 3D transforms
 * (`rotateY(θ) translateZ(R)`), so the row bends around an invisible
 * cylinder like the reference lens carousel: the active card faces the
 * viewer with a phosphor glow, side cards recede along the curve and dim.
 *
 * Interaction: pointer drag with momentum snap, trackpad/wheel horizontal
 * gestures, arrows/Home/End + Enter on the listbox, and click-to-focus /
 * click-again-to-open. When the primary mode changes the item set is
 * swapped with an enter/exit transition and the arc resets to its head.
 * Falls back gracefully: 3D transforms degrade to a flat row on browsers
 * without 3D support, and prefers-reduced-motion collapses the timing.
 */

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight, ArrowRight } from "lucide-react";
import type { SubApp } from "@/lib/apps";
import { MODES } from "@/lib/apps";
import { cn } from "@/lib/utils";

const STEP_BY_COUNT: Record<number, number> = { 2: 62, 3: 56, 4: 44, 5: 40, 6: 36 };
const MAX_VISIBLE_SIDE = 3; // cards beyond ±3 steps are not rendered

export function CurvedCarousel({
  items,
  mode,
  onOpen,
  className,
}: {
  items: SubApp[];
  mode: keyof typeof MODES;
  onOpen: (app: SubApp) => void;
  className?: string;
}) {
  const count = items.length;
  const step = STEP_BY_COUNT[count] ?? 44;
  /* the arc owns its own selection: the page remounts it with key={mode} when
     the mode swaps, so entering a new mode starts at the head without an
     effect that resets parent state */
  const [activeIndex, setActiveIndex] = React.useState(0);
  const onActiveChange = setActiveIndex;
  const [dragDeg, setDragDeg] = React.useState(0);
  const [dragging, setDragging] = React.useState(false);
  const [radius, setRadius] = React.useState(420);
  const viewportRef = React.useRef<HTMLDivElement>(null);
  const dragRef = React.useRef<{ id: number; startX: number; lastX: number; lastT: number; vel: number; moved: boolean } | null>(null);
  const suppressClick = React.useRef(false);
  const wheelLock = React.useRef(0);
  const wheelAcc = React.useRef(0);

  const active = Math.min(Math.max(activeIndex, 0), count - 1);

  /* responsive radius — keeps the arc inside the viewport on every size.
     ResizeObserver reports the initial box as it observes, so the first
     measurement arrives through the subscription callback. */
  React.useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setRadius(Math.max(240, Math.min(470, el.clientWidth * 0.44)));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const clampIndex = React.useCallback(
    (i: number) => Math.min(Math.max(i, 0), count - 1),
    [count],
  );

  const go = React.useCallback(
    (i: number) => onActiveChange(clampIndex(i)),
    [clampIndex, onActiveChange],
  );

  /* ---------------- pointer drag ---------------- */
  const onPointerDown = (e: React.PointerEvent) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    suppressClick.current = false;
    dragRef.current = { id: e.pointerId, startX: e.clientX, lastX: e.clientX, lastT: e.timeStamp, vel: 0, moved: false };
    setDragging(true);
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      /* capture is best-effort */
    }
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d || d.id !== e.pointerId) return;
    const dx = d.startX - e.clientX;
    if (!d.moved && Math.abs(dx) > 6) {
      d.moved = true;
      suppressClick.current = true; // a drag must never turn into a click-open
    }
    d.vel = (e.clientX - d.lastX) / Math.max(1, e.timeStamp - d.lastT);
    d.lastX = e.clientX;
    d.lastT = e.timeStamp;
    setDragDeg(dx * 0.22);
  };

  const endDrag = () => {
    const d = dragRef.current;
    setDragging(false);
    setDragDeg(0);
    dragRef.current = null;
    if (!d) return;
    const offsetDeg = (d.startX - d.lastX) * 0.22;
    const flick = Math.abs(d.vel) > 0.55;
    let next = active + Math.round(offsetDeg / step);
    if (flick && next === active) {
      next = active + (d.vel < 0 ? 1 : -1); // quick flick advances one
    }
    go(next);
  };

  const onClickCapture = (e: React.MouseEvent) => {
    if (suppressClick.current) {
      suppressClick.current = false;
      e.stopPropagation(); // swallow the click that follows a drag
    }
  };

  /* ---------------- wheel / trackpad ---------------- */
  const onWheelCapture = (e: React.WheelEvent) => {
    // Only react to horizontal intent so vertical page scroll is untouched.
    if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    e.preventDefault();
    const now = performance.now();
    if (now < wheelLock.current) return;
    wheelAcc.current += e.deltaX;
    if (Math.abs(wheelAcc.current) > 70) {
      go(active + (wheelAcc.current > 0 ? 1 : -1));
      wheelAcc.current = 0;
      wheelLock.current = now + 240;
    }
  };

  /* ---------------- keyboard ---------------- */
  const onKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowRight":
        e.preventDefault();
        go(active + 1);
        break;
      case "ArrowLeft":
        e.preventDefault();
        go(active - 1);
        break;
      case "Home":
        e.preventDefault();
        go(0);
        break;
      case "End":
        e.preventDefault();
        go(count - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        onOpen(items[active]);
        break;
    }
  };

  const activeApp = items[active];

  return (
    <div className={cn("w-full", className)}>
      {/* ---------------- the arc ---------------- */}
      <div
        ref={viewportRef}
        className="ph-perspective relative mx-auto h-[380px] w-full max-w-5xl select-none touch-pan-y sm:h-[430px]"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClickCapture={onClickCapture}
        onWheelCapture={onWheelCapture}
        onKeyDown={onKeyDown}
        tabIndex={0}
        role="listbox"
        aria-orientation="horizontal"
        aria-activedescendant={`carousel-item-${activeApp?.id}`}
        aria-label={`${MODES[mode].label} subapplications — arrows to move, Enter to open`}
      >
        <AnimatePresence initial={false}>
          {items.map((app, i) => {
            if (Math.abs(i - active) > MAX_VISIBLE_SIDE) return null;
            const delta = i - active + dragDeg / step;
            const theta = delta * step;
            const rad = (theta * Math.PI) / 180;
            const bow = (1 - Math.cos(rad)) * 46; // gentle lens curve
            const ad = Math.abs(delta);
            const isActive = i === active;
            const Icon = app.icon;
            return (
              <motion.div
                key={app.id}
                layout={false}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                id={`carousel-item-${app.id}`}
                role="option"
                aria-selected={isActive}
                aria-label={`${app.name} — ${app.caption}`}
                className={cn(
                  "absolute left-1/2 top-1/2 will-change-transform",
                  dragging ? "cursor-grabbing" : "cursor-grab",
                )}
                style={{
                  width: "min(78vw, 330px)",
                  transform: `translate(-50%, -50%) rotateY(${theta}deg) translateZ(${radius}px) translateY(${bow}px)`,
                  transition: dragging
                    ? "none"
                    : "transform 620ms cubic-bezier(0.22, 1, 0.36, 1), opacity 420ms ease, filter 420ms ease",
                  opacity: isActive ? 1 : Math.max(0.14, 0.62 - ad * 0.16),
                  filter: isActive ? "none" : `brightness(${Math.max(0.42, 0.9 - ad * 0.18)})`,
                  zIndex: 100 - Math.round(ad * 10),
                  pointerEvents: ad > 2.2 ? "none" : "auto",
                }}
                onClick={() => (isActive ? onOpen(app) : go(i))}
              >
                <div
                  className={cn(
                    "ph-ticks relative flex h-full flex-col justify-between overflow-hidden rounded-lg border bg-card/95 p-6 backdrop-blur-sm",
                    isActive
                      ? "border-phosphor/60 ph-glow"
                      : "border-border hover:border-phosphor/30",
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="font-mono text-[10px] tracking-[0.22em] uppercase text-muted-foreground">
                        {app.kicker}
                      </p>
                      <span
                        className={cn(
                          "font-mono text-[10px] tracking-[0.18em]",
                          isActive ? "text-phosphor" : "text-muted-foreground/60",
                        )}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <div
                      className={cn(
                        "mt-6 grid size-14 place-items-center rounded-md border transition-colors duration-300",
                        isActive
                          ? "border-phosphor/60 bg-phosphor/10 text-phosphor-bright ph-glow"
                          : "border-border bg-secondary/70 text-muted-foreground",
                      )}
                    >
                      <Icon className="size-7" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                    <h3
                      className={cn(
                        "mt-5 text-2xl font-semibold tracking-tight",
                        isActive ? "text-foreground ph-glow-text" : "text-foreground/70",
                      )}
                    >
                      {app.name}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {app.caption}
                    </p>
                  </div>
                  <div>
                    <div className="mt-6 flex flex-wrap gap-1.5">
                      {app.capabilities.map((c) => (
                        <span
                          key={c}
                          className="rounded-full border border-border bg-secondary/70 px-2.5 py-0.5 font-mono text-[10px] tracking-wide text-muted-foreground"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                    <div
                      className={cn(
                        "mt-5 flex items-center gap-2 font-mono text-[11px] tracking-[0.2em] uppercase transition-all duration-300",
                        isActive ? "text-phosphor opacity-100" : "opacity-0",
                      )}
                      aria-hidden={!isActive}
                    >
                      Open {app.name}
                      <ArrowRight className="size-3.5" aria-hidden="true" />
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* edge chevrons — quiet affordances, not navigation clutter */}
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => go(active - 1)}
          disabled={active === 0}
          aria-label="Previous subapplication"
          className="absolute left-0 top-1/2 z-[120] -translate-y-1/2 rounded-full border border-border bg-secondary/80 p-2.5 text-muted-foreground opacity-40 transition-all duration-300 hover:border-phosphor/50 hover:text-phosphor hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-0 sm:p-3"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => go(active + 1)}
          disabled={active === count - 1}
          aria-label="Next subapplication"
          className="absolute right-0 top-1/2 z-[120] -translate-y-1/2 rounded-full border border-border bg-secondary/80 p-2.5 text-muted-foreground opacity-40 transition-all duration-300 hover:border-phosphor/50 hover:text-phosphor hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-0 sm:p-3"
        >
          <ChevronRight className="size-4" aria-hidden="true" />
        </button>
      </div>

      {/* ---------------- caption + progress ---------------- */}
      <div className="mx-auto mt-2 flex max-w-5xl flex-col items-center gap-2 px-2 text-center sm:mt-4">
        <p className="font-mono text-[11px] tracking-[0.22em] uppercase text-phosphor ph-glow-text">
          {activeApp?.kicker}
        </p>
        <p className="text-lg text-foreground/90 sm:text-xl">{activeApp?.caption}</p>
        <p className="mt-1 font-mono text-xs tracking-[0.3em] text-muted-foreground" aria-hidden="true">
          {String(active + 1).padStart(2, "0")} / {String(count).padStart(2, "0")}
        </p>
        <div className="mt-1 flex gap-1.5" aria-hidden="true">
          {items.map((a, i) => (
            <span
              key={a.id}
              className={cn(
                "h-1 rounded-full transition-all duration-500",
                i === active ? "w-7 bg-phosphor" : "w-2.5 bg-border",
              )}
            />
          ))}
        </div>
        <p className="sr-only" aria-live="polite">
          {activeApp?.name} selected. Press Enter to open.
        </p>
      </div>
    </div>
  );
}
