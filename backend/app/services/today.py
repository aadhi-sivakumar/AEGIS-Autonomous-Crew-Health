from __future__ import annotations

"""Today summary, daily check-in, symptoms, and soft prompts."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import AppState, AssessmentResult, DailyCheckIn, HealthRecord, SymptomCheck
from ..schemas import (
    CheckInIn,
    CheckInOut,
    EnvContextOut,
    PromptOut,
    SymptomCheckIn,
    SymptomCheckOut,
    TodayMetricOut,
    TodayOut,
)
from ..services import baselines as bl
from ..services import nasa_eda_service
from ..services.demo import get_scenario
from ..services.guidance import is_assessment_marked_complete
from ..services.metric_explain import SCIENCE_NOTE, TRUST_LINE, get_metric_explainer
from ..services.operations import build_operations

PROMPT_KINDS = ("morning_checkin", "weekly_assessment", "pre_eva")


def _snooze_key(kind: str, astronaut_id: str, mission_day: int) -> str:
    return f"prompt_snooze:{kind}:{astronaut_id}:{mission_day}"


def is_prompt_snoozed(db: Session, kind: str, astronaut_id: str, mission_day: int) -> bool:
    row = db.get(AppState, _snooze_key(kind, astronaut_id, mission_day))
    return bool(row and row.value.lower() == "true")


def snooze_prompt(db: Session, kind: str, astronaut_id: str, mission_day: int) -> dict:
    if kind not in PROMPT_KINDS:
        raise ValueError(f"Unknown prompt kind: {kind}")
    key = _snooze_key(kind, astronaut_id, mission_day)
    row = db.get(AppState, key)
    if row:
        row.value = "true"
    else:
        db.add(AppState(key=key, value="true"))
    db.commit()
    return {"kind": kind, "astronaut_id": astronaut_id, "mission_day": mission_day, "snoozed": True}


def get_checkin(db: Session, astronaut_id: str, mission_day: int) -> Optional[DailyCheckIn]:
    return (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.astronaut_id == astronaut_id,
            DailyCheckIn.mission_day == mission_day,
        )
        .one_or_none()
    )


def get_latest_symptoms(db: Session, astronaut_id: str, mission_day: int) -> Optional[SymptomCheck]:
    return (
        db.query(SymptomCheck)
        .filter(
            SymptomCheck.astronaut_id == astronaut_id,
            SymptomCheck.mission_day == mission_day,
        )
        .order_by(SymptomCheck.created_at.desc())
        .first()
    )


def _checkin_out(row: DailyCheckIn) -> CheckInOut:
    return CheckInOut(
        id=row.id,
        astronaut_id=row.astronaut_id,
        mission_day=row.mission_day,
        sleep_h=row.sleep_h,
        fatigue=row.fatigue,
        mood=row.mood,
        resting_hr=row.resting_hr,
        notes=row.notes,
        provenance=row.provenance,
        created_at=row.created_at.isoformat() + "Z",
    )


def _symptom_out(row: SymptomCheck) -> SymptomCheckOut:
    return SymptomCheckOut(
        id=row.id,
        astronaut_id=row.astronaut_id,
        mission_day=row.mission_day,
        headache=row.headache,
        congestion=row.congestion,
        dizziness=row.dizziness,
        nausea=row.nausea,
        other_notes=row.other_notes,
        provenance=row.provenance,
        created_at=row.created_at.isoformat() + "Z",
        attention_needed=_symptom_attention(row),
    )


def _symptom_attention(row: SymptomCheck) -> bool:
    return any(v >= 2 for v in (row.headache, row.congestion, row.dizziness, row.nausea))


def submit_checkin(db: Session, body: CheckInIn) -> CheckInOut:
    state = get_scenario(db)
    mission_day = state.mission_day
    row = get_checkin(db, body.astronaut_id, mission_day)
    if row:
        row.sleep_h = body.sleep_h
        row.fatigue = body.fatigue
        row.mood = body.mood
        row.resting_hr = body.resting_hr
        row.notes = body.notes
        row.created_at = datetime.utcnow()
    else:
        row = DailyCheckIn(
            astronaut_id=body.astronaut_id,
            mission_day=mission_day,
            sleep_h=body.sleep_h,
            fatigue=body.fatigue,
            mood=body.mood,
            resting_hr=body.resting_hr,
            notes=body.notes,
            provenance="CREW_ENTERED",
        )
        db.add(row)

    # Map 1–5 check-in taps onto the seeded health scales (fatigue ~2–10, mood ~3–9).
    fatigue_stored = round(float(body.fatigue) * 2.0, 1)
    mood_stored = round(2.0 + float(body.mood) * 1.4, 1)

    # Mirror into today's health record so baselines / forecast see crew data.
    health = (
        db.query(HealthRecord)
        .filter(
            HealthRecord.astronaut_id == body.astronaut_id,
            HealthRecord.mission_day == mission_day,
        )
        .one_or_none()
    )
    if health:
        health.sleep_h = body.sleep_h
        health.fatigue = fatigue_stored
        health.mood = mood_stored
        if body.resting_hr is not None:
            health.resting_hr = body.resting_hr
        if health.provenance == "SIMULATED_CREW_DATA":
            health.provenance = "CREW_ENTERED"
    else:
        prior = (
            db.query(HealthRecord)
            .filter(HealthRecord.astronaut_id == body.astronaut_id)
            .order_by(HealthRecord.mission_day.desc())
            .first()
        )
        db.add(
            HealthRecord(
                astronaut_id=body.astronaut_id,
                mission_day=mission_day,
                sleep_h=body.sleep_h,
                resting_hr=body.resting_hr if body.resting_hr is not None else (prior.resting_hr if prior else 62.0),
                fatigue=fatigue_stored,
                mood=mood_stored,
                reaction_time_ms=prior.reaction_time_ms if prior else 280.0,
                exercise_adherence=prior.exercise_adherence if prior else 0.8,
                provenance="CREW_ENTERED",
            )
        )

    db.commit()
    db.refresh(row)
    return _checkin_out(row)


def submit_symptoms(db: Session, body: SymptomCheckIn) -> SymptomCheckOut:
    state = get_scenario(db)
    row = SymptomCheck(
        astronaut_id=body.astronaut_id,
        mission_day=state.mission_day,
        headache=body.headache,
        congestion=body.congestion,
        dizziness=body.dizziness,
        nausea=body.nausea,
        other_notes=body.other_notes,
        provenance="CREW_ENTERED",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _symptom_out(row)


def _rank_status(status: str) -> int:
    return {"green": 0, "amber": 1, "red": 2}.get(status, 0)


def _overall_status(metrics: list, pattern, symptoms: Optional[SymptomCheck]) -> str:
    worst = "green"
    for m in metrics:
        if _rank_status(m.status) > _rank_status(worst):
            worst = m.status
    if pattern.detected and _rank_status(pattern.severity) > _rank_status(worst):
        worst = pattern.severity
    if symptoms and _symptom_attention(symptoms) and worst == "green":
        worst = "amber"
    return worst


def _plain_status(status: str, metrics: list, pattern, env: Optional[EnvContextOut] = None) -> str:
    if status == "green":
        if env and env.mode == "nasa_historical" and env.co2_status in ("amber", "red"):
            return (
                "Crew indicators look near baseline, but NASA cabin CO₂ is elevated — "
                "treat environment as a stressor before high-stakes work."
            )
        return "You look close to your personal baseline today."
    top = sorted(metrics, key=lambda m: _rank_status(m.status), reverse=True)[:2]
    bits = []
    for m in top:
        if m.status == "green":
            continue
        name = m.metric.replace("_", " ")
        if m.metric == "sleep_h":
            bits.append(f"sleep is {abs(m.delta):.1f}h below your baseline")
        elif m.metric == "reaction_time_ms":
            bits.append(f"reaction time is {m.delta:+.0f} ms vs baseline")
        elif m.metric == "fatigue":
            bits.append(f"fatigue is elevated ({m.latest:.0f}/10 vs {m.baseline:.0f})")
        elif m.metric == "co2_ppm":
            bits.append(f"cabin CO₂ is elevated ({m.latest:.0f} ppm)")
        else:
            bits.append(f"{name} needs attention")
    if pattern.detected:
        bits.append("combined sleep + reaction pattern flagged")
    if env and env.mode == "nasa_historical" and env.co2_status in ("amber", "red"):
        bits.append("NASA historical cabin CO₂ is a concurrent stressor")
    if not bits:
        return "Some indicators need a closer look versus your baseline."
    return "Attention: " + "; ".join(bits[:2]) + "."


def _build_env_context(db: Session, metrics: list) -> EnvContextOut:
    mode = nasa_eda_service.get_env_data_mode(db)
    nasa_cached = nasa_eda_service.is_mission_cached(db, "RR-1")
    co2 = next((m for m in metrics if m.metric == "co2_ppm"), None)
    if mode == "nasa_historical" and nasa_cached:
        source_label = "NASA RR-1 Historical Environmental Data — 2014"
        provenance = "NASA_HISTORICAL"
        if co2 and co2.status in ("amber", "red"):
            decision_blurb = (
                f"NASA cabin CO₂ at {co2.latest:.0f} ppm ({co2.status.upper()}) — "
                "pair with your personal baseline before EVA/docking. Open Replay to see the spike."
            )
        else:
            decision_blurb = (
                "Cabin environment is driven by cached NASA RR-1 observations "
                "(rodent-research hardware env — cabin analog, not astronaut medical)."
            )
    else:
        source_label = "Simulated cabin environment"
        provenance = "SYNTHETIC_ENVIRONMENT"
        decision_blurb = (
            "Using synthetic cabin fixtures. Switch Env Data Source → NASA Historical "
            "(or Start guided demo) so judges see real NASA OSDR RR-1 data drive the loop."
        )
    return EnvContextOut(
        mode=mode if mode in ("simulated", "nasa_historical") else "simulated",  # type: ignore[arg-type]
        nasa_cached=nasa_cached,
        co2_ppm=co2.latest if co2 else None,
        co2_status=co2.status if co2 else None,  # type: ignore[arg-type]
        co2_baseline=co2.baseline if co2 else None,
        source_label=source_label,
        provenance=provenance,
        decision_blurb=decision_blurb,
        science_note=SCIENCE_NOTE,
    )


def _primary_action(
    status: str,
    checkin_done: bool,
    assessed: bool,
    pattern,
    symptoms: Optional[SymptomCheck],
) -> dict[str, str]:
    if not checkin_done:
        return {
            "id": "checkin",
            "label": "Complete 2-min daily check-in",
            "href": "#checkin",
            "reason": "Log sleep, fatigue, and mood so today's status uses your data.",
        }
    if symptoms is None:
        return {
            "id": "symptoms",
            "label": "Log today's symptoms",
            "href": "/assessment#symptoms",
            "reason": "A quick symptom checklist catches issues charts can miss.",
        }
    if pattern.detected and not assessed:
        return {
            "id": "assessment",
            "label": "Do reaction-time assessment now",
            "href": "/assessment",
            "reason": "Cognitive trend is off baseline — refresh measured reaction time before critical tasks.",
        }
    if status in ("amber", "red"):
        return {
            "id": "operations",
            "label": "Review task readiness",
            "href": "/operations",
            "reason": "Check EVA / docking readiness before high-stakes work.",
        }
    return {
        "id": "trends",
        "label": "Review trends vs baseline",
        "href": "/trends",
        "reason": "Status looks stable — skim personal trends when you have a minute.",
    }


def build_prompts(
    db: Session,
    astronaut_id: str,
    mission_day: int,
    checkin_done: bool,
    assessed: bool,
) -> list[PromptOut]:
    prompts: list[PromptOut] = []
    if not checkin_done and not is_prompt_snoozed(db, "morning_checkin", astronaut_id, mission_day):
        prompts.append(
            PromptOut(
                kind="morning_checkin",
                title="Morning check-in",
                message="Two minutes: sleep, fatigue, mood, optional heart rate.",
                href="#checkin",
                urgency="normal",
            )
        )
    # Weekly-ish: every 7 mission days remind assessment if none marked
    if mission_day % 7 == 0 and not assessed:
        if not is_prompt_snoozed(db, "weekly_assessment", astronaut_id, mission_day):
            prompts.append(
                PromptOut(
                    kind="weekly_assessment",
                    title="Weekly cognitive check",
                    message="Run a short reaction-time assessment to refresh your trend.",
                    href="/assessment",
                    urgency="normal",
                )
            )
    ops = build_operations(db, astronaut_id)
    eva = next((t for t in ops.tasks if t.id == "eva"), None)
    if eva and eva.status != "ready":
        if not is_prompt_snoozed(db, "pre_eva", astronaut_id, mission_day):
            prompts.append(
                PromptOut(
                    kind="pre_eva",
                    title="Pre-EVA readiness",
                    message=eva.justification,
                    href="/operations",
                    urgency="high" if eva.status == "review_required" else "normal",
                )
            )
    return prompts


def build_today(db: Session, astronaut_id: str) -> TodayOut:
    state = get_scenario(db)
    mission_day = state.mission_day
    metrics = bl.build_metrics(db, astronaut_id, mission_day)
    pattern = bl.detect_combined_patterns(db, astronaut_id, mission_day)
    checkin = get_checkin(db, astronaut_id, mission_day)
    symptoms = get_latest_symptoms(db, astronaut_id, mission_day)
    assessed = is_assessment_marked_complete(db, astronaut_id)
    recent_assessment = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.astronaut_id == astronaut_id)
        .order_by(AssessmentResult.created_at.desc())
        .first()
    )

    priority = ["sleep_h", "reaction_time_ms", "fatigue", "resting_hr", "co2_ppm"]
    by_id = {m.metric: m for m in metrics}
    top: list[TodayMetricOut] = []
    for mid in priority:
        m = by_id.get(mid)
        if not m:
            continue
        expl = get_metric_explainer(mid)
        plain = (
            f"{expl['title']}: {m.latest}{m.unit} ({m.delta:+.1f} vs your baseline of {m.baseline}{m.unit})"
            if expl
            else f"{mid}: {m.latest} vs baseline {m.baseline}"
        )
        if mid == "reaction_time_ms":
            plain = (
                f"Reaction time {m.latest:.0f} ms — "
                f"{m.delta:+.0f} ms vs your baseline ({m.baseline:.0f} ms)"
            )
        elif mid == "sleep_h":
            plain = (
                f"Sleep {m.latest:.1f} h — "
                f"{m.delta:+.1f} h vs your baseline ({m.baseline:.1f} h)"
            )
        top.append(
            TodayMetricOut(
                metric=m.metric,
                label=expl["title"] if expl else mid,
                latest=m.latest,
                baseline=m.baseline,
                delta=m.delta,
                unit=m.unit,
                status=m.status,
                plain=plain,
            )
        )
        if len(top) >= 3:
            break

    # Prefer worst metrics if top-3 by priority are all green but others aren't
    if all(t.status == "green" for t in top):
        worst = sorted(metrics, key=lambda m: _rank_status(m.status), reverse=True)
        rebuilt: list[TodayMetricOut] = []
        for m in worst:
            if m.metric in ("humidity_pct", "temperature_c", "mood"):
                continue
            expl = get_metric_explainer(m.metric)
            rebuilt.append(
                TodayMetricOut(
                    metric=m.metric,
                    label=expl["title"] if expl else m.metric,
                    latest=m.latest,
                    baseline=m.baseline,
                    delta=m.delta,
                    unit=m.unit,
                    status=m.status,
                    plain=(
                        f"{expl['title'] if expl else m.metric}: "
                        f"{m.latest}{m.unit} vs baseline {m.baseline}{m.unit}"
                    ),
                )
            )
            if len(rebuilt) >= 3:
                break
        if rebuilt:
            top = rebuilt

    env = _build_env_context(db, metrics)
    status = _overall_status(metrics, pattern, symptoms)
    # Cabin CO₂ amber/red should surface on the overall badge when crew is otherwise green.
    if env.co2_status in ("amber", "red") and _rank_status(env.co2_status) > _rank_status(status):
        status = env.co2_status  # type: ignore[assignment]
    checkin_done = checkin is not None
    primary = _primary_action(status, checkin_done, assessed, pattern, symptoms)
    prompts = build_prompts(db, astronaut_id, mission_day, checkin_done, assessed)

    forecast = bl.simple_forecast(db, astronaut_id, mission_day)
    forecast_blurb = (
        "Next-day reaction time uses a local Ridge model on your recent sleep, "
        "fatigue, HR, prior RT, and cabin CO₂ — illustrative only, not clinical."
        if forecast.model_version.startswith("ridge")
        else "Next-day reaction time uses a simple trend fallback when history is short — illustrative only."
    )
    if env.mode == "nasa_historical":
        forecast_blurb += " Cabin CO₂ input is from NASA RR-1 historical observations when NASA mode is on."

    return TodayOut(
        astronaut_id=astronaut_id,
        mission_day=mission_day,
        overall_status=status,  # type: ignore[arg-type]
        plain_language=_plain_status(status, metrics, pattern, env),
        trust_line=TRUST_LINE,
        top_metrics=top,
        primary_action=primary,
        checkin=_checkin_out(checkin) if checkin else None,
        checkin_done=checkin_done,
        symptoms=_symptom_out(symptoms) if symptoms else None,
        prompts=prompts,
        assessment_complete=assessed,
        has_browser_assessment=recent_assessment is not None,
        forecast_next_day_ms=forecast.next_day_estimate,
        forecast_model=forecast.model_version,
        forecast_blurb=forecast_blurb,
        env_context=env,
    )
