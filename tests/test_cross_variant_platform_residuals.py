import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cross_residuals", ROOT / "analysis/analyze_cross_variant_platform_residuals.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def first_accepted(variant: str):
    directory = ROOT / f"results/{variant}-n100-pcap-comparison-20260919"
    with (directory / "accepted_runs.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    frames = {
        "parent_request": int(row["parent_request_frame"]),
        "parent_response": int(row["parent_response_frame"]),
        "child_id_request": int(row["child_id_request_frame"]),
        "child_id_response": int(row["child_id_response_frame"]),
    }
    return directory / row["pcap_file"], frames


class CrossVariantResidualTests(unittest.TestCase):
    def test_describe_reports_robust_statistics(self):
        stats = MODULE.describe([1, 2, 3, 4, 100])
        self.assertEqual(stats["n"], 5)
        self.assertEqual(stats["median"], 3)
        self.assertEqual(stats["iqr"], 2)
        self.assertGreater(stats["mean"], stats["median"])

    def test_independent_bootstrap_is_deterministic(self):
        first = MODULE.bootstrap_difference([4, 5, 6], [1, 2, 3], "mean", 123, 200)
        second = MODULE.bootstrap_difference([4, 5, 6], [1, 2, 3], "mean", 123, 200)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 3)

    def test_real_unicast_fixture_matches_all_requested_acks(self):
        pcap, frames = first_accepted("fast-attach-ucast-1")
        decoded = MODULE.tshark_frames("tshark", pcap, frames)
        for name in ("parent_request", "parent_response", "child_id_request"):
            self.assertTrue(decoded[f"{name}_ack_requested"])
            self.assertEqual(decoded[f"{name}_ack_match"], "mac_sequence_and_adjacency")
            self.assertNotEqual(decoded[f"{name}_ack_frame"], "")

    def test_real_multicast_fixture_does_not_invent_parent_request_ack(self):
        pcap, frames = first_accepted("stock")
        decoded = MODULE.tshark_frames("tshark", pcap, frames)
        self.assertFalse(decoded["parent_request_ack_requested"])
        self.assertEqual(decoded["parent_request_ack_match"], "unavailable")
        self.assertEqual(decoded["parent_request_ack_frame"], "")
        self.assertEqual(decoded["parent_response_ack_match"], "mac_sequence_and_adjacency")

    def test_full_attach_reconstructs_from_three_legs(self):
        normalized = ROOT / "results/cross-variant-platform-residual-analysis-20260920/normalized_runs.csv"
        with normalized.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 3000)
        for row in rows:
            reconstructed = sum(
                float(row[key])
                for key in (
                    "parent_request_to_response_ms",
                    "parent_response_to_child_id_request_ms",
                    "child_id_request_to_response_ms",
                )
            )
            with self.subTest(platform=row["platform"], source_run=row["source_run"]):
                self.assertAlmostEqual(reconstructed, float(row["full_attach_ms"]), delta=2e-6)


if __name__ == "__main__":
    unittest.main()
