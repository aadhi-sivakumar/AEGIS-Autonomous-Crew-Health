"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { MeasureHowTo, SYMPTOM_HOW_TO } from "@/components/today/MeasureHowTo";
import { api } from "@/lib/api";
import type { SymptomCheck } from "@/lib/types";

const SYMPTOMS: { key: "headache" | "congestion" | "dizziness" | "nausea"; label: string }[] = [
  { key: "headache", label: "Headache" },
  { key: "congestion", label: "Congestion / stuffy" },
  { key: "dizziness", label: "Dizziness" },
  { key: "nausea", label: "Nausea" },
];

const LEVELS = [
  { v: 0, label: "None" },
  { v: 1, label: "Mild" },
  { v: 2, label: "Mod" },
  { v: 3, label: "Strong" },
];

interface Props {
  astronautId: string;
}

export function SymptomChecklist({ astronautId }: Props) {
  const [vals, setVals] = useState({ headache: 0, congestion: 0, dizziness: 0, nausea: 0 });
  const [notes, setNotes] = useState("");
  const [existing, setExisting] = useState<SymptomCheck | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api
      .getSymptoms(astronautId)
      .then((s) => {
        setExisting(s);
        if (s) {
          setVals({
            headache: s.headache,
            congestion: s.congestion,
            dizziness: s.dizziness,
            nausea: s.nausea,
          });
          setNotes(s.other_notes ?? "");
        }
      })
      .catch(() => undefined);
  }, [astronautId]);

  const submit = async () => {
    try {
      setBusy(true);
      setError(null);
      const out = await api.submitSymptoms({
        astronaut_id: astronautId,
        ...vals,
        other_notes: notes.trim() || null,
      });
      setExisting(out);
      setMsg(
        out.attention_needed
          ? "Saved — moderate+ symptoms noted. Skip high-stakes work and follow emergency guidance if they worsen."
          : "Symptom check saved."
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Symptom checklist"
      action={
        <span className="text-[11px] uppercase tracking-wide text-aegis-muted">
          Crew-entered
        </span>
      }
    >
      <p className="mb-3 text-[15px] leading-relaxed text-aegis-muted">
        Second daily measurement besides reaction time. Rate each item — this is not a diagnosis.
      </p>

      <MeasureHowTo steps={SYMPTOM_HOW_TO} defaultOpen={!existing} />

      <div className="space-y-3">
        {SYMPTOMS.map((s) => (
          <div key={s.key}>
            <div className="mb-1.5 text-[14px] text-aegis-text">{s.label}</div>
            <div className="flex gap-1">
              {LEVELS.map((l) => (
                <button
                  key={l.v}
                  type="button"
                  onClick={() => setVals((prev) => ({ ...prev, [s.key]: l.v }))}
                  className={`flex-1 rounded border px-1 py-2 text-[13px] transition-colors ${
                    vals[s.key] === l.v
                      ? l.v >= 2
                        ? "border-aegis-amber bg-aegis-amber/15 text-aegis-amber"
                        : "border-aegis-cyan bg-aegis-cyan/15 text-aegis-cyan"
                      : "border-aegis-border text-aegis-muted hover:border-aegis-cyan/40"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>
        ))}

        <div>
          <label className="mb-1.5 block text-[14px] text-aegis-text">Notes (optional)</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Anything else worth logging"
            className="w-full rounded border border-aegis-border bg-aegis-bg px-2.5 py-2 text-[14px] text-aegis-text outline-none focus:border-aegis-cyan"
          />
        </div>

        <button
          type="button"
          disabled={busy}
          onClick={() => void submit()}
          className="w-full rounded border border-aegis-cyan bg-aegis-cyan/15 px-3 py-2.5 text-[14px] text-aegis-cyan hover:bg-aegis-cyan/25 disabled:opacity-50"
        >
          {busy ? "Saving…" : existing ? "Update symptoms" : "Save symptoms"}
        </button>

        {msg && (
          <p className="text-[13px] text-aegis-green">
            {msg}{" "}
            {existing?.attention_needed && (
              <Link href="/operations#emergency" className="underline">
                Open emergency guidance →
              </Link>
            )}
          </p>
        )}
        {error && <p className="text-[13px] text-aegis-red">{error}</p>}
      </div>
    </Panel>
  );
}
