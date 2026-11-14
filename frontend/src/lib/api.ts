import type {
  AssessmentOut,
  CheckIn,
  CrewMember,
  DemoScenario,
  DemoScenarioOut,
  ExplainersOut,
  GuidanceOut,
  HealthOverview,
  OperationsOut,
  SimulateOut,
  SymptomCheck,
  TelemetryQueue,
  TelemetryReport,
  TodayOut,
  TrendsResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCrew: () => request<CrewMember[]>("/api/crew"),
  getHealth: (id: string) => request<HealthOverview>(`/api/health/${id}`),
  getScenario: () => request<DemoScenarioOut>("/api/demo/scenario"),
  setScenario: (scenario: DemoScenario) =>
    request<DemoScenarioOut>("/api/demo/scenario", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
  resetDemo: () =>
    request<DemoScenarioOut>("/api/demo/reset", {
      method: "POST",
      body: "{}",
    }),
  getTrends: (id: string, metric: string, days: number) =>
    request<TrendsResponse>(
      `/api/trends/${id}?metric=${encodeURIComponent(metric)}&days=${days}`
    ),
  simulate: (body: {
    astronaut_id: string;
    sleep_h: number;
    co2_ppm: number;
    fatigue?: number | null;
  }) =>
    request<SimulateOut>("/api/simulate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  submitAssessment: (body: {
    astronaut_id: string;
    median_rt_ms: number;
    iqr_ms: number;
    trial_count: number;
    invalid_count: number;
    trials: number[];
  }) =>
    request<AssessmentOut>("/api/assessments", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listAssessments: (id: string) =>
    request<
      {
        id: number;
        mission_day: number;
        median_rt_ms: number;
        iqr_ms: number;
        provenance: string;
        created_at: string;
      }[]
    >(`/api/assessments/${id}`),
  getGuidance: (id: string) => request<GuidanceOut>(`/api/guidance/${id}`),
  markAssessmentComplete: (id: string, complete = true) =>
    request<{ astronaut_id: string; assessment_complete: boolean }>(
      `/api/guidance/${id}/assessment-complete`,
      { method: "POST", body: JSON.stringify({ complete }) }
    ),
  getOperations: (id: string) => request<OperationsOut>(`/api/operations/${id}`),
  getTelemetryQueue: () => request<TelemetryQueue>("/api/telemetry/queue"),
  createTelemetryReport: (astronaut_id: string) =>
    request<TelemetryReport>("/api/telemetry/reports", {
      method: "POST",
      body: JSON.stringify({ astronaut_id }),
    }),
  simulateTransmission: () =>
    request<{ detail: string; transmitted: string[]; simulated: boolean }>(
      "/api/telemetry/simulate-transmission",
      { method: "POST", body: "{}" }
    ),
  exportReportUrl: (reportId: string) =>
    `${API_BASE}/api/telemetry/reports/${encodeURIComponent(reportId)}/export`,
  getEnvironment: () =>
    request<{
      nasa_import_loaded: boolean;
      rr1_cached?: boolean;
      banner: string | null;
      note: string;
      chart: {
        time: string;
        label: string;
        co2_ppm: number;
        temperature_c: number;
        humidity_pct: number;
      }[];
      historical_averages: Record<string, { mean: number; stdev: number; min: number; max: number; n: number }>;
      deviations: { metric: string; severity: string; explanation: string }[];
      disclaimer: string;
      points: unknown[];
    }>("/api/environment"),
  nasaMissions: () => request<any>("/api/nasa/missions"),
  nasaImport: (missionId: string) =>
    request<any>(`/api/nasa/import/${encodeURIComponent(missionId)}`, {
      method: "POST",
      body: "{}",
    }),
  nasaReplay: (missionId: string, at?: string) =>
    request<any>(
      `/api/nasa/replay/${encodeURIComponent(missionId)}${
        at ? `?at=${encodeURIComponent(at)}` : ""
      }`
    ),
  nasaSummary: (missionId: string, at?: string) =>
    request<any>(
      `/api/nasa/summary/${encodeURIComponent(missionId)}${
        at ? `?at=${encodeURIComponent(at)}` : ""
      }`
    ),
  nasaAnomalies: (missionId: string) =>
    request<any>(`/api/nasa/anomalies/${encodeURIComponent(missionId)}`),
  getEnvMode: () => request<any>("/api/nasa/env-mode"),
  setEnvMode: (mode: "simulated" | "nasa_historical") =>
    request<any>("/api/nasa/env-mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  getToday: (id: string) => request<TodayOut>(`/api/today/${id}`),
  submitCheckIn: (body: {
    astronaut_id: string;
    sleep_h: number;
    fatigue: number;
    mood: number;
    resting_hr?: number | null;
    notes?: string | null;
  }) =>
    request<CheckIn>("/api/checkins", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getCheckIn: (id: string) => request<CheckIn | null>(`/api/checkins/${id}`),
  submitSymptoms: (body: {
    astronaut_id: string;
    headache: number;
    congestion: number;
    dizziness: number;
    nausea: number;
    other_notes?: string | null;
  }) =>
    request<SymptomCheck>("/api/symptoms", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSymptoms: (id: string) => request<SymptomCheck | null>(`/api/symptoms/${id}`),
  snoozePrompt: (id: string, kind: string) =>
    request<{ snoozed: boolean }>(`/api/prompts/${id}/snooze`, {
      method: "POST",
      body: JSON.stringify({ kind }),
    }),
  getExplainers: () => request<ExplainersOut>("/api/explainers"),
};
