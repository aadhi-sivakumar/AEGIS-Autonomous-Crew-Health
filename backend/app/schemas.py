from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

DemoScenario = Literal["stable", "emerging_decline", "recovery"]
ZoneStatus = Literal["green", "amber", "red"]
Provenance = Literal[
    "SIMULATED_CREW_DATA",
    "SYNTHETIC_ENVIRONMENT",
    "NASA_HISTORICAL",
    "BROWSER_MEASURED",
]


class CrewMemberOut(BaseModel):
    id: str
    callsign: str
    role: str
    scenario_profile: str


class HealthPoint(BaseModel):
    mission_day: int
    sleep_h: float
    resting_hr: float
    fatigue: float
    mood: float
    reaction_time_ms: float
    exercise_adherence: float
    provenance: str


class EnvironmentPoint(BaseModel):
    mission_day: int
    co2_ppm: float
    temperature_c: float
    humidity_pct: float
    provenance: str
    source_label: str


class MetricBaseline(BaseModel):
    metric: str
    baseline: float
    latest: float
    delta: float
    unit: str
    status: ZoneStatus
    sparkline: list[float]
    provenance: str


class ZoneStatusOut(BaseModel):
    zone: Literal["head", "torso", "core"]
    status: ZoneStatus
    label: str
    detail: str


class DeviationOut(BaseModel):
    metric: str
    direction: str
    magnitude: float
    consecutive_days: int
    explanation: str


class CombinedPatternOut(BaseModel):
    detected: bool
    severity: ZoneStatus
    summary: str
    contributing_metrics: list[str]
    recommended_action: str


class ForecastPoint(BaseModel):
    mission_day: int
    value: float
    kind: Literal["observed", "forecast"]
    lower: Optional[float] = None
    upper: Optional[float] = None


class ForecastOut(BaseModel):
    next_day_estimate: float
    baseline_estimate: float
    uncertainty: float
    model_version: str
    disclaimer: str
    series: list[ForecastPoint]
    contributing_inputs: list[str]


class HealthOverviewOut(BaseModel):
    astronaut_id: str
    mission_day: int
    scenario: DemoScenario
    history: list[HealthPoint]
    environment: list[EnvironmentPoint]
    metrics: list[MetricBaseline]
    zones: list[ZoneStatusOut]
    deviations: list[DeviationOut]
    combined_pattern: CombinedPatternOut
    forecast: ForecastOut
    nasa_import_loaded: bool
    environment_banner: Optional[str] = None


class BaselineOut(BaseModel):
    astronaut_id: str
    window_days: int
    baselines: dict[str, float]
    method: str


class DemoScenarioOut(BaseModel):
    scenario: DemoScenario
    mission_day: int
    label: str


class DemoScenarioIn(BaseModel):
    scenario: DemoScenario


class AssessmentIn(BaseModel):
    astronaut_id: str
    median_rt_ms: float
    iqr_ms: float
    trial_count: int = Field(ge=1)
    invalid_count: int = Field(ge=0)
    trials: list[float] = Field(default_factory=list)


class AssessmentOut(BaseModel):
    id: int
    astronaut_id: str
    mission_day: int
    median_rt_ms: float
    iqr_ms: float
    provenance: str
    message: str


class SimulateIn(BaseModel):
    astronaut_id: str
    sleep_h: float = Field(ge=4, le=9)
    co2_ppm: float = Field(ge=500, le=3500)
    fatigue: Optional[float] = Field(default=None, ge=1, le=10)


class SimulateOut(BaseModel):
    current_estimate: float
    hypothetical_estimate: float
    delta_ms: float
    delta_pct: float
    drivers: list[str]
    disclaimer: str
    series_current: list[dict[str, Any]]
    series_hypothetical: list[dict[str, Any]]


class EmergencyStepOut(BaseModel):
    step: int
    title: str
    detail: str
    href: Optional[str] = None


class GuidanceOut(BaseModel):
    astronaut_id: str
    alerts: list[dict[str, Any]]
    recommendations: list[str]
    emergency_disclaimer: str
    emergency_steps: list[EmergencyStepOut] = Field(default_factory=list)
    when_to_escalate: list[str] = Field(default_factory=list)
    assessment_complete: bool = False
    has_browser_assessment: bool = False
    actions: list["ActionItemOut"] = Field(default_factory=list)
    trust_line: str = (
        "Advisory support — not a diagnosis. Escalate via mission medical protocols "
        "if symptoms worsen."
    )


class AssessmentCompleteIn(BaseModel):
    complete: bool = True


class TelemetryCreateIn(BaseModel):
    astronaut_id: str


