# Result: med_static_parent_removal_2routers / 20260919-143000-run01

Static stock OTNS parent-removal benchmark mirroring the ESPHome stock switch-parent test structure with two router-capable devices and one Minimal End Device. Routers are created first, the child is created after a fixed router-settling period, the child's observed current parent is removed, and the child is observed without mobility. Nodes mirror the hardware bench: a horizontal line with the nearest OTNS-representable spacing of 10 cm at the ESP32-C6 default +20 dBm.

## Metadata

- Scenario: `med_static_parent_removal_2routers`
- Scenario file: `scenarios/static/med_static_parent_removal_2routers.yaml`
- Packaged scenario: `scenario.yaml`
- Firmware variant: `otns-fast-attach-corrected-pcap`
- Device profile: `minimal_end_device`
- Thread device type: `med`
- Parent search config: `disabled`
- Node binary path: `/tmp/otns-fast-attach-fixed-build/bin/ot-cli-mtd`
- Node binary profile: `fast-attach`
- FTD node binary path: `/tmp/otns-fast-attach-fixed-build/bin/ot-cli-ftd`
- FTD node binary profile: `fast-attach`
- Build config source: `../ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh`
- Equivalent to: `None`
- OpenThread commit: `a12ff0d0f54fd41954b45047fcdd08f302731c5f`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -listen localhost:57120 -seed 91004 -pcap wpan`
- OTNS random seed: `91004`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Runner command: `/home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/.venv/bin/python /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scripts/run_baseline.py --scenario scenarios/static/med_static_parent_removal_2routers.yaml --results-dir /tmp/fast-attach-final-trace-ltwTgB --timestamp-token 20260919T143000Z --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -listen localhost:57120 -seed 91004 -pcap off' --otns-runtime-dir /tmp/fast-attach-final-trace-ltwTgB/otns_runtime --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns --otns-watch-level note --firmware-variant otns-fast-attach-corrected-pcap --thread-device-type med --parent-search-config disabled --node-binary-path /tmp/otns-fast-attach-fixed-build/bin/ot-cli-mtd --node-binary-profile fast-attach --ftd-node-binary-path /tmp/otns-fast-attach-fixed-build/bin/ot-cli-ftd --ftd-node-binary-profile fast-attach --build-config-source ../ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh --firmware-source-repo ../ESPHome-Thread-ED-Switch-Parent --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f --otns-commit 099a6c2 --copy-results-to-artifact --commit-artifact-dir results/fast-attach-corrected-trace-2routers-20260919`
- OTNS watch level: `note`
- Selected radio model: `MutualInterference`
- Initial observed parent: `None`
- Pre-movement final parent: `None`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `421.0`
- Second switch time (s): `None`
- Switch position x: `1.0`
- Second switch position x: `None`
- Detach count: `1`
- First detach time (s): `420.0`
- First detach position x: `1.0`
- First reattach time (s): `421.0`
- First reattach position x: `1.0`
- Reattach latency (s): `1.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_same_parent`
- Packet delivery ratio: `1.0`
- Total outage (s): `236.0`
- Oscillation events: `0`
- Parent sequence: `['router_b']`
- Time spent by parent (s): `{'router_b': 20.0}`
- Configured node TX power (dBm): `{'router_a': 20.0, 'router_b': 20.0, 'mobile': 20.0}`
- Verified node TX power (dBm): `{'router_a': 20.0, 'router_b': 20.0, 'mobile': 20.0}`
- MLE parent changes: `1`
- MLE attach attempts: `2`
- MLE better parent attach attempts: `0`
- Result classification: `switch_observed`
- Node executable provenance: `{'mobile': {'node_id': 3, 'firmware_profile': 'fast-attach', 'executable_path': '/tmp/otns-fast-attach-fixed-build/bin/ot-cli-mtd', 'executable_sha256': '08d1e625e49c09efc400e02530f78a3fd4b917a9a59dba7f9d9993e653abca6e'}, 'router_a': {'node_id': 1, 'firmware_profile': 'fast-attach', 'executable_path': '/tmp/otns-fast-attach-fixed-build/bin/ot-cli-ftd', 'executable_sha256': '4131ceb4b9ba87aa83981e1fff11dc1c505bf4ef3da2d64e9a62d245e684047a'}, 'router_b': {'node_id': 2, 'firmware_profile': 'fast-attach', 'executable_path': '/tmp/otns-fast-attach-fixed-build/bin/ot-cli-ftd', 'executable_sha256': '4131ceb4b9ba87aa83981e1fff11dc1c505bf4ef3da2d64e9a62d245e684047a'}}`
- Directed mode: `None`
- Directed random seed: `None`
- Directed initial parent: `None`
- Directed target parent: `None`
- Directed command acknowledged: `None`
- Directed final parent: `None`
- Directed labels: `[]`
- Directed result: `None`
- Parent ranking events: `0`
- Parent ranking decisions: `{}`
- Parent ranking criteria: `{}`
- Scenario type: `static_parent_removal`
- Router count: `2`
- Parent before removal: `router_a`
- Removed parent: `router_a`
- Parent removal time (s): `185.0`
- Final parent after removal: `router_b`
- Post-removal switch count: `1`
- Post-removal first switch time (s): `421.0`
- Post-removal reattach latency (s): `236.0`

## Protocol Timing

- Canonical source: `otns_pcap`
- Complete: `True`
- Failure reason: `None`
- OTNS PCAP: `otns_packets_20260919T143000Z.pcap`
- Air timing (ms): `{'parent_request_to_response': 19.736, 'parent_response_to_child_id_request': 5.896, 'child_id_request_to_response': 4.456, 'parent_request_to_child_id_response': 30.088}`
- Internal OpenThread timing: `{'source': None, 'complete': None, 'timestamp_resolution_us': None, 'timing_ms': {}, 'event_timestamps': {}}`

## Parent Ranking

- Ranking CSV: `not captured`
- Preferred-parent event CSV: `not captured`
- Integrity checks: `checksums.sha256`

## Node Logs

- `node_log_mobile_3.log`
- `node_log_router_a_1.log`
- `node_log_router_b_2.log`

## Replay

Replay command:

```bash
Replay was not captured for this artifact.
```
