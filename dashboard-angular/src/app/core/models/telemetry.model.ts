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

export interface TrajectorySignal {
  active: boolean;
  signal_type: string;
  signal_label: string;
  trend_slope_per_min: number;
  delta_abs_pp: number;
  delta_rel_pct: number;
  trend_summary: string;
  trigger_reason: string | null;
  rules_violated_count: number;
  heuristic_severity: number;
}

export interface SentinelTimeline {
  t_zero_timestamp: number;
  elapsed_seconds: number;
  t_sentinel_offset_sec: number | null;
  t_sre_offset_sec: number | null;
  reference_origin: string;
}

export interface SentinelState {
  score: number;
  level: 'healthy' | 'warning' | 'critical' | 'mitigated';
  risk_state?: 'nominal' | 'early_warning' | 'critical';
  state_label?: string;
  triggered: boolean;
  trigger_reason: string | null;
  vector: SentinelVector;
  lead_time_seconds: number | null;
  lead_time_minutes: number | null;
  lead_time_status?: 'NOT_APPLICABLE' | 'OBSERVING_PENDING_BASELINE' | 'CONSOLIDATED' | 'NO_ANTICIPATION';
  lead_time_display?: string;
  lead_time_description?: string;
  trajectory_signal?: TrajectorySignal;
  timeline?: SentinelTimeline;
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

export interface MMcKMetrics {
  arrival_rate_tps: number;
  service_rate_per_sec: number;
  servers_c: number;
  capacity_k: number;
  traffic_intensity_rho: number;
  p_loss_ratio: number;
  p_loss_pct: number;
  l_q_expected: number;
  w_q_ms_expected: number;
  lambda_effective_tps: number;
}

export interface LoadConfig {
  target_tps: number;
  stochastic_mode: boolean;
  mode_label: string;
  system_capacity_k: number;
  servers_c: number;
  mmck_metrics?: MMcKMetrics;
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
  load_config?: LoadConfig;
  stream_meta: StreamMeta;
}
