"""执行上下文生成器。 / Operational-context factory."""

from ..environment import ENVIRONMENT_NAMES, environment_tags

from .models import Context
from .state import STATE_NAMES


def standard_contexts() -> tuple[Context, ...]:
    """生成完整的 30×10 标准网格。 / Build the complete 30-by-10 standard grid."""
    return tuple(
        Context(f"e{ei:02d}-s{si:02d}", environment, state, environment_tags(environment))
        for ei, environment in enumerate(ENVIRONMENT_NAMES)
        for si, state in enumerate(STATE_NAMES)
    )


def generalization_contexts(count: int = 100) -> tuple[Context, ...]:
    """生成确定性的双环境留出组合。 / Build deterministic held-out two-environment mixtures."""
    contexts = []
    for index in range(count):
        first = ENVIRONMENT_NAMES[index % len(ENVIRONMENT_NAMES)]
        second = ENVIRONMENT_NAMES[(index * 7 + 11) % len(ENVIRONMENT_NAMES)]
        state = STATE_NAMES[(index * 3 + 1) % len(STATE_NAMES)]
        contexts.append(Context(
            f"g{index:03d}", f"{first}+{second}", state,
            environment_tags(first) | environment_tags(second), True,
        ))
    return tuple(contexts)
