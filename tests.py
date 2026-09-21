"""Test suite for the Smart Fitness Session Analyzer.

Uses only the standard library, so it runs with:

    python3 tests.py

Tests are grouped into: object model (encapsulation, inheritance,
composition), validation rules, calculations, and end-to-end scenarios.
"""

import traceback

from analysis import (
    analyze_session,
    audit_data_quality,
    classify_session,
    compare_with_baseline,
    detect_recovery,
    summarize_measurements,
)
from models import (
    BaseObservation,
    FitnessObservation,
    ParticipantProfile,
    TrainingSession,
    ValidationError,
)
from reporting import build_report, format_measurement
from sample_data import load_session

PROFILE = ParticipantProfile("TEST", 70, 1.5, 32.0)


def make_observation(**overrides) -> FitnessObservation:
    """A clean, valid observation unless a field is deliberately overridden."""
    defaults = dict(
        timestamp=0,
        heart_rate=72,
        skin_response=1.5,
        temperature=32.0,
        activity_level=0.10,
        signal_quality=0.90,
    )
    defaults.update(overrides)
    return FitnessObservation(**defaults)


def make_session(observations, profile=PROFILE, name="test") -> TrainingSession:
    session = TrainingSession(profile, name)
    for observation in observations:
        session.add_observation(observation)
    return session


def check(condition, message):
    if not condition:
        raise AssertionError(message)


# --- object model ---------------------------------------------------------


def test_baselines_are_read_only():
    """Encapsulation: baselines cannot be reassigned from outside."""
    profile = ParticipantProfile("P", 70, 1.5, 32.0)
    try:
        profile.baseline_heart_rate = 200
    except AttributeError:
        return
    raise AssertionError("baseline_heart_rate should not be settable")


def test_profile_rejects_bad_input():
    for bad in [("", 70, 1.5, 32.0), ("P", "fast", 1.5, 32.0), ("P", 70, None, 32.0)]:
        try:
            ParticipantProfile(*bad)
        except ValidationError:
            continue
        raise AssertionError(f"ParticipantProfile should reject {bad!r}")


def test_fitness_observation_inherits_from_base():
    observation = make_observation()
    check(isinstance(observation, BaseObservation), "FitnessObservation must extend BaseObservation")


def test_subclass_extends_rather_than_replaces_validation():
    """Overriding: the subclass keeps the base class's signal-quality rule."""
    observation = make_observation(signal_quality=1.8)
    issues = observation.validate()
    check(
        any("signal_quality" in issue for issue in issues),
        "base-class signal_quality rule must still apply in the subclass",
    )


def test_subclass_to_dict_includes_base_fields():
    data = make_observation().to_dict()
    for field in ["timestamp", "signal_quality", "heart_rate", "activity_level"]:
        check(field in data, f"to_dict() should include {field}")


def test_session_observation_list_is_protected():
    """Composition + encapsulation: the internal list cannot be mutated."""
    session = make_session([make_observation()])
    session.observations.append(make_observation(timestamp=99))
    check(len(session) == 1, "mutating the returned list must not affect the session")


def test_session_rejects_wrong_type():
    session = TrainingSession(PROFILE)
    try:
        session.add_observation({"timestamp": 0})
    except ValidationError:
        return
    raise AssertionError("add_observation should reject non-FitnessObservation values")


def test_session_orders_observations_by_timestamp():
    session = make_session([make_observation(timestamp=5), make_observation(timestamp=1)])
    stamps = [o.timestamp for o in session.observations]
    check(stamps == [1, 5], f"observations should be ordered, got {stamps}")


def test_from_generator_output_builds_objects():
    session = load_session("resting", seed=42)
    check(isinstance(session, TrainingSession), "should return a TrainingSession")
    check(len(session) == 12, f"expected 12 windows, got {len(session)}")
    check(
        all(isinstance(o, FitnessObservation) for o in session.observations),
        "all windows should be FitnessObservation objects",
    )


# --- validation -----------------------------------------------------------


def test_clean_observation_has_no_issues():
    check(make_observation().validate() == [], "a normal observation should be clean")


def test_missing_values_are_reported():
    for field in ["heart_rate", "skin_response", "temperature", "activity_level"]:
        issues = make_observation(**{field: None}).validate()
        check(any(field in issue for issue in issues), f"missing {field} should be reported")


def test_impossible_heart_rate_is_rejected():
    issues = make_observation(heart_rate=265).validate()
    check(any("heart_rate" in issue for issue in issues), "265 bpm should be rejected")


