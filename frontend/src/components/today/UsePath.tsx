"use client";

import Link from "next/link";
import type { TodayOut } from "@/lib/types";

interface Props {
  today: TodayOut;
}

export function UsePath({ today }: Props) {
  const step1Done = today.checkin_done;
  const step2Done = today.assessment_complete || today.has_browser_assessment;
  const step3Needed =
    today.overall_status !== "green" ||
    Boolean(today.prompts.some((p) => p.kind === "pre_eva"));

  // Emphasize the first incomplete step in the daily loop
  const emphasizeStep = !step1Done ? 1 : !step2Done ? 2 : 3;

  const steps = [
    {
      n: 1,
      label: "Check in",
      detail: step1Done ? "Logged for today" : "Log sleep, fatigue, mood (~2 min)",
      href: "#checkin",
      done: step1Done,
      emphasize: emphasizeStep === 1,
    },
    {
      n: 2,
      label: "Assessment",
      detail: step2Done
        ? "Reaction time measured today"
        : "Measure reaction time (~1 min) before high-stakes work",
      href: "/assessment",
      done: step2Done,
      emphasize: emphasizeStep === 2,
    },
    {
      n: 3,
      label: "Readiness Gate",
      detail: step3Needed
        ? "Check Ready / Caution / Not recommended before high-stakes work"
        : "Optional when status looks stable — still useful before EVA",
      href: "/operations",
      done: false,
      emphasize: emphasizeStep === 3,
    },
  ];

  return (
    <div className="rounded border border-aegis-border bg-aegis-panel px-3 py-2.5">
      <div className="mb-2 text-[13px] font-medium text-aegis-text">How to use AEGIS today</div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {steps.map((s) => (
          <Link
            key={s.n}
            href={s.href}
            className={`rounded border px-2.5 py-2 transition-colors hover:border-aegis-cyan/50 ${
              s.emphasize
                ? "border-aegis-amber/50 bg-aegis-amber/5"
                : s.done
                  ? "border-aegis-green/30 bg-aegis-green/5"
                  : "border-aegis-border bg-aegis-bg/40"
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-mono ${
                  s.done
                    ? "bg-aegis-green/20 text-aegis-green"
                    : s.emphasize
                      ? "bg-aegis-amber/20 text-aegis-amber"
                      : "bg-aegis-cyan/15 text-aegis-cyan"
                }`}
              >
                {s.done ? "✓" : s.n}
              </span>
              <span className="text-[13px] font-medium text-aegis-text">{s.label}</span>
            </div>
            <p className="mt-1 pl-7 text-[12px] leading-snug text-aegis-muted">{s.detail}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
