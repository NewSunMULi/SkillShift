"""可靠性实验的参考系统。 / Reference systems for reliability experiments."""

import random
from typing import Protocol, Sequence

from ..models import Context, LogEntry
from ..skills import SKILL_NAMES
from .contracts import Decision


class ProbabilityProvider(Protocol):
    def probability(self, phase: int, skill: str, context: Context) -> float: ...


class OracleSystem:
    """知道隐藏真值的评估上界。 / Evaluation upper bound that knows hidden truth."""

    def __init__(self, simulator: ProbabilityProvider, phase: int):
        self.simulator, self.phase = simulator, phase

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision:
        estimates = {skill: self.simulator.probability(self.phase, skill, context) for skill in SKILL_NAMES}
        return Decision(False, (), (), estimates, max(estimates, key=estimates.get), False)


class RandomSystem:
    """使用隔离随机源的随机基线。 / Random baseline with an isolated RNG."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision:
        return Decision(False, (), (), {}, self.rng.choice(SKILL_NAMES), False)


class FixedSystem:
    """始终复用第一阶段知识的静态基线。 / Static baseline that always reuses phase-one knowledge."""

    def __init__(self, simulator: ProbabilityProvider):
        self.simulator = simulator

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision:
        estimates = {skill: self.simulator.probability(1, skill, context) for skill in SKILL_NAMES}
        return Decision(False, (), (), estimates, max(estimates, key=estimates.get), False)
