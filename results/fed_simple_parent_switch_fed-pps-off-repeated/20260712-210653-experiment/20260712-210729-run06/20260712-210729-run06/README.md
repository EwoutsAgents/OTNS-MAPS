# Result: fed_simple_parent_switch / 20260712-210729-run01

Simple stock OTNS parent-switching benchmark for a mobile Full End Device. The scenario uses three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A so initial attachment is controlled, then moves beyond Router C at a target 5 m/s and dwells at the end to expose late parent switching.

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
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10040`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_b`
- Final observed parent: `router_a`
- Switch count: `3`
- First switch time (s): `195.0`
- Second switch time (s): `204.0`
- Switch position x: `550.0`
- Second switch position x: `1000.0`
- Packet delivery ratio: `0.9941`
- Total outage (s): `9.0`
- Oscillation events: `1`
- Parent sequence: `['router_b', 'router_a', 'router_c', 'router_a']`
- Time spent by parent (s): `{'router_b': 4.0, 'router_a': 313.0, 'router_c': 29.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- MLE parent changes: `4`
- MLE attach attempts: `2`
- MLE better parent attach attempts: `0`
- Result classification: `initial_parent_unexpected`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`
- `node_log_router_c_4.log`

## Replay

Replay command:

```bash
otns-replay fed_simple_parent_switch_20260712T210729Z.replay
```
