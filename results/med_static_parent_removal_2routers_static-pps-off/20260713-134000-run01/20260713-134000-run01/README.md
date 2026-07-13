# Result: med_static_parent_removal_2routers_static-pps-off / 20260713-134000-run01

Static stock OTNS parent-removal benchmark mirroring the ESPHome stock switch-parent test structure with two router-capable devices and one Minimal End Device. Routers are created first, the child is created after a fixed router-settling period, the child's observed current parent is removed, and the child is observed without mobility.

## Metadata

- Scenario: `med_static_parent_removal_2routers`
- Scenario file: `scenarios/static/med_static_parent_removal_2routers.yaml`
- Firmware variant: `stock-med-pps-off`
- Device profile: `minimal_end_device`
- Thread device type: `med`
- Parent search config: `disabled`
- Node binary path: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- FTD node binary path: `None`
- Build config source: `None`
- Equivalent to: `None`
- OpenThread commit: `unknown`
- OTNS commit: `unknown`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1`
- OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OTNS watch level: `info`
- Selected radio model: `MutualInterference`
- Initial observed parent: `None`
- Pre-movement final parent: `None`
- Pre-movement switch count: `0`
- Pre-movement parent events: `[]`
- Final observed parent: `router_b`
- Switch count: `1`
- First switch time (s): `542.0`
- Second switch time (s): `None`
- Switch position x: `375.0`
- Second switch position x: `None`
- Detach count: `1`
- First detach time (s): `541.0`
- First detach position x: `375.0`
- First reattach time (s): `542.0`
- First reattach position x: `375.0`
- Reattach latency (s): `1.0`
- Ended detached: `False`
- Recovery classification: `detached_reattached_same_parent`
- Packet delivery ratio: `1.0`
- Total outage (s): `237.0`
- Oscillation events: `0`
- Parent sequence: `['router_b']`
- Time spent by parent (s): `{'router_b': 124.0}`
- Configured node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- Verified node TX power (dBm): `{'router_a': 0.0, 'router_b': 0.0, 'mobile': 0.0}`
- MLE parent changes: `1`
- MLE attach attempts: `2`
- MLE better parent attach attempts: `0`
- Result classification: `switch_observed`
- Parent ranking events: `1`
- Parent ranking decisions: `{'accept': 1}`
- Parent ranking criteria: `{'two_way_link_margin': 1}`
- Scenario type: `static_parent_removal`
- Router count: `2`
- Parent before removal: `router_a`
- Removed parent: `router_a`
- Parent removal time (s): `305.0`
- Final parent after removal: `router_b`
- Post-removal switch count: `1`
- Post-removal first switch time (s): `542.0`
- Post-removal reattach latency (s): `237.0`

## Parent Ranking

- Ranking CSV: `parent_rank_20260713T134000Z.csv`

## Node Logs

- `node_log_mobile_3.log`
- `node_log_router_a_1.log`
- `node_log_router_b_2.log`

## Replay

Replay command:

```bash
Replay was not captured for this artifact.
```
