from __future__ import annotations

from statistics import median
from typing import Any

from sqlalchemy.orm import Session

from ..models import EnvironmentRecord, HealthRecord
from ..schemas import (
    CombinedPatternOut,
    DeviationOut,
    ForecastOut,
    HealthPoint,
    MetricBaseline,
    ZoneStatus,
    ZoneStatusOut,
)
from ..seed import BASELINE_WINDOW

# Prototype thresholds — statistical demo rules, NOT clinical / NASA medical limits.
SLEEP_DROP_H = 0.8
RT_RISE_MS = 20.0
FATIGUE_RISE = 1.5
HR_RISE = 6.0
CO2_ELEVATED = 1500.0
CONSECUTIVE_DAYS = 3


def get_health_history(db: Session, astronaut_id: str, up_to_day: int | None = None) -> list[HealthRecord]:
    q = (
        db.query(HealthRecord)
        .filter(HealthRecord.astronaut_id == astronaut_id)
        .order_by(HealthRecord.mission_day.asc())
    )
    if up_to_day is not None:
        q = q.filter(HealthRecord.mission_day <= up_to_day)
    return q.all()


def get_environment_history(db: Session, up_to_day: int | None = None) -> list[EnvironmentRecord]:
    """Active cabin env series (swapped by Simulated vs NASA Historical mode)."""
    q = db.query(EnvironmentRecord).order_by(EnvironmentRecord.mission_day.asc())
    if up_to_day is not None:
        q = q.filter(EnvironmentRecord.mission_day <= up_to_day)
    return q.all()


