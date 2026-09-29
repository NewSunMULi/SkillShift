"""自动可靠性系统的探测器接管入口。 / Rover takeover entry point for autonomous reliability systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .execution import SkillExecutor
from .models import Context, LogEntry, StepResult
from .reliability.contracts import Decision, ReliabilitySystem


@dataclass(frozen=True)
class AgentStepResult:
    """同时保留评测决策和物理执行结果。 / Preserve both evaluation decision and physical result."""

    decision: Decision
    execution: StepResult


@dataclass(frozen=True)
class AutonomousRoverAgent:
    """连接可靠性决策与执行，但不关心模型供应商。

    Connect reliability decisions to execution without knowing the model provider.
    """

    executor: SkillExecutor
    system: ReliabilitySystem

    def run_step(
        self,
        *,
        time: int,
        phase: int,
        context: Context,
        logs: Sequence[LogEntry] = (),
    ) -> AgentStepResult:
        # 隐藏阶段只传给模拟器；可靠性系统只能看到上下文和观测日志。
        # The hidden phase reaches only the simulator; the system sees context and logs.
        decision = self.system.decide(context, tuple(logs))
        execution = self.executor.execute(
            time=time, phase=phase, skill=decision.chosen_skill, context=context,
        )
        return AgentStepResult(decision, execution)
