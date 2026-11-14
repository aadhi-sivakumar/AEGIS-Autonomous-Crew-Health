from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DemoScenarioIn, DemoScenarioOut
from ..services import demo as demo_service

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenario", response_model=DemoScenarioOut)
def get_demo_scenario(db: Session = Depends(get_db)):
    return demo_service.get_scenario(db)


@router.post("/scenario", response_model=DemoScenarioOut)
def set_demo_scenario(body: DemoScenarioIn, db: Session = Depends(get_db)):
    return demo_service.set_scenario(db, body.scenario)


@router.post("/reset", response_model=DemoScenarioOut)
def reset_demo(db: Session = Depends(get_db)):
    return demo_service.reset_demo(db)
