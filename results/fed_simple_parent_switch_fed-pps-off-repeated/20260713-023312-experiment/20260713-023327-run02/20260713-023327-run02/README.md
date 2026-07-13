# Result: fed_simple_parent_switch / 20260713-023327-run01

Simple stock OTNS parent-switching benchmark for a mobile Full End Device. The scenario uses four routers, one mobile end device, straight-line movement, delayed Router B/Router C/Router D activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A and given a fixed Router-A-only attachment window, then moves beyond Router D at a target 5 m/s and dwells at the end to expose late parent switching.

## Metadata

- Scenario: `fed_simple_parent_switch`
- Scenario file: `scenarios/fed_simple_parent_switch.yaml`
- Firmware variant: `stock-fed-pps-off`
- Device profile: `full_end_device`
- Thread device type: `fed`
- Parent search config: `disabled`
- Node binary path: `None`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-off/bin/ot-cli-ftd`
- Build config source: `docs/pps_build_variants.md#pps-disabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10000`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `router_a`
- Pre-movement switch count: `22`
- Pre-movement parent events: `[{'phase': 'post_activation_settle', 'sim_time_s': 988.0, 'elapsed_s': 388, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 991.0, 'elapsed_s': 391, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1001.0, 'elapsed_s': 401, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1005.0, 'elapsed_s': 405, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1021.0, 'elapsed_s': 421, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1028.0, 'elapsed_s': 428, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1036.0, 'elapsed_s': 436, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1042.0, 'elapsed_s': 442, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1060.0, 'elapsed_s': 460, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1067.0, 'elapsed_s': 467, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1086.0, 'elapsed_s': 486, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1089.0, 'elapsed_s': 489, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1108.0, 'elapsed_s': 508, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1114.0, 'elapsed_s': 514, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1134.0, 'elapsed_s': 534, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1147.0, 'elapsed_s': 547, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1166.0, 'elapsed_s': 566, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1174.0, 'elapsed_s': 574, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1179.0, 'elapsed_s': 579, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1183.0, 'elapsed_s': 583, 'from_parent': 'router_b', 'to_parent': 'router_a'}, {'phase': 'post_activation_settle', 'sim_time_s': 1192.0, 'elapsed_s': 592, 'from_parent': 'router_a', 'to_parent': 'router_b'}, {'phase': 'post_activation_settle', 'sim_time_s': 1197.0, 'elapsed_s': 597, 'from_parent': 'router_b', 'to_parent': 'router_a'}]`
- Final observed parent: `router_d`
- Switch count: `2`
- First switch time (s): `1215.0`
- Second switch time (s): `1245.0`
- Switch position x: `1040.278`
- Second switch position x: `2125.0`
- Detach count: `1`
- First detach time (s): `1244.0`
- First detach position x: `2125.0`
- First reattach time (s): `1245.0`
- First reattach position x: `2125.0`
- Reattach latency (s): `1.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_new_parent`
- Packet delivery ratio: `0.991909`
- Total outage (s): `24.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_b', 'router_d']`
- Time spent by parent (s): `{'router_a': 14.0, 'router_b': 29.0, 'router_d': 593.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- MLE parent changes: `24`
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
otns-replay fed_simple_parent_switch_20260713T023327Z.replay
```
