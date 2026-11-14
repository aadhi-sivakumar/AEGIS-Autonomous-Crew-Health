from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AssessmentResult, CrewMember
from ..schemas import AssessmentCompleteIn, GuidanceOut
from ..services import guidance as guidance_service

router = APIRouter(prefix="/api", tags=["guidance"])


@router.get("/guidance/{astronaut_id}", response_model=GuidanceOut)
def get_guidance(astronaut_id: str, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    out = guidance_service.build_guidance(db, astronaut_id)
    has_browser = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.astronaut_id == astronaut_id)
        .count()
        > 0
    )
    out.assessment_complete = guidance_service.is_assessment_marked_complete(db, astronaut_id)
    out.has_browser_assessment = has_browser
    return out


@router.post("/guidance/{astronaut_id}/assessment-complete")
def mark_complete(
    astronaut_id: str,
    body: AssessmentCompleteIn,
    db: Session = Depends(get_db),
):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    return guidance_service.mark_assessment_complete(db, astronaut_id, body.complete)
