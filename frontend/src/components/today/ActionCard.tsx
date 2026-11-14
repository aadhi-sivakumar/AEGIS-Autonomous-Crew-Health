"use client";

import Link from "next/link";
import type { ActionItem } from "@/lib/types";
import { statusColor } from "@/lib/format";

interface Props {
  item: ActionItem;
}

export function ActionCard({ item }: Props) {
  return (
    <div
      className="rounded border px-3 py-2.5"
      style={{ borderColor: `${statusColor(item.severity)}55` }}
    >
      <p className="text-[13px] leading-snug text-aegis-text">{item.summary}</p>
      <p className="mt-1 text-[12px] leading-snug text-aegis-muted">{item.reason}</p>
      <div className="mt-2.5 flex flex-wrap gap-2">
        <Link
          href={item.do_href}
          className="rounded border border-aegis-cyan bg-aegis-cyan/10 px-2.5 py-1.5 text-[12px] text-aegis-cyan"
        >
          {item.do_label}
        </Link>
        {item.escalate_label && item.escalate_href ? (
          <Link
            href={item.escalate_href}
            className="rounded border border-aegis-border px-2.5 py-1.5 text-[12px] text-aegis-muted hover:text-aegis-text"
          >
            {item.escalate_label}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
