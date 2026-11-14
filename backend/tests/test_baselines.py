from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.seed import seed_database
from app.services import baselines as bl


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database(force=True)


def test_baselines_stable_window():
    db = SessionLocal()
    try:
        baselines = bl.calculate_baselines(db, "PLT-02", 42)
        assert "reaction_time_ms" in baselines
        assert 250 < baselines["reaction_time_ms"] < 300
        assert 6.5 < baselines["sleep_h"] < 8.0
    finally:
        db.close()


def test_emerging_decline_detects_pattern():
    db = SessionLocal()
    try:
        pattern = bl.detect_combined_patterns(db, "CDR-01", 42)
        assert pattern.detected is True
        assert pattern.severity in ("amber", "red")
        assert (
            "Sleep" in pattern.contributing_metrics
            or "Reaction time" in pattern.contributing_metrics
        )
    finally:
        db.close()


def test_forecast_returns_estimate():
    db = SessionLocal()
    try:
        forecast = bl.simple_forecast(db, "CDR-01", 42)
        assert forecast.next_day_estimate > 0
        assert forecast.uncertainty > 0
        assert any(p.kind == "forecast" for p in forecast.series)
        assert "ILLUSTRATIVE" in forecast.disclaimer
    finally:
        db.close()
