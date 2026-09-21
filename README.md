# Smart Fitness Session Analyzer

**Student:** *Max Dyrø Finanger*
**Student number:** *409915*

---

## 1. Description

This program simulates the analysis of training data from smart watches or other training devices, and generate reports based in that data. This program structures and organizes the raw data into the different participants and their sessions, it validates every measurement and compares the sessions against the participants reference values. It classifies the sessions intensity, and detects if the participants is in a recovery, and all the sessions are printed showing the summary and its conclusion.

The program can run five scenarios end to end: a resting session, a moderate session, a hard session, a session followed by recovery, and a session where the sensor data is unusable.

The measurement data comes from the instructor-supplied `data_generator.py`, which is included and unmodified.

I have used Claude as a tool when developing this assignment, I used it to help me implement the initial solution and as a tool to further improve the solution to fulfill all the criteria set for this assignment. 

---

## 2. Installation and running

```bash
git clone https://github.com/maxfinanger/Assignment1FitnessTracker
cd Assignment1FitnessTracker
python3 main.py
```

On systems where the interpreter is called `python` rather than `python3`, use:

```bash
python main.py
```

To run the test suite:

```bash
python3 tests.py
```

No additional packages are needed, the project only uses the Python standard
library (`random`, `statistics`, `typing`). `requirements.txt` formally says this, I have not added the usual `install requirements.txt.` since there is nothing in that file except for a comment explaining it.

---

## 3. Repository structure

| File | Responsibility |
|---|---|
| `main.py` | Entry point. Runs all five scenarios and prints the reports and a summary table. |
| `models.py` | The object model: `ParticipantProfile`, `BaseObservation`, `FitnessObservation`, `TrainingSession`. |
| `analysis.py` | Standalone functions for validation auditing, summaries, baseline comparison, recovery detection and classification. |
| `reporting.py` | Standalone functions that turn a result dictionary into console output. |
| `sample_data.py` | Scenario definitions and the bridge between the generator and the object model. |
| `tests.py` | 40 tests covering the object model, validation, calculations and all five scenarios. |
| `data_generator.py` | Instructor-supplied, unmodified. |
| `requirements.txt` | States that only the standard library is used. |

This differs from the suggested layout. The analysis, presentation and object model are separated in three separate files rather than inside `main.py`. The reason is that the three concerns change for different reasons. A new classification rule, a change to the report layout, and a new measurement field are three unrelated edits. Keeping them apart means each can be changed and tested without risk to the others. In my experience larger files becomes cluttered and harder to read, therefore im in the habit of separating files i deem can grow too large. `main.py` remains the single entry point and the program runs from the repository root with no path changes.

---

## 4. Class design

### `ParticipantProfile` — who the measurements belong to

Holds one participant's identifier and their three personal reference values
(resting heart rate, skin response and temperature). Its single responsibility is to
be the fixed point that every later comparison is made against.

### `BaseObservation` — one measurement window from any sensor

Knows only what *every* wearable measurement window has: when it was taken
(`timestamp`) and how much the device trusted the reading (`signal_quality`). It can
validate those two fields, report whether the reading is trustworthy, and serialize
itself.

### `FitnessObservation(BaseObservation)` — one fitness measurement window

Adds the fitness specific fields: heart rate, skin response, temperature and activity level. It extends the base class's validation and serialization rather than replacing them.

### `TrainingSession` — a participant's complete session

Owns one `ParticipantProfile` and an ordered list of `FitnessObservation` objects,
and guards how observations are added. This is where the individual windows stop
being loose numbers and become a session belonging to a specific person.

---

## 5. Where the OOP concepts appear

### Composition — `TrainingSession`

`TrainingSession` is composed of a `ParticipantProfile` and a list of
`FitnessObservation` objects:

```python
self._participant = participant
self._observations: List[FitnessObservation] = []
```

This is composition rather than inheritance because a session **has** a participant
and **has** observations, but it is not a kind of either. The relationship is strong in both directions. The observations are created for the session and have no
independent life outside it, and a session cannot meaningfully exist without a
participant, which is why the constructor refuses to build one without a valid
`ParticipantProfile`.

### Encapsulation — protected attributes behind properties

