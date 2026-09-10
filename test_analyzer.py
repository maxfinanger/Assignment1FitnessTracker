"""Lightweight unit tests (no pytest dependency required).

Run with:  python3 test_analyzer.py
"""

from analysis import classify_session, compute_metrics
from models import Observation, ParticipantProfile, ValidatedObservation
from validation import validate_all, validate_observation

PROFILE = ParticipantProfile(
    participant_id="TEST",
    baseline_heart_rate=70,
    baseline_skin_response=1.5,
    baseline_temperature=32.0,
)


def make_observation(**overrides):
    defaults = dict(
        timestamp=0,
        heart_rate=72,
        skin_response=1.5,
        temperature=32.0,
        activity_level=0.1,
        signal_quality=0.9,
    )
    defaults.update(overrides)
    return Observation(**defaults)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_valid_observation_passes():
    result = validate_observation(make_observation())
    check(result.is_valid, "a normal observation should be valid")
    check(result.issues == [], f"expected no issues, got {result.issues}")


def test_missing_heart_rate_is_rejected():
    result = validate_observation(make_observation(heart_rate=None))
    check(not result.is_valid, "missing heart_rate must invalidate the observation")


def test_impossible_heart_rate_is_rejected():
    result = validate_observation(make_observation(heart_rate=265))
    check(not result.is_valid, "heart_rate of 265 is outside plausible range and must be rejected")


def test_negative_activity_level_is_rejected():
    result = validate_observation(make_observation(activity_level=-0.2))
    check(not result.is_valid, "negative activity_level is impossible and must be rejected")


def test_low_signal_quality_is_flagged_but_not_hard_rejected():
    result = validate_observation(make_observation(signal_quality=0.2))
    check(result.is_valid, "low signal quality alone should not hard-reject an otherwise plausible reading")
    check(any("trust threshold" in issue for issue in result.issues), "low signal quality should still be recorded as an issue")


def test_resting_session_is_classified_as_resting():
    observations = [make_observation(timestamp=t, heart_rate=71, activity_level=0.1) for t in range(8)]
    validated = validate_all(observations)
    metrics = compute_metrics(PROFILE, validated)
    result = classify_session(metrics)
    check(result.label == "resting", f"expected 'resting', got '{result.label}'")


def test_high_activity_session_is_classified_correctly():
    observations = [make_observation(timestamp=t, heart_rate=135, activity_level=0.85) for t in range(8)]
    validated = validate_all(observations)
    metrics = compute_metrics(PROFILE, validated)
    result = classify_session(metrics)
    check(result.label == "high_activity", f"expected 'high_activity', got '{result.label}'")


def test_declining_heart_rate_is_classified_as_recovery():
    observations = [
        make_observation(timestamp=t, heart_rate=130 - 8 * t, activity_level=0.5)
        for t in range(8)
    ]
    validated = validate_all(observations)
    metrics = compute_metrics(PROFILE, validated)
    result = classify_session(metrics)
    check(result.label == "recovery", f"expected 'recovery', got '{result.label}'")


def test_mostly_invalid_session_is_flagged_as_poor_quality():
    observations = [make_observation(timestamp=t, heart_rate=None) for t in range(8)]
    validated = validate_all(observations)
    metrics = compute_metrics(PROFILE, validated)
    result = classify_session(metrics)
    check(result.label == "poor_data_quality", f"expected 'poor_data_quality', got '{result.label}'")


def run_all():
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    passed = 0
    for test in tests:
        test()
        passed += 1
        print(f"PASS  {test.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
