import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { AssessmentSummary, StreamStatus } from "../api/types";

export const POLL_MS = 2_000;
const KEEP = 150;

export interface LiveFeedState {
  items: AssessmentSummary[];
  fresh: Set<string>;
  stream: StreamStatus | null;
  simulationTime: string | null;
  error: unknown;
  failures: number;
  loaded: boolean;
}

/** Merge newest-first, de-duplicating by request ID (cursor overlap or retries never duplicate rows). */
export function mergeFeed(current: AssessmentSummary[], incoming: AssessmentSummary[]): AssessmentSummary[] {
  const seen = new Set(current.map((i) => i.request_id));
  const additions = incoming.filter((i) => !seen.has(i.request_id) && seen.add(i.request_id) !== undefined);
  return [...additions.sort((a, b) => b.cursor - a.cursor), ...current].slice(0, KEEP);
}

/**
 * Polls the backend feed roughly every two seconds. The browser never produces transfers;
 * it only reads what the single backend producer committed. Errors are surfaced and polling
 * continues, so the page recovers on its own.
 */
export function useLiveFeed(pollMs = POLL_MS): LiveFeedState {
  const [state, setState] = useState<LiveFeedState>({
    items: [], fresh: new Set(), stream: null, simulationTime: null, error: null, failures: 0, loaded: false,
  });
  const cursor = useRef(0);

  useEffect(() => {
    let timer: number | undefined;
    let controller: AbortController | undefined;
    let alive = true;
    const tick = async () => {
      controller = new AbortController();
      try {
        const feed = await api.liveTransfers(cursor.current, controller.signal);
        if (!alive) return;
        cursor.current = Math.max(cursor.current, feed.next_cursor);
        setState((s) => ({
          items: mergeFeed(s.items, feed.items),
          fresh: new Set(s.loaded ? feed.items.map((i) => i.request_id) : []),
          stream: feed.stream,
          simulationTime: feed.simulation_time,
          error: null,
          failures: 0,
          loaded: true,
        }));
      } catch (error) {
        if (!alive || (error instanceof DOMException && error.name === "AbortError")) return;
        setState((s) => ({ ...s, error, failures: s.failures + 1, loaded: true, fresh: new Set() }));
      }
      if (alive) timer = window.setTimeout(tick, pollMs);
    };
    void tick();
    return () => {
      alive = false;
      controller?.abort();
      window.clearTimeout(timer);
    };
  }, [pollMs]);

  return state;
}
