"""Turns validated observations into session-level metrics and a classification.

The generator's docstring never reveals the "true" scenario label, so
classification here is built from first principles: baseline-relative
deltas, the documented expected ranges, and a simple trend check (rather
than by reverse-engineering the generator's internal constants).
"""

from dataclasses import dataclass
from typing import List, Optional

from models import ParticipantProfile, ValidatedObservation

# Classification thresholds. These are deliberately simple and named so
# they are easy to defend, tune, and unit-test -- see report.py / the
# write-up for the reasoning behind each one.
RESTING_HR_DELTA = 10          # bpm above baseline
MODERATE_HR_DELTA = 15
HIGH_HR_DELTA = 45
RESTING_ACTIVITY = 0.25
MODERATE_ACTIVITY = 0.30
HIGH_ACTIVITY = 0.65
RECOVERY_SLOPE = -2.5          # bpm per window; a clearly downward trend
LOW_DATA_QUALITY_FRACTION = 0.30   # share of invalid observations
LOW_AVG_SIGNAL_QUALITY = 0.60


@dataclass
class SessionMetrics:
    total_observations: int
    valid_observations: int
    invalid_fraction: float
    avg_signal_quality: Optional[float]
    avg_heart_rate_delta: Optional[float]
    avg_skin_response_delta: Optional[float]
    avg_temperature_delta: Optional[float]
    avg_activity_level: Optional[float]
    heart_rate_trend_bpm_per_window: Optional[float]


@dataclass
class SessionClassification:
    label: str
    reasoning: str


def _mean(values: List[float]) -> Optional[float]:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _linear_trend(xs: List[int], ys: List[float]) -> Optional[float]:
    """Least-squares slope of ys against xs (bpm change per window)."""
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return numerator / denominator


def compute_metrics(
    profile: ParticipantProfile,
    validated: List[ValidatedObservation],
) -> SessionMetrics:
    total = len(validated)
    valid = [v for v in validated if v.is_valid]
    invalid_fraction = (total - len(valid)) / total if total else 1.0

    hr_deltas = [v.observation.heart_rate - profile.baseline_heart_rate for v in valid]
    skin_deltas = [v.observation.skin_response - profile.baseline_skin_response for v in valid]
    temp_deltas = [v.observation.temperature - profile.baseline_temperature for v in valid]
    activity_levels = [v.observation.activity_level for v in valid]
    signal_qualities = [v.observation.signal_quality for v in validated if v.observation.signal_quality is not None]

    trend = _linear_trend(
        [v.timestamp for v in valid],
        [v.observation.heart_rate for v in valid],
    )

    return SessionMetrics(
        total_observations=total,
        valid_observations=len(valid),
        invalid_fraction=round(invalid_fraction, 3),
        avg_signal_quality=round(_mean(signal_qualities), 3) if _mean(signal_qualities) is not None else None,
        avg_heart_rate_delta=_mean(hr_deltas),
        avg_skin_response_delta=_mean(skin_deltas),
        avg_temperature_delta=_mean(temp_deltas),
        avg_activity_level=_mean(activity_levels),
        heart_rate_trend_bpm_per_window=trend,
    )


def classify_session(metrics: SessionMetrics) -> SessionClassification:
    """Label the session using simple, explainable rules over the metrics.

    Order matters: data-quality problems are checked first, because a
    metric computed from mostly-invalid data should not be trusted enough
    to drive an activity-level classification.
    """

    if (
        metrics.valid_observations == 0
        or metrics.invalid_fraction > LOW_DATA_QUALITY_FRACTION
        or (metrics.avg_signal_quality is not None and metrics.avg_signal_quality < LOW_AVG_SIGNAL_QUALITY)
    ):
        quality_str = f"{metrics.avg_signal_quality:.2f}" if metrics.avg_signal_quality is not None else "unknown"
        return SessionClassification(
            label="poor_data_quality",
            reasoning=(
                f"{metrics.invalid_fraction:.0%} of observations were invalid and/or average "
                f"signal quality was low ({quality_str}); results below this "
                "point cannot be trusted."
            ),
        )

    hr_delta = metrics.avg_heart_rate_delta or 0
    activity = metrics.avg_activity_level or 0
    trend = metrics.heart_rate_trend_bpm_per_window

    if trend is not None and trend <= RECOVERY_SLOPE and hr_delta > MODERATE_HR_DELTA:
        return SessionClassification(
            label="recovery",
            reasoning=(
                f"Heart rate is falling steadily ({trend:.2f} bpm/window) from an elevated "
                f"level (+{hr_delta:.1f} bpm over baseline), typical of cooling down after exertion."
            ),
        )

    if hr_delta <= RESTING_HR_DELTA and activity <= RESTING_ACTIVITY:
        return SessionClassification(
            label="resting",
            reasoning=f"Heart rate is close to baseline (+{hr_delta:.1f} bpm) and activity level is low ({activity:.2f}).",
        )

    if hr_delta >= HIGH_HR_DELTA and activity >= HIGH_ACTIVITY:
        return SessionClassification(
            label="high_activity",
            reasoning=f"Heart rate is well above baseline (+{hr_delta:.1f} bpm) with high activity ({activity:.2f}).",
        )

    if hr_delta >= MODERATE_HR_DELTA and activity >= MODERATE_ACTIVITY:
        return SessionClassification(
            label="moderate_activity",
            reasoning=f"Heart rate is moderately above baseline (+{hr_delta:.1f} bpm) with moderate activity ({activity:.2f}).",
        )

    return SessionClassification(
        label="uncertain",
        reasoning=(
            f"Heart rate delta (+{hr_delta:.1f} bpm) and activity level ({activity:.2f}) do not "
            "clearly match resting, moderate, high-activity, or recovery patterns."
        ),
    )
