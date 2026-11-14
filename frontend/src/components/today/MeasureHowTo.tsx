"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export interface HowToStep {
  title: string;
  detail: string;
}

interface Props {
  title?: string;
  steps: HowToStep[];
  defaultOpen?: boolean;
}

export function MeasureHowTo({ title = "How to take this measurement", steps, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="mb-3 rounded border border-aegis-border bg-aegis-bg/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left"
        aria-expanded={open}
      >
        <span className="text-[12px] font-medium text-aegis-cyan">{title}</span>
        {open ? (
          <ChevronDown size={14} className="shrink-0 text-aegis-muted" />
        ) : (
          <ChevronRight size={14} className="shrink-0 text-aegis-muted" />
        )}
      </button>
      {open && (
        <ol className="space-y-2 border-t border-aegis-border px-2.5 py-2.5">
          {steps.map((s, i) => (
            <li key={s.title} className="flex gap-2 text-[12px] leading-snug">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-aegis-cyan/15 font-mono text-[11px] text-aegis-cyan">
                {i + 1}
              </span>
              <span>
                <span className="font-medium text-aegis-text">{s.title}. </span>
                <span className="text-aegis-muted">{s.detail}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export const CHECKIN_HOW_TO: HowToStep[] = [
  {
    title: "Sleep",
    detail:
      "Report hours in your last sleep opportunity (including planned naps if they were part of rest). Estimate honestly — do not round up to look better.",
  },
  {
    title: "Fatigue & mood",
    detail:
      "Rate how you feel right now (1–5), not yesterday. Fatigue: fresh → exhausted. Mood: low → good.",
  },
  {
    title: "Resting heart rate (optional)",
    detail:
      "Sit quietly 2–3 minutes. No caffeine or exercise just before. Measure at the wrist, chest strap, or wearable resting mode. Enter bpm once the reading is stable.",
  },
];

export const RT_HOW_TO: HowToStep[] = [
  {
    title: "Setup",
    detail:
      "Sit upright in a quiet spot. Put the browser tab in focus. Rest your dominant hand so a finger can press SPACE immediately.",
  },
  {
    title: "During the task",
    detail:
      "Watch the center. Press SPACE as soon as the green circle appears — not before. Early presses count as invalid.",
  },
  {
    title: "Finish",
    detail:
      "Complete all 10 trials (~60 s), then save so today's readiness uses your measured RT vs personal baseline.",
  },
];

export const SYMPTOM_HOW_TO: HowToStep[] = [
  {
    title: "Rate current intensity",
    detail:
      "Use how you feel over the last few hours. None → Mild → Moderate → Strong. This is self-report, not a diagnosis.",
  },
  {
    title: "When unsure",
    detail:
      "If a symptom is intermittent, pick the peak intensity. Add a short note if something else matters.",
  },
  {
    title: "If moderate or strong",
    detail:
      "Save the checklist, skip high-stakes tasks, and open Emergency guidance on the Readiness Gate.",
  },
];
