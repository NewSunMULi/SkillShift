"""Shared Dify Workflow client and LLM experiment adapter.

Knowledge retrieval, conversation memory, model selection, and prompt construction belong inside
the published Dify workflow. Python owns the reproducible observations and strict output contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import time
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ReliabilityAssessment
from ..rover.models import Context, LogEntry


EXPERIMENT_SYSTEM_PROMPT = """You detect rover skill reliability changes from observations only.
Never request or infer hidden phase labels, change points, oracle probabilities, or future logs.
Return only the experiment JSON schema. Distinguish probability changes from threshold-crossing
applicability changes. Context regions must be explicit context_id lists; do not return prose rules.
Treat cost-only changes as negative evidence for success-probability change.
"""


@dataclass(frozen=True)
class DifyWorkflowConfig:
    api_key: str
    base_url: str = "http://localhost/v1"
    user: str = "deerlinkai-experiment"
    input_name: str = "request_json"
    output_name: str = "result"
    timeout_seconds: float = 120.0
    max_retries: int = 2
    model_label: str = "unreported"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "DifyWorkflowConfig":
        env = os.environ if environ is None else environ
        api_key = env.get("DIFY_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DIFY_API_KEY is required")
        return cls(
            api_key=api_key,
            base_url=env.get("DIFY_BASE_URL", "http://localhost/v1").rstrip("/"),
            user=env.get("DIFY_WORKFLOW_USER", "deerlinkai-experiment"),
            input_name=env.get("DIFY_INPUT_NAME", "request_json"),
            output_name=env.get("DIFY_OUTPUT_NAME", "result"),
            timeout_seconds=float(env.get("DIFY_TIMEOUT_SECONDS", "120")),
            max_retries=int(env.get("DIFY_MAX_RETRIES", "2")),
            model_label=env.get("DIFY_MODEL_LABEL", "unreported"),
        )


class DifyWorkflowClient:
    """Call Dify's blocking Workflow API using only the Python standard library."""

    def __init__(self, config: DifyWorkflowConfig):
        self.config = config

    def run(self, inputs: Mapping[str, Any]) -> Any:
        body = json.dumps({
            "inputs": dict(inputs), "response_mode": "blocking", "user": self.config.user,
        }, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.config.base_url}/workflows/run", data=body, method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                data = payload.get("data")
                if not isinstance(data, dict) or data.get("status") == "failed":
                    raise RuntimeError(f"Dify workflow failed: {payload}")
                outputs = data.get("outputs")
                if not isinstance(outputs, dict) or self.config.output_name not in outputs:
                    raise RuntimeError(f"Dify output {self.config.output_name!r} is missing")
                return outputs[self.config.output_name]
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                if attempt == self.config.max_retries:
                    break
                time.sleep(0.5 * (2 ** attempt))
        # Transport/workflow failures invalidate the run, not the model prediction. Do not silently
        # turn an unavailable service into sixty empty predictions.
        raise ConnectionError("Dify workflow request failed") from last_error


class DifyAssessmentSystem:
    """Serialize an experiment checkpoint into one Dify workflow invocation."""

    def __init__(
        self, client: DifyWorkflowClient, contexts: Sequence[Context], *, memory_log_limit: int = 2000
    ):
        if memory_log_limit <= 0:
            raise ValueError("memory_log_limit must be positive")
        self.client = client
        self.contexts = tuple(contexts)
        self.valid_ids = frozenset(context.id for context in contexts)
        self.memory_log_limit = memory_log_limit

    @staticmethod
    def _block_summaries(logs: Sequence[LogEntry], block_size: int = 100) -> list[dict[str, Any]]:
        """Compress all visible history without inventing phase boundaries or semantic labels."""
        summaries = []
        for start in range(0, len(logs), block_size):
            block = logs[start:start + block_size]
            by_skill: dict[str, dict[str, float | int]] = {}
            for entry in block:
                item = by_skill.setdefault(entry.skill, {"count": 0, "successes": 0, "cost_sum": 0.0})
                item["count"] += 1
                item["successes"] += int(entry.success)
                item["cost_sum"] += entry.cost
            summaries.append({"start": start, "end": start + len(block), "by_skill": by_skill})
        return summaries

    def assess(self, checkpoint: int, logs: Sequence[LogEntry]) -> ReliabilityAssessment:
        visible_logs = tuple(logs[-self.memory_log_limit:])
        request_payload = {
            "system_instruction": EXPERIMENT_SYSTEM_PROMPT,
            "checkpoint": checkpoint,
            "context_catalog": [asdict(context) for context in self.contexts],
            "observations": [asdict(log) for log in visible_logs],
            "history_block_summaries": self._block_summaries(logs),
            "memory_policy": {
                "raw_log_limit": self.memory_log_limit,
                "summary_block_size": 100,
                "external_knowledge_and_memory": "configured inside the Dify workflow",
            },
        }
        encoded = json.dumps(request_payload, ensure_ascii=False, default=list)
        raw = self.client.run({self.client.config.input_name: encoded})
        if isinstance(raw, str):
            return ReliabilityAssessment.from_json(
                raw, valid_context_ids=self.valid_ids, expected_checkpoint=checkpoint,
            )
        return ReliabilityAssessment.from_mapping(
            raw, valid_context_ids=self.valid_ids, expected_checkpoint=checkpoint,
        )
