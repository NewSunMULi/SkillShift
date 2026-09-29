"""技能执行、人工操作、脚本操作与自动接管测试。

Tests for execution, manual/script operation, and autonomous takeover.
"""

import unittest

from test.rover.agent import AutonomousRoverAgent
from test.rover.execution import SkillExecutor
from test.rover.operators import ManualOperator, ScriptedOperator
from test.rover.reliability import Decision
from test.rover.simulator import MarsReliabilitySimulator


class _FixedDecisionSystem:
    """用于验证自动系统接管路径。 / Stand-in for an autonomous decision system."""

    def decide(self, context, logs):
        return Decision(True, ("heat",), (context.id,), {"heat": 0.9}, "heat", True)


class RoverOperationTests(unittest.TestCase):
    def setUp(self):
        self.simulator = MarsReliabilitySimulator(seed=7)
        self.executor = SkillExecutor(self.simulator)
        self.context = self.simulator.contexts[0]

    def test_executor_runs_an_explicit_skill(self):
        result = self.executor.execute(time=0, phase=1, skill="move", context=self.context)
        self.assertEqual(result.observation.skill, "move")

    def test_custom_script_controls_skill(self):
        operator = ScriptedOperator(
            self.executor, lambda context, logs, skills: "move",
        )
        result = operator.run_step(time=0, phase=1, context=self.context)
        self.assertEqual(result.observation.skill, "move")

    def test_invalid_script_choice_is_rejected_before_execution(self):
        operator = ScriptedOperator(
            self.executor, lambda context, logs, skills: "teleport",
        )
        with self.assertRaises(ValueError):
            operator.run_step(time=0, phase=1, context=self.context)

    def test_manual_operator_accepts_number_after_invalid_input(self):
        answers = iter(["invalid", "2"])
        messages = []
        operator = ManualOperator(self.executor, lambda prompt: next(answers), messages.append)
        result = operator.run_step(time=0, phase=1, context=self.context)
        self.assertEqual(result.observation.skill, "drill")
        self.assertTrue(any("Invalid skill" in message for message in messages))

    def test_agent_preserves_full_decision_for_evaluation(self):
        agent = AutonomousRoverAgent(self.executor, _FixedDecisionSystem())
        result = agent.run_step(time=0, phase=1, context=self.context)
        self.assertEqual(result.execution.observation.skill, "heat")
        self.assertTrue(result.decision.alarm)
        self.assertTrue(result.decision.probe)
        self.assertEqual(result.decision.changed_skills, ("heat",))
        self.assertEqual(result.decision.changed_contexts, (self.context.id,))
        self.assertEqual(result.decision.p_hat, {"heat": 0.9})


if __name__ == "__main__":
    unittest.main()