def _robust_baseline(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def calculate_baselines(db: Session, astronaut_id: str, up_to_day: int | None = None) -> dict[str, float]:
    history = get_health_history(db, astronaut_id, up_to_day)
    if not history:
        return {}

    window = history[:BASELINE_WINDOW] if len(history) >= BASELINE_WINDOW else history[: max(1, len(history) // 2)]
    if len(window) < 3:
        return {
            "sleep_h": history[0].sleep_h,
            "resting_hr": history[0].resting_hr,
            "fatigue": history[0].fatigue,
            "mood": history[0].mood,
            "reaction_time_ms": history[0].reaction_time_ms,
        }

    return {
        "sleep_h": _robust_baseline([r.sleep_h for r in window]),
        "resting_hr": _robust_baseline([r.resting_hr for r in window]),
        "fatigue": _robust_baseline([r.fatigue for r in window]),
        "mood": _robust_baseline([r.mood for r in window]),
        "reaction_time_ms": _robust_baseline([r.reaction_time_ms for r in window]),
    }


def _status_for_delta(metric: str, delta: float) -> ZoneStatus:
    if metric == "sleep_h":
        if delta <= -1.5:
            return "red"
        if delta <= -SLEEP_DROP_H:
            return "amber"
        return "green"
    if metric == "reaction_time_ms":
        if delta >= 40:
            return "red"
        if delta >= RT_RISE_MS:
            return "amber"
        return "green"
    if metric == "fatigue":
        if delta >= 3:
            return "red"
        if delta >= FATIGUE_RISE:
            return "amber"
        return "green"
    if metric == "resting_hr":
        if delta >= 12:
            return "red"
        if delta >= HR_RISE:
            return "amber"
        return "green"
    if metric == "co2_ppm":
        if delta >= 1000 or (delta > 0 and False):
            return "amber"
        return "green"
    return "green"


def _consecutive_direction(values: list[float], baseline: float, worse_if: str) -> int:
    streak = 0
    for v in reversed(values):
        if worse_if == "below" and v < baseline - (0.3 if baseline < 20 else 5):
            streak += 1
        elif worse_if == "above" and v > baseline + (0.3 if baseline < 20 else 5):
            streak += 1
        else:
            break
    return streak


def detect_deviations(db: Session, astronaut_id: str, mission_day: int) -> list[DeviationOut]:
    history = get_health_history(db, astronaut_id, mission_day)
    baselines = calculate_baselines(db, astronaut_id, mission_day)
    if not history or not baselines:
        return []

    recent = history[-7:]
    out: list[DeviationOut] = []

    sleep_vals = [r.sleep_h for r in recent]
    sleep_streak = _consecutive_direction(sleep_vals, baselines["sleep_h"], "below")
    if sleep_streak >= CONSECUTIVE_DAYS:
        delta = recent[-1].sleep_h - baselines["sleep_h"]
        out.append(
            DeviationOut(
                metric="sleep_h",
                direction="decreased",
                magnitude=abs(delta),
                consecutive_days=sleep_streak,
                explanation=(
                    f"Sleep has decreased relative to this crew member's baseline "
                    f"for {sleep_streak} consecutive days."
                ),
            )
        )

    rt_vals = [r.reaction_time_ms for r in recent]
    rt_streak = _consecutive_direction(rt_vals, baselines["reaction_time_ms"], "above")
    if rt_streak >= CONSECUTIVE_DAYS:
        delta = recent[-1].reaction_time_ms - baselines["reaction_time_ms"]
        out.append(
            DeviationOut(
                metric="reaction_time_ms",
                direction="increased",
                magnitude=abs(delta),
                consecutive_days=rt_streak,
                explanation=(
                    f"Reaction times have increased relative to baseline "
                    f"for {rt_streak} consecutive days."
                ),
            )
        )

    fatigue_vals = [r.fatigue for r in recent]
    fat_streak = _consecutive_direction(fatigue_vals, baselines["fatigue"], "above")
    if fat_streak >= CONSECUTIVE_DAYS:
        delta = recent[-1].fatigue - baselines["fatigue"]
        out.append(
            DeviationOut(
                metric="fatigue",
                direction="increased",
                magnitude=abs(delta),
                consecutive_days=fat_streak,
                explanation=(
                    f"Fatigue self-assessment is elevated versus baseline "
                    f"for {fat_streak} consecutive days."
                ),
            )
        )

    return out


def detect_combined_patterns(db: Session, astronaut_id: str, mission_day: int) -> CombinedPatternOut:
    deviations = detect_deviations(db, astronaut_id, mission_day)
    env = get_environment_history(db, mission_day)
    history = get_health_history(db, astronaut_id, mission_day)
    baselines = calculate_baselines(db, astronaut_id, mission_day)

    metrics = {d.metric for d in deviations}
    co2_elevated = bool(env and env[-1].co2_ppm >= CO2_ELEVATED)

    sleep_down = "sleep_h" in metrics
    rt_up = "reaction_time_ms" in metrics
    fatigue_up = "fatigue" in metrics

    contributing: list[str] = []
    if sleep_down:
        contributing.append("Sleep")
    if rt_up:
        contributing.append("Reaction time")
    if fatigue_up:
        contributing.append("Fatigue")
    if co2_elevated:
        contributing.append("Cabin CO₂")

    combined = (sleep_down and rt_up) or (sleep_down and co2_elevated and rt_up) or (rt_up and fatigue_up)

    if not history or not baselines:
        return CombinedPatternOut(
            detected=False,
            severity="green",
            summary="Insufficient data to evaluate combined patterns.",
            contributing_metrics=[],
            recommended_action="Continue routine monitoring.",
        )

    if combined and len(contributing) >= 2:
        parts = []
        if sleep_down:
            parts.append("Sleep ↓")
        if co2_elevated:
            parts.append("CO₂ ↑")
        if rt_up:
            parts.append("reaction time ↑")
        if fatigue_up:
            parts.append("fatigue ↑")
        summary = (
            "Potential performance deterioration detected. "
            + ", ".join(parts)
            + f" over the last {CONSECUTIVE_DAYS}+ days."
        )
        severity: ZoneStatus = "red" if len(contributing) >= 3 and rt_up else "amber"
        return CombinedPatternOut(
            detected=True,
            severity=severity,
            summary=summary,
            contributing_metrics=contributing,
            recommended_action="Complete a cognitive assessment and review sleep / workload / cabin environment.",
        )

    return CombinedPatternOut(
        detected=False,
        severity="green",
        summary="No sustained multi-indicator pattern detected versus personal baseline.",
        contributing_metrics=[],
        recommended_action="Continue routine monitoring.",
    )


def zone_statuses(db: Session, astronaut_id: str, mission_day: int) -> list[ZoneStatusOut]:
    history = get_health_history(db, astronaut_id, mission_day)
    baselines = calculate_baselines(db, astronaut_id, mission_day)
    if not history or not baselines:
        return [
            ZoneStatusOut(zone="head", status="green", label="Cognitive (Head)", detail="No data"),
            ZoneStatusOut(zone="torso", status="green", label="Cardiopulmonary (Torso)", detail="No data"),
            ZoneStatusOut(zone="core", status="green", label="Core (Overall)", detail="No data"),
        ]

    latest = history[-1]
    rt_delta = latest.reaction_time_ms - baselines["reaction_time_ms"]
    sleep_delta = latest.sleep_h - baselines["sleep_h"]
    fatigue_delta = latest.fatigue - baselines["fatigue"]
    hr_delta = latest.resting_hr - baselines["resting_hr"]

    head = _status_for_delta("reaction_time_ms", rt_delta)
    if sleep_delta <= -SLEEP_DROP_H and head == "green":
        head = "amber"
    if fatigue_delta >= FATIGUE_RISE and head == "green":
        head = "amber"

    torso = _status_for_delta("resting_hr", hr_delta)

    # Core reflects fatigue / conditioning
    core = _status_for_delta("fatigue", fatigue_delta)

    head_detail = {
        "green": "Stable alertness",
        "amber": "Low alertness",
        "red": "Cognitive concern",
    }[head]
    torso_detail = {
        "green": "Stable",
        "amber": "Elevated HR",
        "red": "Sustained HR rise",
    }[torso]
    core_detail = {
        "green": "Normal",
        "amber": "Elevated fatigue",
        "red": "High fatigue",
    }[core]

    return [
        ZoneStatusOut(zone="head", status=head, label="Cognitive (Head)", detail=head_detail),
        ZoneStatusOut(zone="torso", status=torso, label="Cardiopulmonary (Torso)", detail=torso_detail),
        ZoneStatusOut(zone="core", status=core, label="Core (Overall)", detail=core_detail),
    ]


def build_metrics(db: Session, astronaut_id: str, mission_day: int) -> list[MetricBaseline]:
    history = get_health_history(db, astronaut_id, mission_day)
    env = get_environment_history(db, mission_day)
    baselines = calculate_baselines(db, astronaut_id, mission_day)
    if not history or not baselines:
        return []

    latest = history[-1]
    spark_n = 14
    recent = history[-spark_n:]

    env_latest = env[-1] if env else None
    env_recent = env[-spark_n:] if env else []

    # For NASA RR-1 data, compare against full historical average; otherwise early window.
    use_rr1_avg = bool(env_latest and env_latest.provenance == "NASA_RR1_HISTORICAL")
    if use_rr1_avg:
        from .rr1_api import historical_stats

        stats = historical_stats(db)
        env_baseline_co2 = stats.get("co2_ppm", {}).get("mean") or median([e.co2_ppm for e in env])
        env_baseline_temp = stats.get("temperature_c", {}).get("mean") or median(
            [e.temperature_c for e in env]
        )
        env_baseline_hum = stats.get("humidity_pct", {}).get("mean") or median(
            [e.humidity_pct for e in env]
        )
    else:
        env_baseline_co2 = median([e.co2_ppm for e in env[:BASELINE_WINDOW]]) if env else 900.0
        env_baseline_temp = median([e.temperature_c for e in env[:BASELINE_WINDOW]]) if env else 22.0
        env_baseline_hum = (
            median([e.humidity_pct for e in env[:BASELINE_WINDOW]]) if env else 45.0
        )

    defs = [
        ("sleep_h", latest.sleep_h, baselines["sleep_h"], "h", [r.sleep_h for r in recent], latest.provenance),
        ("resting_hr", latest.resting_hr, baselines["resting_hr"], "bpm", [r.resting_hr for r in recent], latest.provenance),
        (
            "reaction_time_ms",
            latest.reaction_time_ms,
            baselines["reaction_time_ms"],
            "ms",
            [r.reaction_time_ms for r in recent],
            latest.provenance,
        ),
        ("fatigue", latest.fatigue, baselines["fatigue"], "/10", [r.fatigue for r in recent], latest.provenance),
    ]

    metrics: list[MetricBaseline] = []
    for metric, latest_v, base, unit, spark, prov in defs:
        delta = latest_v - base
        metrics.append(
            MetricBaseline(
                metric=metric,
                baseline=round(base, 2),
                latest=round(latest_v, 2),
                delta=round(delta, 2),
                unit=unit,
                status=_status_for_delta(metric, delta),
                sparkline=[round(v, 2) for v in spark],
                provenance=prov,
            )
        )

    if env_latest:
        co2_delta = env_latest.co2_ppm - env_baseline_co2
        co2_status: ZoneStatus = "green"
        if use_rr1_avg:
            # Relative to RR-1 historical mean (unusual vs average)
            if abs(co2_delta) >= 400:
                co2_status = "red"
            elif abs(co2_delta) >= 200:
                co2_status = "amber"
        else:
            if env_latest.co2_ppm >= 2200:
                co2_status = "red"
            elif env_latest.co2_ppm >= CO2_ELEVATED:
                co2_status = "amber"
        metrics.append(
            MetricBaseline(
                metric="co2_ppm",
                baseline=round(env_baseline_co2, 1),
                latest=round(env_latest.co2_ppm, 1),
                delta=round(co2_delta, 1),
                unit="ppm",
                status=co2_status,
                sparkline=[round(e.co2_ppm, 1) for e in env_recent],
                provenance=env_latest.provenance,
            )
        )
        temp_delta = env_latest.temperature_c - env_baseline_temp
        temp_status: ZoneStatus = "green"
        if use_rr1_avg and abs(temp_delta) >= 1.5:
            temp_status = "amber"
        if use_rr1_avg and abs(temp_delta) >= 3.0:
            temp_status = "red"
        metrics.append(
            MetricBaseline(
                metric="temperature_c",
                baseline=round(env_baseline_temp, 1),
                latest=round(env_latest.temperature_c, 1),
                delta=round(temp_delta, 1),
                unit="°C",
                status=temp_status,
                sparkline=[round(e.temperature_c, 1) for e in env_recent],
                provenance=env_latest.provenance,
            )
        )
        hum_delta = env_latest.humidity_pct - env_baseline_hum
        hum_status: ZoneStatus = "green"
        if use_rr1_avg and abs(hum_delta) >= 5:
            hum_status = "amber"
        if use_rr1_avg and abs(hum_delta) >= 10:
            hum_status = "red"
        metrics.append(
            MetricBaseline(
                metric="humidity_pct",
                baseline=round(env_baseline_hum, 1),
                latest=round(env_latest.humidity_pct, 1),
                delta=round(hum_delta, 1),
                unit="%",
                status=hum_status,
                sparkline=[round(e.humidity_pct, 1) for e in env_recent],
                provenance=env_latest.provenance,
            )
        )

    return metrics


def simple_forecast(db: Session, astronaut_id: str, mission_day: int) -> ForecastOut:
    """Delegate to the local sklearn forecast pipeline (with persistence fallback)."""
    from .forecast import forecast_reaction_time

    return forecast_reaction_time(db, astronaut_id, mission_day)


def records_to_points(records: list[HealthRecord]) -> list[HealthPoint]:
    return [
        HealthPoint(
            mission_day=r.mission_day,
            sleep_h=r.sleep_h,
            resting_hr=r.resting_hr,
            fatigue=r.fatigue,
            mood=r.mood,
            reaction_time_ms=r.reaction_time_ms,
            exercise_adherence=r.exercise_adherence,
            provenance=r.provenance,
        )
        for r in records
    ]


def env_to_points(records: list[EnvironmentRecord]) -> list[Any]:
    from ..schemas import EnvironmentPoint

    return [
        EnvironmentPoint(
            mission_day=e.mission_day,
            co2_ppm=e.co2_ppm,
            temperature_c=e.temperature_c,
            humidity_pct=e.humidity_pct,
            provenance=e.provenance,
            source_label=e.source_label,
        )
        for e in records
    ]
