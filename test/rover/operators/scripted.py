"""自定义 Python 策略操作。 / Custom Python strategy operation."""

from __future__ import annotations

from typing import Callable, Sequence

from ..execution import SkillExecutor
from ..models import Context, LogEntry, StepResult


ScriptStrategy = Callable[[Context, Sequence[LogEntry], tuple[str, ...]], str]


class ScriptedOperator:
    """执行用户注入的策略函数。 / Execute a user-injected strategy function."""

    def __init__(self, executor: SkillExecutor, strategy: ScriptStrategy):
        if not callable(strategy):
            raise TypeError("strategy must be callable")
        self.executor = executor
        self.strategy = strategy

    def run_step(
        self,
        *,
        time: int,
        phase: int,
        context: Context,
        logs: Sequence[LogEntry] = (),
    ) -> StepResult:
        skill = self.strategy(context, tuple(logs), self.executor.available_skills)
        return self.executor.execute(time=time, phase=phase, skill=skill, context=context)
