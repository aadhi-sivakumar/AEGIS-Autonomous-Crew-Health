"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Pause, Play, RefreshCw } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { api } from "@/lib/api";

type TelemPoint = {
  time: string;
  co2_iss: number | null;
  temperature_iss: number | null;
  humidity_iss: number | null;
  co2_ground: number | null;
  temperature_ground: number | null;
  humidity_ground: number | null;
  milestones: string | null;
};

type RadPoint = {
  time: string;
  gcr: number | null;
  saa: number | null;
  total: number | null;
};

type ReplayPayload = {
  mission_id: string;
  mission_title: string;
  time_start: string;
  time_end: string;
  cursor: string;
  timeline: string[];
  timeline_points?: TelemPoint[];
  milestones: { time: string; label: string; source: string }[];
  current_telemetry: TelemPoint | null;
  current_radiation: RadPoint | null;
  radiation_as_of_note: string;
  chart: {
    series: Record<string, { time: string; value: number }[]>;
  };
  radiation_series: RadPoint[];
  anomalies: { metric: string; explanation: string; severity: string; start: string; end: string }[];
  source: {
    system: string;
    telemetry_url: string;
    radiation_url: string;
    imported_at: string;
    disclaimer: string;
  };
};

function radiationAsOf(series: RadPoint[], at: string): RadPoint | null {
  let best: RadPoint | null = null;
  for (const r of series) {
    if (r.time <= at) best = r;
    else break;
  }
  return best;
}

const SPEEDS = [1, 5, 20] as const;

function fmtTime(iso: string) {
  try {
    return new Date(iso).toISOString().replace(".000Z", "Z");
  } catch {
    return iso;
  }
}

