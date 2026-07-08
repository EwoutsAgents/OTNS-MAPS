# Artifact: sed-baseline

Stock OTNS parent-switching benchmark variant for a mobile Sleepy End Device. The scenario mirrors the calibrated delayed-router setup, but uses a SED and treats parent-command output as the primary attachment observation path because ping-based packet probing is not reliable for regular SEDs.

## Metadata

- Scenario: `sed_mobile_parent_switch`
- Scenario file: `scenarios/sed_mobile_parent_switch.yaml`
- Firmware variant: `stock-openthread`
- OpenThread commit: `7874555ef`
- OTNS commit: `099a6c2`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9990`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `1560.0`
- Packet delivery ratio: `0.0`
- Total outage (s): `0.0`
- Result classification: `switch_observed`

## Replay

Replay command:

```bash
otns-replay replay/sed_mobile_parent_switch_20260708T154943Z.replay
```

Rendered GIF:

- `gif/sed_mobile_parent_switch_20260708T154943Z.gif`
- Rendered from the replay with `python3 scripts/replay_to_gif.py replay/sed_mobile_parent_switch_20260708T154943Z.replay --replay-speed 4 --cover-full-replay --end-device-y-offset 40 --gif-frame-duration-ms 500 --show-log-panel`
