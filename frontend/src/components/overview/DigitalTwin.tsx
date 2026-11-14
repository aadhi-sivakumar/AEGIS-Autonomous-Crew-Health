"use client";

import { useState } from "react";
import type { ZoneStatusOut } from "@/lib/types";
import { statusColor } from "@/lib/format";
import { Panel } from "@/components/ui/Panel";

interface Props {
  zones: ZoneStatusOut[];
  onSelectZone: (zone: ZoneStatusOut) => void;
  selectedZone: string | null;
}

const ZONE_TITLE: Record<string, string> = {
  head: "Cognitive",
  torso: "Cardiopulmonary",
  core: "Core",
};

export function DigitalTwin({ zones, onSelectZone, selectedZone }: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const byZone = Object.fromEntries(zones.map((z) => [z.zone, z])) as Record<
    string,
    ZoneStatusOut
  >;

  const head = byZone.head;
  const torso = byZone.torso;
  const core = byZone.core;
  const active = hover ?? selectedZone;

  const Callout = ({ zone }: { zone: ZoneStatusOut }) => (
    <button
      type="button"
      className={`w-full rounded border px-2.5 py-2 text-left transition-colors ${
        selectedZone === zone.zone
          ? "bg-aegis-bg/70"
          : "border-transparent hover:border-aegis-border hover:bg-aegis-bg/50"
      }`}
      style={
        selectedZone === zone.zone ? { borderColor: statusColor(zone.status) } : undefined
      }
      onMouseEnter={() => setHover(zone.zone)}
      onMouseLeave={() => setHover(null)}
      onClick={() => onSelectZone(zone)}
    >
      <div className="flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ background: statusColor(zone.status) }}
        />
        <span className="text-[14px] font-medium leading-none text-aegis-text">
          {ZONE_TITLE[zone.zone] ?? zone.label}
        </span>
      </div>
      <div
        className="mt-1.5 pl-3.5 font-mono text-[12px] leading-snug"
        style={{ color: statusColor(zone.status) }}
      >
        {zone.status.toUpperCase()} — {zone.detail}
      </div>
    </button>
  );

  return (
    <Panel title="Astronaut Health Digital Twin" className="flex h-full min-h-0 w-full flex-col">
      <p className="mb-3 text-[13px] leading-snug text-aegis-muted">
        Visualizes monitored indicators — not a physiological simulation.
      </p>

      <div className="flex min-h-0 flex-1 items-stretch gap-1">
        <div className="flex w-[46%] shrink-0 items-center">
          <svg
            viewBox="0 0 200 420"
            className="mx-auto block h-full max-h-[460px] w-full"
            role="img"
            aria-label="Crew digital twin"
          >
            <path
              d="M100 28 C118 28 130 42 130 58 C130 74 118 88 100 88 C82 88 70 74 70 58 C70 42 82 28 100 28 Z"
              fill="#0F1C2C"
              stroke={statusColor(head?.status ?? "green")}
              strokeWidth={active === "head" ? 2.5 : 1.5}
              className="cursor-pointer"
              onMouseEnter={() => setHover("head")}
              onMouseLeave={() => setHover(null)}
              onClick={() => head && onSelectZone(head)}
            />
            <rect x="92" y="86" width="16" height="18" fill="#142337" stroke="#2C4157" strokeWidth="1" />
            <path
              d="M62 104 L138 104 L148 210 L130 250 L70 250 L52 210 Z"
              fill="#0F1C2C"
              stroke={statusColor(torso?.status ?? "green")}
              strokeWidth={active === "torso" ? 2.5 : 1.5}
              className="cursor-pointer"
              onMouseEnter={() => setHover("torso")}
              onMouseLeave={() => setHover(null)}
              onClick={() => torso && onSelectZone(torso)}
            />
            <path d="M62 110 L28 180 L40 188 L70 130 Z" fill="#142337" stroke="#2C4157" strokeWidth="1" />
            <path d="M138 110 L172 180 L160 188 L130 130 Z" fill="#142337" stroke="#2C4157" strokeWidth="1" />
            <path
              d="M70 248 L130 248 L125 300 L75 300 Z"
              fill="#0F1C2C"
              stroke={statusColor(core?.status ?? "green")}
              strokeWidth={active === "core" ? 2.5 : 1.5}
              className="cursor-pointer"
              onMouseEnter={() => setHover("core")}
              onMouseLeave={() => setHover(null)}
              onClick={() => core && onSelectZone(core)}
            />
            <path d="M75 298 L95 298 L92 400 L70 400 Z" fill="#142337" stroke="#2C4157" strokeWidth="1" />
            <path d="M105 298 L125 298 L130 400 L108 400 Z" fill="#142337" stroke="#2C4157" strokeWidth="1" />
            <circle cx="100" cy="58" r="18" fill="none" stroke="#55B8E8" strokeWidth="0.6" opacity="0.35" />
            <line x1="100" y1="104" x2="100" y2="248" stroke="#55B8E8" strokeWidth="0.5" opacity="0.25" />
          </svg>
        </div>

        <div className="flex min-w-0 flex-1 flex-col justify-center gap-5 py-6 pl-1">
          {head && <Callout zone={head} />}
          {torso && <Callout zone={torso} />}
          {core && <Callout zone={core} />}
        </div>
      </div>
    </Panel>
  );
}
