from __future__ import annotations

from statistics import median
from typing import Optional

from sqlalchemy.orm import Session

from ..models import NasaTelemetryRecord
from . import nasa_eda_service as nasa


def calculate_environment_baseline(
    db: Session,
    mission_id: str,
    metric: str = "co2_iss",
    baseline_fraction: float = 0.2,
) -> dict:
    """Baseline from the earliest portion of the historical series (robust median)."""
    rows = nasa.query_telemetry(db, mission_id, stride=1)
    values = _metric_series(rows, metric)
    if len(values) < 5:
        return {
            "metric": metric,
            "baseline": None,
            "method": "insufficient_data",
            "n": len(values),
            "unit": _unit(metric),
        }
    n = max(5, int(len(values) * baseline_fraction))
    window = values[:n]
    base = median(window)
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / max(1, len(window) - 1)
    return {
        "metric": metric,
        "baseline": round(base, 3),
        "baseline_mean": round(mean, 3),
        "baseline_stdev": round(var**0.5, 3),
        "method": f"median of first {n} samples (~{int(baseline_fraction * 100)}% of series)",
        "n": n,
        "unit": _unit(metric),
        "provenance": "NASA_HISTORICAL",
    }


def detect_environment_anomalies(
    db: Session,
    mission_id: str,
    z_thresh: float = 2.5,
    sustained: int = 6,
) -> list[dict]:
    """Statistical anomalies vs early historical baseline — not medical danger labels."""
    metrics = ["co2_iss", "temperature_iss", "humidity_iss"]
    # Downsample only for large caches (~12k RR-1 rows); keep full resolution for small sets.
    full = nasa.query_telemetry(db, mission_id, stride=1)
    if not full:
        return []
    stride = 8 if len(full) > 500 else 1
    rows = full[::stride] if stride > 1 else full

    anomalies: list[dict] = []
    for metric in metrics:
        base = calculate_environment_baseline(db, mission_id, metric)
        if base["baseline"] is None:
            continue
        baseline = float(base["baseline"])
        stdev = float(base.get("baseline_stdev") or 0.0)
        floor = {"co2_iss": 50.0, "temperature_iss": 0.3, "humidity_iss": 1.0}.get(metric, 1.0)
        scale = max(stdev, floor)

        points = [(r.time_utc, v) for r in rows if (v := _get(r, metric)) is not None]
        streak_vals: list[float] = []
        streak_start: Optional[str] = None
        streak_end: Optional[str] = None

        def flush():
            nonlocal streak_vals, streak_start, streak_end
            if len(streak_vals) >= sustained and streak_start and streak_end:
                anomalies.append(
                    _anomaly(metric, baseline, streak_vals, streak_start, streak_end, len(streak_vals), scale)
                )
            streak_vals = []
            streak_start = None
            streak_end = None

        for t, v in points:
            if metric == "co2_iss":
                hit = (v - baseline) > z_thresh * scale
            else:
                hit = abs(v - baseline) > z_thresh * scale
            if hit:
                if not streak_vals:
                    streak_start = t
                streak_vals.append(v)
                streak_end = t
            else:
                flush()
        flush()

    return anomalies


def get_environment_trends(db: Session, mission_id: str, stride: int = 20) -> dict:
    rows = nasa.query_telemetry(db, mission_id, stride=stride)
    series = {
        "co2_iss": [{"time": r.time_utc, "value": r.co2_iss} for r in rows if r.co2_iss is not None],
        "temperature_iss": [
            {"time": r.time_utc, "value": r.temperature_iss}
            for r in rows
            if r.temperature_iss is not None
        ],
        "humidity_iss": [
            {"time": r.time_utc, "value": r.humidity_iss} for r in rows if r.humidity_iss is not None
        ],
        "co2_ground": [
            {"time": r.time_utc, "value": r.co2_ground} for r in rows if r.co2_ground is not None
        ],
    }
    return {
        "mission_id": mission_id,
        "stride": stride,
        "series": series,
        "stats": {m: nasa.rolling_stats([p["value"] for p in series[m]]) for m in series},
        "provenance": "NASA_HISTORICAL",
    }


