"use client";

import { useEffect, useState } from "react";
import { useApp } from "@/lib/AppContext";
import { AegisLogo } from "./AegisLogo";

export function TopBar() {
  const { crew, selectedCrewId, setSelectedCrewId, overview, scenario } = useApp();
  const [now, setNow] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setNow(
        d.toLocaleTimeString("en-GB", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const missionDay = overview?.mission_day ?? scenario?.mission_day ?? "—";

  return (
    <header className="relative z-20 flex h-12 shrink-0 items-center border-b border-aegis-border bg-aegis-bg px-4">
      <div className="z-10 flex min-w-0 items-center gap-2.5">
        <AegisLogo className="h-7 w-7 shrink-0" />
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-wide text-aegis-text">AEGIS</div>
          <div className="hidden text-[10px] uppercase tracking-[0.12em] text-aegis-muted xl:block">
            Autonomous Crew Health
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 top-0 flex h-12 items-center justify-center">
        <div className="whitespace-nowrap font-mono text-xs text-aegis-text">
          LONG-DURATION MISSION <span className="text-aegis-muted">|</span>{" "}
          <span className="text-aegis-cyan">DAY {missionDay}</span>
        </div>
      </div>

      <div className="z-10 ml-auto flex items-center gap-3">
        <div className="hidden whitespace-nowrap font-mono text-[11px] text-aegis-muted 2xl:block">
          {now}
        </div>
        <div className="flex items-center gap-1.5 whitespace-nowrap text-[11px] text-aegis-green">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-aegis-green" />
          LOCAL
        </div>
        <label className="flex items-center gap-1.5 text-[11px] text-aegis-muted">
          Crew
          <select
            className="rounded border border-aegis-border bg-aegis-panel px-2 py-1 font-mono text-[11px] text-aegis-text outline-none focus:border-aegis-cyan"
            value={selectedCrewId}
            onChange={(e) => setSelectedCrewId(e.target.value)}
          >
            {crew.map((c) => (
              <option key={c.id} value={c.id}>
                {c.callsign}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
