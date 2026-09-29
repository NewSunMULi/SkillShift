"""Balanced, frozen observation streams shared by every evaluated system."""

from __future__ import annotations

from dataclasses import dataclass
import random

from ..environment import PhaseSchedule
from ..rover.models import Context, LogEntry
from ..rover.simulator import MarsReliabilitySimulator
from ..rover.skills import SKILL_NAMES


@dataclass(frozen=True)
class FrozenObservationStream:
    """Generate common-random-number logs without exposing phase labels to systems."""

    seed: int = 20260927
    observations_per_phase: int = 1000
    checkpoint_interval: int = 100

    def __post_init__(self) -> None:
        if self.observations_per_phase <= 0 or self.checkpoint_interval <= 0:
            raise ValueError("stream sizes must be positive")
        if self.observations_per_phase % self.checkpoint_interval:
            raise ValueError("observations_per_phase must be divisible by checkpoint_interval")
        if self.checkpoint_interval % len(SKILL_NAMES):
            raise ValueError("checkpoint_interval must be divisible by the number of skills")

    @property
    def schedule(self) -> PhaseSchedule:
        return PhaseSchedule(tuple(i * self.observations_per_phase for i in range(6)))

    def generate(self, simulator: MarsReliabilitySimulator) -> tuple[LogEntry, ...]:
        rng = random.Random(self.seed)
        contexts = simulator.contexts
        per_skill = self.checkpoint_interval // len(SKILL_NAMES)
        cursors = {skill: rng.randrange(len(contexts)) for skill in SKILL_NAMES}
        # Every stride is coprime with 300, so no skill is trapped in a small context subset.
        context_strides = (17, 19, 23, 29, 31, 37, 41, 43, 47, 49)
        strides = dict(zip(SKILL_NAMES, context_strides))
        logs: list[LogEntry] = []
        total = 6 * self.observations_per_phase
        for block_start in range(0, total, self.checkpoint_interval):
            block: list[tuple[str, Context]] = []
            for skill in SKILL_NAMES:
                for _ in range(per_skill):
                    index = cursors[skill] % len(contexts)
                    block.append((skill, contexts[index]))
                    cursors[skill] += strides[skill]
            rng.shuffle(block)
            for offset, (skill, context) in enumerate(block):
                time = block_start + offset
                phase = self.schedule.phase_at(time)
                success = rng.random() < simulator.probability(phase, skill, context)
                definition = simulator.skill_catalog.require(skill)
                cost = definition.execution_cost * (1.5 if phase == 5 else 1.0)
                logs.append(LogEntry(time, skill, context.id, success, cost + (0 if success else 2)))
        return tuple(logs)

    def checkpoints(self) -> tuple[int, ...]:
        total = 6 * self.observations_per_phase
        return tuple(range(self.checkpoint_interval, total + 1, self.checkpoint_interval))
