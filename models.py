"""Domain classes for the Smart Fitness Session Analyzer.

Design summary (expanded in README.md):

* ``ParticipantProfile`` -- encapsulates a participant's personal reference
  values behind read-only properties.
* ``BaseObservation`` -- the generic idea of "one measurement window from a
  wearable sensor": it knows its timestamp and signal quality, and knows how
  to validate and serialise *those* fields.
* ``FitnessObservation`` -- a fitness-specific window that adds heart rate,
  skin response, temperature and activity level. It **overrides**
  ``validate()`` and ``to_dict()``, extending the base behaviour via
  ``super()`` rather than replacing it.
* ``TrainingSession`` -- **composition**: a session owns one
  ``ParticipantProfile`` and a list of ``FitnessObservation`` objects. The
  observations have no meaning without the session that groups them, and the
  session cannot exist without a participant.
"""

from statistics import mean
from typing import Dict, List, Optional

# Plausibility bounds, derived from DATA_DESCRIPTION.md. Slightly wider than
# the documented "normal" ranges so that genuine outliers survive while
# physically impossible values are rejected.
HEART_RATE_BOUNDS = (30.0, 220.0)
TEMPERATURE_BOUNDS = (25.0, 42.0)
UNIT_INTERVAL = (0.0, 1.0)

# A window whose signal quality falls below this is kept but marked untrusted.
SIGNAL_QUALITY_TRUST_THRESHOLD = 0.5


class ValidationError(ValueError):
    """Raised when data is too malformed to build an object from at all."""


