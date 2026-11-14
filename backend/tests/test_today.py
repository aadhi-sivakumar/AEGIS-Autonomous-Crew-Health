from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.schemas import CheckInIn, SymptomCheckIn
from app.seed import seed_database
from app.services import today as today_service
from app.services.metric_explain import all_explainers
from app.services.operations import build_operations


def setup_module():
    Base.metadata.create_all(bind=engine)
    seed_database(force=False)


def test_today_summary():
    db = SessionLocal()
    try:
        out = today_service.build_today(db, "CDR-01")
        assert out.astronaut_id == "CDR-01"
        assert out.overall_status in ("green", "amber", "red")
        assert len(out.top_metrics) >= 1
        assert out.primary_action.get("label")
        assert out.trust_line
        assert out.forecast_blurb
        assert len(out.reminder_schedule) == 3
        assert {s.id for s in out.reminder_schedule} == {
            "morning_checkin",
            "daily_assessment",
            "symptom_check",
        }
    finally:
        db.close()


def test_reminder_prompts_and_emergency_guidance():
    from app.services.guidance import build_guidance

    db = SessionLocal()
    try:
        out = today_service.build_today(db, "CDR-01")
        kinds = {p.kind for p in out.prompts}
        # Without check-in, morning reminder should fire
        if not out.checkin_done:
            assert "morning_checkin" in kinds
            assert any(p.due_label for p in out.prompts)

        g = build_guidance(db, "CDR-01")
        assert g.emergency_disclaimer
        assert len(g.emergency_steps) >= 5
        assert len(g.when_to_escalate) >= 3
        assert g.emergency_steps[0].title
    finally:
        db.close()


def test_checkin_updates_today():
    db = SessionLocal()
    try:
        today_service.submit_checkin(
            db,
            CheckInIn(
                astronaut_id="PLT-02",
                sleep_h=7.5,
                fatigue=2,
                mood=4,
                resting_hr=62,
            ),
        )
        out = today_service.build_today(db, "PLT-02")
        assert out.checkin_done is True
        assert out.checkin is not None
        assert out.checkin.sleep_h == 7.5
    finally:
        db.close()


def test_symptoms_attention_flag():
    db = SessionLocal()
    try:
        mild = today_service.submit_symptoms(
            db,
            SymptomCheckIn(astronaut_id="FE-03", headache=1, congestion=0, dizziness=0, nausea=0),
        )
        assert mild.attention_needed is False
        strong = today_service.submit_symptoms(
            db,
            SymptomCheckIn(astronaut_id="FE-03", headache=2, congestion=0, dizziness=0, nausea=0),
        )
        assert strong.attention_needed is True
    finally:
        db.close()


def test_explainers_and_gate():
    body = all_explainers()
    assert "sleep_h" in body["metrics"]
    assert "head" in body["zones"]
    db = SessionLocal()
    try:
        ops = build_operations(db, "CDR-01")
        assert ops.gate_summary
        assert ops.tasks[0].gate in ("ready", "caution", "not_recommended")
    finally:
        db.close()
