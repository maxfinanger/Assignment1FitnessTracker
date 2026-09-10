"""Domain objects for the Smart Fitness Session Analyzer.

The instructor-supplied ``data_generator`` module returns plain dictionaries.
This module wraps that raw data in small, purpose-built classes so the rest
of the program (validation, analysis, reporting) works with typed objects
instead of loose dicts.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParticipantProfile:
    """A participant's personal baseline readings.

    All later analysis is relative to these baseline values, since
    "normal" heart rate, skin response, and temperature differ per person.
    """

    participant_id: str
    baseline_heart_rate: float
    baseline_skin_response: float
    baseline_temperature: float

    @classmethod
    def from_dict(cls, data: dict) -> "ParticipantProfile":
        return cls(
            participant_id=data["participant_id"],
            baseline_heart_rate=data["baseline_heart_rate"],
            baseline_skin_response=data["baseline_skin_response"],
            baseline_temperature=data["baseline_temperature"],
        )


@dataclass
class Observation:
    """A single raw measurement window, before validation.

    Fields keep whatever the generator produced, including ``None`` or
    out-of-range values -- validation is a separate, explicit step so it
    can be tested and reasoned about on its own.
    """

    timestamp: int
    heart_rate: Optional[float]
    skin_response: Optional[float]
    temperature: Optional[float]
    activity_level: Optional[float]
    signal_quality: Optional[float]

    @classmethod
    def from_dict(cls, data: dict) -> "Observation":
        return cls(
            timestamp=data["timestamp"],
            heart_rate=data["heart_rate"],
            skin_response=data["skin_response"],
            temperature=data["temperature"],
            activity_level=data["activity_level"],
            signal_quality=data["signal_quality"],
        )


@dataclass
class ValidatedObservation:
    """An :class:`Observation` plus the outcome of validating it.

    ``is_valid`` is False if the observation should be excluded from
    analysis (missing or physiologically impossible values). ``issues``
    records *why*, which is useful for the report and for debugging.
    """

    observation: Observation
    is_valid: bool
    issues: List[str] = field(default_factory=list)

    @property
    def timestamp(self) -> int:
        return self.observation.timestamp
