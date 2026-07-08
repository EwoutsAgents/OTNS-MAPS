# Artifact: real-baseline

Baseline OTNS scenario with two routers and one mobile MED moving from Router A toward Router B without modifying OpenThread parent selection.

## Metadata

- Scenario: `baseline_mobile_parent_switch`
- Scenario file: `scenarios/baseline_mobile_parent_switch.yaml`
- Firmware variant: `stock-openthread`
- OpenThread commit: `7874555ef`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9970`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_b`
- Final observed parent: `router_b`
- Switch count: `0`
- First switch time (s): `None`
- Packet delivery ratio: `1.0`
- Total outage (s): `0.0`
- Result classification: `no_switch_observed`

## Replay

Replay command:

```bash
otns-replay replay/baseline_mobile_parent_switch_20260708T154911Z.replay
```

Rendered GIF:

- `gif/baseline_mobile_parent_switch_20260708T154911Z.gif`
- Rendered from the replay with `python3 scripts/replay_to_gif.py replay/baseline_mobile_parent_switch_20260708T154911Z.replay --replay-speed 4 --cover-full-replay --end-device-y-offset 40 --gif-frame-duration-ms 500 --show-log-panel`
