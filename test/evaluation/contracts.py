"""Shared strict data contract used by experiments 1 and 2."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any

from ..rover.skills import SKILL_NAMES


def _boolean_map(value: Any, field: str) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != set(SKILL_NAMES):
        raise ValueError(f"{field} must contain exactly all skill names")
    if any(not isinstance(item, bool) for item in value.values()):
        raise ValueError(f"{field} values must be booleans")
    return {skill: value[skill] for skill in SKILL_NAMES}


def _context_map(value: Any, field: str, valid_context_ids: frozenset[str]) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict) or set(value) != set(SKILL_NAMES):
        raise ValueError(f"{field} must contain exactly all skill names")
    result: dict[str, tuple[str, ...]] = {}
    for skill in SKILL_NAMES:
        items = value[skill]
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError(f"{field}.{skill} must be a list of context ids")
        if len(items) != len(set(items)):
            raise ValueError(f"{field}.{skill} contains duplicate context ids")
        unknown = set(items) - valid_context_ids
        if unknown:
            raise ValueError(f"{field}.{skill} contains unknown context ids: {sorted(unknown)[:3]}")
        result[skill] = tuple(items)
    return result


@dataclass(frozen=True)
class ReliabilityAssessment:
    """Machine-scoreable response for detection and localization."""

    checkpoint: int
    alarm_probability: dict[str, bool]
    alarm_applicability: dict[str, bool]
    changed_contexts: dict[str, tuple[str, ...]]
    failed_contexts: dict[str, tuple[str, ...]]
    gained_contexts: dict[str, tuple[str, ...]]

    @classmethod
    def from_mapping(
        cls, value: Any, *, valid_context_ids: frozenset[str], expected_checkpoint: int
    ) -> "ReliabilityAssessment":
        required = {
            "checkpoint", "alarm_probability", "alarm_applicability", "changed_contexts",
            "failed_contexts", "gained_contexts",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError(f"assessment keys must be exactly {sorted(required)}")
        checkpoint = value["checkpoint"]
        if not isinstance(checkpoint, int) or isinstance(checkpoint, bool):
            raise ValueError("checkpoint must be an integer")
        if checkpoint != expected_checkpoint or not math.isfinite(float(checkpoint)):
            raise ValueError("assessment checkpoint does not match request")
        return cls(
            checkpoint,
            _boolean_map(value["alarm_probability"], "alarm_probability"),
            _boolean_map(value["alarm_applicability"], "alarm_applicability"),
            _context_map(value["changed_contexts"], "changed_contexts", valid_context_ids),
            _context_map(value["failed_contexts"], "failed_contexts", valid_context_ids),
            _context_map(value["gained_contexts"], "gained_contexts", valid_context_ids),
        )

    @classmethod
    def from_json(
        cls, payload: str, *, valid_context_ids: frozenset[str], expected_checkpoint: int
    ) -> "ReliabilityAssessment":
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("workflow output is not valid JSON") from exc
        return cls.from_mapping(
            value, valid_context_ids=valid_context_ids, expected_checkpoint=expected_checkpoint,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "checkpoint": self.checkpoint,
            "alarm_probability": self.alarm_probability,
            "alarm_applicability": self.alarm_applicability,
            "changed_contexts": {k: list(v) for k, v in self.changed_contexts.items()},
            "failed_contexts": {k: list(v) for k, v in self.failed_contexts.items()},
            "gained_contexts": {k: list(v) for k, v in self.gained_contexts.items()},
        }
