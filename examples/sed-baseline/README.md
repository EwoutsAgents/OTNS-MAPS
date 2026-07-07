# SED baseline example artifact

This directory contains one curated real OTNS artifact from the SED-specific benchmark scaffold.

It is a format and observability reference, not a statistically meaningful experiment.

## Run details

- Date: 2026-07-07
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9990`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Scenario file: `scenarios/sed_mobile_parent_switch.yaml`
- Selected radio model: `MutualInterference`
- Device profile: `sleepy_end_device`

## Observed result

- Initial parent: `router_a`
- Final parent: `router_a`
- Parent switch observed: `no`
- Packet probes reliable: `no`
- Primary parent observation: `parent_command`

## Why this artifact matters

OTNS did create a real `sed` node for this run. The mobile node remained in `child` state and the `parent` command continued to identify `router_a` across the full trajectory, even after Router B had been introduced and the mobile node had moved toward it.

At the same time, ping-based packet probes remained at 100% loss for the regular SED. That means this artifact is useful for validating the SED benchmark format and parent-observation path, but not for treating ping loss as direct evidence of detachment.

## Known limitations

- This run did not observe a stock SED parent switch.
- Packet probing is not reliable for a regular SED in this setup.
- Scan-derived RSSI/LQI fields remain empty because OTNS `scan` output is not captured synchronously in the current CLI workflow.
- Future work may need CSL or `ssed` experiments if reliable packet-response probing becomes a requirement.
