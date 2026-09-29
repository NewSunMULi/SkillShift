"""Build one shared assessment session consumed by experiments 1 and 2."""

from __future__ import annotations

from dataclasses import dataclass

from .dify import DifyAssessmentSystem, DifyWorkflowClient, DifyWorkflowConfig
from .metrics import ExperimentRun, run_assessments
from .stream import FrozenObservationStream
from .systems import OracleAssessmentSystem, WindowedIdBaseline
from ..rover.simulator import MarsReliabilitySimulator


@dataclass(frozen=True)
class EvaluationSession:
    simulator: MarsReliabilitySimulator
    stream: FrozenObservationStream
    run: ExperimentRun
    configuration: dict[str, object]


def build_session(
    *, system_name: str = "id-baseline", seed: int = 20260927, eta: float = 0.1,
    dify_config: DifyWorkflowConfig | None = None, memory_log_limit: int = 2000,
) -> EvaluationSession:
    """Run a system once so experiments 1 and 2 score identical predictions."""
    simulator = MarsReliabilitySimulator(seed)
    stream = FrozenObservationStream(seed=seed)
    logs = stream.generate(simulator)
    if system_name == "oracle":
        system = OracleAssessmentSystem(simulator, stream.schedule, eta)
        model_label = "oracle"
    elif system_name == "id-baseline":
        system = WindowedIdBaseline()
        model_label = "windowed-id-baseline"
    elif system_name == "dify":
        config = dify_config or DifyWorkflowConfig.from_env()
        system = DifyAssessmentSystem(
            DifyWorkflowClient(config), simulator.contexts, memory_log_limit=memory_log_limit,
        )
        model_label = config.model_label
    else:
        raise ValueError(f"unknown system: {system_name}")
    run = run_assessments(system, logs, stream.checkpoints())
    configuration = {
        "system": system_name, "model_label": model_label, "seed": seed, "eta": eta,
        "observations_per_phase": stream.observations_per_phase,
        "checkpoint_interval": stream.checkpoint_interval,
        "memory_log_limit": memory_log_limit if system_name == "dify" else None,
    }
    return EvaluationSession(simulator, stream, run, configuration)
