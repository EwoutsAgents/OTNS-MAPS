# Result: sed_simple_parent_switch / 20260713-024216-run01

Simple stock OTNS parent-switching benchmark for a mobile Sleepy End Device. The scenario uses four routers, one mobile end device, straight-line movement, delayed Router B/Router C/Router D activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A and given a fixed Router-A-only attachment window, then moves beyond Router D at a target 5 m/s and dwells at the end to expose late parent switching. Parent-command output is the primary attachment observation path because ping-based packet probing is not reliable for regular SEDs.

## Metadata

- Scenario: `sed_simple_parent_switch`
- Scenario file: `scenarios/sed_simple_parent_switch.yaml`
- Firmware variant: `stock-sed-pps-on`
- Device profile: `sleepy_end_device`
- Thread device type: `sed`
- Parent search config: `enabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`
- FTD node binary path: `None`
- Build config source: `docs/pps_build_variants.md#pps-enabled-30s`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10040`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `router_a`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_d`
- Switch count: `2`
- First switch time (s): `1237.0`
- Second switch time (s): `1613.0`
- Switch position x: `2125.0`
- Second switch position x: `2125.0`
- Detach count: `2`
- First detach time (s): `1234.0`
- First detach position x: `1977.083`
- First reattach time (s): `1237.0`
- First reattach position x: `2125.0`
- Reattach latency (s): `3.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_new_parent`
- Packet delivery ratio: `0.980165`
- Total outage (s): `6.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_c', 'router_d']`
- Time spent by parent (s): `{'router_a': 33.0, 'router_c': 373.0, 'router_d': 225.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0, 'router_d': 0.0}`
- MLE parent changes: `2`
- MLE attach attempts: `4`
- MLE better parent attach attempts: `2`
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
otns-replay sed_simple_parent_switch_20260713T024216Z.replay
```
