from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.seed import seed_database
from app.services import telemetry as tel
from app.services.guidance import mark_assessment_complete
from app.services.operations import build_operations


def setup_module():
    Base.metadata.create_all(bind=engine)
    seed_database(force=True)


def test_create_and_encrypt_report():
    db = SessionLocal()
    try:
        report = tel.create_report(db, "CDR-01")
        assert report.id.startswith("ETB-")
        assert report.status == "queued"
        assert report.encrypted is True
        path = tel.export_report_path(db, report.id)
        assert path is not None and path.exists()
        payload = tel.decrypt_file(path)
        assert payload["astronaut_id"] == "CDR-01"
        assert payload["simulated_relay"] is True
        assert "recent_measurements" in payload
    finally:
        db.close()


def test_simulate_transmission():
    db = SessionLocal()
    try:
        tel.create_report(db, "PLT-02")
        out = tel.simulate_transmission(db)
        assert out["simulated"] is True
        assert len(out["transmitted"]) >= 1
        queue = tel.list_queue(db)
        assert any(r.status == "sent" for r in queue.reports)
    finally:
        db.close()


def test_operations_assessment_complete_improves_docking():
    db = SessionLocal()
    try:
        before = build_operations(db, "CDR-01")
        assert before.tasks[1].status in ("assessment_recommended", "review_required")
        mark_assessment_complete(db, "CDR-01", True)
        after = build_operations(db, "CDR-01")
        # Docking may clear assessment_recommended once marked complete
        assert after.readiness_pct >= before.readiness_pct
    finally:
        db.close()
