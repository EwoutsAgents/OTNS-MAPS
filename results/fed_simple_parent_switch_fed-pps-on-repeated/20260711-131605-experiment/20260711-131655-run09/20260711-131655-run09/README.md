# Result: fed_simple_parent_switch / 20260711-131655-run01

Simple stock OTNS parent-switching benchmark for a mobile Full End Device. The scenario uses two routers, one mobile end device, straight-line movement, delayed Router B activation, overlapping intended coverage, and no intentional dead zone. The mobile starts before Router A, moves beyond Router B at a target 5 m/s, then dwells at the end to expose late parent switching.

## Metadata

- Scenario: `fed_simple_parent_switch`
- Scenario file: `scenarios/fed_simple_parent_switch.yaml`
- Firmware variant: `stock-fed-pps-on`
- Device profile: `full_end_device`
- Thread device type: `fed`
- Parent search config: `enabled`
- Node binary path: `None`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-on/bin/ot-cli-ftd`
- Build config source: `docs/pps_build_variants.md#fed-pps-enabled-30s`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10380`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_a`
- Switch count: `0`
- First switch time (s): `None`
- Switch position x: `None`
- Packet delivery ratio: `1.0`
- Total outage (s): `0.0`
- Oscillation events: `0`
- Parent sequence: `['router_a']`
- MLE parent changes: `0`
- MLE attach attempts: `2`
- MLE better parent attach attempts: `0`
- Result classification: `no_switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay fed_simple_parent_switch_20260711T131655Z.replay
```
