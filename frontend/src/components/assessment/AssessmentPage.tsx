"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { SymptomChecklist } from "@/components/assessment/SymptomChecklist";
import { MeasureHowTo, RT_HOW_TO } from "@/components/today/MeasureHowTo";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import { statusColor } from "@/lib/format";

type Phase = "instructions" | "waiting" | "stimulus" | "feedback" | "results";

const TRIAL_COUNT = 10;
const MIN_DELAY_MS = 800;
const MAX_DELAY_MS = 2800;
const EARLY_CLICK_MS = 100;

function median(vals: number[]): number {
  if (!vals.length) return 0;
  const s = [...vals].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function iqr(vals: number[]): number {
  if (vals.length < 4) return 0;
  const s = [...vals].sort((a, b) => a - b);
  const q1 = s[Math.floor(s.length * 0.25)];
  const q3 = s[Math.floor(s.length * 0.75)];
  return q3 - q1;
}

export function AssessmentPage() {
  const { selectedCrewId, overview, refresh } = useApp();
  const [phase, setPhase] = useState<Phase>("instructions");
  const [trial, setTrial] = useState(0);
  const [validRts, setValidRts] = useState<number[]>([]);
  const [invalidCount, setInvalidCount] = useState(0);
  const [lastFeedback, setLastFeedback] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stimulusAt = useRef<number>(0);
  const waitingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const phaseRef = useRef<Phase>(phase);
  const trialRef = useRef(trial);
  const validRef = useRef(validRts);
  const invalidRef = useRef(invalidCount);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);
  useEffect(() => {
    trialRef.current = trial;
  }, [trial]);
  useEffect(() => {
    validRef.current = validRts;
  }, [validRts]);
  useEffect(() => {
    invalidRef.current = invalidCount;
  }, [invalidCount]);

  const clearWait = () => {
    if (waitingTimeout.current) {
      clearTimeout(waitingTimeout.current);
      waitingTimeout.current = null;
    }
  };

  const startTrial = useCallback((nextTrial: number) => {
    clearWait();
    setTrial(nextTrial);
    setPhase("waiting");
    setLastFeedback("");
    const delay = MIN_DELAY_MS + Math.random() * (MAX_DELAY_MS - MIN_DELAY_MS);
    waitingTimeout.current = setTimeout(() => {
      stimulusAt.current = performance.now();
      setPhase("stimulus");
    }, delay);
  }, []);

  const finishAssessment = useCallback(() => {
    clearWait();
    setPhase("results");
  }, []);

  const handleResponse = useCallback(() => {
    const p = phaseRef.current;
    if (p === "waiting") {
      clearWait();
      setInvalidCount((c) => c + 1);
      setLastFeedback("Too early — wait for the stimulus.");
      setPhase("feedback");
      setTimeout(() => {
        const next = trialRef.current + 1;
        if (next >= TRIAL_COUNT) finishAssessment();
        else startTrial(next);
      }, 700);
      return;
    }

    if (p === "stimulus") {
      const rt = performance.now() - stimulusAt.current;
      if (rt < EARLY_CLICK_MS) {
        setInvalidCount((c) => c + 1);
        setLastFeedback("Invalid response (too fast).");
      } else {
        setValidRts((prev) => [...prev, rt]);
        setLastFeedback(`${Math.round(rt)} ms`);
      }
      setPhase("feedback");
      setTimeout(() => {
        const next = trialRef.current + 1;
        if (next >= TRIAL_COUNT) finishAssessment();
        else startTrial(next);
      }, 550);
    }
  }, [finishAssessment, startTrial]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== "Space" && e.key !== " ") return;
      e.preventDefault();
      if (phaseRef.current === "waiting" || phaseRef.current === "stimulus") {
        handleResponse();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleResponse]);

  useEffect(() => () => clearWait(), []);

  const begin = () => {
    setValidRts([]);
    setInvalidCount(0);
    setSaveMessage(null);
    setError(null);
    startTrial(0);
  };

  const med = median(validRts);
  const variability = iqr(validRts);
  const baseline =
    overview?.metrics.find((m) => m.metric === "reaction_time_ms")?.baseline ?? med;
  const delta = med - baseline;
  const status = delta >= 40 ? "red" : delta >= 20 ? "amber" : "green";

  const save = async () => {
    try {
      setSaving(true);
      setError(null);
      const out = await api.submitAssessment({
        astronaut_id: selectedCrewId,
        median_rt_ms: Number(med.toFixed(1)),
        iqr_ms: Number(variability.toFixed(1)),
        trial_count: TRIAL_COUNT,
        invalid_count: invalidCount,
        trials: validRts.map((v) => Number(v.toFixed(1))),
      });
      setSaveMessage(out.message);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 pb-3">
      <div>
        <h1 className="text-lg font-medium text-aegis-text">Assessments</h1>
        <p className="mt-2 text-[15px] text-aegis-muted">
          Reaction-time task plus a quick symptom checklist — both crew-entered measurements.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <Panel className="col-span-12 min-h-[360px] lg:col-span-8" title="Task">
          {phase === "instructions" && (
            <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-4 px-2 text-center">
              <p className="max-w-md text-[13px] leading-relaxed text-aegis-muted">
                Press <span className="font-mono text-aegis-cyan">SPACE</span> as soon as the green
                circle appears. There are {TRIAL_COUNT} trials with randomized delays. Early presses
                are marked invalid.
              </p>
              <div className="w-full max-w-md text-left">
                <MeasureHowTo title="How to take this measurement" steps={RT_HOW_TO} defaultOpen />
              </div>
              <button
                type="button"
                onClick={begin}
                className="rounded border border-aegis-cyan bg-aegis-cyan/20 px-4 py-2 text-[12px] text-aegis-cyan hover:bg-aegis-cyan/30"
              >
                Begin Assessment
              </button>
            </div>
          )}

          {(phase === "waiting" || phase === "stimulus" || phase === "feedback") && (
            <div className="flex min-h-[300px] flex-col items-center justify-center gap-6">
              <div className="font-mono text-[12px] text-aegis-muted">
                Trial {Math.min(trial + 1, TRIAL_COUNT)} of {TRIAL_COUNT}
              </div>
              <button
                type="button"
                aria-label="Assessment stimulus area. Press space when circle appears."
                onClick={handleResponse}
                className="flex h-56 w-full max-w-lg items-center justify-center rounded border border-aegis-border bg-aegis-bg outline-none focus-visible:ring-1 focus-visible:ring-aegis-cyan"
              >
                {phase === "stimulus" ? (
                  <span className="block h-24 w-24 rounded-full bg-aegis-green shadow-[0_0_24px_rgba(83,190,139,0.35)]" />
                ) : phase === "feedback" ? (
                  <span className="font-mono text-sm text-aegis-amber">{lastFeedback}</span>
                ) : (
                  <span className="text-[12px] text-aegis-muted">Wait for the circle…</span>
                )}
              </button>
              <div className="text-[11px] text-aegis-muted">
                Press SPACE as soon as the circle appears.
              </div>
            </div>
          )}

          {phase === "results" && (
            <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 text-center">
              <div className="text-[13px] text-aegis-text">Assessment complete</div>
              <div className="font-mono text-3xl" style={{ color: statusColor(status) }}>
                {med.toFixed(0)}
                <span className="ml-1 text-base text-aegis-muted">ms median</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setPhase("instructions");
                  setValidRts([]);
                  setInvalidCount(0);
                  setSaveMessage(null);
                }}
                className="text-[11px] text-aegis-cyan hover:underline"
              >
                Run again
              </button>
            </div>
          )}
        </Panel>

        <div className="col-span-12 flex flex-col gap-3 lg:col-span-4">
          <Panel title="Measurement setup">
            <ol className="space-y-2 text-[14px] text-aegis-muted">
              <li className="flex gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-aegis-cyan/20 text-[12px] text-aegis-cyan">
                  1
                </span>
                Quiet seat, tab focused, finger ready on SPACE.
              </li>
              <li className="flex gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-aegis-cyan/20 text-[12px] text-aegis-cyan">
                  2
                </span>
                Press SPACE only when the green circle appears.
              </li>
              <li className="flex gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-aegis-cyan/20 text-[12px] text-aegis-cyan">
                  3
                </span>
                Finish all {TRIAL_COUNT} trials (~60 s), then save.
              </li>
            </ol>
            <p className="mt-3 text-[13px] leading-relaxed text-aegis-muted">
              Custom vigilance-style task — not a validated substitute for NASA official assessment
              protocols.
            </p>
          </Panel>

          <Panel title="Recent Results">
            {phase === "results" || validRts.length > 0 ? (
              <div className="space-y-2 text-[12px]">
                <div className="flex justify-between">
                  <span className="text-aegis-muted">Median RT</span>
                  <span className="font-mono" style={{ color: statusColor(status) }}>
                    {med.toFixed(0)} ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-aegis-muted">Variability (IQR)</span>
                  <span className="font-mono">{variability.toFixed(0)} ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-aegis-muted">vs Personal Baseline</span>
                  <span className="font-mono" style={{ color: statusColor(status) }}>
                    {delta >= 0 ? "+" : ""}
                    {delta.toFixed(0)} ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-aegis-muted">Valid / Invalid</span>
                  <span className="font-mono">
                    {validRts.length} / {invalidCount}
                  </span>
                </div>
                <div
                  className="mt-2 rounded border px-2 py-1.5 text-center text-[11px]"
                  style={{
                    borderColor: statusColor(status),
                    color: statusColor(status),
                  }}
                >
                  {status === "green"
                    ? "Green — Near baseline"
                    : status === "amber"
                      ? "Amber — Slower than baseline"
                      : "Red — Markedly slower than baseline"}
                </div>
                {phase === "results" && (
                  <button
                    type="button"
                    disabled={saving || validRts.length === 0}
                    onClick={() => void save()}
                    className="mt-2 w-full rounded border border-aegis-cyan bg-aegis-cyan/20 px-3 py-2 text-[12px] text-aegis-cyan hover:bg-aegis-cyan/30 disabled:opacity-40"
                  >
                    {saving ? "Saving…" : "Save Result & Update Profile"}
                  </button>
                )}
                {saveMessage && (
                  <p className="text-[10px] leading-snug text-aegis-green">{saveMessage}</p>
                )}
                {error && <p className="text-[10px] text-aegis-red">{error}</p>}
              </div>
            ) : (
              <p className="text-[15px] leading-snug text-aegis-muted">
                Complete the assessment to compare against {selectedCrewId} baseline (
                {baseline.toFixed(0)} ms).
              </p>
            )}
          </Panel>
        </div>
      </div>

      <div id="symptoms" className="scroll-mt-4">
        <SymptomChecklist astronautId={selectedCrewId} />
      </div>
    </div>
  );
}
