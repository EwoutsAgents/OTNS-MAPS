from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts import run_baseline as runner


ROOT = Path(__file__).resolve().parents[1]
DIRECTED = ROOT / "scenarios" / "directed"


class DirectedParentSwitchTests(unittest.TestCase):
    def test_all_directed_scenarios_validate_in_mock_mode(self) -> None:
        paths = sorted(DIRECTED.glob("*.yaml"))
        self.assertEqual(9, len(paths))
        for path in paths:
            scenario = runner.load_scenario(path)
            runner.validate_scenario_configuration(
                scenario,
                path,
                node_binary_path=None,
                node_binary_profile=None,
                ftd_node_binary_path=None,
                ftd_node_binary_profile=None,
                mock=True,
            )

    def test_multicast_fastpr_combination_is_rejected(self) -> None:
        path = DIRECTED / "med_directed_mcast_2routers.yaml"
        scenario = copy.deepcopy(runner.load_scenario(path))
        scenario["directed_switch"]["expected_router_firmware"] = "fastpr"
        for name in runner.router_names(scenario):
            scenario["nodes"][name]["firmware_profile"] = "fastpr"
        with self.assertRaisesRegex(ValueError, "multicast.*stock"):
            runner.validate_scenario_configuration(
                scenario,
                path,
                node_binary_path=None,
                node_binary_profile=None,
                ftd_node_binary_path=None,
                ftd_node_binary_profile=None,
                mock=True,
            )

    def test_scalar_parser_ignores_asynchronous_events(self) -> None:
        lines = [
            "Node<3>  PREFPARENT event=attacher_state generation=0 state=1",
            "3",
        ]
        self.assertEqual(3, runner.first_integer_payload(lines, "node id"))

    def test_global_profile_cannot_mask_binary_mismatch(self) -> None:
        path = DIRECTED / "med_directed_ucast_2routers.yaml"
        scenario = runner.load_scenario(path)
        with self.assertRaisesRegex(ValueError, "preferred-parent MTD"):
            runner.validate_scenario_configuration(
                scenario,
                path,
                node_binary_path=Path("/tmp/not-used-in-mock"),
                node_binary_profile="stock",
                ftd_node_binary_path=Path("/tmp/not-used-in-mock"),
                ftd_node_binary_profile="stock",
                mock=True,
            )

    def test_real_global_binary_requires_declared_profile(self) -> None:
        path = DIRECTED / "med_directed_ucast_2routers.yaml"
        scenario = runner.load_scenario(path)
        with self.assertRaisesRegex(ValueError, "node-binary-profile"):
            runner.validate_scenario_configuration(
                scenario,
                path,
                node_binary_path=Path("/tmp/not-checked-before-profile"),
                node_binary_profile=None,
                ftd_node_binary_path=Path("/tmp/not-checked-before-profile"),
                ftd_node_binary_profile="stock",
                mock=False,
            )

    def test_mock_run_reaches_deterministic_target(self) -> None:
        path = DIRECTED / "med_directed_ucast_2routers.yaml"
        scenario = runner.load_scenario(path)
        rows, summary = runner.MockBenchmarkRunner(scenario).run()
        self.assertEqual(360, len(rows))
        self.assertTrue(summary["command_acknowledged"])
        self.assertEqual(summary["target_parent"], summary["final_parent"])
        self.assertEqual("selected_target_reached", summary["result_classification"])
        self.assertIn("SELECTED_TARGET_REACHED", summary["labels"])

    def test_prefparent_event_parser_preserves_fields(self) -> None:
        events = runner.parse_prefparent_events(
            ["Node<3>  PREFPARENT event=requested generation=2 target=0011223344556677 mode=unicast"],
            305.0,
        )
        self.assertEqual("requested", events[0]["event"])
        self.assertEqual("2", events[0]["generation"])
        self.assertEqual(305.0, events[0]["observed_time_s"])


if __name__ == "__main__":
    unittest.main()
