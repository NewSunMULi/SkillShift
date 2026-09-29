"""可靠性决策数据合约。 / Reliability decision data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Protocol, Sequence

from ..models import Context, LogEntry
from ..skills import SKILL_NAMES


@dataclass(frozen=True)
class Decision:
    """可靠性系统返回的结构化决策。 / Structured decision returned by a reliability system."""

    alarm: bool
    changed_skills: tuple[str, ...]
    changed_contexts: tuple[str, ...]
    p_hat: dict[str, float]
    chosen_skill: str
    probe: bool

    @classmethod
    def from_json(cls, payload: str) -> "Decision":
        raw = json.loads(payload)
        required = {"alarm", "changed_skills", "changed_contexts", "p_hat", "chosen_skill", "probe"}
        if not isinstance(raw, dict) or set(raw) != required:
            raise ValueError(f"response keys must be exactly {sorted(required)}")
        if raw["chosen_skill"] not in SKILL_NAMES:
            raise ValueError("unknown chosen_skill")
        if not isinstance(raw["alarm"], bool) or not isinstance(raw["probe"], bool):
            raise ValueError("alarm and probe must be booleans")
        if not isinstance(raw["changed_skills"], list) or not isinstance(raw["changed_contexts"], list):
            raise ValueError("changed_skills and changed_contexts must be lists")
        if any(skill not in SKILL_NAMES for skill in raw["changed_skills"]):
            raise ValueError("changed_skills contains an unknown skill")
        probabilities = {str(key): float(value) for key, value in raw["p_hat"].items()}
        if any(key not in SKILL_NAMES for key in probabilities):
            raise ValueError("p_hat contains an unknown skill")
        if any(not 0.0 <= value <= 1.0 for value in probabilities.values()):
            raise ValueError("p_hat values must be in [0, 1]")
        return cls(
            raw["alarm"], tuple(raw["changed_skills"]), tuple(raw["changed_contexts"]),
            probabilities, raw["chosen_skill"], raw["probe"],
        )

    def to_json(self) -> str:
        value = asdict(self)
        value["changed_skills"] = list(self.changed_skills)
        value["changed_contexts"] = list(self.changed_contexts)
        return json.dumps(value, ensure_ascii=False, sort_keys=True)


class ReliabilitySystem(Protocol):
    """可靠性算法与 LLM 共同实现的分析协议。 / Analysis protocol shared by reliability algorithms and LLMs."""

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision: ...
