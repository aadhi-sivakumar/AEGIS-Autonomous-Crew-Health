"use client";

import Link from "next/link";
import { Bell } from "lucide-react";
import type { PromptItem } from "@/lib/types";

interface Props {
  prompts: PromptItem[];
  onSnooze: (kind: PromptItem["kind"]) => void;
}

export function PromptBanner({ prompts, onSnooze }: Props) {
  if (!prompts.length) return null;

  return (
    <div className="space-y-2">
      {prompts.map((p) => (
        <div
          key={p.kind}
          className={`flex flex-col gap-2 rounded border px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between ${
            p.urgency === "high"
              ? "border-aegis-amber/50 bg-aegis-amber/10"
              : "border-aegis-cyan/30 bg-aegis-cyan/5"
          }`}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Bell
                size={12}
                className={p.urgency === "high" ? "text-aegis-amber" : "text-aegis-cyan"}
              />
              <div
                className={`text-[13px] font-medium ${
                  p.urgency === "high" ? "text-aegis-amber" : "text-aegis-cyan"
                }`}
              >
                {p.title}
              </div>
              {p.due_label && (
                <span className="rounded border border-aegis-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-aegis-muted">
                  {p.due_label}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-[12px] leading-snug text-aegis-muted">{p.message}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Link
              href={p.href}
              className="rounded border border-aegis-cyan/50 px-2.5 py-1.5 text-[12px] text-aegis-cyan hover:bg-aegis-cyan/10"
            >
              Measure now
            </Link>
            <button
              type="button"
              onClick={() => onSnooze(p.kind)}
              className="rounded border border-aegis-border px-2.5 py-1.5 text-[12px] text-aegis-muted hover:text-aegis-text"
            >
              Snooze
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
