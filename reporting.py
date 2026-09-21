"""Presentation functions: turn a result dictionary into a console report.

Formatting is kept entirely separate from analysis so that the rules can be
changed without touching the layout, and the layout without risking the
numbers.
"""

from typing import Dict, Optional

LINE_WIDTH = 66


def format_measurement(name: str, summary: Optional[Dict], unit: str = "") -> str:
    """Format one average/minimum/maximum row, or note that it is unavailable."""
    label = name.replace("_", " ") + ":"
    if summary is None:
        return f"  {label:<18} no usable data"
    suffix = f" {unit}" if unit else ""
    return (
        f"  {label:<18} avg {summary['average']}{suffix}"
        f"   min {summary['minimum']}{suffix}   max {summary['maximum']}{suffix}"
    )


def format_data_quality(quality: Dict) -> str:
    lines = [
        f"  windows received:   {quality['total_observations']}",
        f"  windows usable:     {quality['usable_observations']}",
        f"  rejected:           {quality['invalid_fraction']:.0%}",
    ]
    if quality["average_signal_quality"] is not None:
        lines.append(f"  avg signal quality: {quality['average_signal_quality']}")
    if quality["low_confidence_timestamps"]:
        stamps = ", ".join(str(t) for t in quality["low_confidence_timestamps"])
        lines.append(f"  low confidence at:  t={stamps}")
    return "\n".join(lines)


def format_rejections(quality: Dict) -> str:
    """List every rejected window and why it was rejected."""
    if not quality["rejected_observations"]:
        return "  none"
    lines = []
    for entry in quality["rejected_observations"]:
        lines.append(f"  t={entry['timestamp']}: {'; '.join(entry['issues'])}")
    return "\n".join(lines)


def build_report(result: Dict) -> str:
    """Render a complete, readable console report for one analysed session."""
    participant = result["participant"]
    comparison = result["baseline_comparison"]
    recovery = result["recovery"]
    classification = result["classification"]

    lines = []
    lines.append("=" * LINE_WIDTH)
    lines.append(f"SESSION REPORT  |  participant {participant['participant_id']}")
    lines.append(f"scenario: {result['scenario']}")
    lines.append("=" * LINE_WIDTH)

    lines.append("")
    lines.append("PERSONAL REFERENCE VALUES")
    lines.append(f"  heart rate:    {participant['baseline_heart_rate']} bpm")
    lines.append(f"  skin response: {participant['baseline_skin_response']}")
    lines.append(f"  temperature:   {participant['baseline_temperature']} C")

    lines.append("")
    lines.append("DATA QUALITY")
    lines.append(format_data_quality(result["data_quality"]))

    if result["data_quality"]["rejected_observations"]:
        lines.append("")
        lines.append("REJECTED WINDOWS")
        lines.append(format_rejections(result["data_quality"]))

    lines.append("")
    lines.append("MEASUREMENT SUMMARIES")
    summaries = result["summaries"]
    lines.append(format_measurement("heart rate", summaries["heart_rate"], "bpm"))
    lines.append(format_measurement("skin response", summaries["skin_response"]))
    lines.append(format_measurement("temperature", summaries["temperature"], "C"))
    lines.append(format_measurement("activity level", summaries["activity_level"]))

    lines.append("")
    lines.append("COMPARED WITH PERSONAL BASELINE")
    if comparison["heart_rate_delta"] is None:
        lines.append("  no usable data to compare")
    else:
        lines.append(f"  heart rate:     {comparison['heart_rate_delta']:+.2f} bpm")
        lines.append(f"  skin response:  {comparison['skin_response_delta']:+.2f}")
        lines.append(f"  temperature:    {comparison['temperature_delta']:+.2f} C")
        lines.append(f"  activity level: {comparison['average_activity_level']:.2f}")

    lines.append("")
    lines.append("RECOVERY CHECK")
    if recovery["heart_rate_drop"] is None:
        lines.append(f"  {recovery['reason']}")
    else:
        lines.append(f"  recovering: {'yes' if recovery['is_recovering'] else 'no'}")
        lines.append(f"  {recovery['reason']}")

    lines.append("")
    lines.append("CLASSIFICATION")
    lines.append(f"  {classification['label'].upper()}")
    lines.append(f"  {classification['explanation']}")
    lines.append("=" * LINE_WIDTH)

    return "\n".join(lines)
