from __future__ import annotations

from sqlalchemy.orm import Session

from ..schemas import OperationsOut, OperationTaskOut
from ..services import baselines as bl
from ..services import nasa_eda_service
from ..services.demo import get_scenario
from ..services.guidance import is_assessment_marked_complete
from ..services.metric_explain import TRUST_LINE


def build_operations(db: Session, astronaut_id: str) -> OperationsOut:
    state = get_scenario(db)
    pattern = bl.detect_combined_patterns(db, astronaut_id, state.mission_day)
    metrics = bl.build_metrics(db, astronaut_id, state.mission_day)
    rt = next((m for m in metrics if m.metric == "reaction_time_ms"), None)
    sleep = next((m for m in metrics if m.metric == "sleep_h"), None)
    co2 = next((m for m in metrics if m.metric == "co2_ppm"), None)
    assessed = is_assessment_marked_complete(db, astronaut_id)
    env_mode = nasa_eda_service.get_env_data_mode(db)
    nasa_on = env_mode == "nasa_historical"

    if pattern.severity == "red" or (rt and rt.status == "red") or (co2 and co2.status == "red"):
        eva_status = "review_required"
        dock_status = "assessment_recommended" if not assessed else "review_required"
        readiness = 48
    elif pattern.detected or (rt and rt.status == "amber") or (co2 and co2.status == "amber"):
        eva_status = "review_required"
        dock_status = "ready" if assessed else "assessment_recommended"
        readiness = 72 if assessed else 66
    else:
        eva_status = "ready"
        dock_status = "ready"
        readiness = 92

    # Map internal status → crew-facing readiness gate
    gate_map = {
        "ready": ("ready", "READY", "No new concerns versus your personal baseline.", "Continue →"),
        "assessment_recommended": (
            "caution",
            "CAUTION",
            "Complete a cognitive assessment before proceeding.",
            "Start Assessment →",
        ),
        "review_required": (
            "not_recommended",
            "NOT RECOMMENDED",
            "Cognitive performance below readiness threshold (advisory).",
            "View Guidance →",
        ),
    }

    def task(tid: str, name: str, status: str) -> OperationTaskOut:
        gate, label, just, action = gate_map[status]
        recheck = ""
        if gate != "ready":
            recheck = "Recheck after rest or a fresh reaction-time assessment."
        return OperationTaskOut(
            id=tid,
            name=name,
            status=status,  # type: ignore[arg-type]
            status_label=label,
            justification=just,
            action_label=action,
            gate=gate,  # type: ignore[arg-type]
            recheck_hint=recheck,
        )

    factors: list[str] = []
    if rt:
        factors.append(
            f"Reaction time: {rt.delta:+.0f} ms from your baseline ({rt.baseline:.0f} ms)"
        )
    if sleep and sleep.delta < 0:
        factors.append(f"Sleep: {sleep.delta:+.1f} h vs your baseline ({sleep.baseline:.1f} h)")
    if co2 and co2.latest >= 1500:
        label = "NASA RR-1 cabin CO₂" if nasa_on else "Cabin CO₂"
        factors.append(f"{label}: elevated ({co2.latest:.0f} ppm) — env stressor for cognition")
    elif co2 and nasa_on:
        factors.append(f"NASA RR-1 cabin CO₂ in loop: {co2.latest:.0f} ppm (historical env analog)")
    if assessed:
        factors.append("Cognitive assessment marked complete for this session")
    if not factors:
        factors.append("No elevated advisory factors versus personal baseline.")

    worst_gate = "ready"
    for st in (eva_status, dock_status):
        g = gate_map[st][0]
        if g == "not_recommended":
            worst_gate = "not_recommended"
        elif g == "caution" and worst_gate == "ready":
            worst_gate = "caution"

    if worst_gate == "ready":
        gate_summary = "Ready for planned tasks based on current personal-baseline indicators."
    elif worst_gate == "caution":
        gate_summary = (
            "Caution — refresh assessment or rest before high-stakes tasks"
            + (" (NASA cabin CO₂ is part of this call)." if nasa_on and co2 and co2.status != "green" else ".")
        )
    else:
        gate_summary = "Not recommended for EVA/high-stakes work until indicators improve."
        if nasa_on and co2 and co2.status in ("amber", "red"):
            gate_summary += " NASA historical cabin CO₂ is a concurrent environmental stressor."

    return OperationsOut(
        astronaut_id=astronaut_id,
        advisory_label="MISSION READINESS GATE — ADVISORY ONLY",
        readiness_pct=readiness,
        tasks=[
            task("eva", "EVA Preparation", eva_status),
            task("docking", "Docking Operations", dock_status),
            task("maintenance", "Routine Maintenance", "ready"),
        ],
        key_factors=factors,
        gate_summary=gate_summary,
        trust_line=TRUST_LINE,
    )
