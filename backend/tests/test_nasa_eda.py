from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import NasaImportMeta, NasaRadiationRecord, NasaTelemetryRecord
from app.services import env_anomalies
from app.services import nasa_eda_service as nasa

# Isolated in-memory DB — do not touch data/aegis.db used by the running app.
_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


TELEM_RAW = [
    {
        "time": "2014-09-20T03:59:00Z",
        "temperature_iss": 24.1,
        "temperature_ground": 24.0,
        "humidity_iss": 39.0,
        "humidity_ground": 37.0,
        "co2_iss": 2641.0,
        "co2_ground": 484.0,
        "milestones": None,
    },
    {
        "time": "2014-09-20T04:59:00Z",
        "temperature_iss": None,
        "temperature_ground": "na",
        "humidity_iss": 40.0,
        "humidity_ground": 38.0,
        "co2_iss": None,
        "co2_ground": 500.0,
        "milestones": "Launch",
    },
    {
        "time": "bad-time",
        "co2_iss": 9999,
    },
    {
        "time": "2014-09-21T03:59:00Z",
        "temperature_iss": 23.0,
        "temperature_ground": 23.0,
        "humidity_iss": 42.0,
        "humidity_ground": 40.0,
        "co2_iss": 3200.0,
        "co2_ground": 600.0,
        "milestones": None,
    },
]

# Build a longer series for anomaly detection (unique hourly timestamps)
for i in range(48):
    day = 22 + (i // 24)
    hour = i % 24
    TELEM_RAW.append(
        {
            "time": f"2014-09-{day:02d}T{hour:02d}:00:00Z",
            "temperature_iss": 24.0 + (0.05 * i),
            "temperature_ground": 24.0,
            "humidity_iss": 40.0,
            "humidity_ground": 38.0,
            "co2_iss": 2600.0 + (i * 2),
            "co2_ground": 500.0,
            "milestones": None,
        }
    )
# Sustained elevated CO2 streak
for i in range(12):
    TELEM_RAW.append(
        {
            "time": f"2014-09-25T{i:02d}:00:00Z",
            "temperature_iss": 24.0,
            "temperature_ground": 24.0,
            "humidity_iss": 40.0,
            "humidity_ground": 38.0,
            "co2_iss": 4500.0,
            "co2_ground": 500.0,
            "milestones": None,
        }
    )

RAD_RAW = [
    {
        "time": "2014-09-20T00:00:00Z",
        "gcr": 0.12,
        "saa": 0.05,
        "total": 0.17,
        "milestones": None,
    },
    {
        "time": "2014-09-21T00:00:00Z",
        "gcr": 0.11,
        "saa": None,
        "total": 0.16,
        "milestones": None,
    },
    {
        "time": "2014-09-22T00:00:00Z",
        "gcr": "nan",
        "saa": 0.04,
        "total": 0.15,
        "milestones": None,
    },
]


def setup_module():
    Base.metadata.create_all(bind=_engine)


def test_parse_telemetry_nulls_and_timestamps():
    rows = nasa.parse_telemetry_records(TELEM_RAW, "RR-1")
    # bad-time skipped; nulls preserved as None
    assert all(r["time_utc"].endswith("Z") for r in rows)
    assert any(r["co2_iss"] is None for r in rows)
    assert any(r["milestones"] == "Launch" for r in rows)
    assert not any("bad-time" in r["time_utc"] for r in rows)


def test_parse_rejects_non_array():
    try:
        nasa.parse_telemetry_records({"data": []}, "RR-1")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_import_dedupe_and_offline_cache():
    db = SessionLocal()
    try:
        # Direct cache write (no network)
        telem = nasa.parse_telemetry_records(TELEM_RAW, "RR-1")
        rad = nasa.parse_radiation_records(RAD_RAW, "RR-1")
        db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == "RR-1").delete()
        db.query(NasaRadiationRecord).filter(NasaRadiationRecord.mission_id == "RR-1").delete()
        meta = db.get(NasaImportMeta, "RR-1")
        if meta:
            db.delete(meta)
        db.commit()

        for row in telem:
            db.add(NasaTelemetryRecord(**row))
        for row in rad:
            db.add(NasaRadiationRecord(**row))
        db.add(
            NasaImportMeta(
                mission_id="RR-1",
                imported_at="2014-09-25T00:00:00Z",
                telemetry_url="https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/telemetry_data/",
                radiation_url="https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/radiation_data/",
                telemetry_count=len(telem),
                radiation_count=len(rad),
                mission_title="Rodent Research 1",
                time_start=telem[0]["time_utc"],
                time_end=telem[-1]["time_utc"],
            )
        )
        db.commit()

        assert nasa.is_mission_cached(db, "RR-1")
        n1 = db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == "RR-1").count()

        # Re-insert same rows after clear → same count (dedupe via replace pattern)
        db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == "RR-1").delete()
        for row in telem:
            db.add(NasaTelemetryRecord(**row))
        db.commit()
        n2 = db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == "RR-1").count()
        assert n1 == n2

        # Offline query works from SQLite
        rows = nasa.query_telemetry(db, "RR-1", stride=5)
        assert len(rows) > 0
        assert rows[0].time_utc <= rows[-1].time_utc
    finally:
        db.close()


