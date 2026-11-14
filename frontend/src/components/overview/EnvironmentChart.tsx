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
import { Panel } from "@/components/ui/Panel";

export interface EnvChartPoint {
  time: string;
  label: string;
  co2_ppm: number;
  temperature_c: number;
  humidity_pct: number;
}

export interface EnvDeviation {
  metric: string;
  severity: string;
  explanation: string;
}

export interface EnvAverages {
  co2_ppm?: { mean: number; stdev: number };
  temperature_c?: { mean: number; stdev: number };
  humidity_pct?: { mean: number; stdev: number };
}

export function EnvironmentChart({
  series,
  averages,
  deviations,
}: {
  series: EnvChartPoint[];
  averages: EnvAverages;
  deviations: EnvDeviation[];
}) {
  if (!series.length) {
    return (
      <Panel title="NASA RR-1 Environmental Trend">
        <p className="text-[11px] text-aegis-muted">
          No NASA RR-1 cache loaded. Environment chart unavailable without fabricating data.
        </p>
      </Panel>
    );
  }

  return (
    <Panel
      title="NASA RR-1 Environmental Trend"
      action={
        <span className="max-w-[260px] truncate text-[9px] uppercase tracking-wide text-aegis-cyan">
          RR-1 Historical — 2014
        </span>
      }
    >
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "#8FA3B8", fontSize: 9 }}
              stroke="#2C4157"
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis
              yAxisId="co2"
              tick={{ fill: "#8FA3B8", fontSize: 9 }}
              stroke="#2C4157"
              width={42}
              label={{ value: "CO₂", angle: -90, position: "insideLeft", fill: "#8FA3B8", fontSize: 9 }}
            />
            <YAxis
              yAxisId="th"
              orientation="right"
              tick={{ fill: "#8FA3B8", fontSize: 9 }}
              stroke="#2C4157"
              width={36}
            />
            <Tooltip
              contentStyle={{
                background: "#0B1420",
                border: "1px solid #2C4157",
                borderRadius: 6,
                fontSize: 11,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Line
              yAxisId="co2"
              type="monotone"
              dataKey="co2_ppm"
              name="CO₂ (ppm)"
              stroke="#55B8E8"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="th"
              type="monotone"
              dataKey="temperature_c"
              name="Temp (°C)"
              stroke="#E6AD57"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="th"
              type="monotone"
              dataKey="humidity_pct"
              name="Humidity (%)"
              stroke="#53BE8B"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {averages.co2_ppm && (
        <div className="mt-2 grid grid-cols-3 gap-2 text-[10px] text-aegis-muted">
          <div>
            Avg CO₂ <span className="font-mono text-aegis-text">{averages.co2_ppm.mean.toFixed(0)} ppm</span>
          </div>
          <div>
            Avg Temp{" "}
            <span className="font-mono text-aegis-text">
              {averages.temperature_c?.mean.toFixed(1)} °C
            </span>
          </div>
          <div>
            Avg RH{" "}
            <span className="font-mono text-aegis-text">
              {averages.humidity_pct?.mean.toFixed(1)} %
            </span>
          </div>
        </div>
      )}

      {deviations.length > 0 && (
        <ul className="mt-2 space-y-1.5 border-t border-aegis-border pt-2">
          {deviations.map((d) => (
            <li
              key={d.metric}
              className={`text-[10px] leading-snug ${
                d.severity === "red" ? "text-aegis-red" : "text-aegis-amber"
              }`}
            >
              {d.explanation}
            </li>
          ))}
        </ul>
      )}

    </Panel>
  );
}
