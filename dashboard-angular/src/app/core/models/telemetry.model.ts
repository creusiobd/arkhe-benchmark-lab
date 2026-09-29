export interface ScenarioInfo {
  id: string;
  description: string;
  elapsed_seconds: number;
}

export interface RuntimeMetrics {
  event_loop_lag_ms: number;
}

export interface ResourcesMetrics {
  antifraud_pool_capacity: number;
  antifraud_pool_in_use: number;
  antifraud_pool_utilization_ratio: number;
  antifraud_waiters_count: number;
}

export interface QueueingMetrics {
  avg_queue_wait_ms: number;
  avg_service_time_ms: number;
  wq_ws_ratio: number;
}

export interface TrafficMetrics {
  unique_transactions_total: number;
  attempts_total: number;
  retry_amplification_ratio: number;
}

export interface LatencyMetrics {
  p50: number;
  p95: number;
  p99: number;
}

export interface OutcomesMetrics {
  approved: number;
  business_declined: number;
  technical_timeouts: number;
  pool_exhaustion_errors: number;
}

export interface ObservablesTelemetry {
  timestamp: number;
  runtime: RuntimeMetrics;
  resources: ResourcesMetrics;
  queueing: QueueingMetrics;
  traffic: TrafficMetrics;
  latency_ms: LatencyMetrics;
  outcomes: OutcomesMetrics;
}

export interface SentinelVector {
  rho_pool: number;
  d_rho_dt_per_min: number;
  wq_ws_ratio: number;
  avg_queue_wait_ms: number;
  retry_amplification: number;
}

export interface SentinelState {
  score: number;
  level: 'healthy' | 'warning' | 'critical' | 'mitigated';
  triggered: boolean;
  trigger_reason: string | null;
  vector: SentinelVector;
  lead_time_seconds: number;
  lead_time_minutes: number;
}

export interface SreGovernanceState {
  target_sla_availability_pct: number;
  current_sli_availability_pct: number;
  target_sla_latency_pct: number;
  current_sli_latency_pct: number;
  error_budget_remaining_pct: number;
  error_budget_consumed_pct: number;
  burn_rate: number;
  burn_rate_status: string;
  technical_errors_count: number;
  allowed_errors_count: number;
  traditional_alert_triggered: boolean;
}

export interface MitigationAction {
  timestamp: string;
  action: string;
  detail: string;
}

export interface MitigationState {
  enabled: boolean;
  active: boolean;
  fast_path_active: boolean;
  pool_capacity: number;
  prevented_failures: number;
  saved_error_budget_pct: number;
  downtime_avoided_min: number;
  actions: MitigationAction[];
}

export interface TopologyNode {
  id: string;
  label: string;
  role: string;
  icon: string;
  status: 'healthy' | 'warning' | 'critical' | 'mitigated';
  latency_ms: number;
  load: string;
  metrics: Record<string, any>;
}

export interface TopologyState {
  nodes: TopologyNode[];
}

export interface HorizonPoint {
  offset_sec: number;
  label: string;
  rho_expected: number;
  rho_upper: number;
  rho_lower: number;
  rho_mitigated: number;
}

export interface PastPoint {
  offset_sec: number;
  rho: number;
}

export interface ProjectionState {
  current_rho: number;
  d_rho_dt_per_min: number;
  time_to_collapse_sec: number | null;
  time_to_collapse_display: string;
  collapse_status: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  past_trajectory: PastPoint[];
  horizon_points: HorizonPoint[];
  stability_basin_limit: number;
  critical_rupture_limit: number;
}

export interface StageBreakdown {
  ingest_ms?: number;
  limits_ms?: number;
  antifraud_queue_ms?: number;
  antifraud_service_ms?: number;
  authorizer_ms?: number;
  ledger_ms?: number;
}

export interface RecentJourney {
  tx_id: string;
  attempt_id: string;
  card_token: string;
  amount_brl: number;
  timestamp: string;
  total_ms: number;
  status: 'AUTHORIZED' | 'DECLINED' | 'TIMEOUT_504' | 'ACQUIRER_503';
  sla_impact: string;
  stages: StageBreakdown;
}

export interface EventLog {
  timestamp: string;
  message: string;
  level: 'info' | 'warning' | 'danger' | 'success';
}

export interface StreamMeta {
  timestamp: number;
  protocol: string;
  frequency_hz: number;
}

export interface TelemetryPayload {
  scenario: ScenarioInfo;
  telemetry: ObservablesTelemetry;
  sentinel: SentinelState;
  sre_governance: SreGovernanceState;
  mitigation: MitigationState;
  topology: TopologyState;
  projection: ProjectionState;
  recent_journeys: RecentJourney[];
  event_logs: EventLog[];
  stream_meta: StreamMeta;
}
