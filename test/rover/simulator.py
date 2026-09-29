"""探测器执行与状态转移模拟器。 / Rover execution and state-transition simulator."""

from __future__ import annotations

import random
from typing import Iterable, Sequence

from test.benchmark.oracle import ProbabilityOracle
from test.environment import PhaseSchedule

from .context_factory import generalization_contexts, standard_contexts
from .models import Context, LogEntry, StepResult
from .skills import SKILL_NAMES, SkillCatalog


class MarsReliabilitySimulator:
    """使用独立随机数生成器的六阶段模拟器。 / Six-phase simulator with an isolated RNG."""

    def __init__(self, seed: int = 20260927):
        self.seed = seed
        self.rng = random.Random(seed)
        self.skill_catalog = SkillCatalog()
        self.skills = tuple(self.skill_catalog)
        self.contexts = standard_contexts()
        self.generalization_contexts = generalization_contexts()
        self._oracle = ProbabilityOracle(self.skill_catalog)

    def probability(self, phase: int, skill: str, context: Context) -> float:
        """兼容用评估接口；在线控制代码不应调用。 / Compatibility oracle; online code must not call it."""
        return self._oracle.probability(phase, skill, context)

    def is_applicable(self, phase: int, skill: str, context: Context) -> bool:
        return self._oracle.is_applicable(phase, skill, context)

    def execute(self, time: int, phase: int, skill: str, context: Context) -> LogEntry:
        definition = self.skill_catalog.require(skill)
        probability = self.probability(phase, skill, context)
        success = self.rng.random() < probability
        # 第五阶段只改变代价，刻意不干扰成功概率。
        # Phase five changes cost only, deliberately leaving success probability untouched.
        cost = definition.execution_cost * (1.5 if phase == 5 else 1.0)
        return LogEntry(time, skill, context.id, success, cost + (0.0 if success else 2.0))

    def step(self, time: int, phase: int, skill: str, context: Context) -> StepResult:
        """执行技能并应用安全相关状态转移。 / Execute a skill and apply safety-related transitions."""
        observation = self.execute(time, phase, skill, context)
        hazardous = (
            "cold" in context.env_tags
            and context.state in {"low_battery", "critical_battery", "heater_fault"}
            and skill in {"move", "drill", "sample"}
        )
        damaged = hazardous and (not observation.success or self.rng.random() < 0.35)
        next_state = (
            "wheel_worn" if damaged and skill == "move"
            else "arm_degraded" if damaged
            else context.state
        )
        next_context = Context(
            f"dynamic-{time + 1}", context.environment, next_state,
            context.env_tags, context.held_out,
        )
        return StepResult(observation, next_context, damaged)

    def stream(self, count: int, schedule: PhaseSchedule | None = None) -> list[LogEntry]:
        """生成不含隐藏阶段标签的观测流。 / Generate observations without hidden phase labels."""
        if count < 0:
            raise ValueError("count must be non-negative")
        active_schedule = schedule or PhaseSchedule()
        return [
            self.execute(
                time, active_schedule.phase_at(time),
                self.rng.choice(SKILL_NAMES), self.rng.choice(self.contexts),
            )
            for time in range(count)
        ]

    def sample_logs(
        self, phase: int, count: int, *, contexts: Sequence[Context] | None = None
    ) -> list[LogEntry]:
        if count < 0:
            raise ValueError("count must be non-negative")
        pool = tuple(contexts) if contexts is not None else self.contexts
        if not pool and count:
            raise ValueError("contexts must not be empty")
        return [
            self.execute(time, phase, self.rng.choice(SKILL_NAMES), self.rng.choice(pool))
            for time in range(count)
        ]

    def probability_table(
        self, phase: int, contexts: Iterable[Context] | None = None
    ) -> dict[str, dict[str, float]]:
        pool = tuple(contexts) if contexts is not None else self.contexts
        return self._oracle.probability_table(phase, pool)
