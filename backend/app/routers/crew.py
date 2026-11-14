from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..schemas import CrewMemberOut

router = APIRouter(prefix="/api", tags=["crew"])


@router.get("/crew", response_model=list[CrewMemberOut])
def list_crew(db: Session = Depends(get_db)):
    rows = db.query(CrewMember).order_by(CrewMember.id.asc()).all()
    return [
        CrewMemberOut(
            id=r.id,
            callsign=r.callsign,
            role=r.role,
            scenario_profile=r.scenario_profile,
        )
        for r in rows
    ]
