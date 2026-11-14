from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..schemas import TelemetryCreateIn, TelemetryQueueOut, TelemetryReportOut
from ..services import telemetry as telemetry_service

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.post("/reports", response_model=TelemetryReportOut)
def create_report(body: TelemetryCreateIn, db: Session = Depends(get_db)):
    if not db.get(CrewMember, body.astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {body.astronaut_id}")
    return telemetry_service.create_report(db, body.astronaut_id)


@router.get("/queue", response_model=TelemetryQueueOut)
def get_queue(db: Session = Depends(get_db)):
    return telemetry_service.list_queue(db)


@router.post("/simulate-transmission")
def simulate_transmission(db: Session = Depends(get_db)):
    return telemetry_service.simulate_transmission(db)


@router.get("/reports/{report_id}/export")
def export_report(report_id: str, db: Session = Depends(get_db)):
    path = telemetry_service.export_report_path(db, report_id)
    if not path:
        raise HTTPException(status_code=404, detail="Report artifact not found")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{report_id}.bin",
    )
