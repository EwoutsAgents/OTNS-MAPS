# Result: med_directed_ucast_fastpr_2routers / 20260713-222308-run01

Deterministic preferred-parent unicast switch using fast-response routers.

## Metadata

- Scenario: `med_directed_ucast_fastpr_2routers`
- Scenario file: `scenarios/directed/med_directed_ucast_fastpr_2routers.yaml`
- Packaged scenario: `scenario.yaml`
- Firmware variant: `phase12-fastpr-2routers-repeated`
- Device profile: `minimal_end_device`
- Thread device type: `None`
- Parent search config: `disabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd`
- Node binary profile: `preferred-parent`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/fastpr-ftd/ot-cli-ftd`
- FTD node binary profile: `fastpr`
- Build config source: `/home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh`
- Equivalent to: `None`
- OpenThread commit: `a12ff0d0f54fd41954b45047fcdd08f302731c5f`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -pcap off -listen localhost:11520 -seed 3223`
- OTNS random seed: `3223`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Runner command: `/usr/bin/python3 /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scripts/run_baseline.py --scenario scenarios/directed/med_directed_ucast_fastpr_2routers.yaml --results-dir /tmp/phase12-parent-switch-repeated-scratch/phase12-fastpr-2routers-repeated/run_003 --timestamp-token 20260713T222308Z --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -pcap off -listen localhost:11520 -seed 3223' --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns --capture-replay --replay-dir /tmp/phase12-parent-switch-repeated-scratch/phase12-fastpr-2routers-repeated/run_003/replay --firmware-variant phase12-fastpr-2routers-repeated --parent-search-config disabled --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c --otns-watch-level note --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd --node-binary-profile preferred-parent --ftd-node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/fastpr-ftd/ot-cli-ftd --ftd-node-binary-profile fastpr --build-config-source /home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh --firmware-source-repo /home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent --copy-results-to-artifact --commit-artifact-dir results/directed_parent_switch_phase12/20260714-002000-experiment/repeated-fastpr-2routers/20260713-222308-run03/20260713-222308-run03`
- OTNS watch level: `note`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_b`
- Pre-movement final parent: `None`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_b`
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
- Parent sequence: `['router_b']`
- Time spent by parent (s): `{'router_b': 360.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `1`
- MLE better parent attach attempts: `0`
- Result classification: `selected_target_reached`
- Node executable provenance: `{'mobile': {'node_id': 3, 'firmware_profile': 'preferred-parent', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd', 'executable_sha256': 'dd6d97f5418bd7f35b1674f32687faa6116afc65d198436070e2cca8bdba3627'}, 'router_a': {'node_id': 1, 'firmware_profile': 'fastpr', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/fastpr-ftd/ot-cli-ftd', 'executable_sha256': '7bc3917e1d80d8f57258b9eb20ce5049351b772dd4da84058cd8391bd0e6c260'}, 'router_b': {'node_id': 2, 'firmware_profile': 'fastpr', 'executable_path': '/home/ewout/.openclaw/workspace-softwaredeveloper/.tmp/openclaw-spikes/phase10-native-timing/artifacts/fastpr-ftd/ot-cli-ftd', 'executable_sha256': '7bc3917e1d80d8f57258b9eb20ce5049351b772dd4da84058cd8391bd0e6c260'}}`
- Directed mode: `unicast`
- Directed random seed: `2903`
- Directed initial parent: `router_a`
- Directed target parent: `router_b`
- Directed command acknowledged: `True`
- Directed final parent: `router_b`
- Directed labels: `['SELECTED_TARGET_REACHED']`
- Directed result: `selected_target_reached`
- Parent ranking events: `0`
- Parent ranking decisions: `{}`
- Parent ranking criteria: `{}`
- Scenario type: `directed_parent_switch`
- Router count: `2`
- Parent before removal: `None`
- Removed parent: `None`
- Parent removal time (s): `305.0`
- Final parent after removal: `None`
- Post-removal switch count: `None`
- Post-removal first switch time (s): `None`
- Post-removal reattach latency (s): `None`

## Parent Ranking

- Ranking CSV: `not captured`
- Preferred-parent event CSV: `preferred_parent_events_20260713T222308Z.csv`
- Integrity checks: `checksums.sha256`

## Node Logs

- `node_log_mobile_3.log`
- `node_log_router_a_1.log`
- `node_log_router_b_2.log`

## Replay

Replay command:

```bash
otns-replay med_directed_ucast_fastpr_2routers_20260713T222308Z.replay
```
