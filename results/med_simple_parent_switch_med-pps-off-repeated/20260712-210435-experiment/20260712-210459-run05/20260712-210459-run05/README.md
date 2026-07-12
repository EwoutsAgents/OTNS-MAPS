# Result: med_simple_parent_switch / 20260712-210459-run01

Simple stock OTNS parent-switching benchmark for a mobile Minimal End Device. The scenario uses three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile is created near Router A so initial attachment is controlled, then moves beyond Router C at a target 5 m/s and dwells at the end to expose late parent switching.

## Metadata

- Scenario: `med_simple_parent_switch`
- Scenario file: `scenarios/med_simple_parent_switch.yaml`
- Firmware variant: `stock-med-pps-off`
- Device profile: `minimal_end_device`
- Thread device type: `med`
- Parent search config: `disabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- FTD node binary path: `None`
- Build config source: `docs/pps_build_variants.md#pps-disabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10030`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `226.0`
- Second switch time (s): `None`
- Switch position x: `1600.0`
- Second switch position x: `None`
- Packet delivery ratio: `0.97546`
- Total outage (s): `28.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_b']`
- Time spent by parent (s): `{'router_a': 32.0, 'router_b': 311.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `2`
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
otns-replay med_simple_parent_switch_20260712T210459Z.replay
```