class OperationTaskOut(BaseModel):
    id: str
    name: str
    status: Literal["ready", "assessment_recommended", "review_required"]
    status_label: str
    justification: str
    action_label: str
    gate: Literal["ready", "caution", "not_recommended"] = "ready"
    recheck_hint: str = ""


class OperationsOut(BaseModel):
    astronaut_id: str
    advisory_label: str
    readiness_pct: int
    tasks: list[OperationTaskOut]
    key_factors: list[str]
    gate_summary: str = ""
    trust_line: str = (
        "Advisory support — not a diagnosis. Escalate via mission medical protocols "
        "if symptoms worsen."
    )


class CheckInIn(BaseModel):
    astronaut_id: str
    sleep_h: float = Field(ge=0, le=14)
    fatigue: float = Field(ge=1, le=5)
    mood: float = Field(ge=1, le=5)
    resting_hr: Optional[float] = Field(default=None, ge=35, le=140)
    notes: Optional[str] = Field(default=None, max_length=500)


class CheckInOut(BaseModel):
    id: int
    astronaut_id: str
    mission_day: int
    sleep_h: float
    fatigue: float
    mood: float
    resting_hr: Optional[float] = None
    notes: Optional[str] = None
    provenance: str
    created_at: str


class SymptomCheckIn(BaseModel):
    astronaut_id: str
    headache: int = Field(ge=0, le=3, default=0)
    congestion: int = Field(ge=0, le=3, default=0)
    dizziness: int = Field(ge=0, le=3, default=0)
    nausea: int = Field(ge=0, le=3, default=0)
    other_notes: Optional[str] = Field(default=None, max_length=500)


class SymptomCheckOut(BaseModel):
    id: int
    astronaut_id: str
    mission_day: int
    headache: int
    congestion: int
    dizziness: int
    nausea: int
    other_notes: Optional[str] = None
    provenance: str
    created_at: str
    attention_needed: bool = False


class PromptOut(BaseModel):
    kind: Literal[
        "morning_checkin",
        "daily_assessment",
        "symptom_check",
        "weekly_assessment",
        "pre_eva",
    ]
    title: str
    message: str
    href: str
    urgency: Literal["normal", "high"] = "normal"
    due_label: str = ""


class PromptSnoozeIn(BaseModel):
    kind: Literal[
        "morning_checkin",
        "daily_assessment",
        "symptom_check",
        "weekly_assessment",
        "pre_eva",
    ]


class ReminderSlotOut(BaseModel):
    id: str
    label: str
    window: str
    done: bool
    href: str
    how_long: str


class ActionItemOut(BaseModel):
    id: str
    severity: ZoneStatus
    summary: str
    do_label: str
    do_href: str
    escalate_label: Optional[str] = None
    escalate_href: Optional[str] = None
    reason: str


class TodayMetricOut(BaseModel):
    metric: str
    label: str
    latest: float
    baseline: float
    delta: float
    unit: str
    status: ZoneStatus
    plain: str


class EnvContextOut(BaseModel):
    """Cabin environment strip for Today — NASA or simulated."""

    mode: Literal["simulated", "nasa_historical"]
    nasa_cached: bool
    co2_ppm: Optional[float] = None
    co2_status: Optional[ZoneStatus] = None
    co2_baseline: Optional[float] = None
    source_label: str
    provenance: str
    decision_blurb: str
    science_note: str
    replay_href: str = "/nasa-replay"


class TodayOut(BaseModel):
    astronaut_id: str
    mission_day: int
    overall_status: ZoneStatus
    plain_language: str
    trust_line: str
    impact_line: str = ""
    top_metrics: list[TodayMetricOut]
    primary_action: dict[str, str]
    checkin: Optional[CheckInOut] = None
    checkin_done: bool
    symptoms: Optional[SymptomCheckOut] = None
    prompts: list[PromptOut]
    reminder_schedule: list[ReminderSlotOut] = Field(default_factory=list)
    assessment_complete: bool
    has_browser_assessment: bool
    forecast_next_day_ms: float
    forecast_model: str
    forecast_blurb: str
    env_context: Optional[EnvContextOut] = None


class TelemetryReportOut(BaseModel):
    id: str
    astronaut_id: str
    mission_day: int
    status: Literal["queued", "sent"]
    created_at: str
    encrypted: bool
    sections: list[str]


class TelemetryQueueOut(BaseModel):
    reports: list[TelemetryReportOut]
    next_window_label: str
    countdown_seconds: int
    simulated: bool


class ApiMessage(BaseModel):
    detail: str
    phase: Optional[str] = None
