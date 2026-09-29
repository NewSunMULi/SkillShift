"""Shared ground-truth construction and metrics for experiments 1 and 2."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Protocol, Sequence

from .contracts import ReliabilityAssessment
from .stream import FrozenObservationStream
from ..rover.models import LogEntry
from ..rover.simulator import MarsReliabilitySimulator
from ..rover.skills import SKILL_NAMES


class AssessmentSystem(Protocol):
    def assess(self, checkpoint: int, logs: Sequence[LogEntry]) -> ReliabilityAssessment: ...


def empty_assessment(checkpoint: int) -> ReliabilityAssessment:
    flags = {skill: False for skill in SKILL_NAMES}
    regions = {skill: () for skill in SKILL_NAMES}
    return ReliabilityAssessment(checkpoint, flags.copy(), flags.copy(), regions.copy(), regions.copy(), regions.copy())


@dataclass(frozen=True)
class ExperimentRun:
    assessments: dict[int, ReliabilityAssessment]
    invalid_outputs: tuple[dict[str, object], ...]


def run_assessments(
    system: AssessmentSystem, logs: Sequence[LogEntry], checkpoints: Sequence[int]
) -> ExperimentRun:
    results: dict[int, ReliabilityAssessment] = {}
    invalid: list[dict[str, object]] = []
    for checkpoint in checkpoints:
        try:
            results[checkpoint] = system.assess(checkpoint, logs[:checkpoint])
        except (ValueError, RuntimeError) as exc:
            results[checkpoint] = empty_assessment(checkpoint)
            invalid.append({"checkpoint": checkpoint, "error": str(exc)})
    return ExperimentRun(results, tuple(invalid))


def truth_regions(
    simulator: MarsReliabilitySimulator, previous: int, current: int, eta: float,
) -> dict[str, dict[str, frozenset[str]]]:
    truth: dict[str, dict[str, frozenset[str]]] = {}
    for skill in SKILL_NAMES:
        old = {
            context.id for context in simulator.contexts
            if simulator.is_applicable(previous, skill, context)
        }
        new = {
            context.id for context in simulator.contexts
            if simulator.is_applicable(current, skill, context)
        }
        truth[skill] = {
            "changed": frozenset(
                context.id for context in simulator.contexts
                if abs(
                    simulator.probability(current, skill, context)
                    - simulator.probability(previous, skill, context)
                ) >= eta
            ),
            "failed": frozenset(old - new),
            "gained": frozenset(new - old),
            "applicability": frozenset(old ^ new),
        }
    return truth


def detection_report(
    simulator: MarsReliabilitySimulator, stream: FrozenObservationStream,
    assessments: dict[int, ReliabilityAssessment], eta: float,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    boundaries = stream.schedule.change_points[1:]
    phase_length = stream.observations_per_phase
    for boundary_index, boundary in enumerate(boundaries, start=2):
        end = boundary + phase_length
        truth = truth_regions(simulator, boundary_index - 1, boundary_index, eta)
        points = [point for point in stream.checkpoints() if boundary < point <= end]
        for layer, alarm_field, region_name in (
            ("probability", "alarm_probability", "changed"),
            ("applicability", "alarm_applicability", "applicability"),
        ):
            for skill in SKILL_NAMES:
                positive = bool(truth[skill][region_name])
                alarms = [
                    point for point in points
                    if getattr(assessments[point], alarm_field)[skill]
                ]
                first = alarms[0] if alarms else None
                rows.append({
                    "phase": boundary_index, "boundary": boundary, "layer": layer,
                    "skill": skill, "positive": positive,
                    "detected": positive and first is not None,
                    "delay": first - boundary if positive and first is not None else None,
                    "censored_at": phase_length if positive and first is None else None,
                    "false_alarm_checkpoints": len(alarms) if not positive else 0,
                    "negative_checkpoints": len(points) if not positive else 0,
                })
    summary: dict[str, dict[str, float | int | None]] = {}
    for layer in ("probability", "applicability"):
        selected = [row for row in rows if row["layer"] == layer]
        positives = [row for row in selected if row["positive"]]
        negatives = [row for row in selected if not row["positive"]]
        delays = [int(row["delay"]) for row in positives if row["delay"] is not None]
        negative_points = sum(int(row["negative_checkpoints"]) for row in negatives)
        summary[layer] = {
            "events": len(positives),
            "event_recall": sum(bool(row["detected"]) for row in positives) / len(positives) if positives else 1.0,
            "miss_rate": sum(not bool(row["detected"]) for row in positives) / len(positives) if positives else 0.0,
            "conditional_mean_delay": mean(delays) if delays else None,
            "false_alarms_per_1000_negative_checkpoints": (
                1000 * sum(int(row["false_alarm_checkpoints"]) for row in negatives) / negative_points
                if negative_points else 0.0
            ),
        }
    return {"summary": summary, "rows": rows}


def _region_scores(predicted: frozenset[str], actual: frozenset[str]) -> dict[str, float]:
    if not actual:
        return {"iou": 0.0, "precision": 0.0, "recall": 0.0}
    intersection = len(predicted & actual)
    return {
        "iou": intersection / len(predicted | actual) if predicted | actual else 0.0,
        "precision": intersection / len(predicted) if predicted else 0.0,
        "recall": intersection / len(actual),
    }


def localization_report(
    simulator: MarsReliabilitySimulator, stream: FrozenObservationStream,
    assessments: dict[int, ReliabilityAssessment], eta: float,
    horizons: tuple[int, ...] = (100, 300, 900),
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    field_names = {"changed": "changed_contexts", "failed": "failed_contexts", "gained": "gained_contexts"}
    for phase, boundary in enumerate(stream.schedule.change_points[1:], start=2):
        truth = truth_regions(simulator, phase - 1, phase, eta)
        for horizon in horizons:
            checkpoint = boundary + horizon
            if checkpoint not in assessments or checkpoint > boundary + stream.observations_per_phase:
                continue
            assessment = assessments[checkpoint]
            for skill in SKILL_NAMES:
                for region, field_name in field_names.items():
                    actual = truth[skill][region]
                    predicted = frozenset(getattr(assessment, field_name)[skill])
                    alarm = assessment.alarm_probability[skill]
                    if not alarm:
                        predicted = frozenset()
                    if actual:
                        rows.append({
                            "phase": phase, "horizon": horizon, "skill": skill, "region": region,
                            "truth_size": len(actual), "predicted_size": len(predicted),
                            **_region_scores(predicted, actual),
                        })
                    else:
                        rows.append({
                            "phase": phase, "horizon": horizon, "skill": skill, "region": region,
                            "truth_size": 0, "predicted_size": len(predicted), "iou": None,
                            "precision": None, "recall": None,
                            "empty_set_correct": not predicted,
                        })
    positives = [row for row in rows if row["truth_size"]]
    summary = {}
    for region in field_names:
        selected = [row for row in positives if row["region"] == region]
        summary[region] = {
            metric: mean(float(row[metric]) for row in selected) if selected else None
            for metric in ("iou", "precision", "recall")
        }
    negatives = [row for row in rows if not row["truth_size"]]
    summary["negative_regions"] = {
        "empty_set_accuracy": mean(bool(row["empty_set_correct"]) for row in negatives) if negatives else 1.0,
        "mean_predicted_size": mean(int(row["predicted_size"]) for row in negatives) if negatives else 0.0,
    }
    return {"summary": summary, "rows": rows}
