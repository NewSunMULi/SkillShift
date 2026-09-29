"""人工技能操作。 / Manual skill operation."""

from __future__ import annotations

from typing import Callable

from ..execution import SkillExecutor
from ..models import Context, StepResult


class ManualOperator:
    """通过终端名称或序号选择并执行技能。 / Select and execute a skill by terminal name or index."""

    def __init__(
        self,
        executor: SkillExecutor,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ):
        self.executor = executor
        self.input_fn = input_fn
        self.output_fn = output_fn

    def choose_skill(self) -> str:
        skills = self.executor.available_skills
        choices = ", ".join(f"{index + 1}:{name}" for index, name in enumerate(skills))
        self.output_fn(f"可用技能 / Available skills: {choices}")
        while True:
            answer = self.input_fn("选择技能名称或序号 / Choose skill name or number: ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(skills):
                return skills[int(answer) - 1]
            if answer in skills:
                return answer
            self.output_fn("无效技能，请重试。 / Invalid skill; try again.")

    def run_step(self, *, time: int, phase: int, context: Context) -> StepResult:
        return self.executor.execute(
            time=time, phase=phase, skill=self.choose_skill(), context=context,
        )
