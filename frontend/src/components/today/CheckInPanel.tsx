"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { api } from "@/lib/api";
import type { CheckIn } from "@/lib/types";

interface Props {
  astronautId: string;
  existing: CheckIn | null;
  onSaved: () => void;
}

function TapScale({
  label,
  value,
  onChange,
  low,
  high,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  low: string;
  high: string;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-[11px]">
        <span className="text-aegis-text">{label}</span>
        <span className="font-mono text-aegis-cyan">{value}</span>
      </div>
      <div className="flex gap-1.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`h-9 flex-1 rounded border text-[12px] font-mono transition-colors ${
              value === n
                ? "border-aegis-cyan bg-aegis-cyan/15 text-aegis-cyan"
                : "border-aegis-border text-aegis-muted hover:border-aegis-cyan/50"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-aegis-muted">
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  );
}

export function CheckInPanel({ astronautId, existing, onSaved }: Props) {
  const [sleep, setSleep] = useState(existing?.sleep_h ?? 7);
  const [fatigue, setFatigue] = useState(existing?.fatigue ?? 2);
  const [mood, setMood] = useState(existing?.mood ?? 4);
  const [hr, setHr] = useState(existing?.resting_hr?.toString() ?? "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSleep(existing?.sleep_h ?? 7);
    setFatigue(existing?.fatigue ?? 2);
    setMood(existing?.mood ?? 4);
    setHr(existing?.resting_hr?.toString() ?? "");
  }, [existing, astronautId]);

  const submit = async () => {
    try {
      setBusy(true);
      setError(null);
      const resting = hr.trim() ? Number(hr) : null;
      await api.submitCheckIn({
        astronaut_id: astronautId,
        sleep_h: sleep,
        fatigue,
        mood,
        resting_hr: resting && !Number.isNaN(resting) ? resting : null,
      });
      setMsg("Saved. Status updated from your log — next, open Readiness Gate.");
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save check-in");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Daily check-in"
      action={
        existing ? (
          <span className="text-[11px] uppercase tracking-wide text-aegis-green">Logged today</span>
        ) : (
          <span className="text-[11px] uppercase tracking-wide text-aegis-amber">~2 min</span>
        )
      }
    >
      <p className="mb-3 text-[13px] leading-snug text-aegis-muted">
        Tap your sleep, fatigue, and mood. Optional resting HR. This updates today&apos;s personal
        baseline comparison.
      </p>

      <div className="space-y-4">
        <div>
          <div className="mb-1.5 flex items-center justify-between text-[11px]">
            <span className="text-aegis-text">Sleep last night</span>
            <span className="font-mono text-aegis-cyan">{sleep.toFixed(1)} h</span>
          </div>
          <input
            type="range"
            min={4}
            max={10}
            step={0.5}
            value={sleep}
            onChange={(e) => setSleep(Number(e.target.value))}
            className="w-full accent-[#55B8E8]"
          />
        </div>

        <TapScale
          label="Fatigue"
          value={fatigue}
          onChange={setFatigue}
          low="Fresh"
          high="Exhausted"
        />
        <TapScale label="Mood" value={mood} onChange={setMood} low="Low" high="Good" />

        <div>
          <label className="mb-1.5 block text-[11px] text-aegis-text">
            Resting HR <span className="text-aegis-muted">(optional, bpm)</span>
          </label>
          <input
            type="number"
            inputMode="numeric"
            placeholder="e.g. 64"
            value={hr}
            onChange={(e) => setHr(e.target.value)}
            className="w-full rounded border border-aegis-border bg-aegis-bg px-2.5 py-2 font-mono text-[12px] text-aegis-text outline-none focus:border-aegis-cyan"
          />
        </div>

        <button
          type="button"
          disabled={busy}
          onClick={() => void submit()}
          className="w-full rounded border border-aegis-cyan bg-aegis-cyan/15 px-3 py-2.5 text-[12px] text-aegis-cyan transition-colors hover:bg-aegis-cyan/25 disabled:opacity-50"
        >
          {busy ? "Saving…" : existing ? "Update check-in" : "Save check-in"}
        </button>

        {msg && (
          <p className="text-[11px] text-aegis-green">
            {msg}{" "}
            <Link href="/operations" className="underline">
              Go to Readiness Gate →
            </Link>
          </p>
        )}
        {error && <p className="text-[11px] text-aegis-red">{error}</p>}
      </div>
    </Panel>
  );
}
