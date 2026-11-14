from __future__ import annotations

from datetime import datetime
from statistics import median

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AssessmentResult, CrewMember, HealthRecord
from ..schemas import AssessmentIn, AssessmentOut
from ..services.demo import get_scenario

router = APIRouter(prefix="/api", tags=["assessments"])


@router.post("/assessments", response_model=AssessmentOut)
def create_assessment(body: AssessmentIn, db: Session = Depends(get_db)):
    crew = db.get(CrewMember, body.astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {body.astronaut_id}")

    state = get_scenario(db)
    row = AssessmentResult(
        astronaut_id=body.astronaut_id,
        mission_day=state.mission_day,
        median_rt_ms=body.median_rt_ms,
        iqr_ms=body.iqr_ms,
        trial_count=body.trial_count,
        invalid_count=body.invalid_count,
        provenance="BROWSER_MEASURED",
        created_at=datetime.utcnow(),
    )
    db.add(row)

    # Update current mission-day health record so dashboard / forecast reflect browser measurement.
    health = (
        db.query(HealthRecord)
        .filter(
            HealthRecord.astronaut_id == body.astronaut_id,
            HealthRecord.mission_day == state.mission_day,
        )
        .one_or_none()
    )
    if health:
        health.reaction_time_ms = round(body.median_rt_ms, 1)
        health.provenance = "BROWSER_MEASURED"
    else:
        # Clone prior day if needed
        prior = (
            db.query(HealthRecord)
            .filter(HealthRecord.astronaut_id == body.astronaut_id)
            .order_by(HealthRecord.mission_day.desc())
            .first()
        )
        if prior:
            db.add(
                HealthRecord(
                    astronaut_id=body.astronaut_id,
                    mission_day=state.mission_day,
                    sleep_h=prior.sleep_h,
                    resting_hr=prior.resting_hr,
                    fatigue=prior.fatigue,
                    mood=prior.mood,
                    reaction_time_ms=round(body.median_rt_ms, 1),
                    exercise_adherence=prior.exercise_adherence,
                    provenance="BROWSER_MEASURED",
                )
            )

    db.commit()
    db.refresh(row)

    baseline_vals = (
        db.query(HealthRecord.reaction_time_ms)
        .filter(HealthRecord.astronaut_id == body.astronaut_id)
        .order_by(HealthRecord.mission_day.asc())
        .limit(14)
        .all()
    )
    base = median([v[0] for v in baseline_vals]) if baseline_vals else body.median_rt_ms
    delta = body.median_rt_ms - base

    return AssessmentOut(
        id=row.id,
        astronaut_id=row.astronaut_id,
        mission_day=row.mission_day,
        median_rt_ms=row.median_rt_ms,
        iqr_ms=row.iqr_ms,
        provenance=row.provenance,
        message=(
            f"Browser assessment saved (Δ {delta:+.0f} ms vs early baseline). "
            "Dashboard metrics and forecast inputs updated."
        ),
    )


@router.get("/assessments/{astronaut_id}")
def list_assessments(astronaut_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.astronaut_id == astronaut_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "mission_day": r.mission_day,
            "median_rt_ms": r.median_rt_ms,
            "iqr_ms": r.iqr_ms,
            "provenance": r.provenance,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]
