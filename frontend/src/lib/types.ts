export type DemoScenario = "stable" | "emerging_decline" | "recovery";
export type ZoneStatus = "green" | "amber" | "red";

export interface CrewMember {
  id: string;
  callsign: string;
  role: string;
  scenario_profile: string;
}

export interface HealthPoint {
  mission_day: number;
  sleep_h: number;
  resting_hr: number;
  fatigue: number;
  mood: number;
  reaction_time_ms: number;
  exercise_adherence: number;
  provenance: string;
}

export interface EnvironmentPoint {
  mission_day: number;
  co2_ppm: number;
  temperature_c: number;
  humidity_pct: number;
  provenance: string;
  source_label: string;
}

export interface MetricBaseline {
  metric: string;
  baseline: number;
  latest: number;
  delta: number;
  unit: string;
  status: ZoneStatus;
  sparkline: number[];
  provenance: string;
}

export interface ZoneStatusOut {
  zone: "head" | "torso" | "core";
  status: ZoneStatus;
  label: string;
  detail: string;
}

export interface DeviationOut {
  metric: string;
  direction: string;
  magnitude: number;
  consecutive_days: number;
  explanation: string;
}

export interface CombinedPatternOut {
  detected: boolean;
  severity: ZoneStatus;
  summary: string;
  contributing_metrics: string[];
  recommended_action: string;
}

export interface ForecastPoint {
  mission_day: number;
  value: number;
  kind: "observed" | "forecast";
  lower?: number | null;
  upper?: number | null;
}

export interface ForecastOut {
  next_day_estimate: number;
  baseline_estimate: number;
  uncertainty: number;
  model_version: string;
  disclaimer: string;
  series: ForecastPoint[];
  contributing_inputs: string[];
}

export interface HealthOverview {
  astronaut_id: string;
  mission_day: number;
  scenario: DemoScenario;
  history: HealthPoint[];
  environment: EnvironmentPoint[];
  metrics: MetricBaseline[];
  zones: ZoneStatusOut[];
  deviations: DeviationOut[];
  combined_pattern: CombinedPatternOut;
  forecast: ForecastOut;
  nasa_import_loaded: boolean;
  environment_banner?: string | null;
}

export interface DemoScenarioOut {
  scenario: DemoScenario;
  mission_day: number;
  label: string;
}

export interface TrendsResponse {
  astronaut_id: string;
  metric: string;
  label: string;
  unit: string;
  days: number;
  mission_day: number;
  baseline: number;
  latest: number;
  delta: number;
  provenance: string;
  explanation: string;
  series: { mission_day: number; value: number; kind: string; lower?: number; upper?: number }[];
  forecast: { mission_day: number; value: number; kind: string; lower?: number | null; upper?: number | null }[];
  forecast_summary: {
    next_day_estimate: number;
    uncertainty: number;
    baseline_estimate: number;
    model_version: string;
    disclaimer: string;
  };
  contributing_factors: { metric: string; text: string; magnitude: number }[];
}

export interface SimulateOut {
  current_estimate: number;
  hypothetical_estimate: number;
  delta_ms: number;
  delta_pct: number;
  drivers: string[];
  disclaimer: string;
  series_current: { t: number; label?: string; value: number }[];
  series_hypothetical: { t: number; label?: string; value: number }[];
}

export interface AssessmentOut {
  id: number;
  astronaut_id: string;
  mission_day: number;
  median_rt_ms: number;
  iqr_ms: number;
  provenance: string;
  message: string;
}

export interface ActionItem {
  id: string;
  severity: ZoneStatus;
  summary: string;
  do_label: string;
  do_href: string;
  escalate_label?: string | null;
  escalate_href?: string | null;
  reason: string;
}

export interface EmergencyStep {
  step: number;
  title: string;
  detail: string;
  href?: string | null;
}

export interface GuidanceOut {
  astronaut_id: string;
  alerts: {
    severity: string;
    summary: string;
    metrics?: string[];
    action?: string;
  }[];
  recommendations: string[];
  emergency_disclaimer: string;
  emergency_steps?: EmergencyStep[];
  when_to_escalate?: string[];
  assessment_complete: boolean;
  has_browser_assessment: boolean;
  actions?: ActionItem[];
  trust_line?: string;
}

export interface OperationTask {
  id: string;
  name: string;
  status: "ready" | "assessment_recommended" | "review_required";
  status_label: string;
  justification: string;
  action_label: string;
  gate?: "ready" | "caution" | "not_recommended";
  recheck_hint?: string;
}

export interface OperationsOut {
  astronaut_id: string;
  advisory_label: string;
  readiness_pct: number;
  tasks: OperationTask[];
  key_factors: string[];
  gate_summary?: string;
  trust_line?: string;
}

export interface CheckIn {
  id: number;
  astronaut_id: string;
  mission_day: number;
  sleep_h: number;
  fatigue: number;
  mood: number;
  resting_hr?: number | null;
  notes?: string | null;
  provenance: string;
  created_at: string;
}

export interface SymptomCheck {
  id: number;
  astronaut_id: string;
  mission_day: number;
  headache: number;
  congestion: number;
  dizziness: number;
  nausea: number;
  other_notes?: string | null;
  provenance: string;
  created_at: string;
  attention_needed: boolean;
}

export interface PromptItem {
  kind:
    | "morning_checkin"
    | "daily_assessment"
    | "symptom_check"
    | "weekly_assessment"
    | "pre_eva";
  title: string;
  message: string;
  href: string;
  urgency: "normal" | "high";
  due_label?: string;
}

export interface ReminderSlot {
  id: string;
  label: string;
  window: string;
  done: boolean;
  href: string;
  how_long: string;
}

export interface TodayMetric {
  metric: string;
  label: string;
  latest: number;
  baseline: number;
  delta: number;
  unit: string;
  status: ZoneStatus;
  plain: string;
}

export interface EnvContext {
  mode: "simulated" | "nasa_historical";
  nasa_cached: boolean;
  co2_ppm?: number | null;
  co2_status?: ZoneStatus | null;
  co2_baseline?: number | null;
  source_label: string;
  provenance: string;
  decision_blurb: string;
  science_note: string;
  replay_href: string;
}

export interface TodayOut {
  astronaut_id: string;
  mission_day: number;
  overall_status: ZoneStatus;
  plain_language: string;
  trust_line: string;
  impact_line?: string;
  top_metrics: TodayMetric[];
  primary_action: { id: string; label: string; href: string; reason: string };
  checkin: CheckIn | null;
  checkin_done: boolean;
  symptoms: SymptomCheck | null;
  prompts: PromptItem[];
  reminder_schedule?: ReminderSlot[];
  assessment_complete: boolean;
  has_browser_assessment: boolean;
  forecast_next_day_ms: number;
  forecast_model: string;
  forecast_blurb: string;
  env_context?: EnvContext | null;
}

export interface MetricExplainer {
  title: string;
  what: string;
  why_space: string;
  when_worry: string;
  what_helps: string;
}

export interface ExplainersOut {
  metrics: Record<string, MetricExplainer>;
  zones: Record<string, MetricExplainer>;
  trust_line: string;
  impact_line?: string;
  science_note?: string;
  citations?: { topic: string; note: string; anchor: string }[];
}

export interface TelemetryReport {
  id: string;
  astronaut_id: string;
  mission_day: number;
  status: "queued" | "sent";
  created_at: string;
  encrypted: boolean;
  sections: string[];
}

export interface TelemetryQueue {
  reports: TelemetryReport[];
  next_window_label: string;
  countdown_seconds: number;
  simulated: boolean;
}
