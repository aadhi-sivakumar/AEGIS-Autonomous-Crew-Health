"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { CrewMember, DemoScenario, DemoScenarioOut, HealthOverview } from "./types";

interface AppContextValue {
  crew: CrewMember[];
  selectedCrewId: string;
  setSelectedCrewId: (id: string) => void;
  scenario: DemoScenarioOut | null;
  setScenario: (s: DemoScenario) => Promise<void>;
  resetDemo: () => Promise<void>;
  overview: HealthOverview | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

const SCENARIO_DEFAULT_CREW: Record<DemoScenario, string> = {
  stable: "PLT-02",
  emerging_decline: "CDR-01",
  recovery: "FE-03",
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [crew, setCrew] = useState<CrewMember[]>([]);
  const [selectedCrewId, setSelectedCrewId] = useState("CDR-01");
  const [scenario, setScenarioState] = useState<DemoScenarioOut | null>(null);
  const [overview, setOverview] = useState<HealthOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [crewList, scenarioOut, health] = await Promise.all([
        api.getCrew(),
        api.getScenario(),
        api.getHealth(selectedCrewId),
      ]);
      setCrew(crewList);
      setScenarioState(scenarioOut);
      setOverview(health);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load AEGIS data");
    } finally {
      setLoading(false);
    }
  }, [selectedCrewId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setScenario = useCallback(
    async (s: DemoScenario) => {
      const out = await api.setScenario(s);
      setScenarioState(out);
      const nextCrew = SCENARIO_DEFAULT_CREW[s];
      setSelectedCrewId(nextCrew);
      const health = await api.getHealth(nextCrew);
      setOverview(health);
    },
    []
  );

  const resetDemo = useCallback(async () => {
    const out = await api.resetDemo();
    setScenarioState(out);
    setSelectedCrewId(SCENARIO_DEFAULT_CREW[out.scenario]);
    await refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({
      crew,
      selectedCrewId,
      setSelectedCrewId,
      scenario,
      setScenario,
      resetDemo,
      overview,
      loading,
      error,
      refresh,
    }),
    [
      crew,
      selectedCrewId,
      scenario,
      setScenario,
      resetDemo,
      overview,
      loading,
      error,
      refresh,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
