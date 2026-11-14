from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..schemas import SimulateIn, SimulateOut
from ..services.demo import get_scenario
from ..services.forecast import scenario_reaction_time

router = APIRouter(prefix="/api", tags=["simulate"])


@router.post("/simulate", response_model=SimulateOut)
def simulate(body: SimulateIn, db: Session = Depends(get_db)):
    crew = db.get(CrewMember, body.astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {body.astronaut_id}")

    state = get_scenario(db)
    try:
        result = scenario_reaction_time(
            db,
            body.astronaut_id,
            state.mission_day,
            sleep_h=body.sleep_h,
            co2_ppm=body.co2_ppm,
            fatigue=body.fatigue,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return SimulateOut(
        current_estimate=result["current_estimate"],
        hypothetical_estimate=result["hypothetical_estimate"],
        delta_ms=result["delta_ms"],
        delta_pct=result["delta_pct"],
        drivers=result["drivers"],
        disclaimer=result["disclaimer"],
        series_current=result["series_current"],
        series_hypothetical=result["series_hypothetical"],
    )
