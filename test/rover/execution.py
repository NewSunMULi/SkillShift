"""探测器技能的唯一执行入口。 / The rover's single skill-execution entry point."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Context, StepResult
from .skills import SkillCatalog


class RoverRuntime(Protocol):
    """执行器所需的最小运行时接口。 / Minimal runtime interface required by the executor."""

    skill_catalog: SkillCatalog

    def step(self, time: int, phase: int, skill: str, context: Context) -> StepResult: ...


@dataclass(frozen=True)
class SkillExecutor:
    """校验明确指定的技能并交给运行时执行。

    Validate an explicitly selected skill and delegate it to the runtime.
    The executor never decides where the skill came from.
    """

    runtime: RoverRuntime

    @property
    def available_skills(self) -> tuple[str, ...]:
        return self.runtime.skill_catalog.names

    def execute(self, *, time: int, phase: int, skill: str, context: Context) -> StepResult:
        self.runtime.skill_catalog.require(skill)
        return self.runtime.step(time, phase, skill, context)
