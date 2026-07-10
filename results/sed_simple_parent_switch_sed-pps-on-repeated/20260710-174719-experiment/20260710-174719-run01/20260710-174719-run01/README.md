# Result: sed_simple_parent_switch / 20260710-174719-run01

Simple stock OTNS parent-switching benchmark for a mobile Sleepy End Device. The scenario uses two routers, one mobile end device, straight-line movement, delayed Router B activation, overlapping intended coverage, and no intentional dead zone. Parent-command output is the primary attachment observation path because ping-based packet probing is not reliable for regular SEDs.

## Metadata

- Scenario: `sed_simple_parent_switch`
- Scenario file: `scenarios/sed_simple_parent_switch.yaml`
- Firmware variant: `stock-sed-pps-on`
- Device profile: `sleepy_end_device`
- Thread device type: `sed`
- Parent search config: `enabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`
- FTD node binary path: `None`
- Build config source: `docs/pps_build_variants.md#pps-enabled`
- Equivalent to: `None`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9990`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `trace`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `1140.0`
- Switch position x: `444.286`
- Packet delivery ratio: `0.022727`
- Total outage (s): `0.0`
- Oscillation events: `0`
- Parent sequence: `['router_a', 'router_b']`
- MLE parent changes: `1`
- MLE attach attempts: `2`
- MLE better parent attach attempts: `1`
- Result classification: `switch_observed`

## Node Logs

- `node_log_mobile_2.log`
- `node_log_router_a_1.log`
- `node_log_router_b_3.log`

## Replay

Replay command:

```bash
otns-replay sed_simple_parent_switch_20260710T174719Z.replay
```

- Rendered from the replay with `python3 scripts/replay_to_mp4.py sed_simple_parent_switch_20260710T174719Z.replay --frame-count 24 --replay-speed 4 --cover-full-replay --end-device-y-offset 80 --video-fps 8 --show-log-panel --log-lines 10`
