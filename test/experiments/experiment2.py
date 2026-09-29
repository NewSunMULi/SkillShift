"""Experiment 2 orchestration: changed-region localization."""

from __future__ import annotations

from ..evaluation.metrics import localization_report
from ..evaluation.session import EvaluationSession


def run_experiment(
    session: EvaluationSession, *, eta: float = 0.1,
    horizons: tuple[int, ...] = (100, 300, 900),
) -> dict[str, object]:
    """Score localization predictions from an already executed shared session."""
    return localization_report(
        session.simulator, session.stream, session.run.assessments, eta, horizons,
    )
