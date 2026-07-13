# Result: fed_simple_parent_switch / 20260713-023636-run01

Simple stock OTNS parent-switching benchmark for a mobile Full End Device. The scenario uses four routers, one mobile end device, straight-line movement, delayed Router B/Router C/Router D activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A and given a fixed Router-A-only attachment window, then moves beyond Router D at a target 5 m/s and dwells at the end to expose late parent switching.

## Metadata

- Scenario: `fed_simple_parent_switch`
- Scenario file: `scenarios/fed_simple_parent_switch.yaml`
- Firmware variant: `stock-fed-pps-on`
- Device profile: `full_end_device`
- Thread device type: `fed`
- Parent search config: `enabled`
- Node binary path: `None`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-on/bin/ot-cli-ftd`
- Build config source: `docs/pps_build_variants.md#pps-enabled-30s`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10030`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `router_a`
- Pre-movement switch count: `42`
- Pre-movement parent events: `[{'phase': 'post_activation_settle', 'sim_time_s': 834.0, 'elapsed_s': 234, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 839.0, 'elapsed_s': 239, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 844.0, 'elapsed_s': 244, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 852.0, 'elapsed_s': 252, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 857.0, 'elapsed_s': 257, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 864.0, 'elapsed_s': 264, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 868.0, 'elapsed_s': 268, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 875.0, 'elapsed_s': 275, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 879.0, 'elapsed_s': 279, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 889.0, 'elapsed_s': 289, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 893.0, 'elapsed_s': 293, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 898.0, 'elapsed_s': 298, 'from_parent': 'router_b', 'to_parent': 'router_c'}, {'phase': 'post_activation_settle', 'sim_time_s': 906.0, 'elapsed_s': 306, 'from_parent': 'router_c', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 918.0, 'elapsed_s': 318, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 923.0, 'elapsed_s': 323, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 930.0, 'elapsed_s': 330, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 934.0, 'elapsed_s': 334, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 946.0, 'elapsed_s': 346, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 956.0, 'elapsed_s': 356, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 971.0, 'elapsed_s': 371, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 981.0, 'elapsed_s': 381, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 983.0, 'elapsed_s': 383, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 997.0, 'elapsed_s': 397, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1006.0, 'elapsed_s': 406, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1016.0, 'elapsed_s': 416, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1019.0, 'elapsed_s': 419, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1027.0, 'elapsed_s': 427, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1028.0, 'elapsed_s': 428, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1044.0, 'elapsed_s': 444, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1049.0, 'elapsed_s': 449, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1063.0, 'elapsed_s': 463, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1078.0, 'elapsed_s': 478, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1104.0, 'elapsed_s': 504, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1113.0, 'elapsed_s': 513, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1128.0, 'elapsed_s': 528, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1139.0, 'elapsed_s': 539, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1152.0, 'elapsed_s': 552, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1160.0, 'elapsed_s': 560, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1164.0, 'elapsed_s': 564, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1173.0, 'elapsed_s': 573, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1187.0, 'elapsed_s': 587, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1198.0, 'elapsed_s': 598, 'from_parent': 'router_b', 'to_parent': 'router_a'}]`
- Final observed parent: `router_d`
- Switch count: `2`
- First switch time (s): `1210.0`
- Second switch time (s): `1245.0`
- Switch position x: `793.75`
- Second switch position x: `2125.0`
- Detach count: `1`
- First detach time (s): `1244.0`
- First detach position x: `2125.0`
- First reattach time (s): `1245.0`
- First reattach position x: `2125.0`
- Reattach latency (s): `1.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_new_parent`
- Packet delivery ratio: `0.993548`
- Total outage (s): `21.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_b', 'router_d']`
- Time spent by parent (s): `{'router_a': 9.0, 'router_b': 34.0, 'router_d': 593.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- MLE parent changes: `44`
- MLE attach attempts: `3`
- MLE better parent attach attempts: `0`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`
- `node_log_router_c_4.log`
- `node_log_router_d_5.log`

## Replay

Replay command:

```bash
otns-replay fed_simple_parent_switch_20260713T023636Z.replay
```
