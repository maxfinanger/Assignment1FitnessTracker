"""Builds a report from the analysis results."""

from typing import List

from analysis import SessionClassification, SessionMetrics
from models import ParticipantProfile, ValidatedObservation


def build_report(
    profile: ParticipantProfile,
    validated: List[ValidatedObservation],
    metrics: SessionMetrics,
    classification: SessionClassification,
) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"SESSION REPORT — participant {profile.participant_id}")
    lines.append("=" * 60)

    lines.append("")
    lines.append("Baseline")
    lines.append(f"  heart rate:    {profile.baseline_heart_rate} bpm")
    lines.append(f"  skin response: {profile.baseline_skin_response}")
    lines.append(f"  temperature:   {profile.baseline_temperature} C")

    lines.append("")
    lines.append("Data quality")
    lines.append(f"  observations:        {metrics.total_observations}")
    lines.append(f"  valid observations:  {metrics.valid_observations}")
    lines.append(f"  invalid fraction:    {metrics.invalid_fraction:.0%}")
    if metrics.avg_signal_quality is not None:
        lines.append(f"  avg signal quality:  {metrics.avg_signal_quality:.2f}")

    invalid = [v for v in validated if not v.is_valid]
    if invalid:
        lines.append("")
        lines.append("Rejected observations")
        for v in invalid:
            lines.append(f"  t={v.timestamp}: {'; '.join(v.issues)}")

    lines.append("")
    lines.append("Session metrics (relative to baseline)")
    if metrics.avg_heart_rate_delta is not None:
        lines.append(f"  avg heart rate delta:    {metrics.avg_heart_rate_delta:+.1f} bpm")
    if metrics.avg_skin_response_delta is not None:
        lines.append(f"  avg skin response delta: {metrics.avg_skin_response_delta:+.2f}")
    if metrics.avg_temperature_delta is not None:
        lines.append(f"  avg temperature delta:   {metrics.avg_temperature_delta:+.2f} C")
    if metrics.avg_activity_level is not None:
        lines.append(f"  avg activity level:      {metrics.avg_activity_level:.2f}")
    if metrics.heart_rate_trend_bpm_per_window is not None:
        lines.append(f"  heart rate trend:        {metrics.heart_rate_trend_bpm_per_window:+.2f} bpm/window")

    lines.append("")
    lines.append("Classification")
    lines.append(f"  label:     {classification.label}")
    lines.append(f"  reasoning: {classification.reasoning}")

    lines.append("=" * 60)
    return "\n".join(lines)
