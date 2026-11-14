"use client";

import { Activity, Cloud, Droplets, Moon, Thermometer, Timer, Zap } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import type { MetricBaseline, MetricExplainer } from "@/lib/types";
import { METRIC_LABELS, formatDelta, provenanceLabel, statusColor } from "@/lib/format";
import { api } from "@/lib/api";

const ICONS: Record<string, ReactNode> = {
  sleep_h: <Moon size={11} strokeWidth={1.75} />,
  resting_hr: <Activity size={11} strokeWidth={1.75} />,
  reaction_time_ms: <Timer size={11} strokeWidth={1.75} />,
  fatigue: <Zap size={11} strokeWidth={1.75} />,
  co2_ppm: <Cloud size={11} strokeWidth={1.75} />,
  temperature_c: <Thermometer size={11} strokeWidth={1.75} />,
  humidity_pct: <Droplets size={11} strokeWidth={1.75} />,
};

let explainersCache: Record<string, MetricExplainer> | null = null;

export function IndicatorCard({ metric }: { metric: MetricBaseline }) {
  const data = metric.sparkline.map((v, i) => ({ i, v }));
  const label = METRIC_LABELS[metric.metric] ?? metric.metric;
  const deltaColor =
    metric.status === "green" ? "#53BE8B" : metric.status === "amber" ? "#E6AD57" : "#D96767";
  const [open, setOpen] = useState(false);
  const [explainer, setExplainer] = useState<MetricExplainer | null>(null);

  useEffect(() => {
    if (explainersCache) {
      setExplainer(explainersCache[metric.metric] ?? null);
      return;
    }
    void api
      .getExplainers()
      .then((e) => {
        explainersCache = e.metrics;
        setExplainer(e.metrics[metric.metric] ?? null);
      })
      .catch(() => undefined);
  }, [metric.metric]);

  const valueText =
    metric.metric === "co2_ppm"
      ? Math.round(metric.latest).toLocaleString()
      : metric.latest.toFixed(metric.unit === "ms" || metric.unit === "bpm" ? 0 : 1);

  return (
    <div
      className="flex min-h-[108px] min-w-0 flex-col justify-between overflow-hidden rounded border border-aegis-border bg-aegis-bg/40 p-3"
      title={`Provenance: ${provenanceLabel(metric.provenance)}`}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="label-caps truncate">{label}</span>
        <span className="shrink-0 text-aegis-muted">{ICONS[metric.metric] ?? null}</span>
      </button>

      <div className="flex min-w-0 items-end justify-between gap-3 py-2">
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5">
            <span
              className="font-mono text-[22px] tabular-nums leading-none"
              style={{ color: statusColor(metric.status) }}
            >
              {valueText}
            </span>
            <span className="pb-0.5 text-[12px] leading-none text-aegis-muted">{metric.unit}</span>
          </div>
          <div
            className="mt-2 font-mono text-[12px] leading-none tabular-nums"
            style={{ color: deltaColor }}
          >
            {formatDelta(metric.delta, metric.unit)} vs your baseline
          </div>
        </div>

        <div className="mb-0.5 h-8 w-[58px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <YAxis hide domain={["dataMin", "dataMax"]} />
              <Line
                type="monotone"
                dataKey="v"
                stroke="#55B8E8"
                strokeWidth={1.25}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="truncate pt-1 text-[12px] leading-none text-aegis-muted">
        your baseline {metric.baseline}
        {metric.unit}
        {explainer ? " · tap for why" : ""}
      </div>

      {open && explainer && (
        <div className="mt-2 space-y-1 border-t border-aegis-border pt-2 text-[12px] leading-snug text-aegis-muted">
          <p>
            <span className="text-aegis-text">What: </span>
            {explainer.what}
          </p>
          <p>
            <span className="text-aegis-text">In space: </span>
            {explainer.why_space}
          </p>
          <p>
            <span className="text-aegis-text">When to worry: </span>
            {explainer.when_worry}
          </p>
          <p>
            <span className="text-aegis-text">What helps: </span>
            {explainer.what_helps}
          </p>
        </div>
      )}
    </div>
  );
}
