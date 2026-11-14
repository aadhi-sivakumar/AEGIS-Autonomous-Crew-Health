from __future__ import annotations

import csv
import math
import random
from pathlib import Path

from sqlalchemy.orm import Session

from .db import DATA_DIR, Base, SessionLocal, engine
from .models import (
    AppState,
    AssessmentResult,
    CrewMember,
    DailyCheckIn,
    EnvironmentRecord,
    HealthRecord,
    SymptomCheck,
)

MISSION_DAYS = 60
BASELINE_WINDOW = 14
CURRENT_MISSION_DAY = 42  # Day index within 1..60 used as "today" in demo

CREW = [
    {
        "id": "CDR-01",
        "callsign": "CDR-01",
        "role": "Commander",
        "scenario_profile": "emerging_decline",
    },
    {
        "id": "PLT-02",
        "callsign": "PLT-02",
        "role": "Pilot",
        "scenario_profile": "stable",
    },
    {
        "id": "FE-03",
        "callsign": "FE-03",
        "role": "Flight Engineer",
        "scenario_profile": "recovery",
    },
]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def generate_health_series(
    profile: str,
    seed: int,
    days: int = MISSION_DAYS,
) -> list[dict]:
    """Deterministic synthetic health trajectories labeled SIMULATED_CREW_DATA."""
    rng = random.Random(seed)
    rows: list[dict] = []

    sleep = 7.4
    hr = 62.0
    fatigue = 3.5
    mood = 7.0
    rt = 275.0
    exercise = 0.85

    for day in range(1, days + 1):
        noise = lambda scale: rng.uniform(-scale, scale)

        if profile == "stable":
            sleep = _clamp(7.4 + noise(0.35), 6.5, 8.2)
            hr = _clamp(62 + noise(1.5), 58, 68)
            fatigue = _clamp(3.2 + noise(0.6), 2, 5)
            mood = _clamp(7.2 + noise(0.5), 5.5, 8.5)
            rt = _clamp(275 + noise(8), 255, 295)
            exercise = _clamp(0.85 + noise(0.08), 0.6, 1.0)

        elif profile == "emerging_decline":
            # Stable early window, then progressive cognitive load markers.
            if day <= BASELINE_WINDOW:
                sleep = _clamp(7.5 + noise(0.3), 6.8, 8.2)
                hr = _clamp(61 + noise(1.2), 58, 66)
                fatigue = _clamp(3.0 + noise(0.5), 2, 4.5)
                mood = _clamp(7.3 + noise(0.4), 6, 8.5)
                rt = _clamp(272 + noise(7), 255, 290)
            else:
                t = (day - BASELINE_WINDOW) / (days - BASELINE_WINDOW)
                sleep = _clamp(7.5 - 1.8 * t + noise(0.25), 5.2, 7.8)
                hr = _clamp(61 + 8 * t + noise(1.5), 58, 78)
                fatigue = _clamp(3.0 + 4.5 * t + noise(0.4), 2, 9)
                mood = _clamp(7.3 - 2.5 * t + noise(0.4), 3.5, 8)
                rt = _clamp(272 + 55 * t + noise(6), 260, 360)
            exercise = _clamp(0.82 - (0.25 if day > 30 else 0) + noise(0.06), 0.4, 1.0)

        else:  # recovery
            mid = days // 2
            if day <= BASELINE_WINDOW:
                sleep = _clamp(7.3 + noise(0.3), 6.6, 8.0)
                hr = _clamp(62 + noise(1.2), 58, 67)
                fatigue = _clamp(3.2 + noise(0.5), 2, 4.5)
                mood = _clamp(7.0 + noise(0.4), 5.5, 8)
                rt = _clamp(278 + noise(7), 260, 295)
            elif day <= mid:
                t = (day - BASELINE_WINDOW) / max(1, mid - BASELINE_WINDOW)
                sleep = _clamp(7.3 - 1.5 * t + noise(0.25), 5.4, 7.6)
                hr = _clamp(62 + 6 * t + noise(1.4), 58, 76)
                fatigue = _clamp(3.2 + 3.8 * t + noise(0.4), 2, 8.5)
                mood = _clamp(7.0 - 2.0 * t + noise(0.4), 3.5, 8)
                rt = _clamp(278 + 45 * t + noise(6), 265, 350)
            else:
                t = (day - mid) / max(1, days - mid)
                sleep = _clamp(5.8 + 1.6 * t + noise(0.25), 5.5, 8.0)
                hr = _clamp(70 - 7 * t + noise(1.3), 58, 74)
                fatigue = _clamp(7.2 - 3.5 * t + noise(0.4), 2.5, 8)
                mood = _clamp(4.8 + 2.2 * t + noise(0.4), 4, 8.5)
                rt = _clamp(325 - 40 * t + noise(6), 265, 340)
            exercise = _clamp(0.75 + noise(0.08), 0.45, 1.0)

        rows.append(
            {
                "mission_day": day,
                "sleep_h": round(sleep, 2),
                "resting_hr": round(hr, 1),
                "fatigue": round(fatigue, 1),
                "mood": round(mood, 1),
                "reaction_time_ms": round(rt, 1),
                "exercise_adherence": round(exercise, 2),
                "provenance": "SIMULATED_CREW_DATA",
            }
        )
    return rows


