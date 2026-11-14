from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AppState
from ..schemas import DemoScenario, DemoScenarioOut
from ..seed import CURRENT_MISSION_DAY, seed_database

SCENARIO_LABELS: dict[DemoScenario, str] = {
    "stable": "Stable Mission",
    "emerging_decline": "Emerging Decline",
    "recovery": "Recovery After Assessment",
}

# Demo scenario remaps mission day slice for the active trajectory.
SCENARIO_DAY: dict[DemoScenario, int] = {
    "stable": CURRENT_MISSION_DAY,
    "emerging_decline": CURRENT_MISSION_DAY,
    "recovery": 52,  # later in recovery arc
}


def _get_state(db: Session, key: str, default: str) -> str:
    row = db.get(AppState, key)
    return row.value if row else default


def _set_state(db: Session, key: str, value: str) -> None:
    row = db.get(AppState, key)
    if row:
        row.value = value
    else:
        db.add(AppState(key=key, value=value))
    db.commit()


def get_scenario(db: Session) -> DemoScenarioOut:
    scenario = _get_state(db, "demo_scenario", "emerging_decline")  # type: ignore[assignment]
    if scenario not in SCENARIO_LABELS:
        scenario = "emerging_decline"
    mission_day = int(_get_state(db, "mission_day", str(SCENARIO_DAY[scenario])))  # type: ignore[index]
    return DemoScenarioOut(
        scenario=scenario,  # type: ignore[arg-type]
        mission_day=mission_day,
        label=SCENARIO_LABELS[scenario],  # type: ignore[index]
    )


def set_scenario(db: Session, scenario: DemoScenario) -> DemoScenarioOut:
    _set_state(db, "demo_scenario", scenario)
    _set_state(db, "mission_day", str(SCENARIO_DAY[scenario]))
    return get_scenario(db)


def reset_demo(db: Session) -> DemoScenarioOut:
    seed_database(db, force=True)
    return get_scenario(db)
