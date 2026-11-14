"use client";

import Link from "next/link";
import { AlertTriangle, Siren } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import type { GuidanceOut } from "@/lib/types";

interface Props {
  guidance: Pick<
    GuidanceOut,
    "emergency_disclaimer" | "emergency_steps" | "when_to_escalate" | "recommendations"
  >;
  compact?: boolean;
}

export function EmergencyPanel({ guidance, compact = false }: Props) {
  const steps = guidance.emergency_steps ?? [];
  const when = guidance.when_to_escalate ?? [];

  return (
    <Panel
      title="Emergency guidance"
      action={
        <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wide text-aegis-red">
          <Siren size={12} />
          Advisory
        </span>
      }
    >
      <div className="mb-3 flex gap-2 rounded border border-aegis-red/40 bg-aegis-red/10 px-2.5 py-2 text-[12px] leading-snug text-aegis-red">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <p>{guidance.emergency_disclaimer}</p>
      </div>

      {!compact && when.length > 0 && (
        <div className="mb-3">
          <div className="label-caps mb-1.5 text-aegis-amber">When to escalate now</div>
          <ul className="space-y-1">
            {when.map((w) => (
              <li key={w} className="flex gap-2 text-[12px] leading-snug text-aegis-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-aegis-amber" />
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="label-caps mb-1.5">What to do — in order</div>
      <ol className="space-y-2">
        {steps.map((s) => (
          <li
            key={s.step}
            className="rounded border border-aegis-border bg-aegis-bg/50 px-2.5 py-2"
          >
            <div className="flex items-start gap-2">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-aegis-red/15 font-mono text-[11px] text-aegis-red">
                {s.step}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-aegis-text">{s.title}</div>
                <p className="mt-0.5 text-[12px] leading-snug text-aegis-muted">{s.detail}</p>
                {s.href && (
                  <Link
                    href={s.href}
                    className="mt-1 inline-block text-[12px] text-aegis-cyan hover:underline"
                  >
                    Open →
                  </Link>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>

      {!compact && (guidance.recommendations?.length ?? 0) > 0 && (
        <div className="mt-3 border-t border-aegis-border pt-3">
          <div className="label-caps mb-1.5">Also useful when values look off</div>
          <ul className="space-y-1">
            {guidance.recommendations.slice(0, 4).map((r) => (
              <li key={r} className="flex gap-2 text-[12px] leading-snug text-aegis-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-aegis-cyan" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
