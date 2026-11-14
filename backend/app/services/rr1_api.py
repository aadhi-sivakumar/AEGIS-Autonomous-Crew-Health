from __future__ import annotations

"""NASA OSDR RR-1 environmental telemetry client + SQLite cache.

API: https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/telemetry_data/

Fields used (ISS rodent-research hardware environment, 2014):
  - time
  - co2_iss (ppm)
  - temperature_iss (°C)
  - humidity_iss (%)

Not astronaut medical data. Not live spacecraft telemetry.
"""

import json
import statistics
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models import AppState, EnvironmentRecord, NasaEnvSample

RR1_URL = "https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/telemetry_data/"
SOURCE_LABEL = "NASA RR-1 Historical Environmental Data — 2014"
PROVENANCE = "NASA_RR1_HISTORICAL"
FETCH_TIMEOUT_S = 45


def fetch_rr1_telemetry() -> list[dict[str, Any]]:
    """Download RR-1 telemetry JSON. Raises on network/API failure — does not fabricate."""
    req = urllib.request.Request(
        RR1_URL,
        headers={"Accept": "application/json", "User-Agent": "AEGIS-local-prototype/1.0"},
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        payload = json.load(resp)
    if not isinstance(payload, list):
        raise ValueError("Unexpected RR-1 API response: expected a JSON array")
    return payload


def _parse_sample(raw: dict[str, Any]) -> dict[str, Any] | None:
    time_utc = raw.get("time")
    co2 = raw.get("co2_iss")
    temp = raw.get("temperature_iss")
    humidity = raw.get("humidity_iss")
    if not time_utc:
        return None
    if co2 is None and temp is None and humidity is None:
        return None
    try:
        return {
            "time_utc": str(time_utc),
            "co2_ppm": float(co2) if co2 is not None else None,
            "temperature_c": float(temp) if temp is not None else None,
            "humidity_pct": float(humidity) if humidity is not None else None,
        }
    except (TypeError, ValueError):
        return None


def cache_samples(db: Session, raw_rows: list[dict[str, Any]]) -> int:
    """Replace NasaEnvSample cache with parsed RR-1 ISS measurements."""
    parsed: list[dict[str, Any]] = []
    for raw in raw_rows:
        row = _parse_sample(raw)
        if not row:
            continue
        # Skip rows missing any of the three ISS channels
        if row["co2_ppm"] is None or row["temperature_c"] is None or row["humidity_pct"] is None:
            continue
        parsed.append(row)

    if not parsed:
        raise ValueError("RR-1 payload contained no usable ISS CO₂/temperature/humidity rows")

    db.query(NasaEnvSample).delete()
    for row in parsed:
        db.add(
            NasaEnvSample(
                time_utc=row["time_utc"],
                co2_ppm=row["co2_ppm"],
                temperature_c=row["temperature_c"],
                humidity_pct=row["humidity_pct"],
                mission="RR-1",
                provenance=PROVENANCE,
                source_label=SOURCE_LABEL,
            )
        )
    db.commit()
    return len(parsed)


def load_synthetic_environment(db: Session) -> int:
    """Replace active EnvironmentRecord rows with the synthetic cabin fixture."""
    from ..seed import generate_environment

    db.query(EnvironmentRecord).delete()
    db.commit()
    rows = generate_environment()
    for row in rows:
        db.add(EnvironmentRecord(**row))
    db.commit()
    return len(rows)


def apply_daily_env_records(db: Session) -> int:
    """Replace active EnvironmentRecord rows with RR-1 daily averages."""
    samples = (
        db.query(NasaEnvSample)
        .order_by(NasaEnvSample.time_utc.asc())
        .all()
    )
    if not samples:
        return 0

    by_day: dict[str, list[NasaEnvSample]] = defaultdict(list)
    for s in samples:
        by_day[s.time_utc[:10]].append(s)

    ordered_days = sorted(by_day.keys())
    db.query(EnvironmentRecord).delete()
    db.commit()

    for idx, day in enumerate(ordered_days, start=1):
        group = by_day[day]
        db.add(
            EnvironmentRecord(
                mission_day=idx,
                co2_ppm=round(statistics.mean(x.co2_ppm for x in group), 1),
                temperature_c=round(statistics.mean(x.temperature_c for x in group), 1),
                humidity_pct=round(statistics.mean(x.humidity_pct for x in group), 1),
                provenance=PROVENANCE,
                source_label=SOURCE_LABEL,
                sample_date=day,
            )
        )

    flag = db.get(AppState, "nasa_import_loaded")
    if flag:
        flag.value = "true"
    else:
        db.add(AppState(key="nasa_import_loaded", value="true"))
    meta = {
        "mission": "RR-1",
        "source": RR1_URL,
        "label": SOURCE_LABEL,
        "sample_count": len(samples),
        "daily_count": len(ordered_days),
        "start": ordered_days[0],
        "end": ordered_days[-1],
        "note": (
            "ISS RR-1 rodent-research hardware environmental telemetry (2014). "
            "Not astronaut medical data. Not causally paired with simulated crew health."
        ),
    }
    existing_meta = db.get(AppState, "nasa_import_meta")
    if existing_meta:
        existing_meta.value = json.dumps(meta)
    else:
        db.add(AppState(key="nasa_import_meta", value=json.dumps(meta)))
    db.commit()
    return len(ordered_days)


def sync_active_environment(db: Session, mode: str | None = None) -> dict[str, Any]:
    """Swap EnvironmentRecord to match Simulated vs NASA Historical mode."""
    from .nasa_eda_service import get_env_data_mode

    mode = mode or get_env_data_mode(db)
    if mode == "nasa_historical":
        cached = db.query(NasaEnvSample).count()
        if cached <= 0:
            days = load_synthetic_environment(db)
            return {
                "mode": mode,
                "source": "synthetic_fallback",
                "daily_count": days,
                "note": "NASA cache empty — using synthetic cabin fixture.",
            }
        days = apply_daily_env_records(db)
        return {"mode": mode, "source": "nasa_rr1", "daily_count": days, "label": SOURCE_LABEL}

    days = load_synthetic_environment(db)
    return {"mode": "simulated", "source": "synthetic", "daily_count": days}


def ensure_rr1_cached(db: Session, force_refresh: bool = False) -> dict[str, Any]:
    """
    Ensure RR-1 data is cached locally.
    - Uses SQLite cache when present (offline-ready).
    - Fetches from NASA API only when cache empty or force_refresh=True.
    - Does not fabricate rows if the API is unavailable.
    """
    cached = db.query(NasaEnvSample).count()
    if cached and not force_refresh:
        # Ensure EnvironmentRecord reflects NASA cache
        nasa_env = (
            db.query(EnvironmentRecord)
            .filter(EnvironmentRecord.provenance == PROVENANCE)
            .count()
        )
        if nasa_env == 0:
            days = apply_daily_env_records(db)
        else:
            days = nasa_env
        return {
            "ok": True,
            "source": "cache",
            "sample_count": cached,
            "daily_count": days,
            "label": SOURCE_LABEL,
            "offline_ready": True,
        }

    try:
        raw = fetch_rr1_telemetry()
        n = cache_samples(db, raw)
        days = apply_daily_env_records(db)
        return {
            "ok": True,
            "source": "api",
            "sample_count": n,
            "daily_count": days,
            "label": SOURCE_LABEL,
            "offline_ready": True,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        if cached:
            days = apply_daily_env_records(db)
            return {
                "ok": True,
                "source": "cache_fallback",
                "sample_count": cached,
                "daily_count": days,
                "label": SOURCE_LABEL,
                "warning": f"API unavailable ({e}); served local SQLite cache.",
                "offline_ready": True,
            }
        return {
            "ok": False,
            "source": "unavailable",
            "error": str(e),
            "label": SOURCE_LABEL,
            "offline_ready": False,
            "message": (
                "NASA RR-1 API unavailable and no local cache exists. "
                "Synthetic environment fixture remains in use. No data was fabricated."
            ),
        }


def historical_stats(db: Session) -> dict[str, dict[str, float]]:
    samples = db.query(NasaEnvSample).all()
    if not samples:
        return {}

    def pack(vals: list[float]) -> dict[str, float]:
        mean = statistics.mean(vals)
        stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        return {
            "mean": round(mean, 2),
            "stdev": round(stdev, 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "n": float(len(vals)),
        }

    return {
        "co2_ppm": pack([s.co2_ppm for s in samples]),
        "temperature_c": pack([s.temperature_c for s in samples]),
        "humidity_pct": pack([s.humidity_pct for s in samples]),
    }


def deviation_explanations(db: Session, latest: EnvironmentRecord | None) -> list[dict[str, str]]:
    """Compare latest daily values to full RR-1 historical mean ± 1.5σ."""
    if latest is None or latest.provenance != PROVENANCE:
        return []
    stats = historical_stats(db)
    if not stats:
        return []

    out: list[dict[str, str]] = []
    checks = [
        ("co2_ppm", latest.co2_ppm, "CO₂", "ppm"),
        ("temperature_c", latest.temperature_c, "Temperature", "°C"),
        ("humidity_pct", latest.humidity_pct, "Humidity", "%"),
    ]
    for key, value, label, unit in checks:
        s = stats[key]
        mean, stdev = s["mean"], s["stdev"]
        threshold = max(stdev * 1.5, 1.0 if key != "co2_ppm" else 50.0)
        delta = value - mean
        if abs(delta) < threshold:
            continue
        direction = "high" if delta > 0 else "low"
        out.append(
            {
                "metric": key,
                "severity": "amber" if abs(delta) < threshold * 2 else "red",
                "explanation": (
                    f"{label} is unusually {direction} versus the RR-1 historical average "
                    f"({mean:.1f} {unit}): latest {value:.1f} {unit} "
                    f"({delta:+.1f} {unit}). "
                    "ISS rodent-research hardware environment — not astronaut medical data."
                ),
            }
        )
    return out


def chart_series(db: Session, max_points: int = 240) -> list[dict[str, Any]]:
    """Downsampled time series for the overview chart."""
    samples = (
        db.query(NasaEnvSample)
        .order_by(NasaEnvSample.time_utc.asc())
        .all()
    )
    if not samples:
        return []
    step = max(1, len(samples) // max_points)
    series = []
    for s in samples[::step]:
        # Compact label: MM-DD HH:MM
        try:
            dt = datetime.fromisoformat(s.time_utc.replace("Z", "+00:00"))
            label = dt.strftime("%m-%d %H:%M")
        except ValueError:
            label = s.time_utc[:16]
        series.append(
            {
                "time": s.time_utc,
                "label": label,
                "co2_ppm": round(s.co2_ppm, 1),
                "temperature_c": round(s.temperature_c, 1),
                "humidity_pct": round(s.humidity_pct, 1),
            }
        )
    return series
