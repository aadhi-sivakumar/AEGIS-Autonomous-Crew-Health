"use client";

import { AlertTriangle, ArrowRight } from "lucide-react";
import Link from "next/link";
import type { CombinedPatternOut } from "@/lib/types";

export function WarningBar({ pattern }: { pattern: CombinedPatternOut }) {
  if (!pattern.detected) return null;

  const isRed = pattern.severity === "red";
  const border = isRed
    ? "border-aegis-red/60 bg-aegis-red/10"
    : "border-aegis-amber/60 bg-aegis-amber/10";
  const text = isRed ? "text-aegis-red" : "text-aegis-amber";

  return (
    <div className={`grid grid-cols-1 items-center gap-3 rounded border px-3 py-2.5 sm:grid-cols-[auto_1fr_auto] ${border}`}>
      <AlertTriangle size={16} className={`shrink-0 ${text}`} />
      <p className={`text-[12px] leading-snug break-words ${text}`}>{pattern.summary}</p>
      <Link
        href="/assessment"
        className={`inline-flex w-fit shrink-0 items-center gap-1 justify-self-start rounded border px-3 py-1.5 text-[11px] font-medium transition-colors sm:justify-self-end ${
          isRed
            ? "border-aegis-red bg-aegis-red/20 text-aegis-red hover:bg-aegis-red/30"
            : "border-aegis-amber bg-aegis-amber/20 text-aegis-amber hover:bg-aegis-amber/30"
        }`}
      >
        Start Assessment
        <ArrowRight size={12} />
      </Link>
    </div>
  );
}