def get_environment_summary(db: Session, mission_id: str, at: Optional[str] = None) -> dict:
    meta = nasa.get_import_meta(db, mission_id)
    if not meta:
        return {
            "mission_id": mission_id,
            "cached": False,
            "message": "NASA data not imported. POST /api/nasa/import/{mission_id} while online.",
        }

    cursor = at or meta.time_end
    telem = nasa.nearest_telemetry(db, mission_id, cursor) if cursor else None
    rad = nasa.radiation_as_of(db, mission_id, cursor) if cursor else None
    rad_all = nasa.query_radiation(db, mission_id)
    anomalies = detect_environment_anomalies(db, mission_id)

    metrics = {}
    spark_rows = nasa.query_telemetry(db, mission_id, stride=max(1, (meta.telemetry_count // 200) or 1))
    roll_rows = nasa.query_telemetry(db, mission_id, stride=5)
    if telem:
        for key, label, unit in [
            ("co2_iss", "CO₂ (ISS)", "ppm"),
            ("temperature_iss", "Temperature (ISS)", "°C"),
            ("humidity_iss", "Humidity (ISS)", "%"),
        ]:
            base = calculate_environment_baseline(db, mission_id, key)
            val = getattr(telem, key)
            delta = None if val is None or base["baseline"] is None else round(val - base["baseline"], 3)
            spark = [getattr(r, key) for r in spark_rows if getattr(r, key) is not None][-48:]
            metrics[key] = {
                "label": label,
                "value": val,
                "unit": unit,
                "baseline": base["baseline"],
                "delta_vs_baseline": delta,
                "rolling": nasa.rolling_stats(
                    [getattr(r, key) for r in roll_rows if getattr(r, key) is not None]
                ),
                "sparkline": spark,
                "quality": "ok" if val is not None else "missing",
            }

    return {
        "mission_id": mission_id,
        "mission_title": meta.mission_title,
        "cached": True,
        "imported_at": meta.imported_at,
        "source": {
            "system": "NASA OSDR / EDA",
            "telemetry_url": meta.telemetry_url,
            "radiation_url": meta.radiation_url,
            "time_start": meta.time_start,
            "time_end": meta.time_end,
            "disclaimer": (
                "RR-1 contains environmental and radiation measurements associated with NASA's "
                "Rodent Research-1 mission. Historical research observations — not real-time "
                "astronaut medical data."
            ),
        },
        "selected_time": telem.time_utc if telem else cursor,
        "telemetry": nasa.telem_to_dict(telem) if telem else None,
        "radiation": nasa.rad_to_dict(rad) if rad else None,
        "radiation_note": (
            None
            if rad
            else "No radiation sample at/before selected time — daily series only; not interpolated."
        ),
        "cumulative_dose": nasa.cumulative_dose_mgy(rad_all),
        "metrics": metrics,
        "anomaly_count": len(anomalies),
        "recent_anomalies": anomalies[:5],
        "provenance": "NASA_HISTORICAL",
    }


def _get(r: NasaTelemetryRecord, metric: str) -> Optional[float]:
    return getattr(r, metric, None)


def _metric_series(rows: list[NasaTelemetryRecord], metric: str) -> list[float]:
    return [v for r in rows if (v := _get(r, metric)) is not None]


def _unit(metric: str) -> str:
    if "co2" in metric:
        return "ppm"
    if "humidity" in metric:
        return "%"
    return "°C"


def _anomaly(
    metric: str,
    baseline: float,
    window_vals: list[float],
    start: str,
    end: str,
    streak: int,
    scale: float,
) -> dict:
    latest = window_vals[-1] if window_vals else None
    direction = "elevated" if latest is not None and latest > baseline else "depressed"
    label = {
        "co2_iss": "CO₂",
        "temperature_iss": "Temperature",
        "humidity_iss": "Humidity",
    }.get(metric, metric)
    return {
        "metric": metric,
        "kind": "statistical_anomaly",
        "severity": "amber",
        "start": start,
        "end": end,
        "sustained_samples": streak,
        "baseline": baseline,
        "latest": latest,
        "dispersion_scale": round(scale, 3),
        "explanation": (
            f"{label} readings are {direction} relative to the selected historical reference period "
            f"(statistical deviation only — not a medical danger classification)."
        ),
        "unit": _unit(metric),
    }
