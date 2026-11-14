from __future__ import annotations

"""Short plain-language explainers for metrics and body zones.

Not clinical guidance — helps crews interpret indicators quickly.
"""

METRIC_EXPLAINERS: dict[str, dict[str, str]] = {
    "sleep_h": {
        "title": "Sleep",
        "what": "Hours of sleep in the last rest period.",
        "why_space": "Noise, light, CO₂, and schedule pressure often shorten or fragment sleep in flight.",
        "when_worry": "Repeated nights well below your personal baseline, especially with slower reaction times.",
        "what_helps": "Protect a dark/quiet rest block, limit late caffeine, and reduce high-workload evening tasks.",
    },
    "resting_hr": {
        "title": "Resting heart rate",
        "what": "Beats per minute at rest — a simple cardiovascular load signal.",
        "why_space": "Fluid shifts, stress, poor sleep, and illness can raise resting HR above your baseline.",
        "when_worry": "Sustained elevation vs your early-mission baseline with fatigue or dizziness.",
        "what_helps": "Hydrate, rest, ease intense exercise until trend settles; escalate if symptoms worsen.",
    },
    "reaction_time_ms": {
        "title": "Reaction time",
        "what": "How quickly you respond to a simple visual cue (milliseconds).",
        "why_space": "Sleep loss, high CO₂, and fatigue commonly slow simple reaction time.",
        "when_worry": "Clear rise vs your baseline for several days, or before high-stakes tasks (EVA/docking).",
        "what_helps": "Complete a fresh assessment, prioritize sleep, and delay high-risk tasks if advised.",
    },
    "fatigue": {
        "title": "Fatigue",
        "what": "Self-rated tiredness / depleted capacity.",
        "why_space": "Long duty days, circadian misalignment, and cabin environment can accumulate fatigue.",
        "when_worry": "High fatigue plus sleep deficit or rising reaction time before critical ops.",
        "what_helps": "Short rest, workload rebalance, and a daily check-in so trends are visible.",
    },
    "mood": {
        "title": "Mood",
        "what": "Simple 1–5 wellbeing rating from your check-in.",
        "why_space": "Isolation, confinement, and workload stress can depress mood over long missions.",
        "when_worry": "Persistently low ratings with sleep or fatigue problems.",
        "what_helps": "Talk with crew/medical, protect recovery time, keep social connection routines.",
    },
    "co2_ppm": {
        "title": "Cabin CO₂",
        "what": "Carbon dioxide concentration in the habitat atmosphere (ppm).",
        "why_space": "Elevated CO₂ is linked to headaches, reduced alertness, and performance dips.",
        "when_worry": "Sustained levels well above your cabin baseline or known comfort band.",
        "what_helps": "Improve ventilation / module airflow and limit long stagnant work periods.",
    },
    "temperature_c": {
        "title": "Temperature",
        "what": "Cabin air temperature (°C).",
        "why_space": "Thermal comfort affects sleep quality and perceived fatigue.",
        "when_worry": "Large deviations from your usual cabin range with discomfort.",
        "what_helps": "Adjust clothing/module setpoints per procedures; note impact on sleep.",
    },
    "humidity_pct": {
        "title": "Humidity",
        "what": "Relative humidity in the cabin (%).",
        "why_space": "Very dry or humid air can irritate airways and affect comfort/sleep.",
        "when_worry": "Persistent extremes with congestion or sleep disruption.",
        "what_helps": "Follow ECLSS guidance; log symptoms if irritation continues.",
    },
}

ZONE_EXPLAINERS: dict[str, dict[str, str]] = {
    "head": {
        "title": "Cognitive",
        "what": "Alertness and response speed indicators (reaction time).",
        "why_space": "Sleep loss and elevated CO₂ often show up first as slower cognition.",
        "when_worry": "Amber/red cognitive status before EVA, docking, or complex maintenance.",
        "what_helps": "Run a reaction-time check; protect sleep; reassess readiness.",
    },
    "torso": {
        "title": "Cardiopulmonary",
        "what": "Resting heart-rate trend vs your personal baseline.",
        "why_space": "Fluid shifts and stress load the cardiovascular system differently in microgravity.",
        "when_worry": "Clear HR rise with dizziness, headache, or unusual fatigue.",
        "what_helps": "Rest, hydrate, and escalate via medical protocols if symptoms persist.",
    },
    "core": {
        "title": "Core capacity",
        "what": "Fatigue / recovery capacity relative to your baseline.",
        "why_space": "Cumulative workload without recovery depletes reserve for contingencies.",
        "when_worry": "High fatigue stacked with poor sleep or cognitive slowdown.",
        "what_helps": "Shorten high-load blocks, prioritize rest, complete today's check-in.",
    },
}

TRUST_LINE = (
    "Advisory support — not a diagnosis. Escalate via mission medical protocols if symptoms worsen."
)

IMPACT_LINE = (
    "Built for deep-space autonomy with Earth dual-use: Antarctic stations, submarines, "
    "remote clinics, and commercial crew — personal baseline → act before failure."
)

SCIENCE_NOTE = (
    "Prototype rules informed by published associations (sleep loss → slower cognition; "
    "elevated cabin CO₂ → headaches/alertness dips). Not clinical limits or NASA medical standards."
)

# Short literature anchors for judges / pitch (not medical claims).
SCIENCE_CITATIONS: list[dict[str, str]] = [
    {
        "topic": "Cabin CO₂ & cognition",
        "note": "Elevated CO₂ linked to headaches and reduced decision quality in closed environments.",
        "anchor": "NASA HRP / ISS cabin atmosphere research; Satish et al. indoor CO₂ cognition studies",
    },
    {
        "topic": "Sleep & performance",
        "note": "Sustained sleep debt slows simple reaction time and raises operational error risk.",
        "anchor": "NASA Behavioral Health & Performance; aerospace sleep/performance literature",
    },
    {
        "topic": "Personal baselines",
        "note": "Within-person change detection is more actionable than fleet averages for small crews.",
        "anchor": "HRP individualized monitoring concepts; analog-habitat ops practice",
    },
]


def get_metric_explainer(metric: str) -> dict[str, str] | None:
    return METRIC_EXPLAINERS.get(metric)


def all_explainers() -> dict[str, dict]:
    return {
        "metrics": METRIC_EXPLAINERS,
        "zones": ZONE_EXPLAINERS,
        "trust_line": TRUST_LINE,
        "impact_line": IMPACT_LINE,
        "science_note": SCIENCE_NOTE,
        "citations": SCIENCE_CITATIONS,
    }
