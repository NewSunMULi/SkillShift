"""仅供评估使用的隐藏概率真值。 / Hidden probability truth for evaluation only."""

from __future__ import annotations

import hashlib
import math

from ..rover import Context, SKILL_NAMES, SkillCatalog


class ProbabilityOracle:
    """计算成功概率；在线控制器不得直接访问该对象。

    Compute ground-truth success probabilities; online controllers must not access it.
    """

    def __init__(self, skills: SkillCatalog):
        self.skills = skills

    @staticmethod
    def _stable_noise(skill: str, context_id: str) -> float:
        digest = hashlib.sha256(f"{skill}:{context_id}".encode()).digest()
        return (int.from_bytes(digest[:4], "big") / (2**32 - 1) - 0.5) * 1.2

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1.0 / (1.0 + math.exp(-value))

    def probability(self, phase: int, skill: str, context: Context) -> float:
        """返回阶段 1..6 的隐藏真值。 / Return hidden truth for phases 1 through 6."""
        if phase not in range(1, 7):
            raise ValueError("phase must be in 1..6")
        self.skills.require(skill)

        score = 1.25 + self._stable_noise(skill, context.id)
        tags, state = context.env_tags, context.state
        if skill == "move" and "rough" in tags:
            score -= 1.5
        if skill == "image" and ("obscured" in tags or state == "camera_degraded"):
            score -= 1.5
        if skill == "heat":
            score += 0.8 if "cold" in tags else -0.5
            score -= 0.7 if state == "heater_fault" else 0.0
        if skill == "communicate" and (
            context.environment in {"blackout", "long_delay"} or state == "comms_degraded"
        ):
            score -= 1.5
        if skill == "charge":
            score += 0.8 if "bright" in tags else -0.5
        if skill in {"drill", "sample"} and state == "arm_degraded":
            score -= 1.5
        if skill == "repair" and state != "nominal":
            score += 0.5

        # 阶段效应与基础语义分开，便于验证恢复和复现。
        # Keep phase effects separate so recovery and recurrence remain verifiable.
        if phase == 2 and skill == "communicate":
            score -= 4.0
        if phase in {3, 6} and skill == "heat" and "cold" in tags and state == "heater_fault":
            score -= 4.0
        if phase == 5 and skill == "image" and "radiation" in tags:
            score -= 4.0
        return self._sigmoid(score)

    def is_applicable(self, phase: int, skill: str, context: Context) -> bool:
        return self.probability(phase, skill, context) >= self.skills.require(skill).threshold

    def probability_table(
        self, phase: int, contexts: tuple[Context, ...]
    ) -> dict[str, dict[str, float]]:
        return {
            skill: {context.id: self.probability(phase, skill, context) for context in contexts}
            for skill in SKILL_NAMES
        }
