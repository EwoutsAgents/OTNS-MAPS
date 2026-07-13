# Result: fed_simple_parent_switch / 20260713-014043-run01

Simple stock OTNS parent-switching benchmark for a mobile Full End Device. The scenario uses three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A and given a fixed Router-A-only attachment window, then moves beyond Router C at a target 5 m/s and dwells at the end to expose late parent switching.

## Metadata

- Scenario: `fed_simple_parent_switch`
- Scenario file: `scenarios/fed_simple_parent_switch.yaml`
- Firmware variant: `stock-fed-pps-on`
- Device profile: `full_end_device`
- Thread device type: `fed`
- Parent search config: `enabled`
- Node binary path: `None`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-on/bin/ot-cli-ftd`
- Build config source: `docs/pps_build_variants.md#fed-pps-enabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10080`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Pre-movement final parent: `router_a`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_c`
- Switch count: `1`
- First switch time (s): `1234.0`
- Second switch time (s): `None`
- Switch position x: `1600.0`
- Second switch position x: `None`
- Detach count: `1`
- First detach time (s): `1233.0`
- First detach position x: `1600.0`
- First reattach time (s): `1234.0`
- First reattach position x: `1600.0`
- Reattach latency (s): `1.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_new_parent`
- Packet delivery ratio: `0.990228`
- Total outage (s): `18.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_c']`
- Time spent by parent (s): `{'router_a': 32.0, 'router_c': 593.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `3`
- MLE better parent attach attempts: `0`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`
- `node_log_router_c_4.log`

## Replay

Replay command:

```bash
otns-replay fed_simple_parent_switch_20260713T014043Z.replay
```
