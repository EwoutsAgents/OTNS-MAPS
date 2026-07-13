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
        self.assertTrue(summary["protocol_timing_complete"])
        self.assertEqual(65.0, summary["protocol_timing_ms"]["parent_request_to_child_id_response"])

    def test_protocol_timing_uses_native_event_timestamps(self) -> None:
        events = [
            {"event": "parent_request_started", "time_us": "1000", "timing_source": "otns_openthread_event", "resolution_us": "1"},
            {"event": "target_response", "time_us": "51000", "timing_source": "otns_openthread_event", "resolution_us": "1"},
            {"event": "child_id_request_started", "time_us": "56000", "timing_source": "otns_openthread_event", "resolution_us": "1"},
            {"event": "child_id_response_received", "time_us": "66000", "timing_source": "otns_openthread_event", "resolution_us": "1"},
        ]
        timing = runner.derive_preferred_parent_timing(
            events,
            deletion_time_s=0.0,
            samples=[{"sim_time_s": 1.0, "parent_node_guess": "router_b"}],
            target_parent="router_b",
            poll_resolution_s=1,
        )
        self.assertEqual(
            {
                "parent_request_to_response": 50.0,
                "parent_response_to_child_id_request": 5.0,
                "child_id_request_to_response": 10.0,
                "parent_request_to_child_id_response": 65.0,
            },
            timing["protocol_timing_ms"],
        )
        self.assertEqual("otns_openthread_event", timing["protocol_timing_source"])
        self.assertEqual("otns_parent_poll", timing["parent_deletion_to_target_observed_source"])

    def test_uint32_microsecond_clock_wrap(self) -> None:
        self.assertEqual(32, runner.uint32_microsecond_delta(0xFFFFFFF0, 0x10))

    def test_prefparent_event_parser_preserves_fields(self) -> None:
        events = runner.parse_prefparent_events(
            ["Node<3>  PREFPARENT event=requested generation=2 target=0011223344556677 mode=unicast"],
            305.0,
        )
        self.assertEqual("requested", events[0]["event"])
        self.assertEqual("2", events[0]["generation"])
        self.assertEqual(305.0, events[0]["observed_time_s"])

    def test_directed_preflight_skip_and_advisory_labels(self) -> None:
        cases = (
            (
                {"has_parent": False, "parent_is_mapped": False},
                ["SKIP_NO_CHILD_PARENT"],
            ),
            (
                {"has_parent": True, "parent_is_mapped": False},
                ["SKIP_PARENT_NOT_MAPPED_TO_DEVICE"],
            ),
            (
                {
                    "has_parent": True,
                    "parent_is_mapped": True,
                    "eligible_target_count": 0,
                },
                ["SKIP_NO_ELIGIBLE_TARGET_PARENT"],
            ),
            (
                {
                    "has_parent": True,
                    "parent_is_mapped": True,
                    "parent_is_leader": True,
                    "eligible_target_count": 1,
                },
                ["SKIP_PARENT_IS_LEADER"],
            ),
            (
                {
                    "has_parent": True,
                    "parent_is_mapped": True,
                    "parent_is_leader": True,
                    "eligible_target_count": 0,
                },
                ["SKIP_PARENT_IS_LEADER", "SKIP_NO_ELIGIBLE_TARGET_PARENT"],
            ),
        )
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(expected, runner.directed_preflight_labels(**arguments))

    def test_every_directed_result_classification(self) -> None:
        cases = (
            (
                {
                    "command_acknowledged": True,
                    "command_error": None,
                    "labels": [],
                    "final_parent": "router_b",
                    "target_parent": "router_b",
                },
                ("selected_target_reached", "SELECTED_TARGET_REACHED"),
            ),
            (
                {
                    "command_acknowledged": True,
                    "command_error": None,
                    "labels": [],
                    "final_parent": "router_c",
                    "target_parent": "router_b",
                },
                ("attached_to_non_target_parent", "ATTACHED_TO_NON_TARGET_PARENT"),
            ),
            (
                {
                    "command_acknowledged": True,
                    "command_error": None,
                    "labels": [],
                    "final_parent": None,
                    "target_parent": "router_b",
                },
                ("no_reattachment", "NO_REATTACHMENT"),
            ),
            (
                {
                    "command_acknowledged": False,
                    "command_error": "InvalidCommand",
                    "labels": ["COMMAND_REJECTED"],
                    "final_parent": None,
                    "target_parent": "router_b",
                },
                ("command_rejected", None),
            ),
            (
                {
                    "command_acknowledged": False,
                    "command_error": None,
                    "labels": ["SKIP_NO_CHILD_PARENT"],
                    "final_parent": None,
                    "target_parent": None,
                },
                ("skipped", None),
            ),
        )
        for arguments, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, runner.classify_directed_result(**arguments))


if __name__ == "__main__":
    unittest.main()
