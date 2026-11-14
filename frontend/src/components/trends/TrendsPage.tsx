"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/Panel";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import { formatDelta, provenanceLabel } from "@/lib/format";
import type { TrendsResponse } from "@/lib/types";

const METRICS = [
  { value: "reaction_time_ms", label: "Reaction Time" },
  { value: "sleep_h", label: "Sleep" },
  { value: "resting_hr", label: "Heart Rate" },
  { value: "fatigue", label: "Fatigue" },
  { value: "co2_ppm", label: "Cabin CO₂" },
  { value: "temperature_c", label: "Temperature" },
  { value: "humidity_pct", label: "Humidity" },
];

const RANGES = [7, 14, 30, 60];

export function TrendsPage() {
  const { selectedCrewId, overview } = useApp();
  const [metric, setMetric] = useState("reaction_time_ms");
  const [days, setDays] = useState(14);
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await api.getTrends(selectedCrewId, metric, days);
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load trends");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedCrewId, metric, days, overview?.mission_day]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const map = new Map<number, Record<string, number | null>>();
    for (const p of data.series) {
      map.set(p.mission_day, {
        day: p.mission_day,
        observed: p.value,
        forecast: null,
        lower: null,
        upper: null,
      });
    }
    for (const p of data.forecast) {
      const prev = map.get(p.mission_day) ?? {
        day: p.mission_day,
        observed: null,
        forecast: null,
        lower: null,
        upper: null,
      };
      prev.forecast = p.value;
      prev.lower = p.lower ?? null;
      prev.upper = p.upper ?? null;
      map.set(p.mission_day, prev);
    }
    // Bridge last observed into forecast series
    const observedDays = data.series.map((s) => s.mission_day);
    if (observedDays.length && data.forecast.length) {
      const last = observedDays[observedDays.length - 1];
      const row = map.get(last);
      if (row) row.forecast = row.observed;
    }
    return Array.from(map.values()).sort((a, b) => Number(a.day) - Number(b.day));
  }, [data]);

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-medium text-aegis-text">Trends & Forecasts</h1>
          <p className="mt-2 text-[15px] text-aegis-muted">
            Personal baseline reference with illustrative forecast region.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded border border-aegis-border bg-aegis-panel px-2 py-1.5 text-[11px] text-aegis-text outline-none focus:border-aegis-cyan"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            {METRICS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          <div className="flex overflow-hidden rounded border border-aegis-border">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setDays(r)}
                className={`px-2.5 py-1.5 text-[11px] ${
                  days === r
                    ? "bg-aegis-cyan/20 text-aegis-cyan"
                    : "bg-aegis-panel text-aegis-muted hover:text-aegis-text"
                }`}
              >
                {r}D
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded border border-aegis-red/40 bg-aegis-red/10 px-3 py-2 text-[12px] text-aegis-red">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-3">
        <Panel
          className="col-span-12 lg:col-span-9 min-h-[360px]"
          title={`${data?.label ?? "Trend"} & Forecast`}
          action={
            <span className="text-[11px] uppercase tracking-wide text-aegis-amber">
              {data?.forecast_summary.disclaimer ?? "Illustrative"}
            </span>
          }
        >
          {loading && !data ? (
            <div className="flex h-[280px] items-center justify-center text-aegis-muted">Loading…</div>
          ) : (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#8FA3B8", fontSize: 10 }}
                    tickFormatter={(v) => `D${v}`}
                    stroke="#2C4157"
                  />
                  <YAxis
                    tick={{ fill: "#8FA3B8", fontSize: 10 }}
                    stroke="#2C4157"
                    width={42}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0B1420",
                      border: "1px solid #2C4157",
                      borderRadius: 6,
                      fontSize: 11,
                    }}
                    labelFormatter={(v) => `Mission day ${v}`}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {data && (
                    <ReferenceLine
                      y={data.baseline}
                      stroke="#8FA3B8"
                      strokeDasharray="4 4"
                      label={{ value: "Baseline", fill: "#8FA3B8", fontSize: 10 }}
                    />
                  )}
                  <Area
                    type="monotone"
                    dataKey="upper"
                    stroke="none"
                    fill="#E6AD57"
                    fillOpacity={0.12}
                    name="Uncertainty"
                    connectNulls
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="lower"
                    stroke="none"
                    fill="#0B1420"
                    fillOpacity={1}
                    legendType="none"
                    connectNulls
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="observed"
                    name="Observed"
                    stroke="#55B8E8"
                    strokeWidth={2}
                    dot={{ r: 2, fill: "#55B8E8" }}
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    name="Forecast"
                    stroke="#E6AD57"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    dot={{ r: 2, fill: "#E6AD57" }}
                    connectNulls
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
          {data && (
            <div className="mt-2 text-[13px] text-aegis-muted">
              Units: {data.unit} · Provenance: {provenanceLabel(data.provenance)} · Model{" "}
              {data.forecast_summary.model_version}
            </div>
          )}
        </Panel>

        <div className="col-span-12 flex flex-col gap-3 lg:col-span-3">
          <Panel title="Forecast Summary">
            {data ? (
              <div className="space-y-2 text-[15px]">
                <div className="flex justify-between gap-2">
                  <span className="text-aegis-muted">Next-day</span>
                  <span className="font-mono text-aegis-amber">
                    {data.forecast_summary.next_day_estimate.toFixed(0)} {data.unit}
                  </span>
                </div>
                <div className="flex justify-between gap-2">
                  <span className="text-aegis-muted">Uncertainty</span>
                  <span className="font-mono">±{data.forecast_summary.uncertainty.toFixed(0)}</span>
                </div>
                <div className="flex justify-between gap-2">
                  <span className="text-aegis-muted">Baseline</span>
                  <span className="font-mono">{data.baseline}</span>
                </div>
                <div className="flex justify-between gap-2 border-t border-aegis-border pt-2">
                  <span className="text-aegis-muted">Change</span>
                  <span className="font-mono text-aegis-amber">
                    {formatDelta(data.delta, data.unit)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[14px] text-aegis-muted">—</div>
            )}
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Panel title="Pattern Insight">
          <p className="text-[14px] leading-relaxed text-aegis-text">
            {data?.explanation ?? "Select a metric to view pattern insight."}
          </p>
        </Panel>
        <Panel title="Contributing Factors">
          {data && data.contributing_factors.length > 0 ? (
            <ul className="space-y-2 text-[14px] text-aegis-muted">
              {data.contributing_factors.map((f) => (
                <li key={f.metric + f.text} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-aegis-amber" />
                  <span className="leading-snug text-aegis-text">
                    {f.text.includes("_") ? f.text.replace(/_/g, " ") : f.text}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[14px] text-aegis-muted">No sustained adverse deviations flagged.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
