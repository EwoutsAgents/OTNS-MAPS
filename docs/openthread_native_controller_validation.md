# OpenThread-native preferred-parent validation

Date: 2026-07-19

This report covers the controller in
`openthread-preferred-parent-controller.patch` at OpenThread
`a12ff0d0f54fd41954b45047fcdd08f302731c5f`. It supersedes the adapter-owned
controller results in `validation_ladder.md`; those older results remain as
historical evidence.

## Isolated builds

All four profiles built with warnings as errors using GCC 13.3.0. The stock
source clone had no preferred-parent patch or `PREFPARENT` binary marker.
ParentRank instrumentation was disabled.

| Profile | Preferred parent | FastPR | SHA-256 |
| --- | ---: | ---: | --- |
| stock MTD, PPS off | 0 | 0 | `f800652afcbbd52caeb22dcd8369647824b0160ec72efdc0957a8d65c54f1428` |
| preferred-parent MTD, PPS off | 1 | 0 | `bd4fb4d30dbffda2301416b69c84f01dfcefeafefc196dac1e0d5ae6914f02dc` |
| stock FTD | 0 | 0 | `5337afebc134b4b35770cb91985ee24c8be651f2034a4f05bf0f15f1b443ba04` |
| FastPR FTD | 0 | 1 | `83ff3c49556151a6439fa8ab6a29daf59124cdfcdb63ee840193c8f76cba0d49` |

## API and CLI checks

The live native CLI accepted compact and colon-separated extended addresses.
Invalid length, invalid hex, missing mode, and unknown mode returned
`InvalidArgs`. A second start returned `Busy`. `cancel` emitted `cancelled`,
`clear` emitted `cleared`, and final status was `idle` with a zero target.

## Packet-level two-router checks

The directed scenarios preserve the current parent during discovery. PCAPs
were captured from the fixed controller runs. In the operation window:

- multicast used destination `0xffff` and produced one Parent Request;
- unicast and FastPR used the selected router's extended address and produced
  one Parent Request each;
- the multicast target was `0a2e199c3eaeb65d`; a non-target response arrived
  first, but the single Child ID Request addressed the target;
- every case had exactly one target Parent Response, one target Child ID
  Request, and one Child ID Response;
- FastPR had no delayed duplicate target Parent Response in the three-second
  validation window.

## Four-router results

Each variant reached the requested target and emitted
`requested -> parent_request_started -> target_response ->
child_id_request_started -> succeeded`.

| Variant | Parent Request -> target response | Target response -> Child ID Request | Child ID Request -> response | Full attach |
| --- | ---: | ---: | ---: | ---: |
| multicast | 254.120 ms | 0.000 ms | 10.768 ms | 264.888 ms |
| unicast | 408.104 ms | 0.000 ms | 13.648 ms | 421.752 ms |
| FastPR unicast | 18.768 ms | 0.000 ms | 9.808 ms | 28.576 ms |

The 0 ms continuation interval is native OpenThread event timing, not an
artificial simulation delay. The three scenarios use different deterministic
targets and are functional smoke tests, not paired performance trials.

## Regression found during validation

The initial multicast run reached the requested parent but reported
`InvalidState`. OpenThread's ordinary Child ID Response path temporarily calls
`SetStateDetached()` before `SetStateChild()`, and role-change cleanup treated
that expected internal transition as external failure. The controller now
guards only that bounded completion section; external role changes still fail
and clean up the operation. All three variants succeeded after rebuilding.

## Four-router ESP32-C6 results

The hardware profiles used ESP-IDF 5.5.4, its vendored OpenThread commit
`a12ff0d0f54fd41954b45047fcdd08f302731c5f`, and GCC 14.2.0. Each run kept the
initial parent online and selected a different router. Results are stored below
`testing/logs/openthread-native-controller` in the ESPHome repository; the
archived ESPHome-controller baseline was not modified.

| Variant | Run | Parent Request -> target response | Target response -> Child ID Request | Child ID Request -> response | Full attach |
| --- | --- | ---: | ---: | ---: | ---: |
| multicast | `mcast/20260719-175519` | 464 ms | 10 ms | 14 ms | 488 ms |
| unicast | `ucast/20260719-181635` | 251 ms | 11 ms | 13 ms | 275 ms |
| FastPR unicast | `ucast_fastpr-4router-1runs-20260719-182908/20260719-183732-run01` | 9 ms | 11 ms | 12 ms | 32 ms |

The PCAP operation window contained exactly one Parent Request, one target
Parent Response, and one target Child ID Request in each case. Multicast used
destination `0xffff`; both unicast cases addressed only the selected extended
address. FastPR produced one target response and no delayed duplicate during
the six-minute observation window. The unicast and FastPR child logs emitted
`requested -> parent_request_started -> target_response ->
child_id_request_started -> succeeded`.

A final serial-only smoke test verified the shortened ESPHome event contract
fits its fixed log buffer, including the complete line
`PREFPARENT event=succeeded parent=36a24035d9276591`. Its first command named
the already-current parent and terminated cleanly with `error=Already`; a
second operation selected another live router and succeeded.

Two integration defects were exposed before the completed multicast run. The
thin ESPHome adapter initially registered its callback before the OpenThread
instance lock existed, and the hardware runner still depended on an old
adapter-controller parent log. The adapter now initializes immediately after
OpenThread; the runner identifies the current parent from the child and router
RLOC16 values. The skipped captures remain in the new result directory as
failure evidence. A first build-only attempt outside the Git checkout also
exposed ESP-IDF's archive revision lookup constraint; no board was flashed in
that attempt, and isolated build roots now live under the repository's ignored
testing cache directories.

## Remaining ladder step

No repeated 24-run simulation or hardware campaign was started. The single-run
results are ready for review before approving a repeated comparison.
