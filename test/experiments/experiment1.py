"""Experiment 1 orchestration: skill-level change detection."""

from __future__ import annotations

from ..evaluation.metrics import detection_report
from ..evaluation.session import EvaluationSession


def run_experiment(session: EvaluationSession, *, eta: float = 0.1) -> dict[str, object]:
    """Score detection predictions from an already executed shared session."""
    return detection_report(session.simulator, session.stream, session.run.assessments, eta)
