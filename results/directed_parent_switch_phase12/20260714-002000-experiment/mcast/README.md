# Result: med_directed_mcast_4routers / 20260714-002001-run01

Deterministic preferred-parent multicast switch matching the four-router hardware topology.

## Metadata

- Scenario: `med_directed_mcast_4routers`
- Scenario file: `scenarios/directed/med_directed_mcast_4routers.yaml`
- Packaged scenario: `scenario.yaml`
- Firmware variant: `phase12-mcast-4routers`
- Device profile: `minimal_end_device`
- Thread device type: `None`
- Parent search config: `disabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd`
- Node binary profile: `preferred-parent`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd`
- FTD node binary profile: `stock`
- Build config source: `/home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh`
- Equivalent to: `None`
- OpenThread commit: `a12ff0d0f54fd41954b45047fcdd08f302731c5f`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -listen localhost:11400 -web=false -autogo=false -speed 0 -seed 3214 -pcap off`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Runner command: `/usr/bin/python3 /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scripts/run_baseline.py --scenario /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scenarios/directed/med_directed_mcast_4routers.yaml --results-dir /tmp/phase12-parent-switch-scratch/mcast --timestamp-token 20260714T002001Z --otns-command '/home/ewout/go/bin/otns -listen localhost:11400 -web=false -autogo=false -speed 0 -seed 3214 -pcap off' --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd --node-binary-profile preferred-parent --ftd-node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd --ftd-node-binary-profile stock --firmware-variant phase12-mcast-4routers --parent-search-config disabled --build-config-source /home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh --firmware-source-repo /home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c --otns-watch-level info --capture-replay --replay-dir /tmp/phase12-parent-switch-scratch/mcast/replay --copy-results-to-artifact --commit-artifact-dir /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/results/directed_parent_switch_phase12/20260714-002000-experiment/mcast`
- OTNS watch level: `info`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `None`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_a`
- Switch count: `1`
- First switch time (s): `306.0`
- Second switch time (s): `None`
- Switch position x: `375.0`
- Second switch position x: `None`
- Detach count: `0`
- First detach time (s): `None`
- First detach position x: `None`
- First reattach time (s): `None`
- First reattach position x: `None`
- Reattach latency (s): `None`
- Ended detached: `False`
- Recovery classification: `no_detach`
- Packet delivery ratio: `1.0`
- Total outage (s): `1.0`
- Oscillation events: `0`
- Parent sequence: `['router_a']`
- Time spent by parent (s): `{'router_a': 360.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0, 'mobile': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0, 'mobile': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `1`
- MLE better parent attach attempts: `0`
- Result classification: `selected_target_reached`
- Node executable provenance: `{'mobile': {'node_id': 5, 'firmware_profile': 'preferred-parent', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd', 'executable_sha256': 'dd6d97f5418bd7f35b1674f32687faa6116afc65d198436070e2cca8bdba3627'}, 'router_a': {'node_id': 1, 'firmware_profile': 'stock', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd', 'executable_sha256': '6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a'}, 'router_b': {'node_id': 2, 'firmware_profile': 'stock', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd', 'executable_sha256': '6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a'}, 'router_c': {'node_id': 3, 'firmware_profile': 'stock', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd', 'executable_sha256': '6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a'}, 'router_d': {'node_id': 4, 'firmware_profile': 'stock', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/stock-ftd/ot-cli-ftd', 'executable_sha256': '6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a'}}`
- Directed mode: `multicast`
- Directed random seed: `2921`
- Directed initial parent: `router_b`
- Directed target parent: `router_a`
- Directed command acknowledged: `True`
- Directed final parent: `router_a`
- Directed labels: `['SKIP_PARENT_IS_LEADER', 'ROUTER_TOPOLOGY_CHANGED', 'SELECTED_TARGET_REACHED']`
- Directed result: `selected_target_reached`
- Parent ranking events: `0`
- Parent ranking decisions: `{}`
- Parent ranking criteria: `{}`
- Scenario type: `directed_parent_switch`
- Router count: `4`
- Parent before removal: `None`
- Removed parent: `None`
- Parent removal time (s): `305.0`
- Final parent after removal: `None`
- Post-removal switch count: `None`
- Post-removal first switch time (s): `None`
- Post-removal reattach latency (s): `None`

## Parent Ranking

- Ranking CSV: `not captured`
- Preferred-parent event CSV: `preferred_parent_events_20260714T002001Z.csv`
- Integrity checks: `checksums.sha256`

## Node Logs

- `node_log_mobile_5.log`
- `node_log_router_a_1.log`
- `node_log_router_b_2.log`
- `node_log_router_c_3.log`
- `node_log_router_d_4.log`

## Replay

Replay command:

```bash
otns-replay med_directed_mcast_4routers_20260714T002001Z.replay
```
