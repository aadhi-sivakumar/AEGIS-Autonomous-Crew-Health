"use client";

import type { ReactNode } from "react";
import { AppProvider, useApp } from "@/lib/AppContext";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

function ShellInner({ children }: { children: ReactNode }) {
  const { error } = useApp();
  return (
    <div className="flex h-screen min-h-[720px] w-full flex-col overflow-hidden bg-aegis-bg text-aegis-text">
      <TopBar />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-3">
          {error && (
            <div className="mb-3 rounded border border-aegis-red/50 bg-aegis-red/10 px-3 py-2 text-[12px] text-aegis-red">
              Backend unreachable or error: {error}. Start FastAPI on port 8000.
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AppProvider>
      <ShellInner>{children}</ShellInner>
    </AppProvider>
  );
}
