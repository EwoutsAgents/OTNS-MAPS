# Result: calibrated_mobile_parent_switch / 20260710-023303-run01

Stock OTNS parent-switching benchmark variant that stages Router B into the topology after the mobile MED has time to attach to Router A, then moves the MED toward Router B to induce an observable stock parent change, with the mobile node traveling slightly below the routers and dwelling near Router B at the end of the path.

## Metadata

- Scenario: `calibrated_mobile_parent_switch`
- Scenario file: `scenarios/calibrated_mobile_parent_switch.yaml`
- Firmware variant: `stock-med-pps-off`
- Device profile: `mobile_end_device`
- Thread device type: `med`
- Parent search config: `disabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- Build config source: `docs/pps_build_variants.md#pps-disabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:10000`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `1440.0`
- Switch position x: `900.0`
- Packet delivery ratio: `0.322917`
- Total outage (s): `320.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_b']`
- MLE parent changes: `1`
- MLE attach attempts: `3`
- MLE better parent attach attempts: `0`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay calibrated_mobile_parent_switch_20260710T023303Z.replay
```
