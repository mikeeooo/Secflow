// Mirrors backend/schemas.py. Keep field names identical to the API contract.

export type Decision = "Permit" | "Verify" | "Block";
export type DecisionSource = "confirmed_fraud_evidence" | "risk_policy" | "assessment_safeguard";
export type DecisionLabel = "Confirmed fraud evidence" | "Preventive risk block" | "Needs verification" | "Permitted";
export type Outcome =
  | "permitted"
  | "pending_verification"
  | "blocked_attempt"
  | "approved_after_review"
  | "rejected_after_review";
export type ReviewStatus = "not_applicable" | "pending" | "approved" | "rejected";
export type ComponentKey = "isolation_forest" | "lof" | "dbscan" | "rules";
export type AuthMethod = "biometric" | "password" | "otp" | "password_otp";

export interface PartyRef {
  id: string;
  name: string;
  kind: "account" | "counterparty";
}

export interface ComponentBrief {
  isolation_forest: number | null;
  lof: number | null;
  dbscan: number | null;
  rules: number | null;
}

export interface AssessmentSummary {
  cursor: number;
  request_id: string;
  origin: "baseline" | "simulation";
  producer: string | null;
  event_time: string;
  sender: PartyRef;
  recipient: PartyRef;
  amount: number;
  currency: string;
  risk_score: number | null;
  decision: Decision;
  decision_source: DecisionSource;
  decision_label: DecisionLabel;
  assessment_status: string;
  outcome: Outcome;
  review_status: ReviewStatus;
  components: ComponentBrief;
  evidence_ids: string[];
  corroborating_signals: string[];
}

export interface ComponentView {
  key: ComponentKey;
  label: string;
  score: number | null;
  weight: number;
  contribution: number | null;
  raw: number | null;
  status: string | null;
  detail: string;
}

export interface ReasonView {
  code: string;
  family: string;
  description: string;
  detail: string;
  weight: number;
  corroborating: boolean;
}

export interface EvidenceView {
  evidence_id: string;
  evidence_type: string;
  entity_type: string;
  entity_id: string;
  source: string;
  recorded_at: string;
  effective_from: string;
  effective_until: string | null;
  note: string;
}

export interface Thresholds {
  verify: number;
  block: number;
  min_corroborating_families: number;
  source: string;
}

export interface AssessmentDetail extends AssessmentSummary {
  explanation: string;
  status_notes: string[];
  component_details: ComponentView[];
  reasons: ReasonView[];
  evidence: EvidenceView[];
  thresholds: Thresholds;
  model_version: string | null;
  policy_version: string;
  operating_point_version: string;
  assessed_at: string;
  device_id: string;
  session_id: string;
  auth_method: string;
  ip_country: string;
  channel: string;
  facts: Record<string, unknown>;
  idempotent_replay: boolean;
}

export interface TimelineEntry {
  at: string;
  kind: string;
  title: string;
  detail: string | null;
}

export interface ReviewView {
  review_id: string;
  action: "approve" | "reject";
  reason: string;
  actor: string;
  created_at: string;
  original_decision: Decision;
  original_risk_score: number | null;
  resulting_outcome: Outcome;
}

