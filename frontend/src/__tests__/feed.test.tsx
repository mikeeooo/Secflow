import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mergeFeed } from "../lib/useLiveFeed";
import { LiveTransfersPage } from "../pages/LiveTransfers";
import { mockFetch, renderAt, stream, summary } from "./helpers";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("mergeFeed", () => {
  it("drops duplicate records and keeps newest first", () => {
    const first = mergeFeed([], [summary("A", 1), summary("B", 2)]);
    const again = mergeFeed(first, [summary("B", 2), summary("C", 3), summary("C", 3)]);
    expect(again.map((i) => i.request_id)).toEqual(["C", "B", "A"]);
  });

  it("caps the retained history", () => {
    const many = Array.from({ length: 300 }, (_, i) => summary(`R${i}`, i));
    expect(mergeFeed([], many)).toHaveLength(150);
  });
});

describe("Live Transfers", () => {
  it("shows the backend stream and renders each record once across overlapping polls", async () => {
    mockFetch((url) => {
      if (url.startsWith("/api/live-transfers")) {
        return { body: { items: [summary("LIVE-1", 5), summary("LIVE-1", 5)], next_cursor: 5, stream: stream(true), simulation_time: "2026-10-28T10:00:00Z" } };
      }
      if (url.startsWith("/api/simulation-stream")) return { body: stream(true) };
      return { body: { policy: { operating_point: { verify: 61, block: 97, source: "validated" } } } };
    });
    renderAt(<LiveTransfersPage />);
    await waitFor(() => expect(screen.getAllByText(/Amara Okafor/).length).toBeGreaterThan(0));
    expect(screen.getAllByRole("button", { pressed: true })).toHaveLength(1);
    expect(await screen.findByText("Stream running")).toBeInTheDocument();
  });

  it("keeps Stop usable while feed requests fail", async () => {
    let stopped = false;
    const calls = mockFetch((url, init) => {
      if (url.startsWith("/api/live-transfers")) return { status: 503, body: { error: { code: "unavailable", message: "Feed down" } } };
      if (url === "/api/simulation-stream/stop" && init?.method === "POST") {
        stopped = true;
        return { body: stream(false) };
      }
      if (url.startsWith("/api/simulation-stream")) return { body: stream(!stopped) };
      return { status: 503, body: {} };
    });
    renderAt(<LiveTransfersPage />);
    expect(await screen.findByText(/Live updates are unavailable/)).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: /Stop/ }));
    await waitFor(() => expect(screen.getByText("Stream stopped")).toBeInTheDocument());
    expect(calls.some((c) => c.url === "/api/simulation-stream/stop" && c.init?.method === "POST")).toBe(true);
    expect(screen.getByRole("button", { name: /Start/ })).toBeEnabled();
  });

  it("keeps polling after an error and recovers", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let attempt = 0;
    mockFetch((url) => {
      if (url.startsWith("/api/live-transfers")) {
        attempt += 1;
        if (attempt === 1) return { status: 0 };
        return { body: { items: [summary("LIVE-9", 9)], next_cursor: 9, stream: stream(true), simulation_time: "2026-10-28T10:00:00Z" } };
      }
      if (url.startsWith("/api/health")) return { body: { policy: { operating_point: { verify: 61, block: 97, source: "validated" } } } };
      return { body: stream(true) };
    });
    renderAt(<LiveTransfersPage />);
    expect(await screen.findByText(/Live updates are unavailable/)).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(2_100); });
    await waitFor(() => expect(screen.queryByText(/Live updates are unavailable/)).not.toBeInTheDocument());
    expect(screen.getAllByText(/Harbor Lane Utilities/).length).toBeGreaterThan(0);
  });
});
