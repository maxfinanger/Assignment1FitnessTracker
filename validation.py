"""Validation rules for raw fitness observations.

DATA_DESCRIPTION.md gives "expected ranges" for each field and warns that
poor quality scenarios contain ``None`` values and impossible values. This
module turns those expectations into explicit, testable rules and produces
a :class:`~models.ValidatedObservation` for every raw observation. Nothing
is silently dropped, so the report can always say how much data was usable.
"""

from typing import List

from models import Observation, ValidatedObservation

# Plausible physiological / sensor bounds. Slightly wider than the
# "normally X-Y" ranges in DATA_DESCRIPTION.md so that legitimate outliers
# are not rejected as hard errors -- only values documented as impossible.
HEART_RATE_RANGE = (30, 220)
TEMPERATURE_RANGE = (25, 42)
ACTIVITY_LEVEL_RANGE = (0, 1)
SIGNAL_QUALITY_RANGE = (0, 1)
MIN_SIGNAL_QUALITY_FOR_TRUST = 0.5  # below this, treat as unreliable


def _in_range(value, low, high) -> bool:
    return low <= value <= high


def validate_observation(observation: Observation) -> ValidatedObservation:
    """Check one observation and report every problem found (not just the first)."""

    issues: List[str] = []

    if observation.heart_rate is None:
        issues.append("heart_rate is missing")
    elif not _in_range(observation.heart_rate, *HEART_RATE_RANGE):
        issues.append(f"heart_rate {observation.heart_rate} outside plausible range {HEART_RATE_RANGE}")

    if observation.skin_response is None:
        issues.append("skin_response is missing")
    elif observation.skin_response < 0:
        issues.append(f"skin_response {observation.skin_response} is negative")

    if observation.temperature is None:
        issues.append("temperature is missing")
    elif not _in_range(observation.temperature, *TEMPERATURE_RANGE):
        issues.append(f"temperature {observation.temperature} outside plausible range {TEMPERATURE_RANGE}")

    if observation.activity_level is None:
        issues.append("activity_level is missing")
    elif not _in_range(observation.activity_level, *ACTIVITY_LEVEL_RANGE):
        issues.append(f"activity_level {observation.activity_level} outside 0-1")

    if observation.signal_quality is None:
        issues.append("signal_quality is missing")
    elif not _in_range(observation.signal_quality, *SIGNAL_QUALITY_RANGE):
        issues.append(f"signal_quality {observation.signal_quality} outside 0-1")
    elif observation.signal_quality < MIN_SIGNAL_QUALITY_FOR_TRUST:
        issues.append(f"signal_quality {observation.signal_quality} below trust threshold {MIN_SIGNAL_QUALITY_FOR_TRUST}")

    # An observation is only usable for analysis if none of the checks above
    # tripped. Low signal quality is recorded as an issue but is treated
    # more leniently below (see is_valid logic) since it degrades trust
    # rather than making the reading physically impossible.
    hard_failures = [
        i for i in issues
        if "below trust threshold" not in i
    ]
    is_valid = len(hard_failures) == 0

    return ValidatedObservation(observation=observation, is_valid=is_valid, issues=issues)


def validate_all(observations: List[Observation]) -> List[ValidatedObservation]:
    return [validate_observation(o) for o in observations]
