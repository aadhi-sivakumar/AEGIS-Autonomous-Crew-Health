from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, SessionLocal, engine
from .routers import (
    assessments,
    crew,
    demo,
    environment,
    guidance,
    health,
    nasa,
    operations,
    simulate,
    telemetry,
    today,
    trends,
)
from .seed import seed_database
from .services import nasa_eda_service, rr1_api

app = FastAPI(
    title="AEGIS",
    description="Autonomous Crew Health — local prototype API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crew.router)
app.include_router(health.router)
app.include_router(today.router)
app.include_router(demo.router)
app.include_router(environment.router)
app.include_router(trends.router)
app.include_router(assessments.router)
app.include_router(simulate.router)
app.include_router(guidance.router)
app.include_router(operations.router)
app.include_router(telemetry.router)
app.include_router(nasa.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_database(force=False)
    # Prefer real NASA RR-1 env cache; Simulated mode regenerates synthetic on toggle.
    db = SessionLocal()
    try:
        rr1_api.ensure_rr1_cached(db, force_refresh=False)
        # Full EDA telemetry + radiation cache for Mission Replay (skip if already cached).
        if not nasa_eda_service.is_mission_cached(db, "RR-1"):
            try:
                nasa_eda_service.import_mission(db, "RR-1")
            except Exception:
                pass
        # Judge-ready default: NASA Historical when cache is present.
        nasa_eda_service.prefer_nasa_historical_when_cached(db)
        rr1_api.sync_active_environment(db)
    finally:
        db.close()


@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "service": "AEGIS"}
