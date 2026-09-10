"""Smart Fitness Session Analyzer — entry point.

Pulls simulated data from the instructor-supplied ``data_generator``,
converts it into typed objects, validates it, analyzes the session, and
prints a report. Running this file against every documented scenario is a
quick way to sanity-check the classification rules end to end.
"""

from data_generator import available_scenarios, generate_fitness_data

from analysis import classify_session, compute_metrics
from models import Observation, ParticipantProfile
from report import build_report
from validation import validate_all


def analyze_session(participant_id: str, scenario: str, seed: int, number_of_windows: int = 12) -> str:
    raw_profile, raw_observations = generate_fitness_data(
        participant_id=participant_id,
        scenario=scenario,
        seed=seed,
        number_of_windows=number_of_windows,
    )

    profile = ParticipantProfile.from_dict(raw_profile)
    observations = [Observation.from_dict(o) for o in raw_observations]

    validated = validate_all(observations)
    metrics = compute_metrics(profile, validated)
    classification = classify_session(metrics)

    return build_report(profile, validated, metrics, classification)


def main():
    print("Available scenarios:", available_scenarios())
    print()

    for scenario in available_scenarios():
        report = analyze_session(
            participant_id="P001",
            scenario=scenario,
            seed=42,
            number_of_windows=12,
        )
        print(report)
        print()


if __name__ == "__main__":
    main()
