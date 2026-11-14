from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..schemas import (
    CheckInIn,
    CheckInOut,
    PromptSnoozeIn,
    SymptomCheckIn,
    SymptomCheckOut,
    TodayOut,
)
from ..services import today as today_service
from ..services.demo import get_scenario
from ..services.metric_explain import all_explainers

router = APIRouter(prefix="/api", tags=["today"])


@router.get("/today/{astronaut_id}", response_model=TodayOut)
def get_today(astronaut_id: str, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    return today_service.build_today(db, astronaut_id)


@router.get("/checkins/{astronaut_id}", response_model=Optional[CheckInOut])
def get_checkin(astronaut_id: str, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    state = get_scenario(db)
    row = today_service.get_checkin(db, astronaut_id, state.mission_day)
    if not row:
        return None
    return today_service._checkin_out(row)


@router.post("/checkins", response_model=CheckInOut)
def post_checkin(body: CheckInIn, db: Session = Depends(get_db)):
    if not db.get(CrewMember, body.astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {body.astronaut_id}")
    return today_service.submit_checkin(db, body)


@router.post("/symptoms", response_model=SymptomCheckOut)
def post_symptoms(body: SymptomCheckIn, db: Session = Depends(get_db)):
    if not db.get(CrewMember, body.astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {body.astronaut_id}")
    return today_service.submit_symptoms(db, body)


@router.get("/symptoms/{astronaut_id}", response_model=Optional[SymptomCheckOut])
def get_symptoms(astronaut_id: str, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    state = get_scenario(db)
    row = today_service.get_latest_symptoms(db, astronaut_id, state.mission_day)
    if not row:
        return None
    return today_service._symptom_out(row)


@router.post("/prompts/{astronaut_id}/snooze")
def snooze_prompt(astronaut_id: str, body: PromptSnoozeIn, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    state = get_scenario(db)
    try:
        return today_service.snooze_prompt(db, body.kind, astronaut_id, state.mission_day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/explainers")
def explainers():
    return all_explainers()