def test_negative_activity_level_is_rejected():
    issues = make_observation(activity_level=-0.20).validate()
    check(any("activity_level" in issue for issue in issues), "negative movement is impossible")


def test_boundary_values_are_accepted():
    """Values exactly on the documented limits are valid, not rejected."""
    check(make_observation(activity_level=0.0).validate() == [], "0.0 movement is valid")
    check(make_observation(activity_level=1.0).validate() == [], "1.0 movement is valid")
    check(make_observation(temperature=42.0).validate() == [], "42 C is on the limit")


def test_booleans_are_not_accepted_as_numbers():
    issues = make_observation(heart_rate=True).validate()
    check(any("heart_rate" in issue for issue in issues), "True must not count as a heart rate")


def test_low_signal_quality_is_flagged_not_rejected():
    observation = make_observation(signal_quality=0.20)
    check(observation.validate() == [], "low quality alone should not invalidate a plausible reading")
    check(not observation.is_trusted(), "but it should not be trusted either")


def test_audit_reports_rejections_with_reasons():
    session = make_session([make_observation(timestamp=0, heart_rate=None), make_observation(timestamp=1)])
    quality = audit_data_quality(session)
    check(quality["usable_observations"] == 1, "one window should survive")
    check(len(quality["rejected_observations"]) == 1, "one window should be rejected")
    check(quality["rejected_observations"][0]["issues"], "the rejection should carry a reason")


# --- calculations ---------------------------------------------------------


def test_summarize_returns_average_min_max():
    summary = TrainingSession.summarize([10, 20, 30])
    check(summary == {"average": 20.0, "minimum": 10, "maximum": 30}, f"got {summary}")


def test_summarize_ignores_missing_values():
    check(TrainingSession.summarize([None, 5, None, 15])["average"] == 10.0, "None should be skipped")
    check(TrainingSession.summarize([None, None]) is None, "all-missing should give None")


def test_summaries_cover_every_field():
    summaries = summarize_measurements([make_observation(timestamp=t) for t in range(4)])
    for field in ["heart_rate", "skin_response", "temperature", "activity_level"]:
        check(summaries[field] is not None, f"{field} should be summarized")
        for statistic in ["average", "minimum", "maximum"]:
            check(statistic in summaries[field], f"{field} should report {statistic}")


def test_comparison_is_relative_to_baseline():
    observations = [make_observation(timestamp=t, heart_rate=90) for t in range(4)]
    comparison = compare_with_baseline(PROFILE, observations)
    check(comparison["heart_rate_delta"] == 20.0, f"90 - 70 should be 20, got {comparison}")


def test_comparison_handles_empty_input():
    comparison = compare_with_baseline(PROFILE, [])
    check(comparison["heart_rate_delta"] is None, "no data should give None, not a crash")


def test_recovery_detected_when_measurements_fall_at_the_end():
    observations = [
        make_observation(timestamp=t, heart_rate=130 - 8 * t, activity_level=max(0.05, 0.85 - 0.1 * t))
        for t in range(9)
    ]
    recovery = detect_recovery(observations)
    check(recovery["is_recovering"], f"declining session should be recovery, got {recovery}")


def test_recovery_not_detected_in_steady_session():
    observations = [make_observation(timestamp=t, heart_rate=120, activity_level=0.6) for t in range(9)]
    check(not detect_recovery(observations)["is_recovering"], "a flat session is not recovery")


def test_recovery_ignores_sessions_that_are_too_short():
    recovery = detect_recovery([make_observation(timestamp=0), make_observation(timestamp=1)])
    check(not recovery["is_recovering"], "two windows are not enough to judge a trend")
    check(recovery["heart_rate_drop"] is None, "no drop should be reported")


def test_hard_session_that_only_dips_is_not_recovery():
    """Effort must actually ease off, not merely dip below its own peak."""
    heart_rates = [125, 130, 135, 140, 138, 136, 128, 126, 124]
    activities = [0.80, 0.85, 0.90, 0.92, 0.90, 0.88, 0.82, 0.80, 0.78]
    observations = [
        make_observation(timestamp=t, heart_rate=hr, activity_level=a)
        for t, (hr, a) in enumerate(zip(heart_rates, activities))
    ]
    check(
        not detect_recovery(observations)["is_recovering"],
        "still-high closing effort should not count as recovery",
    )