def _is_number(value) -> bool:
    """True for real numbers, deliberately excluding bool (a subclass of int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class ParticipantProfile:
    """A participant and their personal reference measurements.

    Encapsulation: the baselines are stored in protected attributes and
    exposed through read-only properties. Baselines are the fixed point that
    every later comparison is made against, so allowing code elsewhere to
    reassign them would silently invalidate an entire analysis.
    """

    def __init__(
        self,
        participant_id: str,
        baseline_heart_rate: float,
        baseline_skin_response: float,
        baseline_temperature: float,
    ):
        if not isinstance(participant_id, str) or not participant_id.strip():
            raise ValidationError("participant_id must be a non-empty string")
        for name, value in (
            ("baseline_heart_rate", baseline_heart_rate),
            ("baseline_skin_response", baseline_skin_response),
            ("baseline_temperature", baseline_temperature),
        ):
            if not _is_number(value):
                raise ValidationError(f"{name} must be a number, got {value!r}")

        self._participant_id = participant_id.strip()
        self._baseline_heart_rate = float(baseline_heart_rate)
        self._baseline_skin_response = float(baseline_skin_response)
        self._baseline_temperature = float(baseline_temperature)

    # -- read-only properties (encapsulation) ---------------------------

    @property
    def participant_id(self) -> str:
        return self._participant_id

    @property
    def baseline_heart_rate(self) -> float:
        return self._baseline_heart_rate

    @property
    def baseline_skin_response(self) -> float:
        return self._baseline_skin_response

    @property
    def baseline_temperature(self) -> float:
        return self._baseline_temperature

    @classmethod
    def from_dict(cls, data: Dict) -> "ParticipantProfile":
        """Build a profile from the generator's raw dictionary.

        A classmethod is the right tool here: the generator's dictionary is
        one *alternative constructor format*, and keeping the key names in
        one place means a change to the data source touches only this method.
        """
        try:
            return cls(
                participant_id=data["participant_id"],
                baseline_heart_rate=data["baseline_heart_rate"],
                baseline_skin_response=data["baseline_skin_response"],
                baseline_temperature=data["baseline_temperature"],
            )
        except KeyError as missing:
            raise ValidationError(f"profile is missing field {missing}") from missing

    def to_dict(self) -> Dict:
        return {
            "participant_id": self._participant_id,
            "baseline_heart_rate": self._baseline_heart_rate,
            "baseline_skin_response": self._baseline_skin_response,
            "baseline_temperature": self._baseline_temperature,
        }

    def __repr__(self) -> str:
        return f"ParticipantProfile({self._participant_id!r}, hr={self._baseline_heart_rate})"


class BaseObservation:
    """One measurement window from any wearable sensor.

    This base class deliberately knows only what *every* sensor window has:
    when it was taken, and how much the device trusted the reading. Fitness
    specific fields live in the subclass.
    """

    def __init__(self, timestamp, signal_quality):
        if not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp < 0:
            raise ValidationError(f"timestamp must be an integer >= 0, got {timestamp!r}")
        self.timestamp = timestamp
        self.signal_quality = signal_quality

    def validate(self) -> List[str]:
        """Return a list of problems with this window (empty list == clean).

        Subclasses override this and call ``super().validate()`` so the shared
        signal-quality rules are applied exactly once, in one place.
        """
        issues: List[str] = []
        if self.signal_quality is None:
            issues.append("signal_quality is missing")
        elif not _is_number(self.signal_quality):
            issues.append(f"signal_quality is not a number ({self.signal_quality!r})")
        elif not UNIT_INTERVAL[0] <= self.signal_quality <= UNIT_INTERVAL[1]:
            issues.append(f"signal_quality {self.signal_quality} outside 0-1")
        return issues

    def is_trusted(self) -> bool:
        """Whether the device itself reported a reliable reading."""
        return (
            _is_number(self.signal_quality)
            and self.signal_quality >= SIGNAL_QUALITY_TRUST_THRESHOLD
        )

    def to_dict(self) -> Dict:
        return {"timestamp": self.timestamp, "signal_quality": self.signal_quality}


class FitnessObservation(BaseObservation):
    """A fitness measurement window: heart rate, skin, temperature, movement.

    Overrides ``validate()`` and ``to_dict()``, extending rather than
    replacing the base implementations.
    """

    def __init__(
        self,
        timestamp,
        heart_rate,
        skin_response,
        temperature,
        activity_level,
        signal_quality,
    ):
        super().__init__(timestamp, signal_quality)
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level

    # -- overridden methods ---------------------------------------------

    def validate(self) -> List[str]:
        """Extend the base checks with the fitness-specific field rules."""
        issues = super().validate()          # shared signal-quality rules
        issues.extend(self._check_bounded("heart_rate", self.heart_rate, HEART_RATE_BOUNDS))
        issues.extend(self._check_bounded("temperature", self.temperature, TEMPERATURE_BOUNDS))
        issues.extend(self._check_bounded("activity_level", self.activity_level, UNIT_INTERVAL))
        issues.extend(self._check_non_negative("skin_response", self.skin_response))
        return issues

    def to_dict(self) -> Dict:
        data = super().to_dict()             # timestamp + signal_quality
        data.update(
            {
                "heart_rate": self.heart_rate,
                "skin_response": self.skin_response,
                "temperature": self.temperature,
                "activity_level": self.activity_level,
            }
        )
        return data

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _check_bounded(name: str, value, bounds) -> List[str]:
        """Check one optional numeric field against inclusive bounds.

        A staticmethod because it depends only on its arguments, never on a
        particular observation -- which also makes it directly unit-testable.
        """
        low, high = bounds
        if value is None:
            return [f"{name} is missing"]
        if not _is_number(value):
            return [f"{name} is not a number ({value!r})"]
        if not low <= value <= high:
            return [f"{name} {value} outside plausible range {low}-{high}"]
        return []

    @staticmethod
    def _check_non_negative(name: str, value) -> List[str]:
        if value is None:
            return [f"{name} is missing"]
        if not _is_number(value):
            return [f"{name} is not a number ({value!r})"]
        if value < 0:
            return [f"{name} {value} is negative"]
        return []

    @classmethod
    def from_dict(cls, data: Dict) -> "FitnessObservation":
        """Alternative constructor for the generator's raw dictionaries.

        Missing *keys* raise (the data source is broken); missing *values*
        are allowed through so ``validate()`` can report them properly.
        """
        try:
            return cls(
                timestamp=data["timestamp"],
                heart_rate=data["heart_rate"],
                skin_response=data["skin_response"],
                temperature=data["temperature"],
                activity_level=data["activity_level"],
                signal_quality=data["signal_quality"],
            )
        except KeyError as missing:
            raise ValidationError(f"observation is missing field {missing}") from missing

    def __repr__(self) -> str:
        return f"FitnessObservation(t={self.timestamp}, hr={self.heart_rate})"


class TrainingSession:
    """A participant's complete training session: profile + ordered windows.

    This is the composition in the design. The session owns its observations
    (they are created for it and have no independent life outside it) and
    holds the participant profile that gives those numbers meaning.

    The observation list is protected and exposed as a read-only copy, so the
    only way to add data is through ``add_observation()``, which enforces the
    type of what goes in.
    """

    def __init__(self, participant: ParticipantProfile, scenario_name: str = "unspecified"):
        if not isinstance(participant, ParticipantProfile):
            raise ValidationError("participant must be a ParticipantProfile")
        self._participant = participant
        self._scenario_name = scenario_name
        self._observations: List[FitnessObservation] = []

    # -- encapsulated collection -----------------------------------------

    @property
    def participant(self) -> ParticipantProfile:
        return self._participant

    @property
    def scenario_name(self) -> str:
        return self._scenario_name

    @property
    def observations(self) -> List[FitnessObservation]:
        """A copy, so callers cannot mutate the session's internal list."""
        return list(self._observations)

    def add_observation(self, observation: FitnessObservation) -> None:
        if not isinstance(observation, FitnessObservation):
            raise ValidationError("only FitnessObservation objects can be added")
        self._observations.append(observation)
        self._observations.sort(key=lambda o: o.timestamp)

    def __len__(self) -> int:
        return len(self._observations)

    # -- alternative constructor ------------------------------------------

    @classmethod
    def from_generator_output(
        cls,
        profile_data: Dict,
        observation_data: List[Dict],
        scenario_name: str = "unspecified",
    ) -> "TrainingSession":
        """Build a whole session from one ``generate_fitness_data()`` call.

        Justified as a classmethod because it is the single place that knows
        how the instructor's raw output maps onto our object model: the rest
        of the program never touches dictionaries from the generator.
        """
        session = cls(ParticipantProfile.from_dict(profile_data), scenario_name)
        for raw in observation_data:
            session.add_observation(FitnessObservation.from_dict(raw))
        return session

    # -- summarising -------------------------------------------------------

    @staticmethod
    def summarize(values: List[float]) -> Optional[Dict[str, float]]:
        """Return average/minimum/maximum for a list of numbers.

        A staticmethod: it is a pure calculation over its argument, useful to
        any caller, and needs nothing from a particular session instance.
        """
        numbers = [v for v in values if _is_number(v)]
        if not numbers:
            return None
        return {
            "average": round(mean(numbers), 2),
            "minimum": round(min(numbers), 2),
            "maximum": round(max(numbers), 2),
        }

    def valid_observations(self) -> List[FitnessObservation]:
        return [o for o in self._observations if not o.validate()]

    def __repr__(self) -> str:
        return (
            f"TrainingSession({self._participant.participant_id!r}, "
            f"{self._scenario_name!r}, {len(self._observations)} windows)"
        )