export function MissionReplayPage() {
  const [missionId, setMissionId] = useState("RR-1");
  const [missions, setMissions] = useState<{ name: string; title: string; cached?: boolean }[]>([]);
  const [base, setBase] = useState<ReplayPayload | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(5);
  const [compareGround, setCompareGround] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadMissions = useCallback(async () => {
    try {
      const m = await api.nasaMissions();
      setMissions(
        (m.missions || []).map((x: { name: string; title: string; cached?: boolean }) => ({
          name: x.name,
          title: x.title,
          cached: x.cached,
        }))
      );
    } catch {
      setMissions([{ name: "RR-1", title: "Rodent Research 1", cached: false }]);
    }
  }, []);

  const loadReplay = useCallback(async () => {
    try {
      setError(null);
      const data = await api.nasaReplay(missionId);
      setBase(data);
      setIndex(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay unavailable — import NASA data first");
      setBase(null);
    }
  }, [missionId]);

  useEffect(() => {
    void loadMissions();
  }, [loadMissions]);

  useEffect(() => {
    void loadReplay();
  }, [loadReplay]);

  // Playback advances timeline index using cached timestamps (no network spam).
  useEffect(() => {
    if (!playing || !base?.timeline?.length) return;
    timer.current = setInterval(() => {
      setIndex((i) => {
        const next = i + 1;
        if (next >= base.timeline.length) {
          setPlaying(false);
          return i;
        }
        return next;
      });
    }, Math.max(40, 400 / speed));
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, speed, base]);

  const cursor = base?.timeline?.[index];
  const telem = useMemo(() => {
    if (!base) return null;
    const points = base.timeline_points ?? [];
    if (points[index]) return points[index];
    return base.current_telemetry;
  }, [base, index]);
  const rad = useMemo(() => {
    if (!base || !cursor) return null;
    return radiationAsOf(base.radiation_series ?? [], cursor);
  }, [base, cursor]);
  const radiationNote = rad
    ? `Showing most recent daily radiation sample at/before cursor (${rad.time}). Not interpolated.`
    : "No radiation sample available at/before this cursor.";

  const importMission = async () => {
    try {
      setBusy(true);
      setMessage(null);
      setError(null);
      const res = await api.nasaImport(missionId);
      setMessage(
        res.cached_only
          ? res.detail
          : `Imported ${res.telemetry_count} telemetry + ${res.radiation_count} radiation records.`
      );
      await loadMissions();
      await loadReplay();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const chartData = useMemo(() => {
    const points = base?.timeline_points ?? [];
    if (points.length) {
      return points.map((p) => ({
        time: p.time,
        co2: p.co2_iss,
        temp: p.temperature_iss,
        hum: p.humidity_iss,
        co2_ground: p.co2_ground,
      }));
    }
    const co2 = base?.chart?.series?.co2_iss ?? [];
    const temp = base?.chart?.series?.temperature_iss ?? [];
    const hum = base?.chart?.series?.humidity_iss ?? [];
    const ground = base?.chart?.series?.co2_ground ?? [];
    const byTime = new Map<string, Record<string, number | string | null>>();
    for (const p of co2) {
      byTime.set(p.time, { time: p.time, co2: p.value });
    }
    for (const p of temp) {
      const row = byTime.get(p.time) ?? { time: p.time };
      row.temp = p.value;
      byTime.set(p.time, row);
    }
    for (const p of hum) {
      const row = byTime.get(p.time) ?? { time: p.time };
      row.hum = p.value;
      byTime.set(p.time, row);
    }
    if (compareGround) {
      for (const p of ground) {
        const row = byTime.get(p.time) ?? { time: p.time };
        row.co2_ground = p.value;
        byTime.set(p.time, row);
      }
    }
    return Array.from(byTime.values());
  }, [base, compareGround]);

  const radChart = useMemo(
    () =>
      (base?.radiation_series ?? []).map((r) => ({
        time: r.time,
        gcr: r.gcr,
        saa: r.saa,
        total: r.total,
      })),
    [base]
  );

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 pb-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-medium text-aegis-text">NASA Mission Replay</h1>
          <p className="mt-2 text-[15px] text-aegis-muted">
            Historical OSDR / EDA research-environment measurements — not live crew medical data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded border border-aegis-border bg-aegis-panel px-2 py-1.5 text-[11px] text-aegis-text"
            value={missionId}
            onChange={(e) => setMissionId(e.target.value)}
          >
            {(missions.length ? missions : [{ name: "RR-1", title: "RR-1" }]).map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} — {m.title?.slice(0, 40)}
                {m.cached ? " (cached)" : ""}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy}
            onClick={() => void importMission()}
            className="inline-flex items-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/10 px-3 py-1.5 text-[11px] text-aegis-cyan disabled:opacity-50"
          >
            <RefreshCw size={12} />
            Import / Refresh
          </button>
        </div>
      </div>

      <div className="rounded border border-aegis-cyan/30 bg-aegis-cyan/5 px-3 py-2 text-[11px] leading-snug text-aegis-muted">
        <span className="text-aegis-cyan">NASA HISTORICAL DATA</span> — RR-1 Rodent Research-1 (2014)
        ISS research hardware environment. Original timestamps preserved.{" "}
        {base?.source?.disclaimer}
      </div>

      {error && (
        <div className="rounded border border-aegis-amber/40 bg-aegis-amber/10 px-3 py-2 text-[11px] text-aegis-amber">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded border border-aegis-green/40 bg-aegis-green/10 px-3 py-2 text-[11px] text-aegis-green">
          {message}
        </div>
      )}

      {!base ? (
        <Panel title="No cached NASA mission">
          <p className="text-[12px] text-aegis-muted">
            Click Import / Refresh while online to download RR-1 telemetry and radiation into local
            SQLite. After that, replay works offline.
          </p>
        </Panel>
      ) : (
        <>
          <Panel title="Playback">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setPlaying((p) => !p)}
                className="inline-flex items-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/10 px-3 py-1.5 text-[11px] text-aegis-cyan"
              >
                {playing ? <Pause size={12} /> : <Play size={12} />}
                {playing ? "Pause" : "Play"}
              </button>
              <div className="flex items-center gap-1">
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSpeed(s)}
                    className={`rounded border px-2 py-1 font-mono text-[10px] ${
                      speed === s
                        ? "border-aegis-cyan text-aegis-cyan"
                        : "border-aegis-border text-aegis-muted"
                    }`}
                  >
                    {s}×
                  </button>
                ))}
              </div>
              <div className="font-mono text-[12px] text-aegis-text">{cursor ? fmtTime(cursor) : "—"}</div>
              <label className="ml-auto flex items-center gap-2 text-[11px] text-aegis-muted">
                <input
                  type="checkbox"
                  checked={compareGround}
                  onChange={(e) => setCompareGround(e.target.checked)}
                />
                ISS vs ground CO₂
              </label>
            </div>
            <input
              type="range"
              className="mt-3 w-full accent-[#55B8E8]"
              min={0}
              max={Math.max(0, (base.timeline?.length ?? 1) - 1)}
              value={index}
              onChange={(e) => {
                setPlaying(false);
                setIndex(Number(e.target.value));
              }}
            />
            <div className="mt-1 flex justify-between font-mono text-[10px] text-aegis-muted">
              <span>{base.time_start}</span>
              <span>{base.time_end}</span>
            </div>
            {base.milestones?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {base.milestones.slice(0, 12).map((m) => (
                  <button
                    key={`${m.time}-${m.label}`}
                    type="button"
                    className="rounded border border-aegis-border px-2 py-0.5 text-[10px] text-aegis-muted hover:border-aegis-cyan hover:text-aegis-cyan"
                    onClick={() => {
                      const i = base.timeline.findIndex((t) => t >= m.time);
                      if (i >= 0) {
                        setPlaying(false);
                        setIndex(i);
                      }
                    }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            )}
          </Panel>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: "CO₂ ISS", value: telem?.co2_iss, unit: "ppm" },
              { label: "Temp ISS", value: telem?.temperature_iss, unit: "°C" },
              { label: "Humidity ISS", value: telem?.humidity_iss, unit: "%" },
              { label: "Radiation total", value: rad?.total, unit: "mGy/day" },
            ].map((m) => (
              <div key={m.label} className="rounded border border-aegis-border bg-aegis-panel p-2.5">
                <div className="label-caps">{m.label}</div>
                <div className="mt-1 font-mono text-lg text-aegis-cyan">
                  {m.value == null ? "—" : Number(m.value).toLocaleString(undefined, { maximumFractionDigits: 3 })}
                  <span className="ml-1 text-[10px] text-aegis-muted">{m.unit}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <Panel title="Environmental history (cached)">
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis tick={{ fill: "#8FA3B8", fontSize: 10 }} stroke="#2C4157" width={40} />
                    <Tooltip
                      contentStyle={{ background: "#0B1420", border: "1px solid #2C4157", fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line type="monotone" dataKey="co2" name="CO₂ ISS" stroke="#55B8E8" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="temp" name="Temp ISS" stroke="#E6AD57" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="hum" name="Humidity" stroke="#53BE8B" dot={false} isAnimationActive={false} />
                    {compareGround && (
                      <Line
                        type="monotone"
                        dataKey="co2_ground"
                        name="CO₂ Ground"
                        stroke="#8FA3B8"
                        strokeDasharray="4 3"
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Radiation (mGy/day, daily samples)">
              <p className="mb-2 text-[10px] text-aegis-muted">{radiationNote}</p>
              <div className="mb-2 grid grid-cols-3 gap-2 text-[11px]">
                <div>
                  <div className="label-caps">GCR</div>
                  <div className="font-mono text-aegis-text">{rad?.gcr ?? "—"}</div>
                </div>
                <div>
                  <div className="label-caps">SAA</div>
                  <div className="font-mono text-aegis-text">{rad?.saa ?? "—"}</div>
                </div>
                <div>
                  <div className="label-caps">Total</div>
                  <div className="font-mono text-aegis-cyan">{rad?.total ?? "—"}</div>
                </div>
              </div>
              <div className="h-[160px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={radChart}>
                    <CartesianGrid stroke="#2C4157" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis tick={{ fill: "#8FA3B8", fontSize: 10 }} stroke="#2C4157" width={36} />
                    <Tooltip
                      contentStyle={{ background: "#0B1420", border: "1px solid #2C4157", fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line type="monotone" dataKey="gcr" name="GCR" stroke="#55B8E8" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="saa" name="SAA" stroke="#E6AD57" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="total" name="Total" stroke="#D96767" dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-[10px] text-aegis-muted">
                Radiation is not interpolated onto the telemetry timeline. Not used for cognitive forecasting.
              </p>
            </Panel>
          </div>

          <Panel title="Statistical environmental anomalies">
            {(base?.anomalies ?? []).length === 0 ? (
              <p className="text-[11px] text-aegis-muted">No sustained statistical anomalies flagged.</p>
            ) : (
              <ul className="space-y-1.5 text-[11px] text-aegis-amber">
                {(base?.anomalies ?? []).map((a, i) => (
                  <li key={`${a.metric}-${i}`}>• {a.explanation}</li>
                ))}
              </ul>
            )}
          </Panel>

          <div className="text-[10px] leading-snug text-aegis-muted">
            Source: {base.source.system} ·{" "}
            <a className="text-aegis-cyan hover:underline" href={base.source.telemetry_url} target="_blank" rel="noreferrer">
              telemetry endpoint
            </a>{" "}
            ·{" "}
            <a className="text-aegis-cyan hover:underline" href={base.source.radiation_url} target="_blank" rel="noreferrer">
              radiation endpoint
            </a>{" "}
            · imported {base.source.imported_at}
          </div>
        </>
      )}
    </div>
  );
}
