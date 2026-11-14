import type { ZoneStatus } from "./types";

export const METRIC_LABELS: Record<string, string> = {
  sleep_h: "Sleep",
  resting_hr: "Heart Rate",
  reaction_time_ms: "Reaction Time",
  fatigue: "Fatigue",
  co2_ppm: "CO₂",
  temperature_c: "Temperature",
  humidity_pct: "Humidity",
  mood: "Mood",
};

export function statusColor(status: ZoneStatus): string {
  if (status === "green") return "#53BE8B";
  if (status === "amber") return "#E6AD57";
  return "#D96767";
}

export function formatDelta(delta: number, unit: string): string {
  const sign = delta > 0 ? "+" : "";
  if (unit === "ppm") return `${sign}${Math.round(delta)} ppm`;
  if (unit === "ms" || unit === "bpm") return `${sign}${delta.toFixed(0)} ${unit}`;
  if (unit === "h") return `${sign}${delta.toFixed(1)} h`;
  if (unit === "°C") return `${sign}${delta.toFixed(1)} °C`;
  if (unit === "%") return `${sign}${delta.toFixed(1)}%`;
  if (unit === "/10") return `${sign}${delta.toFixed(1)}`;
  return `${sign}${delta.toFixed(1)}${unit ? ` ${unit}` : ""}`;
}

export function provenanceLabel(p: string): string {
  switch (p) {
    case "SIMULATED_CREW_DATA":
      return "SIMULATED CREW DATA";
    case "SYNTHETIC_ENVIRONMENT":
      return "SYNTHETIC ENVIRONMENT";
    case "NASA_HISTORICAL":
      return "NASA HISTORICAL";
    case "NASA_RR1_HISTORICAL":
      return "NASA RR-1 HISTORICAL (2014)";
    case "BROWSER_MEASURED":
      return "MEASURED IN BROWSER";
    case "CREW_ENTERED":
      return "CREW ENTERED";
    default:
      return p;
  }
}

export function statusPlain(status: ZoneStatus): string {
  if (status === "green") return "OK";
  if (status === "amber") return "Caution";
  return "Attention";
}

/** Map internal metric IDs / pattern tags to crew-facing labels. */
export function humanMetricLabel(raw: string): string {
  if (METRIC_LABELS[raw]) return METRIC_LABELS[raw];
  const aliases: Record<string, string> = {
    sleep: "Sleep",
    sleep_h: "Sleep",
    reaction_time: "Reaction time",
    reaction_time_ms: "Reaction time",
    cabin_co2: "Cabin CO₂",
    co2_ppm: "Cabin CO₂",
    resting_hr: "Heart rate",
    recent_reaction_time: "Recent reaction time",
    short_term_trend: "Short-term trend",
    resting_hr_deviation: "Heart-rate vs baseline",
  };
  if (aliases[raw]) return aliases[raw];
  return raw.replace(/_/g, " ");
}

export const SCENARIO_OPTIONS: {
  value: DemoScenarioValue;
  label: string;
  blurb: string;
}[] = [
  {
    value: "stable",
    label: "Stable Mission",
    blurb: "Healthy baseline — mostly Ready",
  },
  {
    value: "emerging_decline",
    label: "Emerging Decline",
    blurb: "Sleep ↓ + slower reactions — best live demo",
  },
  {
    value: "recovery",
    label: "Recovery After Assessment",
    blurb: "Improving after a rough stretch",
  },
];

type DemoScenarioValue = "stable" | "emerging_decline" | "recovery";

export const ONBOARDING_KEY = "aegis_onboarding_dismissed_v1";
export const GUIDE_KEY = "aegis_guide_active_v1";
