import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";
import type { AssessmentSummary, StreamStatus } from "../api/types";

export function renderAt(element: ReactElement, path = "/", pattern = "*") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={pattern} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export type Handler = (url: string, init?: RequestInit) => { status?: number; body?: unknown } | Promise<{ status?: number; body?: unknown }>;

export function mockFetch(handler: Handler) {
  const calls: { url: string; init?: RequestInit }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    const result = await handler(url, init);
    const status = result.status ?? 200;
    if (status === 0) throw new TypeError("Failed to fetch");
    return new Response(result.body === undefined ? "" : JSON.stringify(result.body), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return calls;
}

export const stream = (running: boolean): StreamStatus => ({
  running, mode: "continuous", interval_seconds: 2, produced: 3, failures: 0, last_error: null,
  started_at: null, last_tick_at: null, owner: "backend",
});

export function summary(id: string, cursor: number, overrides: Partial<AssessmentSummary> = {}): AssessmentSummary {
  return {
    cursor, request_id: id, origin: "simulation", producer: "stream", event_time: "2026-10-28T10:00:00Z",
    sender: { id: "ACC-0001", name: "Amara Okafor", kind: "account" },
    recipient: { id: "CP-00001", name: "Harbor Lane Utilities", kind: "counterparty" },
    amount: 42.5, currency: "EUR", risk_score: 31.2, decision: "Permit", decision_source: "risk_policy",
    decision_label: "Permitted", assessment_status: "assessed", outcome: "permitted", review_status: "not_applicable",
    components: { isolation_forest: 0.4, lof: 0.3, dbscan: 0, rules: 0.1 }, evidence_ids: [], corroborating_signals: [],
    ...overrides,
  };
}
