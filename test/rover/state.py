"""探测器内部状态定义。 / Rover internal-state definitions."""

from dataclasses import dataclass


STATE_NAMES = (
    "nominal", "low_battery", "critical_battery", "cold_body", "hot_body",
    "wheel_worn", "arm_degraded", "camera_degraded", "comms_degraded",
    "heater_fault",
)


@dataclass(frozen=True)
class RoverState:
    """探测器当前内部状态。 / Current internal state of the rover."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in STATE_NAMES:
            raise ValueError(f"unknown rover state: {self.name}")
