from __future__ import annotations

from typing import Optional
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AppState, NasaRadiationRecord, NasaTelemetryRecord
from ..services import env_anomalies
from ..services import nasa_eda_service as nasa

router = APIRouter(prefix="/api/nasa", tags=["nasa-eda"])


class EnvModeIn(BaseModel):
    mode: str = Field(description="simulated | nasa_historical")


@router.get("/missions")
def missions(db: Session = Depends(get_db)):
    return nasa.list_missions_local_or_remote(db)


@router.post("/import/{mission_id}")
def import_mission(mission_id: str, db: Session = Depends(get_db)):
    try:
        result = nasa.import_mission(db, mission_id)
    except (URLError, HTTPError, TimeoutError, TimeoutError) as e:
        if nasa.is_mission_cached(db, mission_id):
            meta = nasa.get_import_meta(db, mission_id)
            return {
                "ok": True,
                "cached_only": True,
                "detail": f"Network unavailable ({e}). Serving previously cached records.",
                "mission_id": mission_id,
                "telemetry_count": meta.telemetry_count if meta else 0,
                "radiation_count": meta.radiation_count if meta else 0,
            }
        raise HTTPException(
            status_code=503,
            detail=f"NASA EDA unreachable and no local cache for {mission_id}: {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "cached_only": False, **result}


@router.get("/telemetry/{mission_id}")
def telemetry(
    mission_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    stride: int = Query(default=10, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not nasa.is_mission_cached(db, mission_id):
        raise HTTPException(status_code=404, detail="Mission not cached — import first")
    rows = nasa.query_telemetry(db, mission_id, start=start, end=end, stride=stride)
    meta = nasa.get_import_meta(db, mission_id)
    return {
        "mission_id": mission_id,
        "count": len(rows),
        "stride": stride,
        "cached": True,
        "imported_at": meta.imported_at if meta else None,
        "source_url": meta.telemetry_url if meta else None,
        "points": [nasa.telem_to_dict(r) for r in rows],
        "disclaimer": (
            "Historical NASA EDA research-environment measurements. "
            "Not live astronaut medical telemetry."
        ),
    }


@router.get("/radiation/{mission_id}")
def radiation(
    mission_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not nasa.is_mission_cached(db, mission_id):
        raise HTTPException(status_code=404, detail="Mission not cached — import first")
    rows = nasa.query_radiation(db, mission_id, start=start, end=end)
    meta = nasa.get_import_meta(db, mission_id)
    return {
        "mission_id": mission_id,
        "count": len(rows),
        "unit": "mGy/day",
        "cached": True,
        "imported_at": meta.imported_at if meta else None,
        "source_url": meta.radiation_url if meta else None,
        "points": [nasa.rad_to_dict(r) for r in rows],
        "cumulative": nasa.cumulative_dose_mgy(rows),
        "disclaimer": (
            "Daily radiation dose-rate samples. Not interpolated to telemetry cadence. "
            "Do not interpret as individualized astronaut health outcomes."
        ),
    }


@router.get("/summary/{mission_id}")
def summary(mission_id: str, at: Optional[str] = None, db: Session = Depends(get_db)):
    return env_anomalies.get_environment_summary(db, mission_id, at=at)


@router.get("/anomalies/{mission_id}")
def anomalies(mission_id: str, db: Session = Depends(get_db)):
    if not nasa.is_mission_cached(db, mission_id):
        raise HTTPException(status_code=404, detail="Mission not cached — import first")
    return {
        "mission_id": mission_id,
        "anomalies": env_anomalies.detect_environment_anomalies(db, mission_id),
        "trends": env_anomalies.get_environment_trends(db, mission_id, stride=25),
        "note": "Statistical anomalies relative to early historical baseline — not medical diagnoses.",
    }


@router.get("/replay/{mission_id}")
def replay(
    mission_id: str,
    at: Optional[str] = None,
    chart_stride: int = Query(default=15, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not nasa.is_mission_cached(db, mission_id):
        raise HTTPException(status_code=404, detail="Mission not cached — import first")
    meta = nasa.get_import_meta(db, mission_id)
    assert meta
    cursor = at or meta.time_start or meta.time_end
    telem = nasa.nearest_telemetry(db, mission_id, cursor) if cursor else None
    rad = nasa.radiation_as_of(db, mission_id, cursor) if cursor else None

    telem_stride_rows = nasa.query_telemetry(db, mission_id, stride=max(1, chart_stride))
    all_times = [r.time_utc for r in telem_stride_rows]
    timeline_points = [nasa.telem_to_dict(r) for r in telem_stride_rows]

    telem_ms = (
        db.query(NasaTelemetryRecord)
        .filter(
            NasaTelemetryRecord.mission_id == mission_id,
            NasaTelemetryRecord.milestones.isnot(None),
        )
        .order_by(NasaTelemetryRecord.time_utc.asc())
        .all()
    )
    rad_ms = (
        db.query(NasaRadiationRecord)
        .filter(
            NasaRadiationRecord.mission_id == mission_id,
            NasaRadiationRecord.milestones.isnot(None),
        )
        .order_by(NasaRadiationRecord.time_utc.asc())
        .all()
    )
    milestones = [{"time": r.time_utc, "label": r.milestones, "source": "telemetry"} for r in telem_ms]
    milestones += [{"time": r.time_utc, "label": r.milestones, "source": "radiation"} for r in rad_ms]

    chart = env_anomalies.get_environment_trends(db, mission_id, stride=chart_stride)
    rad_series = [nasa.rad_to_dict(r) for r in nasa.query_radiation(db, mission_id)]

    return {
        "mission_id": mission_id,
        "mission_title": meta.mission_title,
        "time_start": meta.time_start,
        "time_end": meta.time_end,
        "cursor": telem.time_utc if telem else cursor,
        "timeline": all_times,
        "timeline_points": timeline_points,
        "milestones": milestones,
        "current_telemetry": nasa.telem_to_dict(telem) if telem else None,
        "current_radiation": nasa.rad_to_dict(rad) if rad else None,
        "radiation_as_of_note": (
            f"Showing most recent daily radiation sample at/before cursor ({rad.time_utc}). "
            "Not interpolated."
            if rad
            else "No radiation sample available at/before this cursor."
        ),
        "chart": chart,
        "radiation_series": rad_series,
        "anomalies": env_anomalies.detect_environment_anomalies(db, mission_id)[:8],
        "source": {
            "system": "NASA OSDR / EDA",
            "telemetry_url": meta.telemetry_url,
            "radiation_url": meta.radiation_url,
            "imported_at": meta.imported_at,
            "disclaimer": (
                "Historical RR-1 research-environment replay. "
                "Not synchronized with synthetic astronaut health records."
            ),
        },
        "cached": True,
        "offline_ready": True,
    }


@router.get("/env-mode")
def get_mode(db: Session = Depends(get_db)):
    mode = nasa.get_env_data_mode(db)
    active = db.get(AppState, "nasa_active_mission")
    mid = active.value if active else "RR-1"
    return {
        "mode": mode,
        "active_mission": mid,
        "nasa_cached": nasa.is_mission_cached(db, mid),
        "labels": {
            "simulated": "Simulated Mission Data",
            "nasa_historical": "NASA Historical Data",
        },
    }


@router.post("/env-mode")
def set_mode(body: EnvModeIn, db: Session = Depends(get_db)):
    try:
        mode = nasa.set_env_data_mode(db, body.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    active = db.get(AppState, "nasa_active_mission")
    mid = active.value if active else "RR-1"
    cached = nasa.is_mission_cached(db, mid)
    out = {"mode": mode, "nasa_cached": cached, "active_mission": mid}
    if mode == "nasa_historical" and not cached:
        out["warning"] = f"Mode set, but {mid} is not cached. Import required."
    return out
