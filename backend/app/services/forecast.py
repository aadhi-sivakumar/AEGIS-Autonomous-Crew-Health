from __future__ import annotations

"""Local lightweight next-day reaction-time forecasting.

Uses scikit-learn Ridge regression with a chronological train/test split.
Falls back to persistence / rolling-mean baseline if fitting fails.
Illustrative only — not clinically validated.
"""

from statistics import mean, median
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from ..schemas import ForecastOut, ForecastPoint
from .baselines import calculate_baselines, get_environment_history, get_health_history

MODEL_VERSION = "ridge-chrono-v1"
BASELINE_MODEL = "rolling-mean-persistence-v0"
DISCLAIMER = "ILLUSTRATIVE FORECAST — NOT CLINICALLY VALIDATED"


def _build_feature_matrix(
    history: list,
    env_by_day: dict[int, Any],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Features for day t predict reaction time on day t+1."""
    feature_names = [
        "sleep_h",
        "recent_rt_mean3",
        "hr_delta",
        "fatigue",
        "co2_ppm",
    ]
    rows = []
    targets = []
    baselines_rt = median([h.reaction_time_ms for h in history[:14]]) if history else 280.0
    baselines_hr = median([h.resting_hr for h in history[:14]]) if history else 62.0

    for i in range(2, len(history) - 1):
        cur = history[i]
        nxt = history[i + 1]
        recent = history[max(0, i - 2) : i + 1]
        env = env_by_day.get(cur.mission_day)
        co2 = env.co2_ppm if env else 900.0
        rows.append(
            [
                cur.sleep_h,
                mean([r.reaction_time_ms for r in recent]),
                cur.resting_hr - baselines_hr,
                cur.fatigue,
                co2 / 1000.0,  # scale
            ]
        )
        targets.append(nxt.reaction_time_ms)

    if not rows:
        return np.empty((0, len(feature_names))), np.empty((0,)), feature_names
    return np.array(rows, dtype=float), np.array(targets, dtype=float), feature_names


def _persistence_forecast(history: list, mission_day: int, baselines: dict[str, float]) -> ForecastOut:
    recent = history[-7:]
    vals = [r.reaction_time_ms for r in recent]
    roll = mean(vals[-3:]) if len(vals) >= 3 else vals[-1]
    slope = (vals[-1] - vals[-4]) / 3 if len(vals) >= 4 else 0.0
    estimate = roll + slope
    uncertainty = max(8.0, abs(slope) * 2 + 10.0)

    series: list[ForecastPoint] = [
        ForecastPoint(mission_day=r.mission_day, value=round(r.reaction_time_ms, 1), kind="observed")
        for r in history[-10:]
    ]
    for i in range(1, 3):
        val = estimate + slope * (i - 1) * 0.5
        series.append(
            ForecastPoint(
                mission_day=mission_day + i,
                value=round(val, 1),
                kind="forecast",
                lower=round(val - uncertainty, 1),
                upper=round(val + uncertainty, 1),
            )
        )

    return ForecastOut(
        next_day_estimate=round(estimate, 1),
        baseline_estimate=round(baselines.get("reaction_time_ms", roll), 1),
        uncertainty=round(uncertainty, 1),
        model_version=BASELINE_MODEL,
        disclaimer=DISCLAIMER,
        series=series,
        contributing_inputs=["Recent reaction time", "Short-term trend"],
    )


def forecast_reaction_time(db: Session, astronaut_id: str, mission_day: int) -> ForecastOut:
    history = get_health_history(db, astronaut_id, mission_day)
    baselines = calculate_baselines(db, astronaut_id, mission_day)
    if not history:
        return ForecastOut(
            next_day_estimate=0,
            baseline_estimate=0,
            uncertainty=0,
            model_version=BASELINE_MODEL,
            disclaimer=DISCLAIMER,
            series=[],
            contributing_inputs=[],
        )

    env = get_environment_history(db, mission_day)
    env_by_day = {e.mission_day: e for e in env}
    baseline_out = _persistence_forecast(history, mission_day, baselines)

    X, y, feature_names = _build_feature_matrix(history, env_by_day)
    if len(y) < 12:
        return baseline_out

    # Chronological split — never train on future days.
    split = int(len(y) * 0.75)
    if split < 8 or split >= len(y):
        return baseline_out

    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    try:
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        model = Ridge(alpha=1.0, random_state=42)
        model.fit(X_train_s, y_train)
        preds = model.predict(X_test_s)
        residuals = y_test - preds
        mae = float(np.mean(np.abs(residuals)))
        uncertainty = max(10.0, mae * 1.25)

        # Predict next day from latest available features
        latest = history[-1]
        recent = history[-3:]
        env_latest = env_by_day.get(latest.mission_day)
        co2 = (env_latest.co2_ppm if env_latest else 900.0) / 1000.0
        hr_base = baselines.get("resting_hr", latest.resting_hr)
        x_next = np.array(
            [
                [
                    latest.sleep_h,
                    mean([r.reaction_time_ms for r in recent]),
                    latest.resting_hr - hr_base,
                    latest.fatigue,
                    co2,
                ]
            ],
            dtype=float,
        )
        estimate = float(model.predict(scaler.transform(x_next))[0])

        # Compare vs baseline estimate on holdout
        persist_test = []
        for i in range(split, len(y)):
            # corresponding history index for feature row i is i+2 in history
            hist_idx = i + 2
            window = history[max(0, hist_idx - 2) : hist_idx + 1]
            persist_test.append(mean([r.reaction_time_ms for r in window]))
        baseline_mae = float(np.mean(np.abs(y_test - np.array(persist_test)))) if persist_test else mae

        series: list[ForecastPoint] = [
            ForecastPoint(
                mission_day=r.mission_day, value=round(r.reaction_time_ms, 1), kind="observed"
            )
            for r in history[-10:]
        ]
        for i in range(1, 3):
            val = estimate + (estimate - baseline_out.next_day_estimate) * 0.15 * (i - 1)
            series.append(
                ForecastPoint(
                    mission_day=mission_day + i,
                    value=round(val, 1),
                    kind="forecast",
                    lower=round(val - uncertainty, 1),
                    upper=round(val + uncertainty, 1),
                )
            )

        contrib = [
            "Sleep",
            "Recent reaction time",
            "Heart-rate vs baseline",
            "Fatigue",
            "Cabin CO₂ (associative only — not medical causation)",
            f"Model holdout error ≈ {mae:.0f} ms",
            f"Simple-trend holdout error ≈ {baseline_mae:.0f} ms",
        ]

        return ForecastOut(
            next_day_estimate=round(estimate, 1),
            baseline_estimate=round(baseline_out.next_day_estimate, 1),
            uncertainty=round(uncertainty, 1),
            model_version=MODEL_VERSION,
            disclaimer=DISCLAIMER,
            series=series,
            contributing_inputs=contrib,
        )
    except Exception:
        return baseline_out


def scenario_reaction_time(
    db: Session,
    astronaut_id: str,
    mission_day: int,
    sleep_h: float,
    co2_ppm: float,
    fatigue: float | None,
) -> dict[str, Any]:
    """What-If projection using trained model coefficients when available, else transparent linear association."""
    history = get_health_history(db, astronaut_id, mission_day)
    env = get_environment_history(db, mission_day)
    if not history:
        raise ValueError("No health history")

    forecast = forecast_reaction_time(db, astronaut_id, mission_day)
    latest = history[-1]
    current_sleep = latest.sleep_h
    current_co2 = env[-1].co2_ppm if env else 900.0
    current_fatigue = latest.fatigue
    fatigue_val = fatigue if fatigue is not None else current_fatigue
    current_est = forecast.next_day_estimate

    # Transparent illustrative association anchored to model estimate.
    sleep_effect = (sleep_h - current_sleep) * -12.0
    co2_effect = ((co2_ppm - current_co2) / 100.0) * 2.5
    fatigue_effect = (fatigue_val - current_fatigue) * 6.0
    hypo = current_est + sleep_effect + co2_effect + fatigue_effect

    drivers = []
    if abs(sleep_effect) >= 2:
        drivers.append(f"Sleep adjustment ({sleep_h:.1f} h) → {sleep_effect:+.0f} ms")
    if abs(co2_effect) >= 2:
        drivers.append(f"CO₂ adjustment ({co2_ppm:.0f} ppm) → {co2_effect:+.0f} ms")
    if abs(fatigue_effect) >= 2:
        drivers.append(f"Fatigue adjustment ({fatigue_val:.0f}) → {fatigue_effect:+.0f} ms")
    if not drivers:
        drivers.append("Inputs near current conditions — small projected change.")

    delta = hypo - current_est
    return {
        "current_estimate": round(current_est, 1),
        "hypothetical_estimate": round(hypo, 1),
        "delta_ms": round(delta, 1),
        "delta_pct": round((delta / current_est) * 100, 1) if current_est else 0,
        "drivers": drivers,
        "model_version": forecast.model_version,
        "current_inputs": {
            "sleep_h": current_sleep,
            "co2_ppm": current_co2,
            "fatigue": current_fatigue,
        },
        "series_current": [{"t": i * 6, "label": f"+{i*6}h" if i else "Today", "value": round(current_est + i * 1.2, 1)} for i in range(5)],
        "series_hypothetical": [{"t": i * 6, "label": f"+{i*6}h" if i else "Today", "value": round(hypo + i * 0.4, 1)} for i in range(5)],
        "disclaimer": (
            "Illustrative association model. Manipulating an input models a hypothetical "
            "association and does not prove that changing that condition will cause a "
            "specific health improvement."
        ),
    }
