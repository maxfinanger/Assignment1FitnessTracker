# Smart Fitness Session Analyzer

## Files

| File | Responsibility |
|---|---|
| `data_generator.py` | Instructor-supplied. Unmodified. Produces raw dicts. |
| `models.py` | Typed objects: `ParticipantProfile`, `Observation`, `ValidatedObservation`. |
| `validation.py` | Field-by-field checks; decides which observations are usable. |
| `analysis.py` | Baseline-relative metrics, trend detection, session classification. |
| `report.py` | Formats profile + metrics + classification into a readable report. |
| `main.py` | Wires it all together; run this. |
| `test_analyzer.py` | Unit tests for validation and classification (no pytest needed). |

## Clone and Run  

```bash
git clone https://github.com/maxfinanger/Assignment1FitnessTracker
cd Assignment1FitnessTracker
python3 main.py            # prints a report for every documented scenario
python3 test_analyzer.py   # runs the unit tests
```

## Report

- **Separation of concerns**: generation (given) → typed objects (`models.py`)
  → validation (`validation.py`) → analysis (`analysis.py`) → presentation
  (`report.py`). Each stage can be tested and changed independently.
- **Nothing is silently dropped**: every observation gets a
  `ValidatedObservation` with `is_valid` and a list of `issues`, so the
  report can always state how much data was usable and why the rest wasn't.
- **Low signal quality is a soft flag, not a hard rejection**: a reading
  with a plausible value but a low `signal_quality` is kept but marked as
  less trustworthy, whereas missing or physically impossible values are
  hard-rejected. This distinction is worth explaining/justifying in the report.
- **Classification is threshold-based and explainable**: `analysis.py`
  derives session-level features (average heart-rate delta from personal
  baseline, average activity level, a least-squares heart-rate trend) and
  compares them against named, adjustable constants rather than hidden
  numbers, and it always returns a one-line `reasoning` string.
- **Data-quality gating comes first**: if too many observations are invalid
  or average signal quality is too low, the analyzer reports
  `poor_data_quality` instead of guessing at an activity level from
  untrustworthy numbers.
