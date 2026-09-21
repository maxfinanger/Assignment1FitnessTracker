"""Smart Fitness Session Analyzer -- program entry point.

Run from the repository root:

    python3 main.py
"""

from analysis import analyze_session
from reporting import build_report
from sample_data import DEMO_SCENARIOS, generator_scenarios, load_demo_sessions


def print_summary_table(results):
    """Print a compact overview of how every scenario was classified."""
    print()
    print("=" * 66)
    print("SUMMARY OF ALL SCENARIOS")
    print("=" * 66)
    header = f"{'scenario':<20}{'participant':<14}{'usable':<10}{'classification'}"
    print(header)
    print("-" * 66)
    for result in results:
        quality = result["data_quality"]
        usable = f"{quality['usable_observations']}/{quality['total_observations']}"
        print(
            f"{result['scenario']:<20}"
            f"{result['participant']['participant_id']:<14}"
            f"{usable:<10}"
            f"{result['classification']['label']}"
        )
    print("=" * 66)


def main():
    print("Smart Fitness Session Analyzer")
    print(f"Scenarios supported by the data generator: {generator_scenarios()}")
    print()

    sessions = load_demo_sessions()
    results = []

    for session, meta in zip(sessions, DEMO_SCENARIOS):
        print(f"### {meta['note']}")
        result = analyze_session(session)
        results.append(result)
        print(build_report(result))
        print()

    print_summary_table(results)


if __name__ == "__main__":
    main()