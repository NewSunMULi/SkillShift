"""供应商无关的 LLM JSON 适配器。 / Provider-neutral LLM JSON adapter."""

from dataclasses import asdict
import json
from typing import Callable, Sequence

from ..models import Context, LogEntry
from ..skills import SKILL_NAMES
from .contracts import Decision


SYSTEM_PROMPT = """You maintain rover skill reliability from observations only.
Never infer or request hidden phase labels, change points, or oracle probabilities.
Return one JSON object with exactly: alarm, changed_skills, changed_contexts,
p_hat, chosen_skill, probe. chosen_skill must be one of: {skills}.
""".format(skills=", ".join(SKILL_NAMES))


class LLMJsonAdapter:
    """注入模型调用函数，避免保存凭据或绑定 SDK。 / Inject calls to avoid credentials and SDK coupling."""

    def __init__(self, model: str, complete: Callable[[str, str], str]):
        self.model = model
        self.complete = complete

    def decide(self, context: Context, logs: Sequence[LogEntry]) -> Decision:
        observations = [asdict(entry) for entry in logs]
        user = json.dumps(
            {"context": asdict(context), "logs": observations}, ensure_ascii=False, default=list,
        )
        return Decision.from_json(self.complete(SYSTEM_PROMPT, user))
