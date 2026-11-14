from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from ..db import DATA_DIR
from ..models import AssessmentResult, TelemetryReport
from ..schemas import TelemetryQueueOut, TelemetryReportOut
from ..services import baselines as bl
from ..services.demo import get_scenario

REPORTS_DIR = DATA_DIR / "telemetry" / "reports"
KEYS_DIR = DATA_DIR / "keys"
KEY_PATH = KEYS_DIR / "aegis_telemetry.key"


def _ensure_key() -> bytes:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = AESGCM.generate_key(bit_length=256)
    KEY_PATH.write_bytes(key)
    # Restrictive permissions where supported
    try:
        os.chmod(KEY_PATH, 0o600)
    except OSError:
        pass
    return key


def encrypt_payload(payload: dict) -> tuple[bytes, bytes]:
    """Return (nonce, ciphertext) using AES-GCM."""
    key = _ensure_key()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ct = aes.encrypt(nonce, data, associated_data=b"AEGIS-TELEMETRY-v1")
    return nonce, ct


def decrypt_file(path: Path) -> dict:
    raw = path.read_bytes()
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_ensure_key())
    plain = aes.decrypt(nonce, ct, associated_data=b"AEGIS-TELEMETRY-v1")
    return json.loads(plain.decode("utf-8"))


def build_report_payload(db: Session, astronaut_id: str) -> dict:
    state = get_scenario(db)
    mission_day = state.mission_day
    history = bl.get_health_history(db, astronaut_id, mission_day)
    env = bl.get_environment_history(db, mission_day)
    metrics = bl.build_metrics(db, astronaut_id, mission_day)
    deviations = bl.detect_deviations(db, astronaut_id, mission_day)
    pattern = bl.detect_combined_patterns(db, astronaut_id, mission_day)
    assessments = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.astronaut_id == astronaut_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(3)
        .all()
    )

    latest = history[-1] if history else None
    env_latest = env[-1] if env else None

    return {
        "report_type": "AEGIS_CREW_HEALTH_SUMMARY",
        "version": "1.0",
        "simulated_relay": True,
        "astronaut_id": astronaut_id,
        "mission_day": mission_day,
        "scenario": state.scenario,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "recent_measurements": {
            "sleep_h": latest.sleep_h if latest else None,
            "resting_hr": latest.resting_hr if latest else None,
            "fatigue": latest.fatigue if latest else None,
            "reaction_time_ms": latest.reaction_time_ms if latest else None,
            "provenance": latest.provenance if latest else None,
        },
        "environment": {
            "co2_ppm": env_latest.co2_ppm if env_latest else None,
            "temperature_c": env_latest.temperature_c if env_latest else None,
            "humidity_pct": env_latest.humidity_pct if env_latest else None,
            "provenance": env_latest.provenance if env_latest else None,
            "source_label": env_latest.source_label if env_latest else None,
        },
        "baselines": {m.metric: {"latest": m.latest, "baseline": m.baseline, "delta": m.delta} for m in metrics},
        "deviations": [d.model_dump() for d in deviations],
        "combined_pattern": pattern.model_dump(),
        "assessment_results": [
            {
                "id": a.id,
                "mission_day": a.mission_day,
                "median_rt_ms": a.median_rt_ms,
                "iqr_ms": a.iqr_ms,
                "provenance": a.provenance,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assessments
        ],
        "advisory_status": pattern.severity if pattern.detected else "green",
        "disclaimer": (
            "Illustrative local prototype report. Not a clinical medical record. "
            "Not a real NASA relay transmission."
        ),
    }


def create_report(db: Session, astronaut_id: str) -> TelemetryReportOut:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state = get_scenario(db)
    payload = build_report_payload(db, astronaut_id)
    seq = db.query(TelemetryReport).count() + 1
    report_id = f"ETB-{state.mission_day:04d}-{chr(64 + min(seq, 26))}"

    nonce, ct = encrypt_payload(payload)
    path = REPORTS_DIR / f"{report_id}.bin"
    path.write_bytes(nonce + ct)

    sections = [
        "Health Summary",
        "Trend Analysis",
        "Assessment Result",
        "Environmental Data",
    ]
    row = TelemetryReport(
        id=report_id,
        astronaut_id=astronaut_id,
        mission_day=state.mission_day,
        status="queued",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ciphertext_path=str(path),
        sections_json=json.dumps(sections),
        plaintext_preview=json.dumps(
            {
                "astronaut_id": astronaut_id,
                "mission_day": state.mission_day,
                "advisory_status": payload["advisory_status"],
                "sections": sections,
            }
        ),
    )
    db.add(row)
    db.commit()
    return _to_out(row)


def list_queue(db: Session) -> TelemetryQueueOut:
    state = get_scenario(db)
    rows = db.query(TelemetryReport).order_by(TelemetryReport.created_at.desc()).all()
    # Simulated next window: ~18–20 minutes from a fixed offset based on day
    countdown = 18 * 60 + (state.mission_day % 60)
    hour = 6
    minute = 24 + (state.mission_day % 20)
    if minute >= 60:
        hour += 1
        minute -= 60
    return TelemetryQueueOut(
        reports=[_to_out(r) for r in rows],
        next_window_label=(
            f"Mars Relay (Simulated) — next available window: "
            f"Day {state.mission_day}, {hour:02d}:{minute:02d} UTC"
        ),
        countdown_seconds=countdown,
        simulated=True,
    )


def simulate_transmission(db: Session) -> dict:
    queued = (
        db.query(TelemetryReport)
        .filter(TelemetryReport.status == "queued")
        .order_by(TelemetryReport.created_at.asc())
        .all()
    )
    if not queued:
        return {
            "detail": "No queued reports to transmit.",
            "transmitted": [],
            "simulated": True,
        }
    sent_ids = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in queued:
        row.status = "sent"
        row.sent_at = now
        sent_ids.append(row.id)
    db.commit()
    return {
        "detail": f"Simulated transmission complete for {len(sent_ids)} report(s).",
        "transmitted": sent_ids,
        "simulated": True,
        "note": "No real NASA relay was contacted. Artifacts remain local.",
    }


def export_report_path(db: Session, report_id: str) -> Path | None:
    row = db.get(TelemetryReport, report_id)
    if not row:
        return None
    path = Path(row.ciphertext_path)
    return path if path.exists() else None


def _to_out(row: TelemetryReport) -> TelemetryReportOut:
    try:
        sections = json.loads(row.sections_json or "[]")
    except json.JSONDecodeError:
        sections = []
    return TelemetryReportOut(
        id=row.id,
        astronaut_id=row.astronaut_id,
        mission_day=row.mission_day,
        status=row.status,  # type: ignore[arg-type]
        created_at=(row.created_at or datetime.now(timezone.utc).replace(tzinfo=None)).isoformat() + "Z",
        encrypted=True,
        sections=sections,
    )
