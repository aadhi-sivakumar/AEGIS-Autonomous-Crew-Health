from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AppState, AssessmentResult
from ..schemas import ActionItemOut, EmergencyStepOut, GuidanceOut
from ..services import baselines as bl
from ..services.demo import get_scenario
from ..services.metric_explain import TRUST_LINE

EMERGENCY_STEPS = [
    EmergencyStepOut(
        step=1,
        title="Stop high-stakes work",
        detail=(
            "Do not start or continue EVA, docking, or critical maintenance. "
            "Secure tools and move to a safe location."
        ),
        href="/operations",
    ),
    EmergencyStepOut(
        step=2,
        title="Stabilize and note the time",
        detail=(
            "Sit or restrain as needed. Write the time, what you feel "
            "(pain, dizziness, confusion, chest symptoms), and what you were doing."
        ),
        href="/assessment#symptoms",
    ),
    EmergencyStepOut(
        step=3,
        title="Quick recheck if safe",
        detail=(
            "If you can do so safely: log symptoms, optional resting HR after 2–3 min seated rest, "
            "and a fresh reaction-time check. Skip any step that feels unsafe."
        ),
        href="/assessment",
    ),
    EmergencyStepOut(
        step=4,
        title="Escalate to ground medical",
        detail=(
            "Generate an encrypted health summary and queue it for the next relay window. "
            "Notify the crew medical officer / commander using onboard protocols."
        ),
        href="/telemetry",
    ),
    EmergencyStepOut(
        step=5,
        title="Follow onboard medical procedures",
        detail=(
            "Use established mission medical kit and CMO procedures. "
            "AEGIS does not prescribe medication or replace medical authority."
        ),
        href=None,
    ),
]

WHEN_TO_ESCALATE = [
    "Sudden chest pain, severe shortness of breath, fainting, or confusion",
    "Severe or rapidly worsening headache, dizziness, or nausea",
    "Symptoms that interfere with safe task performance",
    "Any red readiness gate before EVA / docking that does not improve after rest + recheck",
    "You are unsure — escalate early; delay makes remote medical harder",
]


def _assessment_complete_key(astronaut_id: str) -> str:
    return f"assessment_complete:{astronaut_id}"


def is_assessment_marked_complete(db: Session, astronaut_id: str) -> bool:
    row = db.get(AppState, _assessment_complete_key(astronaut_id))
    return bool(row and row.value.lower() == "true")


def mark_assessment_complete(db: Session, astronaut_id: str, complete: bool = True) -> dict:
    key = _assessment_complete_key(astronaut_id)
    row = db.get(AppState, key)
    value = "true" if complete else "false"
    if row:
        row.value = value
    else:
        db.add(AppState(key=key, value=value))
    db.commit()
    return {"astronaut_id": astronaut_id, "assessment_complete": complete}


def build_guidance(db: Session, astronaut_id: str) -> GuidanceOut:
    state = get_scenario(db)
    pattern = bl.detect_combined_patterns(db, astronaut_id, state.mission_day)
    deviations = bl.detect_deviations(db, astronaut_id, state.mission_day)
    marked = is_assessment_marked_complete(db, astronaut_id)
    recent_assessment = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.astronaut_id == astronaut_id)
        .order_by(AssessmentResult.created_at.desc())
        .first()
    )

    alerts: list[dict] = []
    actions: list[ActionItemOut] = []

    if pattern.detected:
        alerts.append(
            {
                "severity": pattern.severity,
                "summary": pattern.summary,
                "metrics": pattern.contributing_metrics,
                "action": "Complete cognitive assessment" if not marked else "Review latest assessment",
            }
        )
        actions.append(
            ActionItemOut(
                id="pattern",
                severity=pattern.severity,
                summary=pattern.summary,
                do_label="Do reaction assessment" if not marked else "Open readiness gate",
                do_href="/assessment" if not marked else "/operations",
                escalate_label="Escalate to ground",
                escalate_href="/telemetry",
                reason=(
                    "Target ≥7.5 h sleep tonight, complete a fresh RT check, then reassess EVA/docking."
                ),
            )
        )

    for d in deviations:
        alerts.append(
            {
                "severity": "amber",
                "summary": d.explanation,
                "metrics": [d.metric],
                "action": "Recheck reading vs personal baseline",
            }
        )
        if d.metric == "sleep_h":
            do_label, do_href, reason = (
                "Protect sleep block",
                "#checkin",
                "Aim closer to your personal sleep baseline; log tonight's hours in check-in.",
            )
        elif d.metric == "reaction_time_ms":
            do_label, do_href, reason = (
                "Do RT assessment",
                "/assessment",
                "Refresh measured reaction time before high-stakes tasks.",
            )
        elif d.metric == "co2_ppm":
            do_label, do_href, reason = (
                "Review cabin CO₂",
                "/trends",
                "Improve airflow / reduce stagnant work time if CO₂ stays elevated.",
            )
        else:
            do_label, do_href, reason = (
                "View trends",
                "/trends",
                "Compare against your personal baseline before changing plans.",
            )
        actions.append(
            ActionItemOut(
                id=f"dev_{d.metric}",
                severity="amber",
                summary=d.explanation,
                do_label=do_label,
                do_href=do_href,
                escalate_label="Remind later",
                escalate_href=None,
                reason=reason,
            )
        )

    recommendations = [
        "Recheck unexpected readings against personal baseline.",
        "Target sleep near your early-mission baseline; reduce late high-load tasks.",
        "If cabin CO₂ is elevated, improve ventilation and limit long stagnant work blocks.",
        "Follow onboard crew medical procedures for concerning symptoms or persistent abnormalities.",
    ]
    if pattern.detected and not marked:
        recommendations.insert(
            0,
            "Complete a browser cognitive assessment to refresh reaction-time data.",
        )
    elif marked or recent_assessment:
        recommendations.insert(
            0,
            "Assessment recorded — generate a health summary for the telemetry queue if needed.",
        )

    if not actions:
        actions.append(
            ActionItemOut(
                id="stable",
                severity="green",
                summary="No active multi-indicator advisories.",
                do_label="Keep daily check-in",
                do_href="/",
                escalate_label="Generate summary",
                escalate_href="/telemetry",
                reason="Stay consistent so early changes remain visible against your baseline.",
            )
        )

    return GuidanceOut(
        astronaut_id=astronaut_id,
        alerts=alerts,
        recommendations=recommendations,
        emergency_disclaimer=(
            "Urgent symptoms require established mission medical protocols "
            "regardless of model output. AEGIS is advisory only and does not "
            "issue medication or treatment advice."
        ),
        emergency_steps=EMERGENCY_STEPS,
        when_to_escalate=WHEN_TO_ESCALATE,
        actions=actions,
        trust_line=TRUST_LINE,
    )
