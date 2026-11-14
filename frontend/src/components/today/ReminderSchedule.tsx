"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, BellOff, Check } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import type { ReminderSlot } from "@/lib/types";

const PREF_KEY = "aegis_reminder_notifications";
const NUDGE_MS = 45 * 60 * 1000; // 45 min soft re-nudge while tab is open

interface Props {
  slots: ReminderSlot[];
  astronautId: string;
}

export function ReminderSchedule({ slots, astronautId }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [perm, setPerm] = useState<NotificationPermission | "unsupported">("default");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pending = slots.filter((s) => !s.done);

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setPerm("unsupported");
      return;
    }
    setPerm(Notification.permission);
    setEnabled(localStorage.getItem(PREF_KEY) === "1" && Notification.permission === "granted");
  }, []);

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const fireNudge = useCallback(() => {
    if (!enabled || perm !== "granted" || pending.length === 0) return;
    const next = pending[0];
    try {
      new Notification("AEGIS measurement reminder", {
        body: `${next.label} still due (${next.window}).`,
        tag: `aegis-${astronautId}-${next.id}`,
      });
    } catch {
      /* ignore */
    }
  }, [enabled, perm, pending, astronautId]);

  useEffect(() => {
    clearTimer();
    if (!enabled || pending.length === 0) return;
    timerRef.current = setTimeout(fireNudge, NUDGE_MS);
    return clearTimer;
  }, [enabled, pending.length, fireNudge, astronautId]);

  const enableNotifications = async () => {
    if (typeof window === "undefined" || !("Notification" in window)) return;
    const result = await Notification.requestPermission();
    setPerm(result);
    if (result === "granted") {
      localStorage.setItem(PREF_KEY, "1");
      setEnabled(true);
      const next = slots.find((s) => !s.done);
      if (next) {
        new Notification("AEGIS reminders on", {
          body: `Next due: ${next.label}. We'll nudge again if this tab stays open.`,
          tag: `aegis-${astronautId}-enabled`,
        });
      }
    }
  };

  const disableNotifications = () => {
    localStorage.setItem(PREF_KEY, "0");
    setEnabled(false);
    clearTimer();
  };

  const doneCount = slots.filter((s) => s.done).length;

  return (
    <Panel
      title="Measurement reminders"
      action={
        <span className="font-mono text-[11px] text-aegis-muted">
          {doneCount}/{slots.length} done
        </span>
      }
    >
      <p className="mb-3 text-[12px] leading-snug text-aegis-muted">
        Today&apos;s measurement cadence. Complete each slot so status and readiness use fresh
        crew-entered data.
      </p>

      <ul className="space-y-2">
        {slots.map((s) => (
          <li key={s.id}>
            <Link
              href={s.href}
              className={`flex items-start gap-2.5 rounded border px-2.5 py-2 transition-colors hover:border-aegis-cyan/50 ${
                s.done
                  ? "border-aegis-green/30 bg-aegis-green/5"
                  : "border-aegis-amber/40 bg-aegis-amber/5"
              }`}
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                  s.done
                    ? "bg-aegis-green/20 text-aegis-green"
                    : "bg-aegis-amber/20 text-aegis-amber"
                }`}
              >
                {s.done ? <Check size={12} /> : <Bell size={11} />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-medium text-aegis-text">{s.label}</span>
                  <span className="text-[11px] text-aegis-muted">{s.how_long}</span>
                  <span
                    className={`text-[11px] uppercase tracking-wide ${
                      s.done ? "text-aegis-green" : "text-aegis-amber"
                    }`}
                  >
                    {s.done ? "Done" : "Due"}
                  </span>
                </div>
                <p className="mt-0.5 text-[12px] leading-snug text-aegis-muted">{s.window}</p>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      <div className="mt-3 border-t border-aegis-border pt-3">
        {perm === "unsupported" ? (
          <p className="text-[11px] text-aegis-muted">
            Browser notifications unavailable here — use the due list above while AEGIS is open.
          </p>
        ) : enabled ? (
          <button
            type="button"
            onClick={disableNotifications}
            className="inline-flex items-center gap-1.5 rounded border border-aegis-border px-2.5 py-1.5 text-[12px] text-aegis-muted hover:border-aegis-cyan hover:text-aegis-cyan"
          >
            <BellOff size={12} />
            Turn off browser nudges
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void enableNotifications()}
            className="inline-flex items-center gap-1.5 rounded border border-aegis-cyan/50 bg-aegis-cyan/10 px-2.5 py-1.5 text-[12px] text-aegis-cyan hover:bg-aegis-cyan/20"
          >
            <Bell size={12} />
            Enable browser reminders
          </button>
        )}
        {enabled && (
          <p className="mt-1.5 text-[11px] leading-snug text-aegis-muted">
            Soft nudge in ~45 min if measurements are still due and this tab stays open.
          </p>
        )}
      </div>
    </Panel>
  );
}
