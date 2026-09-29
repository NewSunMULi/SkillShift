"""评估器拥有的阶段调度。 / Evaluator-owned phase scheduling."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseSchedule:
    """将时间映射到六个阶段，且不向在线系统泄露阶段标签。

    Map time to six phases without exposing phase labels to online systems.
    """

    change_points: tuple[int, ...] = (0, 1000, 2000, 3000, 4000, 5000)

    def __post_init__(self) -> None:
        strictly_increasing = all(
            left < right for left, right in zip(self.change_points, self.change_points[1:])
        )
        if len(self.change_points) != 6 or not strictly_increasing or self.change_points[0] < 0:
            raise ValueError("change_points must contain six strictly increasing non-negative positions")

    def phase_at(self, time: int) -> int:
        if time < 0:
            raise ValueError("time must be non-negative")
        phase = sum(time >= point for point in self.change_points)
        if phase == 0:
            raise ValueError("time precedes the first phase")
        return phase
