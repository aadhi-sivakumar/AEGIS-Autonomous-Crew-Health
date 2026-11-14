"use client";

import { useCallback, useEffect, useState } from "react";
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
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import type { SimulateOut } from "@/lib/types";

export function WhatIfPage() {
  const { selectedCrewId, overview } = useApp();

  const sleepMetric = overview?.metrics.find((m) => m.metric === "sleep_h");
  const co2Metric = overview?.metrics.find((m) => m.metric === "co2_ppm");
  const fatigueMetric = overview?.metrics.find((m) => m.metric === "fatigue");

  const [sleep, setSleep] = useState(7.0);
  const [co2, setCo2] = useState(1000);
  const [fatigue, setFatigue] = useState(4);
  const [includeFatigue, setIncludeFatigue] = useState(true);
  const [result, setResult] = useState<SimulateOut | null>(null);
  const [compare, setCompare] = useState<SimulateOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [nasaCo2, setNasaCo2] = useState<number | null>(null);

  const loadNasaCo2 = async (silent = false) => {
    try {
      const summary = await api.nasaSummary("RR-1");
      const v = summary?.telemetry?.co2_iss ?? summary?.metrics?.co2_iss?.value ?? null;
      if (v == null) {
        if (!silent) {
          setError("NASA CO₂ unavailable — import RR-1 on NASA Mission Replay first.");
        }
        return;
      }
      setNasaCo2(Number(v));
      setCo2(Math.min(3500, Math.max(500, Math.round(Number(v)))));
      if (!silent) setError(null);
    } catch (e) {
      if (!silent) {
        setError(e instanceof Error ? e.message : "Failed to load NASA CO₂");
      }
    }
  };

  // Seed sliders from current conditions when overview loads
  useEffect(() => {
    if (sleepMetric) setSleep(Number(sleepMetric.latest.toFixed(1)));
    if (co2Metric) setCo2(Math.round(co2Metric.latest));
    if (fatigueMetric) setFatigue(Math.round(fatigueMetric.latest));
  }, [sleepMetric?.latest, co2Metric?.latest, fatigueMetric?.latest]);

  // Auto-pull NASA RR-1 CO₂ so the What-If wow beat is one click less for judges.
  useEffect(() => {
    void loadNasaCo2(true);
  }, []);

  const runSimulate = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const out = await api.simulate({
        astronaut_id: selectedCrewId,
        sleep_h: sleep,
        co2_ppm: co2,
        fatigue: includeFatigue ? fatigue : null,
      });
      setResult(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }, [selectedCrewId, sleep, co2, fatigue, includeFatigue]);

  useEffect(() => {
    const t = setTimeout(() => {
      void runSimulate();
    }, 180);
    return () => clearTimeout(t);
  }, [runSimulate]);

  const resetToCurrent = () => {
    if (sleepMetric) setSleep(Number(sleepMetric.latest.toFixed(1)));
    if (co2Metric) setCo2(Math.round(co2Metric.latest));
    if (fatigueMetric) setFatigue(Math.round(fatigueMetric.latest));
    setCompare(null);
  };

  const saveCompare = () => {
    if (result) setCompare(result);
  };

  const chartData =
    result?.series_current.map((c, i) => ({
      label: c.label ?? `+${c.t}h`,
      current: c.value,
      adjusted: result.series_hypothetical[i]?.value ?? null,
      compare: compare?.series_hypothetical[i]?.value ?? null,
    })) ?? [];

  const improved = result ? result.delta_ms < 0 : false;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3">
      <div>
        <h1 className="text-lg font-medium text-aegis-text">What-If Mission Simulator</h1>
        <p className="mt-2 text-[15px] text-aegis-muted">
          Explore how sleep, fatigue, and CO₂ may affect next-day reaction time.
        </p>
      </div>

      {error && (
        <div className="rounded border border-aegis-red/40 bg-aegis-red/10 px-3 py-2 text-[12px] text-aegis-red">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-3">
        <Panel title="Adjust Conditions" className="col-span-12 lg:col-span-5">
          <div className="space-y-6">
            <SliderRow
              label="Average Nightly Sleep"
              valueLabel={`${sleep.toFixed(1)} h`}
              min={4}
              max={9}
              step={0.1}
              value={sleep}
              onChange={setSleep}
            />
            <SliderRow
              label="Cabin CO₂ Concentration"
              valueLabel={`${Math.round(co2).toLocaleString()} ppm`}
              min={500}
              max={3500}
              step={10}
              value={co2}
              onChange={setCo2}
            />
            <div className="rounded border border-aegis-border/80 bg-aegis-bg/40 px-2 py-2 text-[13px] text-aegis-muted">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  NASA RR-1 CO₂:{" "}
                  <span className="font-mono text-aegis-cyan">
                    {nasaCo2 == null ? "…" : `${Math.round(nasaCo2).toLocaleString()} ppm`}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => void loadNasaCo2(false)}
                  className="rounded border border-aegis-cyan/40 px-2 py-0.5 text-aegis-cyan hover:bg-aegis-cyan/10"
                >
                  Load into slider
                </button>
              </div>
            </div>
            <div>
              <label className="mb-2 flex items-center gap-2 text-[14px] text-aegis-muted">
                <input
                  type="checkbox"
                  checked={includeFatigue}
                  onChange={(e) => setIncludeFatigue(e.target.checked)}
                />
                Include fatigue score
              </label>
              <SliderRow
                label="Fatigue Score (1–10)"
                valueLabel={`${fatigue}`}
                min={1}
                max={10}
                step={1}
                value={fatigue}
                onChange={setFatigue}
                disabled={!includeFatigue}
              />
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <button
                type="button"
                onClick={resetToCurrent}
                className="rounded border border-aegis-border px-3 py-1.5 text-[14px] text-aegis-muted hover:border-aegis-cyan hover:text-aegis-cyan"
              >
                Reset to Current Scenario
              </button>
              <button
                type="button"
                onClick={saveCompare}
                className="rounded border border-aegis-cyan/40 bg-aegis-cyan/10 px-3 py-1.5 text-[14px] text-aegis-cyan"
              >
                Compare Scenarios
              </button>
            </div>
          </div>
        </Panel>

        <Panel title="Projected Reaction Time (Next 24 h)" className="col-span-12 lg:col-span-7">
          {result ? (
            <>
              <div className="mb-4 flex flex-wrap items-end gap-6">
                <div>
                  <div className="label-caps mb-1">Current Conditions</div>
                  <div className="font-mono text-2xl text-aegis-amber">
                    {result.current_estimate.toFixed(0)}
                    <span className="ml-1 text-sm text-aegis-muted">ms</span>
                  </div>
                </div>
                <div className="pb-1 text-aegis-muted">→</div>
                <div>
                  <div className="label-caps mb-1">Adjusted Scenario</div>
                  <div
                    className="font-mono text-2xl"
                    style={{ color: improved ? "#53BE8B" : "#E6AD57" }}
                  >
                    {result.hypothetical_estimate.toFixed(0)}
                    <span className="ml-1 text-sm text-aegis-muted">ms</span>
                  </div>
                </div>
                <div
                  className={`rounded border px-2 py-1 font-mono text-[14px] ${
                    improved
                      ? "border-aegis-green/40 text-aegis-green"
                      : "border-aegis-amber/40 text-aegis-amber"
                  }`}
                >
                  {result.delta_ms > 0 ? "+" : ""}
                  {result.delta_ms.toFixed(0)} ms ({result.delta_pct > 0 ? "+" : ""}
                  {result.delta_pct.toFixed(0)}%)
                </div>
                {busy && <span className="text-[13px] text-aegis-muted">Updating…</span>}
              </div>

              <div className="h-[220px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: "#8FA3B8", fontSize: 12 }} stroke="#2C4157" />
                    <YAxis
                      tick={{ fill: "#8FA3B8", fontSize: 12 }}
                      stroke="#2C4157"
                      width={36}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0B1420",
                        border: "1px solid #2C4157",
                        borderRadius: 6,
                        fontSize: 13,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line
                      type="monotone"
                      dataKey="current"
                      name="Current (baseline)"
                      stroke="#E6AD57"
                      strokeDasharray="5 4"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="adjusted"
                      name="Adjusted"
                      stroke="#53BE8B"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                    {compare && (
                      <Line
                        type="monotone"
                        dataKey="compare"
                        name="Saved compare"
                        stroke="#55B8E8"
                        strokeWidth={1.5}
                        strokeDasharray="2 3"
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded border border-aegis-border bg-aegis-bg/40 p-3">
                  <div className="label-caps mb-2">Current Conditions</div>
                  <ul className="space-y-1 font-mono text-[14px] text-aegis-muted">
                    <li>Sleep {sleepMetric?.latest.toFixed(1) ?? "—"} h</li>
                    <li>CO₂ {co2Metric ? Math.round(co2Metric.latest).toLocaleString() : "—"} ppm</li>
                    <li>Fatigue {fatigueMetric?.latest.toFixed(0) ?? "—"}</li>
                  </ul>
                </div>
                <div className="rounded border border-aegis-border bg-aegis-bg/40 p-3">
                  <div className="label-caps mb-2">Hypothetical Conditions</div>
                  <ul className="space-y-1 font-mono text-[14px] text-aegis-text">
                    <li>Sleep {sleep.toFixed(1)} h</li>
                    <li>CO₂ {Math.round(co2).toLocaleString()} ppm</li>
                    <li>Fatigue {includeFatigue ? fatigue : "—"}</li>
                  </ul>
                </div>
              </div>

              <div className="mt-3">
                <div className="label-caps mb-1">Drivers</div>
                <ul className="space-y-1 text-[14px] text-aegis-muted">
                  {result.drivers.map((d) => (
                    <li key={d}>• {d}</li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <div className="text-[14px] text-aegis-muted">Loading simulation…</div>
          )}
        </Panel>
      </div>

      <div className="rounded border border-aegis-border bg-aegis-panel/60 px-3 py-2 text-[14px] leading-relaxed text-aegis-muted">
        {result?.disclaimer ??
          "This simulation shows an estimated association based on the model. It does not prove causation or guarantee a specific outcome."}
      </div>
    </div>
  );
}

function SliderRow({
  label,
  valueLabel,
  min,
  max,
  step,
  value,
  onChange,
  disabled,
}: {
  label: string;
  valueLabel: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[14px] text-aegis-muted">{label}</span>
        <span className="rounded border border-aegis-border bg-aegis-bg px-2 py-0.5 font-mono text-[14px] text-aegis-text">
          {valueLabel}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded bg-aegis-border accent-aegis-cyan disabled:cursor-not-allowed"
      />
      <div className="mt-1 flex justify-between font-mono text-[12px] text-aegis-muted">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
