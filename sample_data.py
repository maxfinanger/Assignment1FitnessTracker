"""Scenario definitions and session loading.

The assignment's suggested repository layout names this file ``sample_data.py``.
It sits between the instructor-supplied ``data_generator`` module (which is
used unmodified) and the rest of the program: it names the scenarios the
program demonstrates and builds ``TrainingSession`` objects from them.

Keeping this in one place means the analysis code never imports the generator
directly, so swapping in a real data source later would change only this file.
"""

from typing import Dict, List

from data_generator import available_scenarios, generate_fitness_data
from models import TrainingSession

# The five required scenarios: normal cases, an unusual case and an
# invalid-data case. Each entry fixes a seed so the demonstration output is
# reproducible for whoever marks it.
DEMO_SCENARIOS: List[Dict] = [
    {
        "scenario": "resting",
        "participant_id": "P001",
        "seed": 42,
        "number_of_windows": 12,
        "note": "Normal case: participant sitting still.",
    },
    {
        "scenario": "moderate_activity",
        "participant_id": "P002",
        "seed": 42,
        "number_of_windows": 12,
        "note": "Normal case: steady training effort.",
    },
    {
        "scenario": "high_activity",
        "participant_id": "P003",
        "seed": 7,
        "number_of_windows": 12,
        "note": "Normal case: hard training effort.",
    },
    {
        "scenario": "recovery",
        "participant_id": "P004",
        "seed": 42,
        "number_of_windows": 12,
        "note": "Unusual case: effort declining back towards baseline.",
    },
    {
        "scenario": "poor_quality",
        "participant_id": "P005",
        "seed": 13,
        "number_of_windows": 12,
        "note": "Invalid-data case: missing and impossible sensor values.",
    },
]


def load_session(
    scenario: str,
    participant_id: str = "P001",
    seed: int = 42,
    number_of_windows: int = 12,
) -> TrainingSession:
    """Generate one scenario and return it as a ``TrainingSession`` object."""
    profile_data, observation_data = generate_fitness_data(
        participant_id=participant_id,
        scenario=scenario,
        seed=seed,
        number_of_windows=number_of_windows,
    )
    return TrainingSession.from_generator_output(
        profile_data, observation_data, scenario_name=scenario
    )


def load_demo_sessions() -> List[TrainingSession]:
    """Build every scenario listed in :data:`DEMO_SCENARIOS`."""
    return [
        load_session(
            scenario=entry["scenario"],
            participant_id=entry["participant_id"],
            seed=entry["seed"],
            number_of_windows=entry["number_of_windows"],
        )
        for entry in DEMO_SCENARIOS
    ]


def generator_scenarios():
    """Pass through the scenario names the instructor's generator supports."""
    return available_scenarios()
