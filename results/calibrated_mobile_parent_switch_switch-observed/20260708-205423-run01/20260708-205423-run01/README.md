# Result: calibrated_mobile_parent_switch_switch-observed / 20260708-205423-run01

Stock OTNS parent-switching benchmark variant that stages Router B into the topology after the mobile MED has time to attach to Router A, then moves the MED toward Router B to induce an observable stock parent change, with the mobile node traveling slightly below the routers and dwelling near Router B at the end of the path.

## Metadata

- Scenario: `calibrated_mobile_parent_switch`
- Scenario file: `scenarios/calibrated_mobile_parent_switch.yaml`
- Firmware variant: `stock-openthread`
- OpenThread commit: `7874555ef`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9970 -logfile trace`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `1200.0`
- Packet delivery ratio: `0.447917`
- Total outage (s): `100.0`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay calibrated_mobile_parent_switch_20260708T205423Z.replay
```

- Rendered from the replay with `python3 scripts/replay_to_mp4.py calibrated_mobile_parent_switch_20260708T205423Z.replay --frame-count 72 --replay-speed 4 --cover-full-replay --end-device-y-offset 80 --video-fps 8 --show-log-panel --log-lines 10`
