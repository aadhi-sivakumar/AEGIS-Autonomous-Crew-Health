from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.models import EnvironmentRecord, NasaEnvSample
from app.seed import seed_database
from app.services import rr1_api


SAMPLE_PAYLOAD = [
    {
        "time": "2014-09-20T03:59:00Z",
        "temperature_iss": 24.1,
        "temperature_ground": 24.1,
        "humidity_iss": 39.0,
        "humidity_ground": 37.0,
        "co2_iss": 2641.0,
        "co2_ground": 484.0,
        "milestones": None,
    },
    {
        "time": "2014-09-20T04:59:00Z",
        "temperature_iss": 24.3,
        "temperature_ground": 24.2,
        "humidity_iss": 40.0,
        "humidity_ground": 38.0,
        "co2_iss": 2700.0,
        "co2_ground": 500.0,
        "milestones": None,
    },
    {
        "time": "2014-09-21T03:59:00Z",
        "temperature_iss": 23.0,
        "temperature_ground": 23.0,
        "humidity_iss": 42.0,
        "humidity_ground": 40.0,
        "co2_iss": 3000.0,
        "co2_ground": 600.0,
        "milestones": None,
    },
]


def setup_module():
    Base.metadata.create_all(bind=engine)
    seed_database(force=True)


def test_parse_and_cache_rr1_samples():
    db = SessionLocal()
    try:
        n = rr1_api.cache_samples(db, SAMPLE_PAYLOAD)
        assert n == 3
        assert db.query(NasaEnvSample).count() == 3
        days = rr1_api.apply_daily_env_records(db)
        assert days == 2
        env = db.query(EnvironmentRecord).order_by(EnvironmentRecord.mission_day).all()
        assert env[0].provenance == "NASA_RR1_HISTORICAL"
        assert "RR-1" in env[0].source_label
        assert env[0].co2_ppm == round((2641 + 2700) / 2, 1)
    finally:
        db.close()


def test_historical_stats_and_deviations():
    db = SessionLocal()
    try:
        rr1_api.cache_samples(db, SAMPLE_PAYLOAD)
        rr1_api.apply_daily_env_records(db)
        stats = rr1_api.historical_stats(db)
        assert "co2_ppm" in stats
        assert stats["co2_ppm"]["n"] == 3
        latest = (
            db.query(EnvironmentRecord)
            .order_by(EnvironmentRecord.mission_day.desc())
            .first()
        )
        # Force an extreme latest for explanation coverage
        latest.co2_ppm = 5000.0
        db.commit()
        notes = rr1_api.deviation_explanations(db, latest)
        assert any(d["metric"] == "co2_ppm" for d in notes)
    finally:
        db.close()


def test_ensure_uses_cache_without_network(monkeypatch):
    db = SessionLocal()
    try:
        rr1_api.cache_samples(db, SAMPLE_PAYLOAD)
        rr1_api.apply_daily_env_records(db)

        def boom():
            raise TimeoutError("no network")

        monkeypatch.setattr(rr1_api, "fetch_rr1_telemetry", boom)
        out = rr1_api.ensure_rr1_cached(db, force_refresh=False)
        assert out["ok"] is True
        assert out["source"] == "cache"
    finally:
        db.close()
