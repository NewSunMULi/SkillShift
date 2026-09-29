"""Tests for the experiment 1–2 protocol and Dify boundary."""

import json
import unittest

from test.evaluation.contracts import ReliabilityAssessment
from test.evaluation.dify import DifyAssessmentSystem, DifyWorkflowConfig
from test.evaluation.stream import FrozenObservationStream
from test.experiments.run_1_2 import run_experiments
from test.rover.simulator import MarsReliabilitySimulator
from test.rover.skills import SKILL_NAMES


def _empty_payload(checkpoint):
    return {
        "checkpoint": checkpoint,
        "alarm_probability": {skill: False for skill in SKILL_NAMES},
        "alarm_applicability": {skill: False for skill in SKILL_NAMES},
        "changed_contexts": {skill: [] for skill in SKILL_NAMES},
        "failed_contexts": {skill: [] for skill in SKILL_NAMES},
        "gained_contexts": {skill: [] for skill in SKILL_NAMES},
    }


class _FakeDifyClient:
    def __init__(self):
        self.config = DifyWorkflowConfig("secret")
        self.inputs = None

    def run(self, inputs):
        self.inputs = inputs
        request = json.loads(inputs[self.config.input_name])
        return json.dumps(_empty_payload(request["checkpoint"]))


class ExperimentsOneTwoTests(unittest.TestCase):
    def test_frozen_stream_is_reproducible_and_skill_balanced(self):
        simulator = MarsReliabilitySimulator(11)
        stream = FrozenObservationStream(seed=11)
        first = stream.generate(simulator)
        second = stream.generate(MarsReliabilitySimulator(11))
        self.assertEqual(first, second)
        for start in range(0, len(first), stream.checkpoint_interval):
            block = first[start:start + stream.checkpoint_interval]
            self.assertEqual(
                {skill: sum(log.skill == skill for log in block) for skill in SKILL_NAMES},
                {skill: 10 for skill in SKILL_NAMES},
            )
        self.assertFalse(hasattr(first[0], "phase"))

    def test_contract_rejects_unknown_context(self):
        payload = _empty_payload(100)
        payload["changed_contexts"]["move"] = ["not-a-context"]
        with self.assertRaises(ValueError):
            ReliabilityAssessment.from_mapping(
                payload, valid_context_ids=frozenset({"known"}), expected_checkpoint=100,
            )

    def test_dify_adapter_sends_catalog_logs_and_memory_policy(self):
        simulator = MarsReliabilitySimulator(5)
        logs = FrozenObservationStream(seed=5).generate(simulator)[:100]
        client = _FakeDifyClient()
        system = DifyAssessmentSystem(client, simulator.contexts, memory_log_limit=50)
        result = system.assess(100, logs)
        request = json.loads(client.inputs[client.config.input_name])
        self.assertEqual(result.checkpoint, 100)
        self.assertEqual(len(request["context_catalog"]), 300)
        self.assertEqual(len(request["observations"]), 50)
        self.assertEqual(len(request["history_block_summaries"]), 1)
        self.assertEqual(request["history_block_summaries"][0]["end"], 100)
        self.assertNotIn("phase", request["observations"][0])

    def test_oracle_scores_perfectly(self):
        report = run_experiments(system_name="oracle", seed=17)
        detection = report["experiment1"]["summary"]
        localization = report["experiment2"]["summary"]
        self.assertEqual(detection["probability"]["event_recall"], 1.0)
        self.assertEqual(detection["probability"]["false_alarms_per_1000_negative_checkpoints"], 0.0)
        self.assertEqual(localization["changed"]["iou"], 1.0)
        self.assertEqual(localization["failed"]["iou"], 1.0)
        self.assertEqual(localization["gained"]["iou"], 1.0)


if __name__ == "__main__":
    unittest.main()