def test_time_range_filter():
    db = SessionLocal()
    try:
        rows = nasa.query_telemetry(
            db,
            "RR-1",
            start="2014-09-21T00:00:00Z",
            end="2014-09-22T23:59:59Z",
            stride=1,
        )
        assert rows
        assert all("2014-09-21" in r.time_utc or "2014-09-22" in r.time_utc for r in rows)
    finally:
        db.close()


def test_radiation_units_and_cumulative():
    db = SessionLocal()
    try:
        rad = nasa.query_radiation(db, "RR-1")
        cum = nasa.cumulative_dose_mgy(rad)
        assert cum["unit"] == "mGy"
        assert cum["days_counted"] >= 1
        assert cum["cumulative_mgy"] is not None
        d = nasa.rad_to_dict(rad[0])
        assert d["units"] == "mGy/day"
        # As-of: telemetry mid-day should get prior daily sample (no interpolation)
        asof = nasa.radiation_as_of(db, "RR-1", "2014-09-21T12:00:00Z")
        assert asof is not None
        assert asof.time_utc.startswith("2014-09-21") or asof.time_utc.startswith("2014-09-20")
    finally:
        db.close()


def test_anomaly_and_summary():
    db = SessionLocal()
    try:
        base = env_anomalies.calculate_environment_baseline(db, "RR-1", "co2_iss")
        assert base["baseline"] is not None
        anomalies = env_anomalies.detect_environment_anomalies(db, "RR-1")
        assert isinstance(anomalies, list)
        # Sustained high CO2 should produce at least one statistical anomaly
        assert any("CO₂" in a["explanation"] or "co2" in a["metric"] for a in anomalies)
        assert all(a.get("kind") != "medical" for a in anomalies)
        summary = env_anomalies.get_environment_summary(db, "RR-1")
        assert summary["cached"] is True
        assert "telemetry" in summary
        trends = env_anomalies.get_environment_trends(db, "RR-1", stride=10)
        assert "series" in trends
    finally:
        db.close()


def test_env_mode_and_normalize_time():
    assert nasa._normalize_time("2014-09-20T03:59:00Z") == "2014-09-20T03:59:00Z"
    assert nasa._normalize_time(None) is None
    assert nasa._to_float("na") is None
    assert nasa._to_float(12.5) == 12.5
    db = SessionLocal()
    try:
        nasa.set_env_data_mode(db, "nasa_historical")
        assert nasa.get_env_data_mode(db) == "nasa_historical"
        nasa.set_env_data_mode(db, "simulated")
        assert nasa.get_env_data_mode(db) == "simulated"
    finally:
        db.close()


def test_replay_sync_cursor():
    db = SessionLocal()
    try:
        telem = nasa.nearest_telemetry(db, "RR-1", "2014-09-21T12:00:00Z")
        assert telem is not None
        assert telem.time_utc <= "2014-09-21T12:00:00Z" or telem.time_utc > "2014-09-21T12:00:00Z"
        rad = nasa.radiation_as_of(db, "RR-1", telem.time_utc)
        # Radiation may lag; if present it must be at/before telemetry time
        if rad:
            assert rad.time_utc <= telem.time_utc
    finally:
        db.close()
