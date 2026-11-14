import clsx from "clsx";
import type { ReactNode } from "react";

export function Panel({
  children,
  className,
  title,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  action?: ReactNode;
}) {
  return (
    <section className={clsx("panel flex flex-col", className)}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-aegis-border px-3 py-2">
          {title ? (
            <h2 className="min-w-0 truncate text-[15px] font-medium tracking-wide text-aegis-text">
              {title}
            </h2>
          ) : (
            <span />
          )}
          {action ? <div className="shrink-0">{action}</div> : null}
        </header>
      )}
      <div className="min-h-0 flex-1 p-3">{children}</div>
    </section>
  );
}
