"""实验零集成测试。 / Experiment-zero integration tests."""

import json
import unittest

from test.environment import PhaseSchedule
from test.experiments.experiment0 import run_experiment
from test.rover.reliability import Decision
from test.rover.simulator import MarsReliabilitySimulator


class Experiment0Tests(unittest.TestCase):
    def test_all_design_checks_pass(self):
        self.assertTrue(all(run_experiment()["checks"].values()))

    def test_probability_is_bounded(self):
        sim = MarsReliabilitySimulator()
        for phase in range(1, 7):
            for skill, values in sim.probability_table(phase).items():
                self.assertTrue(all(0.0 < value < 1.0 for value in values.values()), skill)

    def test_llm_contract_rejects_extra_fields(self):
        payload = {
            "alarm": False, "changed_skills": [], "changed_contexts": [],
            "p_hat": {"move": 0.7}, "chosen_skill": "move", "probe": False,
            "hidden_phase": 1,
        }
        with self.assertRaises(ValueError):
            Decision.from_json(json.dumps(payload))

    def test_stream_does_not_leak_phase(self):
        logs = MarsReliabilitySimulator().stream(12, PhaseSchedule((0, 2, 4, 6, 8, 10)))
        self.assertEqual(len(logs), 12)
        self.assertFalse(hasattr(logs[0], "phase"))


if __name__ == "__main__":
    unittest.main()