`ParticipantProfile` stores baselines as `_baseline_heart_rate` etc, exposing them only through read only properties. Baselines are the reference point for every calculation in the program. Allowing other code to reassign them mid analysis would silently invalidate results that still looked perfectly plausible.

`TrainingSession` protects its observation list the same way. The `observations`
property returns a **copy**, so external code cannot append to, reorder or empty the
session's internal list:

```python
@property
def observations(self) -> List[FitnessObservation]:
    """A copy, so callers cannot mutate the session's internal list."""
    return list(self._observations)
```

The only route in is `add_observation()`, which rejects anything that is not a
`FitnessObservation` and keeps the list ordered by timestamp. Ordering the
recovery check depends on being correct.

### Inheritance and overriding — `BaseObservation` → `FitnessObservation`

The split reflects a real distinction: *every* sensor window has a timestamp and a
signal quality, but only a fitness window has a heart rate. Putting the shared
concepts in a base class means a future observation type (ex. a sleep parameter) would inherit the timestamp and signal quality handling.

`FitnessObservation` overrides two methods, and in both cases **extends** the parent
via `super()` rather than replacing it:

```python
def validate(self) -> List[str]:
    """Extend the base checks with the fitness specific field rules."""
    issues = super().validate()          # shared signal quality rules
    issues.extend(self._check_bounded("heart_rate", self.heart_rate, HEART_RATE_BOUNDS))
    ...
```

The signal quality rule is written once, in one place, and cannot drift out of step between observation types. `tests.py` locks the behavior in with `test_subclass_extends_rather_than_replaces_validation`, which checks that a bad
signal quality value on a `FitnessObservation` is still caught by the inherited rule.

### Class and static methods

| Method | Type | Why |
|---|---|---|
| `TrainingSession.from_generator_output()` | `classmethod` | An alternative constructor. It is the single place that knows how the generator's raw output maps onto the object model, so a change of data source touches one method. |
| `ParticipantProfile.from_dict()` / `FitnessObservation.from_dict()` | `classmethod` | Same reasoning at the level of individual objects: the dictionary key names appear once each. |
| `TrainingSession.summarize()` | `staticmethod` | A pure calculation over a list of numbers, returning average/minimum/maximum. It needs nothing from a particular session, so binding it to an instance would be misleading — and as a static method it can be tested directly on its own. |
| `FitnessObservation._check_bounded()` / `._check_non_negative()` | `staticmethod` | Field checking helpers that depend only on their arguments. Keeping them static makes the bounds logic reusable across fields and independently testable. |

### Standalone functions

Calculations, validation and presentation live in module level functions rather than
methods, because each is a self contained operation on data passed in:

- `audit_data_quality()` — validate every window and report what was usable
- `summarize_measurements()` — average, minimum and maximum per field
- `compare_with_baseline()` — express the session relative to personal references
- `detect_recovery()` — test for decline towards the end of the session
- `classify_session()` — apply the classification rules
- `analyze_session()` — run the pipeline and assemble the result dictionary
- `build_report()`, `format_measurement()`, `format_data_quality()`, `format_rejections()` — presentation

### Lists and dictionaries

Sessions hold a `list` of observations; validation issues accumulate in `list`s;
`DEMO_SCENARIOS` is a list of dictionaries; and the whole analysis result is returned as a nested `dict`.

---

## 6. Validation rules and assumptions

Every window is checked field by field, and **all** problems are reported rather than just the first, so the report can explain exactly why a window was dropped.

| Field | Rule |
|---|---|
| `timestamp` | Integer, 0 or greater. Enforced in the constructor — a window without a position in time cannot be built at all. |
| `heart_rate` | Present, numeric, 30–220 bpm |
| `temperature` | Present, numeric, 25–42 °C |
| `activity_level` | Present, numeric, 0–1 |
| `skin_response` | Present, numeric, not negative |
| `signal_quality` | Present, numeric, 0–1 |

**Assumptions and decisions:**

- **Bounds are slightly wider than the documented "normal" ranges.**
  `DATA_DESCRIPTION.md` gives heart rate as normally 35–205 bpm; this program rejects outside 30–220. The documented range describes what the generator usually produces, not what is physiologically possible, so widening it slightly avoids discarding genuine extremes while still catching impossible readings such as the 265 bpm the poor quality scenario injects.

