"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import { METRIC_LABELS, formatDelta, statusColor } from "@/lib/format";
import type { MetricExplainer, ZoneStatusOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { DigitalTwin } from "./DigitalTwin";
import { EnvironmentChart } from "./EnvironmentChart";
import { ForecastChart } from "./ForecastChart";
import { IndicatorCard } from "./IndicatorCard";
import { WarningBar } from "./WarningBar";

export function MissionOverview() {
  const { overview, loading } = useApp();
  const [selectedZone, setSelectedZone] = useState<ZoneStatusOut | null>(null);
  const [envChart, setEnvChart] = useState<{
    chart: {
      time: string;
      label: string;
      co2_ppm: number;
      temperature_c: number;
      humidity_pct: number;
    }[];
    historical_averages: Record<string, { mean: number; stdev: number }>;
    deviations: { metric: string; severity: string; explanation: string }[];
    rr1_cached?: boolean;
  } | null>(null);
  const [zoneExplain, setZoneExplain] = useState<Record<string, MetricExplainer>>({});

  useEffect(() => {
    let cancelled = false;
    void api
      .getEnvironment()
      .then((env) => {
        if (!cancelled) {
          setEnvChart({
            chart: env.chart ?? [],
            historical_averages: env.historical_averages ?? {},
            deviations: env.deviations ?? [],
            rr1_cached: env.rr1_cached,
          });
        }
      })
      .catch(() => {
        if (!cancelled) setEnvChart(null);
      });
    void api
      .getExplainers()
      .then((e) => {
        if (!cancelled) setZoneExplain(e.zones);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [overview?.mission_day, overview?.nasa_import_loaded]);

  const primaryMetrics = useMemo(() => {
    if (!overview) return [];
    const order = [
      "sleep_h",
      "resting_hr",
      "reaction_time_ms",
      "fatigue",
      "co2_ppm",
      "temperature_c",
    ];
    return order
      .map((id) => overview.metrics.find((m) => m.metric === id))
      .filter(Boolean);
  }, [overview]);

  const humidity = overview?.metrics.find((m) => m.metric === "humidity_pct");

  if (loading && !overview) {
    return (
      <div className="flex h-full items-center justify-center text-aegis-muted">
        Loading mission overview…
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex h-full items-center justify-center text-aegis-muted">
        No overview data available.
      </div>
    );
  }

  const zoneHistory = overview.history.slice(-14).map((h) => ({
    day: h.mission_day,
    reaction_time_ms: h.reaction_time_ms,
    resting_hr: h.resting_hr,
    fatigue: h.fatigue,
    sleep_h: h.sleep_h,
  }));

  const zoneMetricKey =
    selectedZone?.zone === "head"
      ? "reaction_time_ms"
      : selectedZone?.zone === "torso"
        ? "resting_hr"
        : "fatigue";

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 pb-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-medium text-aegis-text">Digital Twin</h1>
          <p className="mt-2 text-[15px] text-aegis-muted">
            Full indicator view vs your personal baseline.
          </p>
        </div>
        <Link href="/" className="text-[11px] text-aegis-cyan hover:underline">
          ← Back to Today
        </Link>
      </div>
      <p className="text-[13px] leading-snug text-aegis-muted">
        Advisory support — not a diagnosis. Escalate via mission medical protocols if symptoms
        worsen.
      </p>

      {overview.environment_banner && (
        <div className="rounded border border-aegis-amber/40 bg-aegis-amber/5 px-3 py-2 text-[13px] leading-normal text-aegis-amber">
          {overview.environment_banner}
        </div>
      )}

      <div className="grid grid-cols-12 items-stretch gap-3">
        <div className="col-span-12 flex min-w-0 lg:col-span-5">
          <DigitalTwin
            zones={overview.zones}
            selectedZone={selectedZone?.zone ?? null}
            onSelectZone={(z) =>
              setSelectedZone((prev) => (prev?.zone === z.zone ? null : z))
            }
          />
        </div>

        <div className="col-span-12 flex min-w-0 flex-col gap-3 lg:col-span-7">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {primaryMetrics.map((m) => m && <IndicatorCard key={m.metric} metric={m} />)}
          </div>
          <ForecastChart forecast={overview.forecast} />
        </div>
      </div>

      {selectedZone && (
        <Panel
          title={`Zone detail — ${selectedZone.label}`}
          action={
            <button
              type="button"
              className="text-[10px] text-aegis-muted hover:text-aegis-cyan"
              onClick={() => setSelectedZone(null)}
            >
              Close
            </button>
          }
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="min-w-[200px] shrink-0">
              <div className="label-caps mb-1">Status</div>
              <div
                className="font-mono text-sm leading-snug"
                style={{ color: statusColor(selectedZone.status) }}
              >
                {selectedZone.status.toUpperCase()}
              </div>
              <div className="mt-1 text-[13px] leading-snug text-aegis-muted">
                {selectedZone.detail}
              </div>
              {zoneExplain[selectedZone.zone] && (
                <div className="mt-2 space-y-1 text-[13px] leading-snug text-aegis-muted">
                  <p>
                    <span className="text-aegis-text">What: </span>
                    {zoneExplain[selectedZone.zone].what}
                  </p>
                  <p>
                    <span className="text-aegis-text">In space: </span>
                    {zoneExplain[selectedZone.zone].why_space}
                  </p>
                  <p>
                    <span className="text-aegis-text">What helps: </span>
                    {zoneExplain[selectedZone.zone].what_helps}
                  </p>
                </div>
              )}
            </div>
            <div className="h-20 min-w-0 flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={zoneHistory} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="day" hide />
                  <YAxis hide domain={["auto", "auto"]} />
                  <Line
                    type="monotone"
                    dataKey={zoneMetricKey}
                    stroke="#55B8E8"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Panel>
      )}

      <WarningBar pattern={overview.combined_pattern} />

      {overview.nasa_import_loaded && envChart && (
        <EnvironmentChart
          series={envChart.chart}
          averages={envChart.historical_averages}
          deviations={envChart.deviations}
        />
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Panel title="Personal Baseline Comparison">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="text-aegis-muted">
                  <th className="pb-1.5 pr-3 font-normal">Metric</th>
                  <th className="pb-1.5 pr-3 font-normal">Latest</th>
                  <th className="pb-1.5 pr-3 font-normal">Base</th>
                  <th className="pb-1.5 font-normal">Δ</th>
                </tr>
              </thead>
              <tbody>
                {overview.metrics
                  .filter((m) =>
                    [
                      "sleep_h",
                      "resting_hr",
                      "reaction_time_ms",
                      "fatigue",
                      "humidity_pct",
                    ].includes(m.metric)
                  )
                  .map((m) => (
                    <tr key={m.metric} className="border-t border-aegis-border/60">
                      <td className="py-1.5 pr-3 whitespace-nowrap">
                        {METRIC_LABELS[m.metric]}
                      </td>
                      <td className="py-1.5 pr-3 font-mono whitespace-nowrap">{m.latest}</td>
                      <td className="py-1.5 pr-3 font-mono whitespace-nowrap text-aegis-muted">
                        {m.baseline}
                      </td>
                      <td
                        className="py-1.5 font-mono whitespace-nowrap"
                        style={{ color: statusColor(m.status) }}
                      >
                        {formatDelta(m.delta, m.unit)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {humidity && (
            <p className="mt-2 text-[12px] leading-snug text-aegis-muted">
              {overview.nasa_import_loaded
                ? "Humidity from NASA RR-1 historical ISS environmental telemetry (2014)."
                : "Humidity from synthetic environment fixture."}
            </p>
          )}
        </Panel>

        <Panel title="Recommended Next Action">
          <p className="mb-2 text-[14px] leading-relaxed text-aegis-text">
            {overview.combined_pattern.recommended_action}
          </p>
          {overview.deviations.length > 0 && (
            <ul className="space-y-1.5 text-[13px] leading-relaxed text-aegis-muted">
              {overview.deviations.map((d) => (
                <li key={d.metric} className="break-words">
                  • {d.explanation}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