def generate_environment(seed: int = 42, days: int = MISSION_DAYS) -> list[dict]:
    """Synthetic cabin environment — NOT live spacecraft telemetry."""
    rng = random.Random(seed)
    rows: list[dict] = []
    co2 = 900.0
    temp = 22.0
    humidity = 45.0

    for day in range(1, days + 1):
        # Mild rise mid-mission for demo coincidence with decline scenario.
        bump = 0.0
        if 28 <= day <= 48:
            bump = 400 + 500 * math.sin((day - 28) / 20 * math.pi)
        co2 = _clamp(900 + bump + rng.uniform(-40, 40), 700, 2800)
        temp = _clamp(22.0 + rng.uniform(-0.4, 0.6) + (0.3 if bump > 200 else 0), 20.5, 24.5)
        humidity = _clamp(45 + rng.uniform(-3, 3) + (2 if bump > 200 else 0), 35, 60)
        rows.append(
            {
                "mission_day": day,
                "co2_ppm": round(co2, 0),
                "temperature_c": round(temp, 1),
                "humidity_pct": round(humidity, 1),
                "provenance": "SYNTHETIC_ENVIRONMENT",
                "source_label": "DEMO DATA — NASA IMPORT NOT LOADED",
            }
        )
    return rows


def write_environment_fixture(rows: list[dict]) -> Path:
    fixtures = DATA_DIR / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    path = fixtures / "environment_synthetic.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mission_day",
                "co2_ppm",
                "temperature_c",
                "humidity_pct",
                "provenance",
                "source_label",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def seed_database(db: Session | None = None, force: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    own_session = db is None
    if own_session:
        db = SessionLocal()

    assert db is not None
    try:
        existing = db.query(CrewMember).count()
        if existing and not force:
            if not db.get(AppState, "demo_scenario"):
                db.add(AppState(key="demo_scenario", value="emerging_decline"))
                db.add(AppState(key="mission_day", value=str(CURRENT_MISSION_DAY)))
                db.commit()
            return

        if force:
            db.query(SymptomCheck).delete()
            db.query(DailyCheckIn).delete()
            db.query(AssessmentResult).delete()
            db.query(HealthRecord).delete()
            db.query(EnvironmentRecord).delete()
            db.query(CrewMember).delete()
            db.query(AppState).delete()
            # Keep NasaEnvSample cache so offline RR-1 data survives Reset Demo.
            db.commit()

        for member in CREW:
            db.add(CrewMember(**member))

        profile_seed = {"emerging_decline": 101, "stable": 202, "recovery": 303}
        for member in CREW:
            series = generate_health_series(member["scenario_profile"], profile_seed[member["scenario_profile"]])
            for row in series:
                db.add(HealthRecord(astronaut_id=member["id"], **row))

        # Seed synthetic cabin env; sync to NASA RR-1 if cache exists and mode prefers it.
        env_rows = generate_environment()
        write_environment_fixture(env_rows)
        for row in env_rows:
            db.add(EnvironmentRecord(**row))

        db.add(AppState(key="demo_scenario", value="emerging_decline"))
        db.add(AppState(key="mission_day", value=str(CURRENT_MISSION_DAY)))
        db.add(AppState(key="nasa_import_loaded", value="false"))
        db.commit()

        try:
            from .services.rr1_api import sync_active_environment
            from .services.nasa_eda_service import prefer_nasa_historical_when_cached

            prefer_nasa_historical_when_cached(db)
            sync_active_environment(db)
        except Exception:
            pass
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    seed_database(force=True)
    print(f"Seeded AEGIS database with {MISSION_DAYS} mission days for {len(CREW)} crew members.")