- **Low signal quality is a warning, not a rejection.** A reading with a plausible
  value but a signal quality of 0.2 is kept and listed under "low confidence", not
  discarded. A weak signal makes a reading *less trustworthy*; it does not make it
  *wrong*. Throwing such windows away individually would discard usable information,
  so the program instead handles the problem at session level: if average signal
  quality across the session falls below 0.60, the whole session is declared
  unclassifiable. This keeps a single weak window from being dramatic, while a
  session wide quality collapse is still caught.

- **`True` is not a number.** Python treats `bool` as a subclass of `int`, so a stray `True` would otherwise pass as a heart rate of 1. The numeric check excludes it explicitly.

- **Boundary values are valid.** An activity level of exactly 0.0 or 1.0, or a
  temperature of exactly 42 °C, is accepted. The documented ranges are inclusive.

- **Everything is relative to the individual.** No absolute heart rate thresholds are used anywhere. 95 bpm is hard work for one person and an easy walk for another, so all rules operate on the difference from that participant's own baseline.

---

## 7. Classification rules

The result of `analyze_session()` is a single structured dictionary:

```python
{
    "participant":         {...},   # the profile's reference values
    "scenario":            "recovery",
    "data_quality":        {...},   # counts, invalid fraction, rejections with reasons
    "summaries":           {...},   # average / minimum / maximum per field
    "baseline_comparison": {...},   # deltas from the participant's own baseline
    "recovery":            {...},   # whether measurements fall at the end, and by how much
    "classification":      {"label": ..., "explanation": ...},
}
```

Rules are applied **in this order**, and the order is part of the design:

**1 — `insufficient_data`** if fewer than 3 windows are usable, *or* more than 30% were rejected, *or* average signal quality is below 0.60.

This gate runs first deliberately. An intensity label computed from mostly-unusable
windows would look just as authoritative as a real one while resting on nothing, so
the program refuses to produce one rather than guessing.

**2 — `recovering`** if heart rate fell at least 12 bpm and activity fell at least 0.10 from the session's peak to its closing block, *and* closing activity is below 0.65.

Recovery is checked before the intensity rules because a recovering session can sit at almost any average intensity. Its average is a blend of the hard part and the calm part. So the level based rules below would otherwise mislabel it.

**3 — `resting`** if heart rate is at most 10 bpm above baseline and activity is at
most 0.25.

**4 — `high_activity`** if heart rate is at least 45 bpm above baseline and activity is at least 0.65.

**5 — `moderate_activity`** if heart rate is at least 15 bpm above baseline and
activity is at least 0.30.

**6 — `uncertain`** otherwise. Rather than forcing a borderline session into the
nearest label, the program says so and reports the numbers.

### How recovery is detected

The assignment asks whether measurements decline *near the end* of a session, so the
program compares the **closing block** of windows against the **highest sustained
earlier block**, where a block is one third of the usable windows.

Alternatively comparing the first third against the last third was tried first and rejected, because it misses the most typical recovery shape of all: a session that starts calm, climbs to a peak, then falls away. There the first and last thirds can have *identical* averages while an obvious recovery sits in between.
`test_recovery_beats_a_flat_overall_average` in `tests.py` is exactly that case, and it fails against the first third method.

A block average is used rather than a single peak reading so that one noisy spike
cannot masquerade as a peak of effort. The third condition is that closing activity must be below 0.65, was added after testing showed that hard sessions which merely dipped slightly at the end were being called recovery. A hard session that tapers a little is still a hard session, the participant must have eased off.

### Threshold origins

The thresholds are drawn from the documented ranges in `DATA_DESCRIPTION.md` and from normal exercise physiology, **not** reverse engineered from the generator's internal constants. The generator does not reveal its labels, and reading its source to match them would produce a program that classifies nothing and merely recognizes one particular data source. They are named constants at the top of `analysis.py` so they can be inspected and adjusted in one place.

Testing across 300 seeds per scenario (1500 sessions) classifies every one correctly.

---

## 8. Example output

`python3 main.py` prints a full report for each of the five scenarios.

