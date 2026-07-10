# Result: med_simple_parent_switch / 20260710-174356-run01

Simple stock OTNS parent-switching benchmark for a mobile Minimal End Device. The scenario uses two routers, one mobile end device, straight-line movement, delayed Router B activation, overlapping intended coverage, and no intentional dead zone.

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
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10000`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_a`
- Switch count: `0`
- First switch time (s): `None`
- Switch position x: `None`
- Packet delivery ratio: `0.9375`
- Total outage (s): `60.0`
- Oscillation events: `0`
- Parent sequence: `['router_a']`
- MLE parent changes: `0`
- MLE attach attempts: `1`
- MLE better parent attach attempts: `0`
- Result classification: `no_switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay med_simple_parent_switch_20260710T174356Z.replay
```
