"""Shared reference systems for experiments 1 and 2."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .contracts import ReliabilityAssessment
from ..environment import PhaseSchedule
from ..rover.models import Context, LogEntry
from ..rover.simulator import MarsReliabilitySimulator
from ..rover.skills import SKILL_NAMES


def _empty_context_map() -> dict[str, tuple[str, ...]]:
    return {skill: () for skill in SKILL_NAMES}


@dataclass(frozen=True)
class OracleAssessmentSystem:
    """Evaluation-only upper bound; never use it as an online controller."""

    simulator: MarsReliabilitySimulator
    schedule: PhaseSchedule
    eta: float = 0.1

    def assess(self, checkpoint: int, logs: Sequence[LogEntry]) -> ReliabilityAssessment:
        del logs
        phase = self.schedule.phase_at(checkpoint - 1)
        previous = max(1, phase - 1)
        changed, failed, gained = {}, {}, {}
        alarm_p, alarm_u = {}, {}
        for skill in SKILL_NAMES:
            changed[skill] = tuple(
                context.id for context in self.simulator.contexts
                if abs(
                    self.simulator.probability(phase, skill, context)
                    - self.simulator.probability(previous, skill, context)
                ) >= self.eta
            )
            old = {
                context.id for context in self.simulator.contexts
                if self.simulator.is_applicable(previous, skill, context)
            }
            new = {
                context.id for context in self.simulator.contexts
                if self.simulator.is_applicable(phase, skill, context)
            }
            failed[skill], gained[skill] = tuple(sorted(old - new)), tuple(sorted(new - old))
            alarm_p[skill] = bool(changed[skill])
            alarm_u[skill] = bool(failed[skill] or gained[skill])
        return ReliabilityAssessment(checkpoint, alarm_p, alarm_u, changed, failed, gained)


class WindowedIdBaseline:
    """Non-semantic baseline using only per-ID empirical rates in adjacent windows."""

    def __init__(
        self, *, window_size: int = 1000, probability_delta: float = 0.25,
        applicability_threshold: float = 0.65, minimum_count: int = 1,
    ):
        if window_size <= 0 or window_size % 2 or minimum_count <= 0:
            raise ValueError("window_size must be positive and even; minimum_count must be positive")
        self.window_size = window_size
        self.probability_delta = probability_delta
        self.applicability_threshold = applicability_threshold
        self.minimum_count = minimum_count

    @staticmethod
    def _rates(logs: Sequence[LogEntry]) -> tuple[dict[str, tuple[int, int]], dict[tuple[str, str], tuple[int, int]]]:
        skills: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        contexts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for log in logs:
            skills[log.skill][0] += int(log.success)
            skills[log.skill][1] += 1
            contexts[(log.skill, log.context_id)][0] += int(log.success)
            contexts[(log.skill, log.context_id)][1] += 1
        return (
            {key: (value[0], value[1]) for key, value in skills.items()},
            {key: (value[0], value[1]) for key, value in contexts.items()},
        )

    def assess(self, checkpoint: int, logs: Sequence[LogEntry]) -> ReliabilityAssessment:
        recent = tuple(logs[-self.window_size:])
        midpoint = len(recent) // 2
        old_skill, old_context = self._rates(recent[:midpoint])
        new_skill, new_context = self._rates(recent[midpoint:])
        alarm_p, alarm_u = {}, {}
        changed, failed, gained = _empty_context_map(), _empty_context_map(), _empty_context_map()
        for skill in SKILL_NAMES:
            old_success, old_count = old_skill.get(skill, (0, 0))
            new_success, new_count = new_skill.get(skill, (0, 0))
            old_rate = old_success / old_count if old_count else 0.5
            new_rate = new_success / new_count if new_count else 0.5
            alarm_p[skill] = (
                old_count >= self.minimum_count and new_count >= self.minimum_count
                and abs(new_rate - old_rate) >= self.probability_delta
            )
            alarm_u[skill] = alarm_p[skill] and (
                (old_rate >= self.applicability_threshold) !=
                (new_rate >= self.applicability_threshold)
            )
            changed_ids, failed_ids, gained_ids = [], [], []
            ids = {context_id for seen_skill, context_id in old_context if seen_skill == skill}
            ids |= {context_id for seen_skill, context_id in new_context if seen_skill == skill}
            for context_id in sorted(ids):
                os, oc = old_context.get((skill, context_id), (0, 0))
                ns, nc = new_context.get((skill, context_id), (0, 0))
                if oc < self.minimum_count or nc < self.minimum_count:
                    continue
                old_value, new_value = os / oc, ns / nc
                if abs(new_value - old_value) >= self.probability_delta:
                    changed_ids.append(context_id)
                if old_value >= self.applicability_threshold > new_value:
                    failed_ids.append(context_id)
                if new_value >= self.applicability_threshold > old_value:
                    gained_ids.append(context_id)
            changed[skill] = tuple(changed_ids)
            failed[skill] = tuple(failed_ids)
            gained[skill] = tuple(gained_ids)
        return ReliabilityAssessment(checkpoint, alarm_p, alarm_u, changed, failed, gained)
