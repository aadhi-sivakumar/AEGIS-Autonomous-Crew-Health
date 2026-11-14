"use client";

import clsx from "clsx";
import {
  Activity,
  ClipboardCheck,
  Home,
  LineChart,
  Play,
  Radio,
  Rocket,
  Satellite,
  SlidersHorizontal,
  LayoutDashboard,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useApp } from "@/lib/AppContext";
import { api } from "@/lib/api";
import { SCENARIO_OPTIONS } from "@/lib/format";
import type { DemoScenario } from "@/lib/types";

const NAV = [
  { href: "/", label: "Today", icon: Home },
  { href: "/trends", label: "Trends & Forecasts", icon: LineChart },
  { href: "/assessment", label: "Assessments", icon: ClipboardCheck },
  { href: "/operations", label: "Readiness Gate", icon: Rocket },
  { href: "/overview", label: "Digital Twin", icon: LayoutDashboard },
  { href: "/what-if", label: "What-If Simulator", icon: SlidersHorizontal },
  { href: "/nasa-replay", label: "NASA Mission Replay", icon: Satellite },
  { href: "/telemetry", label: "Telemetry & Relay", icon: Radio },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { scenario, setScenario, resetDemo, refresh } = useApp();
  const [envMode, setEnvMode] = useState<"simulated" | "nasa_historical">("simulated");
  const [nasaCached, setNasaCached] = useState(false);
  const [guidedBusy, setGuidedBusy] = useState(false);
  const [guidedMsg, setGuidedMsg] = useState<string | null>(null);

  useEffect(() => {
    void api
      .getEnvMode()
      .then((m) => {
        setEnvMode(m.mode === "nasa_historical" ? "nasa_historical" : "simulated");
        setNasaCached(Boolean(m.nasa_cached));
      })
      .catch(() => undefined);
  }, []);

  const changeEnvMode = async (mode: "simulated" | "nasa_historical") => {
    try {
      const out = await api.setEnvMode(mode);
      setEnvMode(out.mode === "nasa_historical" ? "nasa_historical" : "simulated");
      setNasaCached(Boolean(out.nasa_cached));
      await refresh();
    } catch {
      /* keep prior mode */
    }
  };

  const startGuidedDemo = async () => {
    try {
      setGuidedBusy(true);
      setGuidedMsg(null);

      // 1) Emerging Decline scenario (CDR-01)
      await setScenario("emerging_decline");

      // 2) Ensure NASA RR-1 is cached, then switch env mode
      let cached = nasaCached;
      if (!cached) {
        setGuidedMsg("Importing NASA RR-1…");
        try {
          await api.nasaImport("RR-1");
          cached = true;
        } catch {
          cached = false;
        }
      }

      const out = await api.setEnvMode("nasa_historical");
      setEnvMode(out.mode === "nasa_historical" ? "nasa_historical" : "simulated");
      setNasaCached(Boolean(out.nasa_cached) || cached);
      await refresh();

      setGuidedMsg(
        out.nasa_cached || cached
          ? "Guided demo ready — Emerging Decline + NASA Historical."
          : "Scenario set. NASA cache missing — import on Mission Replay."
      );
      router.push("/");
    } catch (e) {
      setGuidedMsg(e instanceof Error ? e.message : "Could not start guided demo");
    } finally {
      setGuidedBusy(false);
    }
  };

  const NavLink = ({
    href,
    label,
    icon: Icon,
  }: {
    href: string;
    label: string;
    icon: typeof Home;
  }) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={clsx(
          "flex items-center gap-2.5 rounded px-2.5 py-2 text-[13px] leading-none transition-colors",
          active
            ? "border border-aegis-cyan/40 bg-aegis-cyan/10 text-aegis-cyan"
            : "border border-transparent text-aegis-muted hover:bg-aegis-panel hover:text-aegis-text"
        )}
      >
        <Icon size={14} strokeWidth={1.75} className="shrink-0" />
        <span className="leading-tight">{label}</span>
      </Link>
    );
  };

  const scenarioBlurb =
    SCENARIO_OPTIONS.find((o) => o.value === (scenario?.scenario ?? "emerging_decline"))?.blurb ??
    "";

  return (
    <aside className="flex w-[208px] shrink-0 flex-col border-r border-aegis-border bg-aegis-bg">
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2 pt-3">
        {NAV.map((item) => (
          <NavLink key={item.href} {...item} />
        ))}
      </nav>

      <div className="border-t border-aegis-border p-3">
        <button
          type="button"
          disabled={guidedBusy}
          onClick={() => void startGuidedDemo()}
          className="mb-3 flex w-full items-center justify-center gap-1.5 rounded border border-aegis-cyan bg-aegis-cyan/15 px-2 py-2 text-[13px] text-aegis-cyan transition-colors hover:bg-aegis-cyan/25 disabled:opacity-50"
        >
          <Play size={13} strokeWidth={2} />
          {guidedBusy ? "Starting…" : "Start guided demo"}
        </button>
        {guidedMsg && (
          <p className="mb-3 text-[11px] leading-snug text-aegis-muted">{guidedMsg}</p>
        )}

        <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.08em] text-aegis-muted">
          Env Data Source
        </div>
        <select
          className="mb-3 w-full rounded border border-aegis-border bg-aegis-panel px-2 py-1.5 text-[12px] text-aegis-text outline-none focus:border-aegis-cyan"
          value={envMode}
          onChange={(e) => void changeEnvMode(e.target.value as "simulated" | "nasa_historical")}
        >
          <option value="simulated">Simulated Mission Data</option>
          <option value="nasa_historical">NASA Historical Data</option>
        </select>
        <p className="mb-3 text-[11px] leading-snug text-aegis-muted">
          {envMode === "nasa_historical"
            ? nasaCached
              ? "NASA RR-1 cached."
              : "Import RR-1 on Mission Replay."
            : "Synthetic cabin fixtures."}
        </p>

        <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.08em] text-aegis-muted">
          <Activity size={11} />
          Demo Scenario
        </div>
        <select
          className="mb-1 w-full rounded border border-aegis-border bg-aegis-panel px-2 py-1.5 text-[12px] text-aegis-text outline-none focus:border-aegis-cyan"
          value={scenario?.scenario ?? "emerging_decline"}
          onChange={(e) => void setScenario(e.target.value as DemoScenario)}
        >
          {SCENARIO_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <p className="mb-2 text-[11px] leading-snug text-aegis-muted">{scenarioBlurb}</p>
        <button
          type="button"
          onClick={() => void resetDemo()}
          className="w-full rounded border border-aegis-border px-2 py-1.5 text-[12px] text-aegis-muted transition-colors hover:border-aegis-cyan hover:text-aegis-cyan"
        >
          Reset Demo
        </button>
      </div>
    </aside>
  );
}
