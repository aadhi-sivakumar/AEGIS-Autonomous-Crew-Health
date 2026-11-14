"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Download, Lock, Plus, Radio, Send } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import type { TelemetryQueue, TelemetryReport } from "@/lib/types";

function formatCountdown(total: number) {
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `T - ${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function TelemetryPage() {
  const { selectedCrewId } = useApp();
  const [queue, setQueue] = useState<TelemetryQueue | null>(null);
  const [selected, setSelected] = useState<TelemetryReport | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const q = await api.getTelemetryQueue();
      setQueue(q);
      setCountdown(q.countdown_seconds);
      setSelected((prev) => {
        if (prev && q.reports.find((r) => r.id === prev.id)) {
          return q.reports.find((r) => r.id === prev.id) ?? q.reports[0] ?? null;
        }
        return q.reports[0] ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load telemetry queue");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!queue) return;
    const id = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : queue.countdown_seconds));
    }, 1000);
    return () => clearInterval(id);
  }, [queue]);

  const queuedCount = useMemo(
    () => queue?.reports.filter((r) => r.status === "queued").length ?? 0,
    [queue]
  );

  const generate = async () => {
    try {
      setBusy(true);
      setMessage(null);
      const report = await api.createTelemetryReport(selectedCrewId);
      setMessage(`Report ${report.id} queued (AES-GCM encrypted locally).`);
      await load();
      setSelected(report);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setBusy(false);
    }
  };

  const transmit = async () => {
    try {
      setBusy(true);
      setMessage(null);
      const out = await api.simulateTransmission();
      setMessage(out.detail);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transmission simulation failed");
    } finally {
      setBusy(false);
    }
  };

  if (!queue && !error) {
    return (
      <div className="flex h-40 items-center justify-center text-aegis-muted">
        Loading telemetry queue…
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 pb-3">
      <div>
        <h1 className="text-lg font-medium text-aegis-text">Telemetry & Relay</h1>
        <p className="mt-2 text-[15px] text-aegis-muted">
          Queued medical reports and simulated relay communications.
        </p>
      </div>

      <div className="rounded border border-aegis-amber/40 bg-aegis-amber/5 px-3 py-2 text-[11px] text-aegis-amber">
        Simulated communications window only — no real NASA relay integration.
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title={`Report Queue (${queue?.reports.length ?? 0})`}>
          <div className="space-y-2">
            {(queue?.reports ?? []).length === 0 && (
              <p className="text-[11px] text-aegis-muted">
                No reports yet. Generate a local encrypted health summary for {selectedCrewId}.
              </p>
            )}
            {(queue?.reports ?? []).map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => setSelected(r)}
                className={`flex w-full items-center justify-between rounded border px-2.5 py-2 text-left transition-colors ${
                  selected?.id === r.id
                    ? "border-aegis-cyan/50 bg-aegis-cyan/10"
                    : "border-aegis-border hover:border-aegis-cyan/30"
                }`}
              >
                <div>
                  <div className="font-mono text-[12px] text-aegis-text">{r.id}</div>
                  <div className="text-[10px] text-aegis-muted">
                    Mission Day {r.mission_day} • {r.astronaut_id}
                  </div>
                </div>
                <span
                  className={`rounded border px-1.5 py-0.5 text-[9px] uppercase ${
                    r.status === "sent"
                      ? "border-aegis-green text-aegis-green"
                      : "border-aegis-amber text-aegis-amber"
                  }`}
                >
                  {r.status}
                </span>
              </button>
            ))}

            <button
              type="button"
              disabled={busy}
              onClick={() => void generate()}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/10 px-3 py-2 text-[12px] text-aegis-cyan disabled:opacity-50"
            >
              <Plus size={14} />
              Generate New Report
            </button>
          </div>
        </Panel>

        <Panel title="Next Communication Window">
          <div className="flex flex-col items-center gap-3 py-2 text-center">
            <Radio size={28} className="text-aegis-cyan" />
            <div className="font-mono text-3xl tracking-tight text-aegis-text">
              {formatCountdown(countdown)}
            </div>
            <p className="max-w-sm text-[14px] leading-snug text-aegis-muted">
              {queue?.next_window_label}
            </p>
            <p className="max-w-sm text-[13px] leading-snug text-aegis-muted">
              Countdown until the next simulated Mars relay pass when queued encrypted reports can
              be transmitted to ground.
            </p>
            <button
              type="button"
              disabled={busy || queuedCount === 0}
              onClick={() => void transmit()}
              className="inline-flex items-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/15 px-4 py-2 text-[12px] text-aegis-cyan disabled:opacity-40"
            >
              <Send size={14} />
              Transmit Queued Reports ({queuedCount})
            </button>
          </div>
        </Panel>
      </div>

      <Panel
        title={selected ? `Report Content (${selected.id})` : "Report Content"}
        action={
          selected ? (
            <a
              href={api.exportReportUrl(selected.id)}
              className="inline-flex items-center gap-1 text-[10px] text-aegis-cyan hover:underline"
            >
              <Download size={11} />
              Export encrypted artifact
            </a>
          ) : null
        }
      >
        {selected ? (
          <div className="flex flex-wrap items-center gap-4">
            {selected.sections.map((s) => (
              <div key={s} className="flex items-center gap-1.5 text-[12px] text-aegis-text">
                <Check size={12} className="text-aegis-green" />
                {s}
              </div>
            ))}
            <div className="ml-auto flex items-center gap-1.5 text-[11px] text-aegis-amber">
              <Lock size={12} />
              Encrypted (AES-GCM)
            </div>
          </div>
        ) : (
          <p className="text-[11px] text-aegis-muted">Select or generate a report to preview.</p>
        )}
      </Panel>

      {message && (
        <div className="rounded border border-aegis-green/40 bg-aegis-green/10 px-3 py-2 text-[11px] text-aegis-green">
          {message}
        </div>
      )}
      {error && (
        <div className="rounded border border-aegis-red/40 bg-aegis-red/10 px-3 py-2 text-[11px] text-aegis-red">
          {error}
        </div>
      )}
    </div>
  );
}
