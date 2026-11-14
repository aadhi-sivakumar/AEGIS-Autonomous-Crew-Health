# AEGIS Prototype Thresholds

These are **demo / research thresholds** for the Space Apps prototype. They are **not** clinical limits and are **not** official NASA medical standards.

## Baseline window

- First 14 mission days (or half of available history if shorter)
- Statistic: median (robust to outliers)

## Deviation rules

| Metric | Amber | Red (approx.) |
|--------|-------|----------------|
| Sleep vs baseline | ≤ −0.8 h | ≤ −1.5 h |
| Reaction time vs baseline | ≥ +20 ms | ≥ +40 ms |
| Fatigue vs baseline | ≥ +1.5 | ≥ +3.0 |
| Resting HR vs baseline | ≥ +6 bpm | ≥ +12 bpm |
| Cabin CO₂ (absolute) | ≥ 1500 ppm | ≥ 2200 ppm |

Consecutive-day rule: ≥ 3 days on the adverse side of baseline for sleep, RT, or fatigue.

## Combined pattern

Triggered when sustained sleep↓ and reaction↑ co-occur (optionally with elevated CO₂ or fatigue). Explanations describe temporal coincidence only — not medical causation.
