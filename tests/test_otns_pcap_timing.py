from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from analysis import analyze_baseline
from scripts import otns_pcap_timing
from scripts import run_baseline


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "directed_attach_with_initial_traffic.pcap"
CHILD = "5281d60dbda1e6a5"
TARGET = "02fb00def7b709cb"


def packet(number: int, timestamp: float, command: int, src: str, dst: str) -> otns_pcap_timing.AttachPacket:
    return otns_pcap_timing.AttachPacket(number, timestamp, command, src, dst)


class OtnsPcapTimingTests(unittest.TestCase):
    def test_directed_command_forces_wpan_pcap(self) -> None:
        command = run_baseline.with_otns_pcap("otns -web=false -pcap off", True)
        self.assertIn("-pcap wpan", command)
        self.assertNotIn("-pcap off", command)

    def test_real_fixture_extracts_air_to_air_sequence_after_initial_attach(self) -> None:
        result = otns_pcap_timing.extract_air_timing(
            FIXTURE,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=185.0,
        )
        self.assertTrue(result["complete"])
        self.assertEqual("otns_pcap", result["source"])
        self.assertEqual(
            {
                "parent_request_to_response": 6.08,
                "parent_response_to_child_id_request": 13.648,
                "child_id_request_to_response": 5.416,
                "parent_request_to_child_id_response": 25.144,
            },
            result["timing_ms"],
        )
        self.assertEqual(15, result["packets"]["parent_request"]["frame_number"])
        self.assertEqual(26, result["packets"]["child_id_response"]["frame_number"])

    def test_target_filter_ignores_other_router_and_unrelated_mle(self) -> None:
        other = "1111111111111111"
        packets = [
            packet(1, 10.0, 9, CHILD, TARGET),
            packet(2, 10.1, 10, other, CHILD),
            packet(3, 10.2, 10, TARGET, CHILD),
            packet(4, 10.3, 9, other, TARGET),
            packet(5, 10.4, 11, CHILD, TARGET),
            packet(6, 10.5, 12, TARGET, CHILD),
        ]
        result = otns_pcap_timing.derive_air_timing(
            packets,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=9.0,
        )
        self.assertTrue(result["complete"])
        self.assertEqual(200.0, result["timing_ms"]["parent_request_to_response"])

    def test_multicast_request_is_correlated_to_selected_target_response(self) -> None:
        packets = [
            otns_pcap_timing.AttachPacket(1, 1.0, 9, CHILD, None, dst16="0xffff"),
            packet(2, 1.1, 10, "1111111111111111", CHILD),
            packet(3, 1.2, 10, TARGET, CHILD),
            packet(4, 1.3, 11, CHILD, TARGET),
            packet(5, 1.4, 12, TARGET, CHILD),
        ]
        result = otns_pcap_timing.derive_air_timing(
            packets,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="multicast",
            operation_start_s=0.0,
        )
        self.assertTrue(result["complete"])
        self.assertEqual(200.0, result["timing_ms"]["parent_request_to_response"])

    def test_missing_pcap_is_not_backfilled(self) -> None:
        result = otns_pcap_timing.extract_air_timing(
            Path("/definitely/not/a/capture.pcap"),
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=0.0,
        )
        self.assertFalse(result["complete"])
        self.assertEqual("pcap_missing", result["failure_reason"])
        self.assertEqual({}, result["timing_ms"])

    def test_missing_packets_report_specific_failure(self) -> None:
        complete = [
            packet(1, 1.0, 9, CHILD, TARGET),
            packet(2, 1.1, 10, TARGET, CHILD),
            packet(3, 1.2, 11, CHILD, TARGET),
            packet(4, 1.3, 12, TARGET, CHILD),
        ]
        expected = {
            10: "missing_parent_response",
            11: "missing_child_id_request",
            12: "missing_child_id_response",
        }
        for command, reason in expected.items():
            result = otns_pcap_timing.derive_air_timing(
                [item for item in complete if item.command != command],
                child_extaddr=CHILD,
                target_extaddr=TARGET,
                mode="unicast",
                operation_start_s=0.0,
            )
            self.assertFalse(result["complete"])
            self.assertEqual(reason, result["failure_reason"])
        result = otns_pcap_timing.derive_air_timing(
            complete,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=2.0,
        )
        self.assertEqual("missing_parent_request", result["failure_reason"])

    def test_ambiguous_multiple_complete_sequences_are_rejected(self) -> None:
        packets = []
        for offset in (0.0, 1.0):
            packets.extend(
                [
                    packet(len(packets) + 1, offset + 0.1, 9, CHILD, TARGET),
                    packet(len(packets) + 2, offset + 0.2, 10, TARGET, CHILD),
                    packet(len(packets) + 3, offset + 0.3, 11, CHILD, TARGET),
                    packet(len(packets) + 4, offset + 0.4, 12, TARGET, CHILD),
                ]
            )
        result = otns_pcap_timing.derive_air_timing(
            packets,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=0.0,
        )
        self.assertFalse(result["complete"])
        self.assertEqual("ambiguous_attach_sequence", result["failure_reason"])

    def test_interval_sum_equals_full_attach(self) -> None:
        result = otns_pcap_timing.extract_air_timing(
            FIXTURE,
            child_extaddr=CHILD,
            target_extaddr=TARGET,
            mode="unicast",
            operation_start_s=185.0,
        )
        timing = result["timing_ms"]
        parts = (
            timing["parent_request_to_response"]
            + timing["parent_response_to_child_id_request"]
            + timing["child_id_request_to_response"]
        )
        self.assertAlmostEqual(timing["parent_request_to_child_id_response"], parts, places=3)

    def test_capture_preserves_internal_timing_and_isolates_parallel_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            outputs = []
            for index in (1, 2):
                runtime = root / f"runtime-{index}"
                results = root / f"results-{index}"
                runtime.mkdir()
                results.mkdir()
                shutil.copy2(FIXTURE, runtime / "current.pcap")
                summary = {
                    "protocol_timing_source": "otns_openthread_event",
                    "protocol_timing_complete": True,
                    "protocol_timing_resolution_us": 1,
                    "protocol_timing_ms": {"parent_response_to_child_id_request": 0.0},
                    "protocol_event_timestamps": {},
                    "mobile_extaddr": CHILD,
                    "target_parent_extaddr": TARGET,
                    "directed_mode": "unicast",
                    "preferred_parent_events": [{"event": "requested", "observed_time_s": 185.0}],
                }
                output = run_baseline.capture_directed_pcap_timing(
                    scenario={"scenario_type": "directed_parent_switch"},
                    summary=summary,
                    runtime_dir=runtime,
                    results_dir=results,
                    token="fixture",
                    network_key=otns_pcap_timing.DEFAULT_THREAD_NETWORK_KEY,
                    tshark="tshark",
                )
                outputs.append(output)
                self.assertEqual(0.0, summary["openthread_event_timing_ms"]["parent_response_to_child_id_request"])
                self.assertEqual(13.648, summary["protocol_timing_ms"]["parent_response_to_child_id_request"])
                self.assertEqual("otns_pcap", summary["protocol_timing_source"])
            self.assertNotEqual(outputs[0], outputs[1])
            self.assertTrue(all(path and path.is_file() for path in outputs))

    def test_aggregate_uses_only_complete_pcap_metrics(self) -> None:
        base = {
            "protocol_timing_source": "otns_pcap",
            "protocol_timing_complete": True,
            "protocol_timing_ms": {
                "parent_request_to_response": 10.0,
                "parent_response_to_child_id_request": 5.0,
                "child_id_request_to_response": 15.0,
                "parent_request_to_child_id_response": 30.0,
            },
        }
        summaries = [dict(base), dict(base)]
        summaries.append(
            {
                "protocol_timing_source": "otns_openthread_event",
                "protocol_timing_complete": True,
                "protocol_timing_ms": {"parent_request_to_child_id_response": 999.0},
            }
        )
        aggregate = analyze_baseline.aggregate_runs(summaries)
        assert aggregate is not None
        self.assertEqual("otns_pcap", aggregate["protocol_timing_source"])
        self.assertEqual(2, aggregate["protocol_timing_complete_runs"])
        self.assertEqual(30.0, aggregate["protocol_timing_stats"]["parent_request_to_child_id_response"]["mean_ms"])


if __name__ == "__main__":
    unittest.main()
