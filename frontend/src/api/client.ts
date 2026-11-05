import type {
  ClusterGraph,
  Dashboard,
  DashboardWindow,
  AccountDetail,
  AccountSummary,
  AssessmentDetail,
  Health,
  Investigation,
  LiveFeed,
  Overview,
  Paged,
  PartyOption,
  Report,
  ReviewRequest,
  SimulationRequest,
  SimulatorOptions,
  StreamStatus,
  AssessmentSummary,
} from "./types";

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: FieldError[];

  constructor(status: number, code: string, message: string, fields: FieldError[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "network_error", "Can't reach the SecFlow server. Check that the backend is running.");
  }
  const text = await response.text();
  const body = text ? safeJson(text) : null;
  if (!response.ok) {
    const error = (body as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    const fields = Array.isArray(error?.details) ? (error.details as FieldError[]) : [];
    throw new ApiError(response.status, error?.code ?? "http_error", error?.message ?? `Request failed (${response.status})`, fields);
  }
  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

const post = (body?: unknown): RequestInit => ({ method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/api/health"),
  overview: () => request<Overview>("/api/overview"),
  transactions: (params: Record<string, string | number | undefined>) =>
    request<Paged<AssessmentSummary>>(`/api/transactions${query(params)}`),
  accounts: (params: Record<string, string | number | undefined>) =>
    request<Paged<AccountSummary>>(`/api/accounts${query(params)}`),
  account: (id: string) => request<AccountDetail>(`/api/accounts/${encodeURIComponent(id)}`),
  parties: (q: string, limit = 12) => request<PartyOption[]>(`/api/parties${query({ q, limit })}`),
  simulatorOptions: (senderId?: string) => request<SimulatorOptions>(`/api/simulator/options${query({ sender_id: senderId })}`),
  simulate: (body: SimulationRequest) => request<AssessmentDetail>("/api/simulations", post(body)),
  investigation: (id: string) => request<Investigation>(`/api/investigations/${encodeURIComponent(id)}`),
  review: (id: string, body: ReviewRequest) =>
    request<Investigation>(`/api/investigations/${encodeURIComponent(id)}/reviews`, post(body)),
  liveTransfers: (after: number, signal?: AbortSignal) =>
    request<LiveFeed>(`/api/live-transfers${query({ after, limit: 100 })}`, { signal }),
  streamStatus: () => request<StreamStatus>("/api/simulation-stream"),
  streamStart: () => request<StreamStatus>("/api/simulation-stream/start", post()),
  streamStop: () => request<StreamStatus>("/api/simulation-stream/stop", post()),
  streamMode: (mode: StreamStatus["mode"]) => request<StreamStatus>("/api/simulation-stream/mode", post({ mode })),
  algorithms: () => request<Report>("/api/algorithms"),
  evaluation: () => request<Report>("/api/evaluation"),
  dashboard: (window: DashboardWindow) => request<Dashboard>(`/api/dashboard${query({ window })}`),
  clusterGraph: (anomalies: number) => request<ClusterGraph>(`/api/algorithms/cluster-graph${query({ anomalies })}`),
};