def test_recovery_beats_a_flat_overall_average():
    """A climb-then-drop session is recovering even with a flat overall slope."""
    heart_rates = [80, 100, 120, 130, 130, 130, 120, 100, 80]
    activities = [0.2, 0.5, 0.8, 0.9, 0.9, 0.9, 0.6, 0.3, 0.1]
    observations = [
        make_observation(timestamp=t, heart_rate=hr, activity_level=a)
        for t, (hr, a) in enumerate(zip(heart_rates, activities))
    ]
    check(detect_recovery(observations)["is_recovering"], "end-of-session decline should be detected")


# --- classification and results ------------------------------------------


def test_result_is_a_dictionary_with_expected_sections():
    result = analyze_session(load_session("resting", seed=42))
    check(isinstance(result, dict), "analyze_session should return a dictionary")
    for section in [
        "participant",
        "scenario",
        "data_quality",
        "summaries",
        "baseline_comparison",
        "recovery",
        "classification",
    ]:
        check(section in result, f"result should contain a {section!r} section")


def test_classification_always_explains_itself():
    for scenario in ["resting", "moderate_activity", "high_activity", "recovery", "poor_quality"]:
        result = analyze_session(load_session(scenario, seed=42))
        explanation = result["classification"]["explanation"]
        check(bool(explanation.strip()), f"{scenario} should carry an explanation")


def test_quality_gate_runs_before_intensity_rules():
    """Unusable data must not be labelled with an intensity."""
    session = make_session([make_observation(timestamp=t, heart_rate=None) for t in range(8)])
    result = analyze_session(session)
    check(
        result["classification"]["label"] == "insufficient_data",
        f"expected insufficient_data, got {result['classification']['label']}",
    )


def test_empty_session_does_not_crash():
    result = analyze_session(TrainingSession(PROFILE, "empty"))
    check(result["classification"]["label"] == "insufficient_data", "an empty session is insufficient")


# --- end-to-end scenarios -------------------------------------------------


def _label_for(scenario, **kwargs):
    return analyze_session(load_session(scenario, **kwargs))["classification"]["label"]


def test_scenario_resting():
    check(_label_for("resting", seed=42) == "resting", "resting scenario mislabelled")


def test_scenario_moderate_activity():
    check(
        _label_for("moderate_activity", seed=42) == "moderate_activity",
        "moderate scenario mislabelled",
    )


def test_scenario_high_activity():
    check(_label_for("high_activity", seed=7) == "high_activity", "high scenario mislabelled")


def test_scenario_recovery():
    check(_label_for("recovery", seed=42) == "recovering", "recovery scenario mislabelled")


def test_scenario_poor_quality():
    check(
        _label_for("poor_quality", seed=13) == "insufficient_data",
        "poor-quality scenario mislabelled",
    )


def test_scenarios_are_stable_across_several_seeds():
    """The rules should not depend on one lucky seed."""
    for seed in [1, 42, 99, 2024]:
        check(_label_for("resting", seed=seed) == "resting", f"resting failed at seed {seed}")
        check(
            _label_for("recovery", seed=seed) == "recovering",
            f"recovery failed at seed {seed}",
        )
        check(
            _label_for("poor_quality", seed=seed) == "insufficient_data",
            f"poor_quality failed at seed {seed}",
        )


# --- reporting ------------------------------------------------------------


def test_report_contains_the_key_sections():
    report = build_report(analyze_session(load_session("moderate_activity", seed=42)))
    for heading in ["DATA QUALITY", "MEASUREMENT SUMMARIES", "RECOVERY CHECK", "CLASSIFICATION"]:
        check(heading in report, f"report should contain {heading}")


def test_report_handles_a_session_with_no_usable_data():
    report = build_report(analyze_session(load_session("poor_quality", seed=13)))
    check("no usable data" in report, "report should say when there is nothing to summarize")


def test_format_measurement_handles_missing_summary():
    check("no usable data" in format_measurement("heart rate", None), "None should format safely")


# --- runner ---------------------------------------------------------------


def run_all():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    passed, failed = 0, []

    for test in tests:
        try:
            test()
        except Exception as error:  # noqa: BLE001 - a test runner should catch everything
            failed.append((test.__name__, error))
            print(f"FAIL  {test.__name__}: {error}")
            traceback.print_exc()
        else:
            passed += 1
            print(f"PASS  {test.__name__}")

    print()
    print(f"{passed}/{len(tests)} tests passed")
    if failed:
        print(f"{len(failed)} failed")
    return not failed


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
