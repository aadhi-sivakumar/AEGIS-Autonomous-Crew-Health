"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import { statusColor, statusPlain } from "@/lib/format";
import type { PromptItem, TodayOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { CheckInPanel } from "./CheckInPanel";
import { PromptBanner } from "./PromptBanner";
import { UsePath } from "./UsePath";

export function TodayPage() {
  const { selectedCrewId, refresh } = useApp();
  const [today, setToday] = useState<TodayOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [justCheckedIn, setJustCheckedIn] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getToday(selectedCrewId);
      setToday(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Today");
    } finally {
      setLoading(false);
    }
  }, [selectedCrewId]);

  useEffect(() => {
    void load();
    setJustCheckedIn(false);
  }, [load]);

  const onSnooze = async (kind: PromptItem["kind"]) => {
    try {
      await api.snoozePrompt(selectedCrewId, kind);
      await load();
    } catch {
      /* ignore */
    }
  };

  const onCheckInSaved = async () => {
    setJustCheckedIn(true);
    await load();
    await refresh();
  };

  if (loading && !today) {
    return (
      <div className="flex h-40 items-center justify-center text-aegis-muted">
        Loading today&apos;s status…
      </div>
    );
  }

  if (error && !today) {
    return <div className="p-4 text-[12px] text-aegis-red">{error}</div>;
  }

  if (!today) return null;

  const status = today.overall_status;
  const whyStatus =
    status === "green"
      ? "Why: indicators are close to your personal baseline — no multi-signal advisory."
      : `Why: ${today.plain_language.replace(/^Attention:\s*/i, "")} Compared to your early-mission baseline, not a fleet average.`;

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-3 pb-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-medium text-aegis-text">Today</h1>
          <p className="mt-2 text-[15px] text-aegis-muted">
            Day {today.mission_day} status versus your personal baseline
          </p>
        </div>
        <Link href="/overview" className="text-[12px] text-aegis-cyan hover:underline">
          Full digital twin →
        </Link>
      </div>

      <p className="text-[12px] leading-snug text-aegis-muted">{today.trust_line}</p>

      <UsePath today={today} />

      <PromptBanner prompts={today.prompts} onSnooze={(k) => void onSnooze(k)} />

      {justCheckedIn && (
        <div className="rounded border border-aegis-green/40 bg-aegis-green/10 px-3 py-2 text-[13px] text-aegis-green">
          Check-in saved — status now uses your log. Next: run the{" "}
          <Link href="/assessment" className="underline">
            Assessment
          </Link>
          , then open the Readiness Gate.
        </div>
      )}

      {/* Status hero */}
      <div
        id="status"
        className="scroll-mt-4 rounded border bg-aegis-panel px-4 py-4"
        style={{ borderColor: `${statusColor(status)}66` }}
      >
        <div className="flex flex-wrap items-center gap-3">
          <span
            className="inline-flex items-center gap-2 rounded border px-2.5 py-1 font-mono text-[13px]"
            style={{
              color: statusColor(status),
              borderColor: `${statusColor(status)}88`,
            }}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: statusColor(status) }}
            />
            {statusPlain(status).toUpperCase()}
          </span>
          <p className="min-w-0 flex-1 text-[14px] leading-snug text-aegis-text">
            {today.plain_language}
          </p>
        </div>

        <p className="mt-2 text-[13px] leading-snug text-aegis-muted">{whyStatus}</p>

        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {today.top_metrics.map((m) => (
            <div
              key={m.metric}
              className="rounded border border-aegis-border bg-aegis-bg/50 px-3 py-2.5"
            >
              <div className="label-caps mb-1">{m.label}</div>
              <div
                className="font-mono text-lg leading-none"
                style={{ color: statusColor(m.status) }}
              >
                {m.unit === "ms" || m.unit === "bpm" || m.unit === "ppm"
                  ? Math.round(m.latest)
                  : m.latest.toFixed(1)}
                <span className="ml-1 text-[10px] text-aegis-muted">{m.unit}</span>
              </div>
              <p className="mt-1.5 text-[12px] leading-snug text-aegis-muted">{m.plain}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-2 rounded border border-aegis-cyan/30 bg-aegis-cyan/5 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="label-caps mb-0.5 text-aegis-cyan">Primary action</div>
            <p className="text-[14px] text-aegis-text">{today.primary_action.label}</p>
            <p className="text-[12px] text-aegis-muted">{today.primary_action.reason}</p>
          </div>
          <Link
            href={today.primary_action.href}
            className="shrink-0 rounded border border-aegis-cyan bg-aegis-cyan/15 px-3 py-2 text-center text-[13px] text-aegis-cyan"
          >
            Do this →
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div id="checkin" className="scroll-mt-4">
          <CheckInPanel
            astronautId={selectedCrewId}
            existing={today.checkin}
            onSaved={() => void onCheckInSaved()}
          />
        </div>

        <Panel
          title="Cognitive forecast"
          action={
            <span className="text-[11px] uppercase tracking-wide text-aegis-muted">
              {today.forecast_model}
            </span>
          }
        >
          <div className="flex items-end justify-between gap-3">
            <div>
              <div className="label-caps mb-1">Next-day reaction time</div>
              <div className="font-mono text-2xl text-aegis-text">
                {Math.round(today.forecast_next_day_ms)}
                <span className="ml-1 text-sm text-aegis-muted">ms</span>
              </div>
            </div>
            <Link href="/trends" className="text-[13px] text-aegis-cyan hover:underline">
              Trends →
            </Link>
          </div>
          <p className="mt-2 text-[13px] leading-snug text-aegis-muted">
            {today.forecast_blurb}
          </p>
        </Panel>
      </div>
    </div>
  );
}
