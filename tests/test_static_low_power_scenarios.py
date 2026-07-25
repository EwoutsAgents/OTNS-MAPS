from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class StaticLowPowerScenarioTests(unittest.TestCase):
    def test_low_power_matrix_matches_hardware(self) -> None:
        expected = {
            2: {"router_a": 20, "router_b": 20, "mobile": 20},
            3: {"router_a": 20, "router_b": 20, "router_c": -15, "mobile": 20},
            4: {
                "router_a": 20,
                "router_b": 20,
                "router_c": -15,
                "router_d": -15,
                "mobile": 20,
            },
        }

        for router_count, expected_power in expected.items():
            with self.subTest(router_count=router_count):
                path = (
                    ROOT
                    / "scenarios"
                    / "static"
                    / f"med_static_parent_removal_low_power_{router_count}routers.yaml"
                )
                scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertEqual(0.1, scenario["coordinate_system"]["meter_per_unit"])
                self.assertEqual("observed_mobile_parent", scenario["removal"]["target"])
                self.assertEqual(
                    expected_power,
                    {
                        name: config["tx_power_dbm"]
                        for name, config in scenario["nodes"].items()
                    },
                )


if __name__ == "__main__":
    unittest.main()
