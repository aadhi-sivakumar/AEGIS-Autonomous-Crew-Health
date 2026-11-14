from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AppState, EnvironmentRecord, NasaEnvSample
from ..services import baselines as bl
from ..services.demo import get_scenario
from ..services.nasa_importer import IMPORTS_DIR, import_osdr_csv, try_auto_import
from ..services import rr1_api

router = APIRouter(prefix="/api", tags=["environment"])

RR1_BANNER = "NASA RR-1 Historical Environmental Data — 2014"
RR1_NOTE = (
    "ISS rodent-research hardware environmental telemetry (RR-1, 2014). "
    "Not astronaut medical data. Not live spacecraft telemetry. "
    "Not causally paired with simulated crew health."
)


@router.get("/environment")
def environment(db: Session = Depends(get_db)):
    scenario_state = get_scenario(db)
    env = bl.get_environment_history(db, scenario_state.mission_day)
    nasa_flag = db.get(AppState, "nasa_import_loaded")
    nasa_loaded = bool(nasa_flag and nasa_flag.value.lower() == "true")
    rr1_cached = db.query(NasaEnvSample).count() > 0
    latest = env[-1] if env else None
    stats = rr1_api.historical_stats(db) if rr1_cached else {}
    deviations = rr1_api.deviation_explanations(db, latest) if rr1_cached else []

    if rr1_cached or (latest and latest.provenance == rr1_api.PROVENANCE):
        banner = RR1_BANNER
    elif nasa_loaded:
        banner = latest.source_label if latest else "NASA HISTORICAL ENVIRONMENTAL DATA"
    else:
        banner = "DEMO DATA — NASA IMPORT NOT LOADED"

    return {
        "nasa_import_loaded": nasa_loaded or rr1_cached,
        "rr1_cached": rr1_cached,
        "banner": banner,
        "note": RR1_NOTE if rr1_cached else (
            "Historical NASA OSDR import when loaded; otherwise synthetic fixture. "
            "Not live spacecraft telemetry."
        ),
        "points": bl.env_to_points(env),
        "chart": rr1_api.chart_series(db) if rr1_cached else [],
        "historical_averages": stats,
        "deviations": deviations,
    }


@router.post("/environment/fetch-rr1")
def fetch_rr1(force: bool = False, db: Session = Depends(get_db)):
    """Fetch NASA RR-1 telemetry and cache in SQLite (or refresh from API)."""
    result = rr1_api.ensure_rr1_cached(db, force_refresh=force)
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result)
    return result


@router.post("/environment/import")
async def import_environment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv exported from NASA OSDR EDA")

    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMPORTS_DIR / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)

    try:
        meta = import_osdr_csv(db, dest, replace=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "ok": True,
        "meta": meta,
        "banner": None,
        "message": "NASA historical environmental CSV imported. Not live telemetry.",
    }


@router.post("/environment/import-local")
def import_local(db: Session = Depends(get_db)):
    """Import newest CSV from data/imports/ if present."""
    meta = try_auto_import(db)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"No CSV found in {IMPORTS_DIR}. Place an OSDR export there first.",
        )
    return {"ok": True, "meta": meta}
