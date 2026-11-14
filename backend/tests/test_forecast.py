from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.seed import seed_database
from app.services.forecast import forecast_reaction_time, scenario_reaction_time
from app.services.nasa_importer import map_columns, parse_osdr_csv


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database(force=True)


def test_forecast_returns_sklearn_or_baseline():
    db = SessionLocal()
    try:
        out = forecast_reaction_time(db, "CDR-01", 42)
        assert out.next_day_estimate > 0
        assert out.uncertainty > 0
        assert "ILLUSTRATIVE" in out.disclaimer
        assert out.model_version in {
            "ridge-chrono-v1",
            "rolling-mean-persistence-v0",
        }
        assert any(p.kind == "forecast" for p in out.series)
    finally:
        db.close()


def test_scenario_what_if_moves_with_sleep():
    db = SessionLocal()
    try:
        low_sleep = scenario_reaction_time(db, "CDR-01", 42, sleep_h=4.5, co2_ppm=1900, fatigue=7)
        high_sleep = scenario_reaction_time(db, "CDR-01", 42, sleep_h=8.5, co2_ppm=1900, fatigue=7)
        assert high_sleep["hypothetical_estimate"] < low_sleep["hypothetical_estimate"]
    finally:
        db.close()


def test_column_mapping():
    mapping = map_columns(["Day", "CO2", "Temp_C", "RH"])
    assert mapping["mission_day"] == "Day"
    assert mapping["co2_ppm"] == "CO2"
    assert mapping["temperature_c"] == "Temp_C"
    assert mapping["humidity_pct"] == "RH"


def test_parse_example_csv():
    path = Path(__file__).resolve().parents[2] / "data" / "imports" / "example_osdr_style.csv"
    rows, meta = parse_osdr_csv(path)
    assert len(rows) >= 5
    assert meta["provenance"] == "NASA_HISTORICAL"
    assert rows[0]["provenance"] == "NASA_HISTORICAL"
