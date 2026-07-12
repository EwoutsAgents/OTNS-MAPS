# Result: med_simple_parent_switch / 20260712-152014-run01

Simple stock OTNS parent-switching benchmark for a mobile Minimal End Device. The scenario uses three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile starts before Router A, moves beyond Router C at a target 5 m/s, then dwells at the end to expose late parent switching.

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
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10180`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_a`
- Switch count: `0`
- First switch time (s): `None`
- Second switch time (s): `None`
- Switch position x: `None`
- Second switch position x: `None`
- Packet delivery ratio: `1.0`
- Total outage (s): `0.0`
- Oscillation events: `0`
- Parent sequence: `['router_a']`
- Time spent by parent (s): `{'router_a': 336.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'mobile': 0.0, 'router_b': 0.0, 'router_c': 0.0}`
- MLE parent changes: `0`
- MLE attach attempts: `1`
- MLE better parent attach attempts: `0`
- Result classification: `no_switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`
- `node_log_router_c_4.log`

## Replay

Replay command:

```bash
otns-replay med_simple_parent_switch_20260712T152014Z.replay
```
