"""环境模块测试。 / Environment module tests."""

import unittest

from test.environment import Environment, PhaseSchedule


class EnvironmentTests(unittest.TestCase):
    def test_environment_tags_are_derived_without_rover_state(self):
        environment = Environment.from_name("heavy_snow")
        self.assertEqual(environment.name, "heavy_snow")
        self.assertIn("cold", environment.tags)

    def test_schedule_requires_strictly_increasing_points(self):
        with self.assertRaises(ValueError):
            PhaseSchedule((0, 2, 2, 6, 8, 10))


if __name__ == "__main__":
    unittest.main()
