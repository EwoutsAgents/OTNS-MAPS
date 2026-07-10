# Result: calibrated_mobile_parent_switch_med-pps-on / 20260710-020715-run01

Stock OTNS parent-switching benchmark variant that stages Router B into the topology after the mobile MED has time to attach to Router A, then moves the MED toward Router B to induce an observable stock parent change, with the mobile node traveling slightly below the routers and dwelling near Router B at the end of the path.

## Metadata

- Scenario: `calibrated_mobile_parent_switch`
- Scenario file: `scenarios/calibrated_mobile_parent_switch.yaml`
- Firmware variant: `stock-med-pps-on`
- Device profile: `mobile_end_device`
- Thread device type: `med`
- Parent search config: `enabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`
- Build config source: `cmake -G "Unix Makefiles" ... -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1 -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1; make ot-cli-mtd`
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
- First switch time (s): `1100.0`
- Packet delivery ratio: `0.5`
- Total outage (s): `0.0`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay calibrated_mobile_parent_switch_20260710T020715Z.replay
```

- Rendered from the replay with `python3 scripts/replay_to_mp4.py calibrated_mobile_parent_switch_20260710T020715Z.replay --frame-count 24 --replay-speed 4 --cover-full-replay --end-device-y-offset 80 --video-fps 8 --show-log-panel --log-lines 10`