export interface Investigation {
  assessment: AssessmentDetail;
  timeline: TimelineEntry[];
  reviews: ReviewView[];
  can_review: boolean;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AccountSummary {
  account_id: string;
  display_name: string;
  account_type: string;
  home_country: string;
  created_at: string;
  requests: number;
  flagged: number;
  last_activity: string | null;
  last_decision: Decision | null;
}

export interface StreamStatus {
  running: boolean;
  mode: "continuous" | "batch_5" | "batch_10" | "batch_20";
  interval_seconds: number;
  produced: number;
  failures: number;
  last_error: string | null;
  started_at: string | null;
  last_tick_at: string | null;
  owner: string;
}

export interface LiveFeed {
  items: AssessmentSummary[];
  next_cursor: number;
  stream: StreamStatus;
  simulation_time: string;
}

export interface TrendPoint {
  date: string;
  requests: number;
  permit: number;
  verify: number;
  block: number;
  mean_risk: number | null;
}

export interface Overview {
  totals: {
    assessed: number;
    baseline: number;
    simulations: number;
    permitted: number;
    needs_verification: number;
    preventive_blocks: number;
    confirmed_evidence_blocks: number;
    awaiting_review: number;
    reviewed: number;
  };
  outcomes: Record<string, number>;
  volumes: { completed: number; pending_verification: number; blocked_attempts: number; currency: string; note: string };
  trend: TrendPoint[];
  recent: AssessmentSummary[];
  review_queue: AssessmentSummary[];
  simulation_time: string;
  stream: StreamStatus;
}

export interface AccountDetail {
  account: { account_id: string; display_name: string; account_type: string; home_country: string; created_at: string };
  profile: {
    requests_sent: number;
    requests_received: number;
    median_amount: number | null;
    p90_amount: number | null;
    typical_hour: number | null;
    decisions: Partial<Record<Decision, number>>;
    top_recipients: (PartyRef & { payments: number })[];
    devices: { device_id: string; first_seen: string; last_seen: string; sign_ins: number }[];
  };
  context: {
    latest: { request_id: string; status: string; score: number; distance: number | null; cluster: number | null; at: string } | null;
    counts: Record<string, number>;
  };
  activity: AssessmentSummary[];
}

export interface PartyOption {
  id: string;
  name: string;
  kind: "account" | "counterparty";
  detail: string;
}

export interface SimulatorOptions {
  simulation_time: string;
  currencies: string[];
  auth_methods: AuthMethod[];
  countries: string[];
  flagged_beneficiaries: { evidence_id: string; id: string; name: string; evidence_type: string }[];
  sender: {
    account_id: string;
    home_country: string;
    known_devices: string[];
    recent_recipients: PartyRef[];
    median_amount: number | null;
  } | null;
}

export interface SimulationRequest {
  request_id: string;
  sender_id: string;
  recipient_id?: string | null;
  new_recipient_name?: string | null;
  amount: number;
  currency: "EUR";
  device_id: string | null;
  auth_method: AuthMethod;
  failed_login_attempts: number;
  ip_country: string;
  channel: "mobile_app" | "web";
}

export interface ReviewRequest {
  action: "approve" | "reject";
  reason: string;
  actor: string;
}

export interface Health {
  status: "ok" | "degraded";
  started_at: string;
  data: { source: string; dataset: string; requests: number; accounts: number; generator_version: string; seed: number };
  model: { loaded: boolean; version: string | null; error: string | null };
  policy: { version: string; operating_point: { verify: number; block: number; source: string } };
  state: { kind: string; simulations: number; reviews: number; persisted: boolean; shared_across_workers: boolean; note: string };
  stream: StreamStatus;
  simulation_time: string;
}

// The algorithms and evaluation payloads are large reports; the pages read them defensively.
export type Report = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export type DashboardWindow = "history" | "live";

export interface DashboardBucket {
  t: string;
  requests: number;
  permit: number;
  verify: number;
  block_risk: number;
  block_evidence: number;
  safeguard: number;
  outside_context: number;
  scored: number;
  completed_amount: number;
  pending_amount: number;
  blocked_amount: number;
  mean_isolation_forest: number | null;
  mean_lof: number | null;
  mean_rules: number | null;
  latency_mean_ms: number | null;
  latency_max_ms: number | null;
  risk_p50: number | null;
  risk_p90: number | null;
  risk_p99: number | null;
}

export interface Dashboard {
  window: DashboardWindow;
  label: string;
  bucket_seconds: number;
  range: { from: string; to: string };
  series: DashboardBucket[];
  totals: {
    requests: number;
    verify_rate: number | null;
    block_rate: number | null;
    outside_context_rate: number | null;
    preventive_blocks: number;
    evidence_blocks: number;
    latency_mean_ms: number | null;
    latency_p95_ms: number | null;
  };
  decision_sources: Record<string, number>;
  rule_triggers: { code: string; count: number; share: number }[];
  thresholds: { verify: number; block: number };
  goals: { max_verify_rate: number | null };
}

export interface GraphNode {
  id: string;
  kind: "cluster" | "core" | "anomaly";
  cluster: number | null;
  size?: number;
  request_id?: string;
  decision_label?: DecisionLabel;
  risk_score?: number | null;
  distance?: number;
  sender?: string;
  recipient?: string;
  amount?: number;
  event_time?: string;
  origin?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: "member" | "near" | "nearest" | "anomaly";
  distance: number;
  pairs: number;
}

export interface ClusterGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: { cluster: number; size: number; anomalies: number }[];
  summary: {
    clusters: number;
    core_samples: number;
    eps: number;
    min_samples: number;
    link_distance: number;
    near_links: number;
    nearest_links: number;
    training_noise_fraction: number | null;
    anomalies_total: number;
    anomalies_shown: number;
    note: string;
  };
}
