"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

export function ForecastChart({ forecast }: { forecast: ForecastOut }) {
  const data = forecast.series.map((p) => ({
    day: p.mission_day,
    observed: p.kind === "observed" ? p.value : null,
    forecastVal: p.kind === "forecast" ? p.value : null,
  }));

  const lastObsIdx = forecast.series.map((p) => p.kind).lastIndexOf("observed");
  if (lastObsIdx >= 0 && lastObsIdx < data.length - 1) {
    data[lastObsIdx] = {
      ...data[lastObsIdx],
      forecastVal: forecast.series[lastObsIdx].value,
    };
  }

  const estimateColor =
    forecast.next_day_estimate - forecast.baseline_estimate >= 20 ? "#E6AD57" : "#53BE8B";

  return (
    <Panel
      title="24-Hour Cognitive Forecast"
      action={
        <span className="text-[11px] uppercase tracking-wide text-aegis-amber">
          Illustrative
        </span>
      }
      className="min-h-[280px] flex-1"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-stretch">
        <div className="min-w-0 flex-1 overflow-hidden">
          <div className="h-[190px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#8FA3B8", fontSize: 11 }}
                  tickFormatter={(v) => `D${v}`}
                  stroke="#2C4157"
                  height={22}
                />
                <YAxis
                  tick={{ fill: "#8FA3B8", fontSize: 11 }}
                  stroke="#2C4157"
                  domain={["auto", "auto"]}
                  width={36}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0B1420",
                    border: "1px solid #2C4157",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                  labelFormatter={(v) => `Mission day ${v}`}
                />
                <Legend
                  verticalAlign="bottom"
                  height={24}
                  wrapperStyle={{ fontSize: 12, paddingTop: 4 }}
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
                  dataKey="forecastVal"
                  name="Forecast"
                  stroke="#E6AD57"
                  strokeWidth={2}
                  strokeDasharray="5 4"
                  dot={{ r: 2, fill: "#E6AD57" }}
                  connectNulls
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-1 text-[12px] text-aegis-muted">
            {forecast.model_version} · reaction time (ms)
          </div>
        </div>

        <div className="flex w-full shrink-0 flex-col justify-center gap-1 rounded border border-aegis-border bg-aegis-bg/50 p-3 xl:w-[128px]">
          <div className="label-caps">Next-day</div>
          <div className="font-mono text-2xl leading-none" style={{ color: estimateColor }}>
            {forecast.next_day_estimate.toFixed(0)}
            <span className="ml-1 text-sm text-aegis-muted">ms</span>
          </div>
          <div className="font-mono text-[13px] text-aegis-muted">
            ±{forecast.uncertainty.toFixed(0)} ms
          </div>
          <div className="mt-2 border-t border-aegis-border pt-2 text-[12px] text-aegis-muted">
            Baseline {forecast.baseline_estimate.toFixed(0)} ms
          </div>
        </div>
      </div>
      <details className="mt-2 rounded border border-aegis-border/60 bg-aegis-bg/40 px-2.5 py-2">
        <summary className="cursor-pointer text-[13px] text-aegis-cyan">
          How this forecast works
        </summary>
        <p className="mt-1.5 text-[13px] leading-snug text-aegis-muted">
          Real local Ridge regression (scikit-learn) predicts next-day reaction time from recent
          sleep, fatigue, heart-rate deviation, prior RT, and cabin CO₂. Chronological train/test
          split; falls back to a rolling-mean trend if history is short. Illustrative only — trained
          on demo/crew-entered series, not a clinical model. Version: {forecast.model_version}.
        </p>
      </details>
    </Panel>
  );
}
