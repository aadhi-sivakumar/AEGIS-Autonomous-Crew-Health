from __future__ import annotations

"""Reusable importer for locally downloaded NASA OSDR Environmental Data Application CSVs.

Source reference: https://visualization.osdr.nasa.gov/eda/

This does NOT call a live NASA API. Place exported CSVs under data/imports/ and
invoke import_osdr_csv() (or POST /api/environment/import).
"""

import csv
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..db import DATA_DIR
from ..models import AppState, EnvironmentRecord

IMPORTS_DIR = DATA_DIR / "imports"
IMPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Flexible column aliases for OSDR / common environmental exports.
COLUMN_ALIASES: dict[str, list[str]] = {
    "mission_day": ["mission_day", "day", "sol", "missionday", "mission day"],
    "timestamp": ["timestamp", "time", "datetime", "date", "sample_time"],
    "co2_ppm": ["co2_ppm", "co2", "co2_ppm_avg", "carbon_dioxide", "co₂", "pco2"],
    "temperature_c": ["temperature_c", "temp_c", "temperature", "temp", "cabin_temp"],
    "humidity_pct": ["humidity_pct", "humidity", "rh", "relative_humidity", "rh_pct"],
}


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace("-", "_").replace(" ", "_")


def map_columns(headers: list[str]) -> dict[str, str | None]:
    """Map canonical fields to actual CSV header names when possible."""
    normalized = {_normalize_header(h): h for h in headers}
    mapping: dict[str, str | None] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                found = normalized[key]
                break
        mapping[canonical] = found
    return mapping


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in {"na", "nan", "null", "none", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_osdr_csv(path: Path) -> tuple[list[dict], dict[str, Any]]:
    """Parse a local OSDR-style CSV into normalized environment rows."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        mapping = map_columns(list(reader.fieldnames))
        if not mapping.get("co2_ppm") and not mapping.get("temperature_c") and not mapping.get("humidity_pct"):
            raise ValueError(
                "Could not map CO₂ / temperature / humidity columns. "
                f"Found headers: {reader.fieldnames}"
            )

        rows: list[dict] = []
        day_counter = 1
        for raw in reader:
            co2 = _to_float(raw.get(mapping["co2_ppm"])) if mapping["co2_ppm"] else None
            temp = _to_float(raw.get(mapping["temperature_c"])) if mapping["temperature_c"] else None
            humidity = _to_float(raw.get(mapping["humidity_pct"])) if mapping["humidity_pct"] else None
            if co2 is None and temp is None and humidity is None:
                continue  # skip empty / missing-value rows

            day_val = None
            if mapping["mission_day"]:
                day_val = _to_float(raw.get(mapping["mission_day"]))
            mission_day = int(day_val) if day_val is not None else day_counter
            day_counter = max(day_counter, mission_day + 1)

            rows.append(
                {
                    "mission_day": mission_day,
                    "co2_ppm": round(co2 if co2 is not None else 900.0, 1),
                    "temperature_c": round(temp if temp is not None else 22.0, 1),
                    "humidity_pct": round(humidity if humidity is not None else 45.0, 1),
                    "provenance": "NASA_HISTORICAL",
                    "source_label": f"NASA OSDR import: {path.name}",
                }
            )

    meta = {
        "source_file": str(path),
        "dataset_id": path.stem,
        "row_count": len(rows),
        "column_mapping": mapping,
        "provenance": "NASA_HISTORICAL",
        "note": "Historical environmental import — not live spacecraft telemetry.",
    }
    return rows, meta


def import_osdr_csv(db: Session, path: Path, replace: bool = True) -> dict[str, Any]:
    rows, meta = parse_osdr_csv(path)
    if not rows:
        raise ValueError("No usable rows after missing-value handling")

    if replace:
        db.query(EnvironmentRecord).delete()
        db.commit()

    for row in rows:
        existing = (
            db.query(EnvironmentRecord)
            .filter(EnvironmentRecord.mission_day == row["mission_day"])
            .one_or_none()
        )
        if existing:
            existing.co2_ppm = row["co2_ppm"]
            existing.temperature_c = row["temperature_c"]
            existing.humidity_pct = row["humidity_pct"]
            existing.provenance = row["provenance"]
            existing.source_label = row["source_label"]
        else:
            db.add(EnvironmentRecord(**row))

    flag = db.get(AppState, "nasa_import_loaded")
    if flag:
        flag.value = "true"
    else:
        db.add(AppState(key="nasa_import_loaded", value="true"))
    db.add(AppState(key="nasa_import_meta", value=str(meta)))
    db.commit()
    return meta


def try_auto_import(db: Session) -> dict[str, Any] | None:
    """If a CSV exists in data/imports/, load the newest one."""
    csvs = sorted(IMPORTS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        return None
    return import_osdr_csv(db, csvs[0], replace=True)
