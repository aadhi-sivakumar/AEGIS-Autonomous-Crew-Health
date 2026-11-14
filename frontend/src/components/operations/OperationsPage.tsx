"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Crosshair,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { ActionCard } from "@/components/today/ActionCard";
import { EmergencyPanel } from "@/components/today/EmergencyPanel";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import type { GuidanceOut, OperationsOut } from "@/lib/types";

const TASK_ICONS: Record<string, typeof Wrench> = {
  eva: ShieldAlert,
  docking: Crosshair,
  maintenance: Wrench,
};

function gateStyles(gate: string) {
  if (gate === "ready")
    return {
      border: "border-aegis-green/50",
      badge: "border-aegis-green text-aegis-green",
      text: "text-aegis-green",
    };
  if (gate === "caution")
    return {
      border: "border-aegis-amber/50",
      badge: "border-aegis-amber text-aegis-amber",
      text: "text-aegis-amber",
    };
  return {
    border: "border-aegis-red/50",
    badge: "border-aegis-red text-aegis-red",
    text: "text-aegis-red",
  };
}

function ReadinessGauge({ pct }: { pct: number }) {
  const color = pct >= 85 ? "#53BE8B" : pct >= 60 ? "#E6AD57" : "#D96767";
  const r = 54;
  const c = 2 * Math.PI * r;
  const filled = c * (pct / 100);
  return (
    <div className="relative mx-auto h-[140px] w-[140px]">
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#2C4157" strokeWidth="8" />
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${filled} ${c - filled}`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-mono text-2xl text-aegis-text">{pct}%</div>
        <div className="text-[12px] uppercase tracking-wide text-aegis-muted">Readiness</div>
      </div>
    </div>
  );
}

export function OperationsPage() {
  const { selectedCrewId, refresh } = useApp();
  const [ops, setOps] = useState<OperationsOut | null>(null);
  const [guidance, setGuidance] = useState<GuidanceOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [o, g] = await Promise.all([
        api.getOperations(selectedCrewId),
        api.getGuidance(selectedCrewId),
      ]);
      setOps(o);
      setGuidance(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load operations");
    }
  }, [selectedCrewId]);

  useEffect(() => {
    void load();
  }, [load]);

  const markComplete = async () => {
    try {
      setBusy(true);
      await api.markAssessmentComplete(selectedCrewId, true);
      await load();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to mark complete");
    } finally {
      setBusy(false);
    }
  };

  if (error && !ops) {
    return <div className="p-4 text-aegis-red text-[12px]">{error}</div>;
  }

  if (!ops || !guidance) {
    return (
      <div className="flex h-40 items-center justify-center text-aegis-muted">
        Loading readiness gate…
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 pb-3">
      <div>
        <h1 className="text-lg font-medium text-aegis-text">Readiness Gate</h1>
        <p className="mt-2 text-[15px] text-aegis-muted">
          Step 3 of daily use: Ready / Caution / Not recommended before EVA, docking, or
          maintenance — based on your personal baseline.
        </p>
      </div>

      <p className="text-[14px] leading-snug text-aegis-muted">
        {ops.trust_line ?? guidance.trust_line}
      </p>

      {ops.gate_summary && (
        <div className="rounded border border-aegis-border bg-aegis-panel px-3 py-2.5 text-[14px] text-aegis-text">
          {ops.gate_summary}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {ops.tasks.map((task) => {
          const Icon = TASK_ICONS[task.id] ?? Wrench;
          const gate = task.gate ?? (task.status === "ready" ? "ready" : task.status === "assessment_recommended" ? "caution" : "not_recommended");
          const styles = gateStyles(gate);
          const href =
            task.status === "assessment_recommended"
              ? "/assessment"
              : task.status === "review_required"
                ? "#guidance"
                : undefined;
          return (
            <div
              key={task.id}
              className={`rounded border bg-aegis-panel p-3 ${styles.border}`}
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon size={16} className="text-aegis-cyan" />
                  <div className="text-[15px] font-medium text-aegis-text">{task.name}</div>
                </div>
                <span
                  className={`rounded border px-1.5 py-0.5 text-[11px] uppercase tracking-wide ${styles.badge}`}
                >
                  {task.status_label}
                </span>
              </div>
              <p className="mb-2 text-[14px] leading-snug text-aegis-muted">{task.justification}</p>
              {task.recheck_hint && (
                <p className="mb-3 text-[13px] leading-snug text-aegis-amber">{task.recheck_hint}</p>
              )}
              {href ? (
                <Link
                  href={href}
                  className="inline-flex text-[14px] text-aegis-cyan hover:underline"
                >
                  {task.action_label}
                </Link>
              ) : (
                <span className="text-[14px] text-aegis-muted">{task.action_label}</span>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title="Readiness Summary">
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center sm:gap-6">
            <ReadinessGauge pct={ops.readiness_pct} />
            <div className="min-w-0 flex-1">
              <div className="label-caps mb-2">Why (vs your baseline)</div>
              <ul className="space-y-1.5 text-[14px] text-aegis-muted">
                {ops.key_factors.map((f) => (
                  <li key={f} className="flex gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-aegis-amber" />
                    <span className="leading-snug">{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>

        <Panel title="Action center" className="scroll-mt-4">
          <div id="guidance" className="space-y-3">
            {(guidance.actions ?? []).length > 0 ? (
              guidance.actions!.slice(0, 4).map((a) => <ActionCard key={a.id} item={a} />)
            ) : guidance.alerts.length === 0 ? (
              <div className="flex items-center gap-2 text-[14px] text-aegis-green">
                <CheckCircle2 size={14} />
                No active multi-indicator advisories.
              </div>
            ) : (
              guidance.alerts.map((a, i) => (
                <div
                  key={`${a.summary}-${i}`}
                  className={`rounded border px-2.5 py-2 text-[14px] ${
                    a.severity === "red"
                      ? "border-aegis-red/40 bg-aegis-red/10 text-aegis-red"
                      : "border-aegis-amber/40 bg-aegis-amber/10 text-aegis-amber"
                  }`}
                >
                  <div className="mb-1 flex items-center gap-1.5 font-medium">
                    <AlertTriangle size={12} />
                    {a.action ?? "Advisory"}
                  </div>
                  <p className="leading-snug opacity-90">{a.summary}</p>
                </div>
              ))
            )}

            <div className="flex flex-wrap gap-2 pt-1">
              <Link
                href="/assessment"
                className="inline-flex items-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/10 px-3 py-1.5 text-[14px] text-aegis-cyan"
              >
                <ClipboardCheck size={12} />
                Open Assessment
              </Link>
              <button
                type="button"
                disabled={busy || guidance.assessment_complete}
                onClick={() => void markComplete()}
                className="rounded border border-aegis-border px-3 py-1.5 text-[14px] text-aegis-muted hover:border-aegis-cyan hover:text-aegis-cyan disabled:opacity-50"
              >
                {guidance.assessment_complete
                  ? "Assessment marked complete"
                  : "Mark assessment complete"}
              </button>
              <Link
                href="#emergency"
                className="rounded border border-aegis-red/40 px-3 py-1.5 text-[14px] text-aegis-red hover:bg-aegis-red/10"
              >
                Emergency steps →
              </Link>
              <Link
                href="/telemetry"
                className="rounded border border-aegis-border px-3 py-1.5 text-[14px] text-aegis-muted hover:border-aegis-cyan hover:text-aegis-cyan"
              >
                Escalate / health summary →
              </Link>
            </div>
          </div>
        </Panel>
      </div>

      <div id="emergency" className="scroll-mt-4">
        <EmergencyPanel guidance={guidance} />
      </div>

      {error && <div className="text-[14px] text-aegis-red">{error}</div>}
    </div>
  );
}
