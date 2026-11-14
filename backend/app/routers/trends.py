from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..services import baselines as bl
from ..services.demo import get_scenario
from ..services.forecast import forecast_reaction_time

router = APIRouter(prefix="/api", tags=["trends"])

METRIC_ACCESSORS = {
    "reaction_time_ms": ("reaction_time_ms", "ms", "Reaction Time"),
    "sleep_h": ("sleep_h", "h", "Sleep"),
    "resting_hr": ("resting_hr", "bpm", "Heart Rate"),
    "fatigue": ("fatigue", "/10", "Fatigue"),
    "mood": ("mood", "/10", "Mood"),
    "co2_ppm": ("co2_ppm", "ppm", "Cabin CO₂"),
    "temperature_c": ("temperature_c", "°C", "Temperature"),
    "humidity_pct": ("humidity_pct", "%", "Humidity"),
}


@router.get("/trends/{astronaut_id}")
def trends(
    astronaut_id: str,
    metric: str = Query("reaction_time_ms"),
    days: int = Query(14, ge=7, le=60),
    db: Session = Depends(get_db),
):
    crew = db.get(CrewMember, astronaut_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    if metric not in METRIC_ACCESSORS:
        raise HTTPException(status_code=400, detail=f"Unsupported metric: {metric}")

    state = get_scenario(db)
    mission_day = state.mission_day
    field, unit, label = METRIC_ACCESSORS[metric]
    history = bl.get_health_history(db, astronaut_id, mission_day)
    env = bl.get_environment_history(db, mission_day)
    baselines = bl.calculate_baselines(db, astronaut_id, mission_day)
    forecast = forecast_reaction_time(db, astronaut_id, mission_day)
    deviations = bl.detect_deviations(db, astronaut_id, mission_day)
    pattern = bl.detect_combined_patterns(db, astronaut_id, mission_day)

    start_day = max(1, mission_day - days + 1)
    series = []
    provenance = "SIMULATED_CREW_DATA"

    if field in {"co2_ppm", "temperature_c", "humidity_pct"}:
        for e in env:
            if start_day <= e.mission_day <= mission_day:
                series.append(
                    {
                        "mission_day": e.mission_day,
                        "value": getattr(e, field),
                        "kind": "observed",
                    }
                )
        provenance = env[-1].provenance if env else "SYNTHETIC_ENVIRONMENT"
        baseline_val = (
            sorted([getattr(e, field) for e in env[:14]])[len(env[:14]) // 2] if env else 0
        )
    else:
        for h in history:
            if start_day <= h.mission_day <= mission_day:
                series.append(
                    {
                        "mission_day": h.mission_day,
                        "value": getattr(h, field),
                        "kind": "observed",
                        "provenance": h.provenance,
                    }
                )
        if history:
            provenance = history[-1].provenance
        baseline_val = baselines.get(field, 0)

    forecast_region = []
    if metric == "reaction_time_ms":
        for p in forecast.series:
            if p.kind == "forecast":
                forecast_region.append(
                    {
                        "mission_day": p.mission_day,
                        "value": p.value,
                        "kind": "forecast",
                        "lower": p.lower,
                        "upper": p.upper,
                    }
                )

    # Pattern explanation
    if metric == "reaction_time_ms" and any(d.metric == "reaction_time_ms" for d in deviations):
        explanation = next(d.explanation for d in deviations if d.metric == "reaction_time_ms")
        if pattern.detected:
            explanation += " Combined multi-indicator pattern also flagged."
    elif any(d.metric == field for d in deviations):
        explanation = next(d.explanation for d in deviations if d.metric == field)
    else:
        explanation = f"{label} is within typical variation versus this crew member's personal baseline."

    contributing = []
    if metric == "reaction_time_ms":
        for d in deviations:
            contributing.append({"metric": d.metric, "text": d.explanation, "magnitude": d.magnitude})

    latest = series[-1]["value"] if series else 0
    return {
        "astronaut_id": astronaut_id,
        "metric": metric,
        "label": label,
        "unit": unit,
        "days": days,
        "mission_day": mission_day,
        "baseline": round(float(baseline_val), 2),
        "latest": round(float(latest), 2),
        "delta": round(float(latest) - float(baseline_val), 2),
        "provenance": provenance,
        "explanation": explanation,
        "series": series,
        "forecast": forecast_region,
        "forecast_summary": {
            "next_day_estimate": forecast.next_day_estimate,
            "uncertainty": forecast.uncertainty,
            "baseline_estimate": forecast.baseline_estimate,
            "model_version": forecast.model_version,
            "disclaimer": forecast.disclaimer,
        },
        "contributing_factors": contributing,
    }
