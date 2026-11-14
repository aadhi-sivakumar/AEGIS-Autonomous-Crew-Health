from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    callsign: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(64))
    scenario_profile: Mapped[str] = mapped_column(String(64))


class HealthRecord(Base):
    __tablename__ = "health_records"
    __table_args__ = (UniqueConstraint("astronaut_id", "mission_day", name="uq_health_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    astronaut_id: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int] = mapped_column(Integer, index=True)
    sleep_h: Mapped[float] = mapped_column(Float)
    resting_hr: Mapped[float] = mapped_column(Float)
    fatigue: Mapped[float] = mapped_column(Float)
    mood: Mapped[float] = mapped_column(Float)
    reaction_time_ms: Mapped[float] = mapped_column(Float)
    exercise_adherence: Mapped[float] = mapped_column(Float)
    provenance: Mapped[str] = mapped_column(String(64), default="SIMULATED_CREW_DATA")


class EnvironmentRecord(Base):
    __tablename__ = "environment_records"
    __table_args__ = (UniqueConstraint("mission_day", name="uq_env_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_day: Mapped[int] = mapped_column(Integer, index=True)
    co2_ppm: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    provenance: Mapped[str] = mapped_column(String(64), default="SYNTHETIC_ENVIRONMENT")
    source_label: Mapped[str] = mapped_column(String(128), default="DEMO DATA — NASA IMPORT NOT LOADED")
    sample_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class NasaEnvSample(Base):
    """Cached NASA OSDR RR-1 ISS environmental telemetry samples."""

    __tablename__ = "nasa_env_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time_utc: Mapped[str] = mapped_column(String(64), index=True)
    co2_ppm: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    mission: Mapped[str] = mapped_column(String(32), default="RR-1")
    provenance: Mapped[str] = mapped_column(
        String(64), default="NASA_RR1_HISTORICAL"
    )
    source_label: Mapped[str] = mapped_column(
        String(128), default="NASA RR-1 Historical Environmental Data — 2014"
    )


class NasaTelemetryRecord(Base):
    """Full NASA EDA telemetry cache (ISS + ground), original units preserved."""

    __tablename__ = "nasa_telemetry_records"
    __table_args__ = (
        UniqueConstraint("mission_id", "time_utc", name="uq_nasa_telem_mission_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    time_utc: Mapped[str] = mapped_column(String(64), index=True)
    temperature_iss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature_ground: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_iss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_ground: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    co2_iss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    co2_ground: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    milestones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), default="")


class NasaRadiationRecord(Base):
    """NASA EDA radiation dose-rate cache (mGy/day)."""

    __tablename__ = "nasa_radiation_records"
    __table_args__ = (
        UniqueConstraint("mission_id", "time_utc", name="uq_nasa_rad_mission_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    time_utc: Mapped[str] = mapped_column(String(64), index=True)
    gcr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    saa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    milestones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), default="")


class NasaImportMeta(Base):
    """Import provenance for a cached NASA EDA mission."""

    __tablename__ = "nasa_import_meta"

    mission_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    imported_at: Mapped[str] = mapped_column(String(64))
    telemetry_url: Mapped[str] = mapped_column(String(512))
    radiation_url: Mapped[str] = mapped_column(String(512))
    telemetry_count: Mapped[int] = mapped_column(Integer, default=0)
    radiation_count: Mapped[int] = mapped_column(Integer, default=0)
    mission_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    time_start: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    time_end: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    astronaut_id: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    median_rt_ms: Mapped[float] = mapped_column(Float)
    iqr_ms: Mapped[float] = mapped_column(Float)
    trial_count: Mapped[int] = mapped_column(Integer)
    invalid_count: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[str] = mapped_column(String(64), default="BROWSER_MEASURED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyCheckIn(Base):
    """Crew-entered daily wellness log (sleep, fatigue, mood, optional HR)."""

    __tablename__ = "daily_checkins"
    __table_args__ = (UniqueConstraint("astronaut_id", "mission_day", name="uq_checkin_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    astronaut_id: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int] = mapped_column(Integer, index=True)
    sleep_h: Mapped[float] = mapped_column(Float)
    fatigue: Mapped[float] = mapped_column(Float)  # 1–5
    mood: Mapped[float] = mapped_column(Float)  # 1–5
    resting_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[str] = mapped_column(String(64), default="CREW_ENTERED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SymptomCheck(Base):
    """Simple symptom checklist — second real crew measurement besides RT."""

    __tablename__ = "symptom_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    astronaut_id: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int] = mapped_column(Integer, index=True)
    headache: Mapped[int] = mapped_column(Integer, default=0)  # 0–3
    congestion: Mapped[int] = mapped_column(Integer, default=0)
    dizziness: Mapped[int] = mapped_column(Integer, default=0)
    nausea: Mapped[int] = mapped_column(Integer, default=0)
    other_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[str] = mapped_column(String(64), default="CREW_ENTERED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class TelemetryReport(Base):
    __tablename__ = "telemetry_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    astronaut_id: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | sent
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ciphertext_path: Mapped[str] = mapped_column(String(512))
    sections_json: Mapped[str] = mapped_column(Text, default="[]")
    plaintext_preview: Mapped[str] = mapped_column(Text, default="")