```
==================================================================
SESSION REPORT  |  participant P004
scenario: recovery
==================================================================

PERSONAL REFERENCE VALUES
  heart rate:    78.0 bpm
  skin response: 1.17
  temperature:   32.76 C

DATA QUALITY
  windows received:   12
  windows usable:     12
  rejected:           0%
  avg signal quality: 0.91

MEASUREMENT SUMMARIES
  heart rate:        avg 112.83 bpm   min 86 bpm   max 141 bpm
  skin response:     avg 1.57   min 1.22   max 1.93
  temperature:       avg 33.05 C   min 32.81 C   max 33.34 C
  activity level:    avg 0.48   min 0.1   max 0.88

COMPARED WITH PERSONAL BASELINE
  heart rate:     +34.83 bpm
  skin response:  +0.40
  temperature:    +0.29 C
  activity level: 0.48

RECOVERY CHECK
  recovering: yes
  heart rate fell 39.75 bpm and movement fell 0.6 from the session peak
  to the final 4 window(s)

CLASSIFICATION
  RECOVERING
  Measurements decline towards the end of the session: heart rate fell
  39.75 bpm and movement fell 0.6 from the session peak to the final 4
  window(s). Average heart rate was +34.8 bpm relative to baseline.
==================================================================
```

The invalid-data scenario reports every rejected window and why:

```
DATA QUALITY
  windows received:   12
  windows usable:     0
  rejected:           100%
  avg signal quality: 0.287

REJECTED WINDOWS
  t=0: heart_rate is missing
  t=1: heart_rate 265 outside plausible range 30.0-220.0
  t=2: activity_level -0.2 outside plausible range 0.0-1.0
  t=3: skin_response is missing
  ...

CLASSIFICATION
  INSUFFICIENT_DATA
  Only 0 of 12 windows were usable and average signal quality was 0.287.
  The session cannot be classified reliably.
```

Every run ends with a summary table:

```
==================================================================
SUMMARY OF ALL SCENARIOS
==================================================================
scenario            participant   usable    classification
------------------------------------------------------------------
resting             P001          12/12     resting
moderate_activity   P002          12/12     moderate_activity
high_activity       P003          12/12     high_activity
recovery            P004          12/12     recovering
poor_quality        P005          0/12      insufficient_data
==================================================================
```

---

## 9. Testing

`python3 tests.py` runs 40 tests with no third party test runner. They are grouped
into four areas:

- **Object model** — read only baselines, protected observation list, type checking on `add_observation()`, timestamp ordering, that `FitnessObservation` extends
  `BaseObservation`, and that overriding extends rather than replaces the parent.
- **Validation** — missing values, impossible values, negative movement, booleans
  rejected as numbers, boundary values accepted, low signal quality flagged but not
  rejected.
- **Calculations** — average/minimum/maximum including with missing values, baseline
  comparison, and four recovery cases: a declining session, a steady session, a
  too short session, the "climb then drop" case, and a hard session that only dips.
- **End to end** — all five scenarios classify correctly, the result is a dictionary
  with every expected section, the quality gate runs before the intensity rules, an
  empty session does not crash, and the labels hold across several different seeds.

---

## 10. Known limitations

- **Thresholds are hand set, not learned.** They classify all 1500 test sessions
  correctly, but they are tuned against one simulated data source. Real wearable data would need them reexamined against labelled sessions.

- **Recovery needs at least three usable windows** and compares thirds of the session. On a very short session the blocks become one window each and the      detection is correspondingly noisy.

- **Interval splitting is crude.** A session containing repeated hard/easy intervals
  may be labelled `recovering` if it happens to end on an easy interval, or
  `uncertain` if the averages fall between categories. Detecting interval structure
  would need per window segmentation rather than session level averages.

- **A single measurement drives rejection.** A window is dropped if *any* field is
  invalid, even when the remaining fields are fine. Partial use of damaged windows
  (for example, using a valid heart rate from a window whose temperature is missing)
  would recover more data, at the cost of more complicated bookkeeping.

- **Skin response and temperature are reported but do not affect classification.**
  Both are summarized and compared against baseline, but the rules use only heart rate and activity level, because the relationship between skin response and exercise intensity is too participant dependent to threshold confidently on simulated data.

- **No persistence.** Results are printed and discarded. The dictionary form of the
  result was chosen partly so that writing it to JSON later would be straightforward.