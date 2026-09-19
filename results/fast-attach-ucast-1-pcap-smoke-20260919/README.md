# Result: med_directed_ucast_fast_attach_1_2routers / 20260919-091500-run01

Deterministic Fast Attach (fixed 1 ms) preferred-parent unicast switch matching the ESPHome hardware procedure.

## Metadata

- Scenario: `med_directed_ucast_fast_attach_1_2routers`
- Scenario file: `scenarios/directed/med_directed_ucast_fast_attach_1_2routers.yaml`
- Packaged scenario: `scenario.yaml`
- Firmware variant: `otns-fast-attach-ucast-1-pcap`
- Device profile: `minimal_end_device`
- Thread device type: `med`
- Parent search config: `disabled`
- Node binary path: `/tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-mtd`
- Node binary profile: `fast-attach-ucast-1`
- FTD node binary path: `/tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd`
- FTD node binary profile: `fast-attach-ucast-1`
- Build config source: `None`
- Equivalent to: `None`
- OpenThread commit: `a12ff0d0f54fd41954b45047fcdd08f302731c5f`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -listen localhost:30000 -seed 9101 -pcap wpan`
- OTNS random seed: `9101`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Runner command: `/home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/.venv/bin/python /home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scripts/run_baseline.py --scenario scenarios/directed/med_directed_ucast_fast_attach_1_2routers.yaml --results-dir results/smoke/fast-attach-ucast-1-pcap-smoke-20260919 --timestamp-token 20260919T091500Z --directed-random-seed 9101 --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -listen localhost:30000 -seed 9101 -pcap off' --otns-runtime-dir results/smoke/fast-attach-ucast-1-pcap-smoke-20260919/otns_runtime --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns --otns-watch-level note --firmware-variant otns-fast-attach-ucast-1-pcap --thread-device-type med --parent-search-config disabled --node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-mtd --node-binary-profile fast-attach-ucast-1 --ftd-node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd --ftd-node-binary-profile fast-attach-ucast-1 --firmware-source-repo ../ESPHome-Thread-ED-Switch-Parent --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f --otns-commit 099a6c2 --copy-results-to-artifact --commit-artifact-dir results/fast-attach-ucast-1-pcap-smoke-20260919`
- OTNS watch level: `note`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `None`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_a`
- Switch count: `1`
- First switch time (s): `186.0`
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
- Total outage (s): `0.0`
- Oscillation events: `0`
- Parent sequence: `['router_a']`
- Time spent by parent (s): `{'router_a': 255.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `1`
- MLE better parent attach attempts: `0`
- Result classification: `selected_target_reached`
- Node executable provenance: `{'mobile': {'node_id': 3, 'firmware_profile': 'fast-attach-ucast-1', 'executable_path': '/tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-mtd', 'executable_sha256': '7089140d3296f0c5ac612623afa34813fd7c0bfa015f4193c0713c57c4cf26a5'}, 'router_a': {'node_id': 1, 'firmware_profile': 'fast-attach-ucast-1', 'executable_path': '/tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd', 'executable_sha256': 'e412cec50dbe9e68620e59154f03a257d89cd06cbff24d61cd0b1d89856b7621'}, 'router_b': {'node_id': 2, 'firmware_profile': 'fast-attach-ucast-1', 'executable_path': '/tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd', 'executable_sha256': 'e412cec50dbe9e68620e59154f03a257d89cd06cbff24d61cd0b1d89856b7621'}}`
- Directed mode: `unicast`
- Directed random seed: `9101`
- Directed initial parent: `router_b`
- Directed target parent: `router_a`
- Directed command acknowledged: `True`
- Directed final parent: `router_a`
- Directed labels: `['SKIP_PARENT_IS_LEADER', 'SELECTED_TARGET_REACHED']`
- Directed result: `selected_target_reached`
- Parent ranking events: `0`
- Parent ranking decisions: `{}`
- Parent ranking criteria: `{}`
- Scenario type: `directed_parent_switch`
- Router count: `2`
- Parent before removal: `None`
- Removed parent: `None`
- Parent removal time (s): `None`
- Final parent after removal: `None`
- Post-removal switch count: `None`
- Post-removal first switch time (s): `None`
- Post-removal reattach latency (s): `None`

## Protocol Timing

- Canonical source: `otns_pcap`
- Complete: `True`
- Failure reason: `None`
- OTNS PCAP: `otns_packets_20260919T091500Z.pcap`
- Air timing (ms): `{'child_id_request_to_response': 8.296, 'parent_request_to_child_id_response': 31.928, 'parent_request_to_response': 4.04, 'parent_response_to_child_id_request': 19.592}`
- Internal OpenThread timing (ms): `{'child_id_request_to_response': 27.024, 'parent_request_to_child_id_response': 38.976, 'parent_request_to_response': 11.952, 'parent_response_to_child_id_request': 0.0}`

## Parent Ranking

- Ranking CSV: `not captured`
- Preferred-parent event CSV: `preferred_parent_events_20260919T091500Z.csv`
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
