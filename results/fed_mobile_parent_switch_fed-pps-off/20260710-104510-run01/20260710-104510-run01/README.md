# Result: fed_mobile_parent_switch_fed-pps-off / 20260710-104510-run01

Stock OTNS parent-switching benchmark variant for a mobile Full End Device. The scenario mirrors the calibrated delayed-router MED setup, but uses a FED so the mobile child is built from OTNS's FTD executable path.

## Metadata

- Scenario: `fed_mobile_parent_switch`
- Scenario file: `scenarios/fed_mobile_parent_switch.yaml`
- Firmware variant: `stock-fed-pps-off`
- Device profile: `full_end_device`
- Thread device type: `fed`
- Parent search config: `disabled`
- Node binary path: `None`
- FTD node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-off/bin/ot-cli-ftd`
- Build config source: `docs/pps_build_variants.md#fed-pps-disabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `1200.0`
- Switch position x: `817.949`
- Packet delivery ratio: `0.447917`
- Total outage (s): `100.0`
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
otns-replay fed_mobile_parent_switch_20260710T104510Z.replay
```

- Rendered from the replay with `python3 scripts/replay_to_mp4.py fed_mobile_parent_switch_20260710T104510Z.replay --frame-count 24 --replay-speed 4 --cover-full-replay --end-device-y-offset 80 --video-fps 8 --show-log-panel --log-lines 10`
