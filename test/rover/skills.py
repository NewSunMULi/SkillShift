"""探测器技能定义与目录。 / Rover skill definitions and catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator


SKILL_NAMES = (
    "move", "drill", "sample", "image", "heat", "communicate", "charge",
    "avoid", "repair", "sleep",
)


@dataclass(frozen=True)
class Skill:
    """技能的稳定执行配置。 / Stable execution configuration for one skill."""

    name: str
    threshold: float = 0.65
    max_steps: int = 20
    execution_cost: float = 1.0

    def __post_init__(self) -> None:
        if self.name not in SKILL_NAMES:
            raise ValueError(f"unknown skill: {self.name}")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        if self.max_steps <= 0 or self.execution_cost < 0:
            raise ValueError("max_steps must be positive and execution_cost non-negative")


class SkillCatalog:
    """集中保存技能配置并提供快速校验。 / Store and validate skill configurations."""

    def __init__(self, skills: Iterable[Skill] | None = None):
        items = tuple(skills) if skills is not None else tuple(Skill(name) for name in SKILL_NAMES)
        if len({item.name for item in items}) != len(items):
            raise ValueError("skill names must be unique")
        self._skills = items
        self._by_name = {item.name: item for item in items}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._by_name)

    def require(self, name: str) -> Skill:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise ValueError(f"unknown skill: {name}") from exc

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills)
