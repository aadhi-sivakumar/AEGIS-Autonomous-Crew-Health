from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AppState, CrewMember, NasaEnvSample
from ..schemas import BaselineOut, HealthOverviewOut
from ..services import baselines as bl
from ..services import nasa_eda_service as nasa
from ..services.demo import get_scenario
from ..services.rr1_api import SOURCE_LABEL

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health/{astronaut_id}", response_model=HealthOverviewOut)
def health_overview(astronaut_id: str, db: Session = Depends(get_db)):
    crew = db.get(CrewMember, astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")

    scenario_state = get_scenario(db)
    mission_day = scenario_state.mission_day
    env_mode = nasa.get_env_data_mode(db)

    history = bl.get_health_history(db, astronaut_id, mission_day)
    env = bl.get_environment_history(db, mission_day)
    nasa_flag = db.get(AppState, "nasa_import_loaded")
    eda_flag = db.get(AppState, "nasa_eda_cached")
    nasa_loaded = bool(nasa_flag and nasa_flag.value.lower() == "true")
    eda_cached = bool(eda_flag and eda_flag.value.lower() == "true") or nasa.is_mission_cached(
        db, "RR-1"
    )
    rr1_cached = db.query(NasaEnvSample).count() > 0
    nasa_ready = nasa_loaded or rr1_cached or eda_cached

    if env_mode == "nasa_historical":
        if not nasa_ready:
            env_banner = (
                "NASA Historical Data selected — no RR-1 cache. "
                "Import on NASA Mission Replay. Crew health remains SIMULATED."
            )
        else:
            env_banner = (
                f"{SOURCE_LABEL} · Cabin env from NASA RR-1. "
                "Crew health remains SIMULATED CREW DATA."
            )
    else:
        env_banner = "Simulated Mission Data — synthetic cabin environment."

    return HealthOverviewOut(
        astronaut_id=astronaut_id,
        mission_day=mission_day,
        scenario=scenario_state.scenario,
        history=bl.records_to_points(history),
        environment=bl.env_to_points(env),
        metrics=bl.build_metrics(db, astronaut_id, mission_day),
        zones=bl.zone_statuses(db, astronaut_id, mission_day),
        deviations=bl.detect_deviations(db, astronaut_id, mission_day),
        combined_pattern=bl.detect_combined_patterns(db, astronaut_id, mission_day),
        forecast=bl.simple_forecast(db, astronaut_id, mission_day),
        nasa_import_loaded=nasa_ready and env_mode == "nasa_historical",
        environment_banner=env_banner,
    )


@router.get("/health/{astronaut_id}/baseline", response_model=BaselineOut)
def health_baseline(astronaut_id: str, db: Session = Depends(get_db)):
    crew = db.get(CrewMember, astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    scenario_state = get_scenario(db)
    baselines = bl.calculate_baselines(db, astronaut_id, scenario_state.mission_day)
    return BaselineOut(
        astronaut_id=astronaut_id,
        window_days=14,
        baselines=baselines,
        method="median of early stable window (prototype)",
    )


@router.get("/health/{astronaut_id}/forecast")
def health_forecast(astronaut_id: str, db: Session = Depends(get_db)):
    crew = db.get(CrewMember, astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    scenario_state = get_scenario(db)
    return bl.simple_forecast(db, astronaut_id, scenario_state.mission_day)
