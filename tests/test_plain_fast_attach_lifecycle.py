from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import run_baseline


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATCH = (
    ROOT.parent
    / "ESPHome-Thread-ED-Switch-Parent"
    / "patches"
    / "otns"
    / "plain-fast-attach-native-adapter.patch"
)


class PlainFastAttachLifecycleTests(unittest.TestCase):
    def analyze(self, mobile: list[str], routers: list[str], router_count: int = 2):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mobile_path = root / "node_log_mobile_3.log"
            router_path = root / "node_log_router_a_1.log"
            mobile_path.write_text("\n".join(mobile) + "\n", encoding="utf-8")
            router_path.write_text("\n".join(routers) + "\n", encoding="utf-8")
            return run_baseline.analyze_fast_attach_lifecycle(
                [str(mobile_path), str(router_path)], expected=True, router_count=router_count
            )

    def test_complete_post_detach_lifecycle_is_valid(self) -> None:
        result = self.analyze(
            [
                "100 FAST_ATTACH event=attached_seen time_us=100 role=2 enabled=0",
                "200 FAST_ATTACH event=detached_seen time_us=200 role=1",
                "200 FAST_ATTACH event=arm_after_detach time_us=200 role=1 api_error=0 enabled=1",
                "300 [N] FAST_ATTACH event=parent_request_sent scan_mask=0xa0 enabled=1",
                "340 [N] FAST_ATTACH event=acceptable_lq3_response parent=0011223344556677",
                "340 [N] FAST_ATTACH event=early_timer_zero",
                "340 [N] FAST_ATTACH event=child_id_request parent=0011223344556677 enabled=1",
                "350 [N] FAST_ATTACH event=attached_clear enabled=0",
                "350 FAST_ATTACH event=attached_seen time_us=350 role=2 enabled=0",
            ],
            ["320 [N] ParentResponseDelay delay_ms=31 scan_mask=0xa0 child=8899aabbccddeeff"],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(1, result["arm_attempt_count"])
        self.assertTrue(result["ordering_valid"])
        self.assertTrue(result["one_shot_cleared"])
        self.assertEqual([31], result["router_response_delays_ms"])

    def test_compiled_but_unarmed_is_rejected(self) -> None:
        result = self.analyze(
            [
                "100 FAST_ATTACH event=attached_seen time_us=100 role=2 enabled=0",
                "200 FAST_ATTACH event=detached_seen time_us=200 role=1",
                "300 [N] FAST_ATTACH event=parent_request_sent scan_mask=0x80 enabled=0",
            ],
            ["500 [N] ParentResponseDelay delay_ms=300 scan_mask=0x80 child=8899aabbccddeeff"],
        )
        self.assertFalse(result["valid"])
        self.assertEqual("fast_attach_not_armed", result["failure_reason"])

    def test_initial_attach_never_arms_and_router_ceiling_is_enforced(self) -> None:
        initial_only = self.analyze(
            [
                "100 [N] FAST_ATTACH event=parent_request_sent scan_mask=0x80 enabled=0",
                "200 FAST_ATTACH event=attached_seen time_us=200 role=2 enabled=0",
            ],
            [],
        )
        self.assertFalse(initial_only["arm_attempted"])
        excessive_delay = self.analyze(
            [
                "100 FAST_ATTACH event=attached_seen time_us=100 role=2 enabled=0",
                "200 FAST_ATTACH event=detached_seen time_us=200 role=1",
                "200 FAST_ATTACH event=arm_after_detach time_us=200 role=1 api_error=0 enabled=1",
                "300 [N] FAST_ATTACH event=parent_request_sent scan_mask=0xa0 enabled=1",
            ],
            ["310 [N] ParentResponseDelay delay_ms=65 scan_mask=0xa0 child=8899aabbccddeeff"],
        )
        self.assertFalse(excessive_delay["router_delay_rule_valid"])

    def test_duplicate_arm_attempt_is_rejected(self) -> None:
        result = self.analyze(
            [
                "100 FAST_ATTACH event=attached_seen time_us=100 role=2 enabled=0",
                "200 FAST_ATTACH event=detached_seen time_us=200 role=1",
                "200 FAST_ATTACH event=arm_after_detach time_us=200 role=1 api_error=0 enabled=1",
                "201 FAST_ATTACH event=arm_after_detach time_us=201 role=1 api_error=0 enabled=1",
                "300 [N] FAST_ATTACH event=parent_request_sent scan_mask=0xa0 enabled=1",
            ],
            [],
        )
        self.assertFalse(result["valid"])
        self.assertIn("exactly_one_arm_attempt", result["missing_proofs"])

    def test_adapter_uses_public_api_and_is_mtd_only(self) -> None:
        text = ADAPTER_PATCH.read_text(encoding="utf-8")
        self.assertIn("otThreadSetFastAttachEnabled(instance, true)", text)
        self.assertIn("otThreadIsFastAttachEnabled(instance)", text)
        self.assertIn("!OPENTHREAD_FTD", text)
        self.assertNotIn("SetStateDetached(void)", text)

    def test_stock_and_other_variants_are_not_expected_to_prove_lifecycle(self) -> None:
        result = run_baseline.analyze_fast_attach_lifecycle([], expected=False, router_count=4)
        self.assertFalse(result["expected"])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
