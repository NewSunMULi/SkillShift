"""基于 Beta 后验下置信界的可靠性系统。 / Beta-posterior lower-confidence system."""

import math
from typing import Sequence

from ..models import Context, LogEntry
from ..skills import SKILL_NAMES
from .contracts import Decision


class BetaLCBSystem:
    """优先选择可靠性下界最高的技能。 / Select the skill with the highest reliability lower bound."""

    def __init__(self, confidence_scale: float = 1.0):
        if confidence_scale < 0:
            raise ValueError("confidence_scale must be non-negative")
        self.scale = confidence_scale

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision:
        estimates: dict[str, float] = {}
        lower_bounds: dict[str, float] = {}
        for skill in SKILL_NAMES:
            matching = [entry for entry in logs if entry.skill == skill and entry.context_id == context.id]
            successes = sum(entry.success for entry in matching)
            alpha, beta = 1 + successes, 1 + len(matching) - successes
            mean = alpha / (alpha + beta)
            variance = alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1))
            estimates[skill] = mean
            lower_bounds[skill] = max(0.0, mean - self.scale * math.sqrt(variance))
        chosen = max(lower_bounds, key=lower_bounds.get)
        return Decision(False, (), (), estimates, chosen, not bool(logs))
