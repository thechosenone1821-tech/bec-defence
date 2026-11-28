"use client";

import * as React from "react";

/**
 * Shared polling hook for the console's read-only backend views.
 *
 * Every console surface reads the same-origin Python gateway, and each one
 * used to hand-roll the same "call an async loader in an effect, then again on
 * an interval" code. That shape is what React's new
 * `react-hooks/set-state-in-effect` rule complains about: a loader that marks
 * itself busy synchronously re-renders the component before the fetch even
 * starts. This hook keeps the one reviewed place where that is handled:
 *
 *   * the loader is stored in a ref and refreshed from an effect, so changing
 *     the callback identity never re-subscribes the interval;
 *   * the first pass starts with `await`, so no state is set synchronously in
 *     the effect body;
 *   * `pending` is derived from the pass counter, so a spinner can be shown
 *     for the mount-time pass without a pre-await `setState`;
 *   * unmount cancels the interval and the interval pass is what sets manual
 *     busy state, from a callback rather than from render or an effect body.
 */

export type PollOptions = {
  /** Milliseconds between passes. Pass `false` to poll once on mount only. */
  everyMs?: number | false;
  /** Disable polling entirely (useful while a mutation is in flight). */
  enabled?: boolean;
};

export function usePoll(
  loader: () => Promise<void>,
  { everyMs = 15000, enabled = true }: PollOptions = {},
) {
  const loaderRef = React.useRef(loader);
  const [passes, setPasses] = React.useState(0);
  const [manual, setManual] = React.useState(false);

  React.useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  React.useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const pass = async () => {
      try {
        await loaderRef.current();
      } finally {
        if (!cancelled) setPasses((n) => n + 1);
      }
    };
    void pass();
    const timer =
      everyMs === false ? null : setInterval(() => void pass(), everyMs);
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [enabled, everyMs]);

  /** Refresh on demand from an event handler. */
  const refresh = React.useCallback(async () => {
    setManual(true);
    try {
      await loaderRef.current();
    } finally {
      setManual(false);
      setPasses((n) => n + 1);
    }
  }, []);

  return { pending: manual || passes === 0, passes, refresh };
}
