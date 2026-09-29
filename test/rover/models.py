"""探测器运行期数据模型。 / Rover runtime data models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Context:
    """环境与探测器状态组成的执行上下文。 / Execution context combining environment and rover state."""

    id: str
    environment: str
    state: str
    env_tags: frozenset[str] = field(compare=False)
    held_out: bool = False


@dataclass(frozen=True)
class LogEntry:
    """在线系统唯一可见的执行观测。 / Execution observation visible to online systems."""

    time: int
    skill: str
    context_id: str
    success: bool
    cost: float


@dataclass(frozen=True)
class StepResult:
    """一次技能使用及其状态转移结果。 / Result and state transition of one skill use."""

    observation: LogEntry
    next_context: Context
    damaged: bool
