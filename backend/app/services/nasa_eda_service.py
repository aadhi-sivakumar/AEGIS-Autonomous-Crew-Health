"""NASA OSDR Environmental Data Application (EDA) live API client + local SQLite cache.

API base: https://visualization.osdr.nasa.gov/eda/api/
Telemetry/radiation responses are bare JSON arrays (no `data` wrapper).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from statistics import median
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from ..models import AppState, NasaImportMeta, NasaRadiationRecord, NasaTelemetryRecord

EDA_BASE = "https://visualization.osdr.nasa.gov/eda/api"
DEFAULT_MISSION = "RR-1"
REQUEST_TIMEOUT_S = 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() in {"na", "nan", "null", "none", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_time(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # Accept ISO 8601; normalize Z
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def fetch_json(url: str) -> Any:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "AEGIS-local/1.0"})
    with urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def list_missions_remote() -> list[dict]:
    data = fetch_json(f"{EDA_BASE}/missions/")
    if not isinstance(data, list):
        raise ValueError("Unexpected missions payload — expected a JSON array")
    return data


def parse_telemetry_records(raw: Any, mission_id: str) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError("Telemetry payload must be a JSON array")
    url = f"{EDA_BASE}/missions/{mission_id}/telemetry_data/"
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = _normalize_time(item.get("time"))
        if not t:
            continue
        out.append(
            {
                "mission_id": mission_id,
                "time_utc": t,
                "temperature_iss": _to_float(item.get("temperature_iss")),
                "temperature_ground": _to_float(item.get("temperature_ground")),
                "humidity_iss": _to_float(item.get("humidity_iss")),
                "humidity_ground": _to_float(item.get("humidity_ground")),
                "co2_iss": _to_float(item.get("co2_iss")),
                "co2_ground": _to_float(item.get("co2_ground")),
                "milestones": item.get("milestones") or None,
                "source_url": url,
            }
        )
    return out


def parse_radiation_records(raw: Any, mission_id: str) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError("Radiation payload must be a JSON array")
    url = f"{EDA_BASE}/missions/{mission_id}/radiation_data/"
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = _normalize_time(item.get("time"))
        if not t:
            continue
        out.append(
            {
                "mission_id": mission_id,
                "time_utc": t,
                "gcr": _to_float(item.get("gcr")),
                "saa": _to_float(item.get("saa")),
                "total": _to_float(item.get("total")),
                "milestones": item.get("milestones") or None,
                "source_url": url,
            }
        )
    return out


def import_mission(db: Session, mission_id: str = DEFAULT_MISSION) -> dict:
    """Fetch RR-1 (or other) telemetry + radiation and upsert into SQLite."""
    missions = list_missions_remote()
    title = next((m.get("title") or mission_id for m in missions if m.get("name") == mission_id), mission_id)

    telem_url = f"{EDA_BASE}/missions/{mission_id}/telemetry_data/"
    rad_url = f"{EDA_BASE}/missions/{mission_id}/radiation_data/"
    telem_raw = fetch_json(telem_url)
    rad_raw = fetch_json(rad_url)

    telem_rows = parse_telemetry_records(telem_raw, mission_id)
    rad_rows = parse_radiation_records(rad_raw, mission_id)

    # Replace mission cache (dedupe by unique constraint; clear first for clean reimport)
    db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == mission_id).delete()
    db.query(NasaRadiationRecord).filter(NasaRadiationRecord.mission_id == mission_id).delete()

    for row in telem_rows:
        db.add(NasaTelemetryRecord(**row))
    for row in rad_rows:
        db.add(NasaRadiationRecord(**row))

    times = [r["time_utc"] for r in telem_rows]
    meta = db.get(NasaImportMeta, mission_id)
    payload = dict(
        imported_at=_now_iso(),
        telemetry_url=telem_url,
        radiation_url=rad_url,
        telemetry_count=len(telem_rows),
        radiation_count=len(rad_rows),
        mission_title=title,
        time_start=min(times) if times else None,
        time_end=max(times) if times else None,
    )
    if meta:
        for k, v in payload.items():
            setattr(meta, k, v)
    else:
        db.add(NasaImportMeta(mission_id=mission_id, **payload))

    # Flags for overview / env mode
    flag = db.get(AppState, "nasa_eda_cached")
    if flag:
        flag.value = "true"
    else:
        db.add(AppState(key="nasa_eda_cached", value="true"))
    active = db.get(AppState, "nasa_active_mission")
    if active:
        active.value = mission_id
    else:
        db.add(AppState(key="nasa_active_mission", value=mission_id))

    db.commit()

    # Keep legacy overview path in sync (NasaEnvSample + daily EnvironmentRecord).
    synced_daily = 0
    if mission_id == "RR-1":
        try:
            from . import rr1_api

            rr1_api.cache_samples(db, telem_raw if isinstance(telem_raw, list) else [])
            synced_daily = rr1_api.apply_daily_env_records(db)
        except Exception:
            synced_daily = 0

    return {
        "mission_id": mission_id,
        "mission_title": title,
        "telemetry_count": len(telem_rows),
        "radiation_count": len(rad_rows),
        "daily_env_records": synced_daily,
        "time_start": payload["time_start"],
        "time_end": payload["time_end"],
        "imported_at": payload["imported_at"],
        "telemetry_url": telem_url,
        "radiation_url": rad_url,
        "cached": True,
        "note": (
            "RR-1 environmental/radiation observations are historical NASA research data "
            "(Rodent Research-1, 2014). Not real-time astronaut medical telemetry."
        ),
    }


def get_import_meta(db: Session, mission_id: str) -> Optional[NasaImportMeta]:
    return db.get(NasaImportMeta, mission_id)


def is_mission_cached(db: Session, mission_id: str) -> bool:
    meta = get_import_meta(db, mission_id)
    return bool(meta and meta.telemetry_count > 0)


def get_env_data_mode(db: Session) -> str:
    row = db.get(AppState, "env_data_mode")
    if row and row.value in {"simulated", "nasa_historical"}:
        return row.value
    # Prefer NASA historical when RR-1 is already cached (judge-ready default).
    if is_mission_cached(db, "RR-1"):
        return "nasa_historical"
    return "simulated"


def set_env_data_mode(db: Session, mode: str) -> str:
    if mode not in {"simulated", "nasa_historical"}:
        raise ValueError("mode must be simulated or nasa_historical")
    row = db.get(AppState, "env_data_mode")
    if row:
        row.value = mode
    else:
        db.add(AppState(key="env_data_mode", value=mode))
    db.commit()
    # Rebuild active cabin series so Overview/Today CO₂ actually changes.
    from .rr1_api import sync_active_environment

    sync_active_environment(db, mode)
    return mode


def prefer_nasa_historical_when_cached(db: Session) -> str:
    """Set env mode to NASA historical if cache exists and mode was never chosen."""
    row = db.get(AppState, "env_data_mode")
    if row is None and is_mission_cached(db, "RR-1"):
        return set_env_data_mode(db, "nasa_historical")
    return get_env_data_mode(db)


def query_telemetry(
    db: Session,
    mission_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    stride: int = 1,
) -> list[NasaTelemetryRecord]:
    q = db.query(NasaTelemetryRecord).filter(NasaTelemetryRecord.mission_id == mission_id)
    if start:
        start_n = _normalize_time(start) or start
        q = q.filter(NasaTelemetryRecord.time_utc >= start_n)
    if end:
        end_n = _normalize_time(end) or end
        q = q.filter(NasaTelemetryRecord.time_utc <= end_n)
    rows = q.order_by(NasaTelemetryRecord.time_utc.asc()).all()
    stride = max(1, int(stride))
    if stride == 1:
        return rows
    # Always keep first/last and any milestone rows
    kept: list[NasaTelemetryRecord] = []
    for i, r in enumerate(rows):
        if i % stride == 0 or r.milestones or i == len(rows) - 1:
            kept.append(r)
    return kept


def query_radiation(
    db: Session,
    mission_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[NasaRadiationRecord]:
    q = db.query(NasaRadiationRecord).filter(NasaRadiationRecord.mission_id == mission_id)
    if start:
        q = q.filter(NasaRadiationRecord.time_utc >= (_normalize_time(start) or start))
    if end:
        q = q.filter(NasaRadiationRecord.time_utc <= (_normalize_time(end) or end))
    return q.order_by(NasaRadiationRecord.time_utc.asc()).all()


def nearest_telemetry(db: Session, mission_id: str, at: str) -> Optional[NasaTelemetryRecord]:
    t = _normalize_time(at) or at
    # Prefer exact or last at-or-before; else first after
    before = (
        db.query(NasaTelemetryRecord)
        .filter(NasaTelemetryRecord.mission_id == mission_id, NasaTelemetryRecord.time_utc <= t)
        .order_by(NasaTelemetryRecord.time_utc.desc())
        .first()
    )
    if before:
        return before
    return (
        db.query(NasaTelemetryRecord)
        .filter(NasaTelemetryRecord.mission_id == mission_id, NasaTelemetryRecord.time_utc > t)
        .order_by(NasaTelemetryRecord.time_utc.asc())
        .first()
    )


def radiation_as_of(db: Session, mission_id: str, at: str) -> Optional[NasaRadiationRecord]:
    """Most recent daily radiation record at or before `at` (do not interpolate)."""
    t = _normalize_time(at) or at
    return (
        db.query(NasaRadiationRecord)
        .filter(NasaRadiationRecord.mission_id == mission_id, NasaRadiationRecord.time_utc <= t)
        .order_by(NasaRadiationRecord.time_utc.desc())
        .first()
    )


def cumulative_dose_mgy(records: list[NasaRadiationRecord]) -> dict:
    """Sum daily total dose rates (mGy/day) assuming ~1 day per record.

    Radiation EDA series is daily; we treat each `total` as that day's dose contribution
    without interpolating between days. Does not mix uneven intervals.
    """
    vals = [r.total for r in records if r.total is not None]
    return {
        "cumulative_mgy": round(sum(vals), 5) if vals else None,
        "days_counted": len(vals),
        "method": (
            "Sum of daily `total` dose-rate samples (mGy/day), one contribution per radiation "
            "record day. Not interpolated to telemetry cadence."
        ),
        "unit": "mGy",
    }


def telem_to_dict(r: NasaTelemetryRecord) -> dict:
    return {
        "time": r.time_utc,
        "temperature_iss": r.temperature_iss,
        "temperature_ground": r.temperature_ground,
        "humidity_iss": r.humidity_iss,
        "humidity_ground": r.humidity_ground,
        "co2_iss": r.co2_iss,
        "co2_ground": r.co2_ground,
        "milestones": r.milestones,
        "units": {"temperature": "°C", "humidity": "%", "co2": "ppm"},
        "provenance": "NASA_HISTORICAL",
        "context": "ISS research-environment (RR hardware / EDA), not crew medical telemetry",
    }


def rad_to_dict(r: NasaRadiationRecord) -> dict:
    return {
        "time": r.time_utc,
        "gcr": r.gcr,
        "saa": r.saa,
        "total": r.total,
        "milestones": r.milestones,
        "units": "mGy/day",
        "provenance": "NASA_HISTORICAL",
    }


def list_missions_local_or_remote(db: Session) -> dict:
    cached = db.query(NasaImportMeta).all()
    cached_ids = {m.mission_id for m in cached}
    remote: list[dict] = []
    online = True
    try:
        remote = list_missions_remote()
    except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        online = False
        remote = [
            {
                "name": m.mission_id,
                "title": m.mission_title or m.mission_id,
                "description": "Cached locally — remote mission list unavailable.",
                "link": m.telemetry_url,
            }
            for m in cached
        ]
        err = str(e)
    else:
        err = None

    return {
        "online": online,
        "error": err,
        "missions": [
            {
                **m,
                "cached": m.get("name") in cached_ids,
            }
            for m in remote
        ],
        "cached_missions": [
            {
                "mission_id": m.mission_id,
                "title": m.mission_title,
                "imported_at": m.imported_at,
                "telemetry_count": m.telemetry_count,
                "radiation_count": m.radiation_count,
                "time_start": m.time_start,
                "time_end": m.time_end,
            }
            for m in cached
        ],
    }


def rolling_stats(values: list[float], window: int = 48) -> dict:
    if not values:
        return {"mean": None, "median": None, "stdev": None, "latest": None}
    latest = values[-1]
    w = values[-window:] if len(values) >= window else values
    mean = sum(w) / len(w)
    med = median(w)
    var = sum((x - mean) ** 2 for x in w) / max(1, len(w) - 1)
    stdev = var**0.5
    return {
        "latest": round(latest, 3),
        "rolling_mean": round(mean, 3),
        "rolling_median": round(med, 3),
        "rolling_stdev": round(stdev, 3),
        "n": len(w),
    }
