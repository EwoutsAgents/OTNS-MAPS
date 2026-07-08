# Artifact: calibrated-med-switch-observed

Stock OTNS parent-switching benchmark variant that stages Router B into the topology after the mobile MED has time to attach to Router A, then moves the MED toward Router B to induce an observable stock parent change.

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
otns-replay replay/calibrated_mobile_parent_switch_20260707T192927Z.replay
```

Rendered GIF:

- `gif/calibrated_mobile_parent_switch_20260707T192927Z.gif`
- Rendered from the replay with `python3 scripts/replay_to_gif.py replay/calibrated_mobile_parent_switch_20260707T192927Z.replay --replay-speed 4 --cover-full-replay --end-device-y-offset 40 --gif-frame-duration-ms 500 --show-log-panel`
