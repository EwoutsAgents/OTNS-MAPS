# Result: calibrated_mobile_parent_switch_switch-observed / 20260707-192927-run01

Tracked OTNS benchmark result.

## Metadata

- Scenario: `calibrated_mobile_parent_switch`
- Scenario file: `scenarios/calibrated_mobile_parent_switch.yaml`
- Firmware variant: `stock-openthread`
- OpenThread commit: `7874555ef`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9960`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `960.0`
- Packet delivery ratio: `0.4625`
- Total outage (s): `60.0`
- Result classification: `switch_observed`

## Replay

Replay command:

```bash
otns-replay calibrated_mobile_parent_switch_20260707T192927Z.replay
```

- Rendered from the replay with `python3 scripts/replay_to_mp4.py calibrated_mobile_parent_switch_20260707T192927Z.replay --replay-speed 4 --cover-full-replay --end-device-y-offset 40 --video-fps 3 --show-log-panel --log-lines 10`
