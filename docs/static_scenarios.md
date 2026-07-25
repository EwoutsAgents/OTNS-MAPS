# Static Parent-Removal Scenarios

The static scenarios mirror the structure of the local ESPHome stock
switch-parent tests in `ESPHome-Thread-ED-Switch-Parent/testing`.

## Scenario Matrix

- `scenarios/static/med_static_parent_removal_2routers.yaml`
- `scenarios/static/med_static_parent_removal_3routers.yaml`
- `scenarios/static/med_static_parent_removal_4routers.yaml`
- `scenarios/static/med_static_parent_removal_low_power_2routers.yaml`
- `scenarios/static/med_static_parent_removal_low_power_3routers.yaml`
- `scenarios/static/med_static_parent_removal_low_power_4routers.yaml`

Each scenario uses stock OpenThread behavior, one static Minimal End Device, and
2, 3, or 4 router-capable nodes.

The `low_power` scenarios match the hardware `stock_low_power` variants:
Routers 1/2 and the MED use +20 dBm, while present Routers 3/4 use -15 dBm.
This keeps all routers connected at the 10 cm bench spacing but makes the
remaining +20 dBm router the stronger second-attach candidate. Run these
scenarios with the stock MTD and the separately built
`stock-ftd-delay-diagnostic` FTD. The diagnostic changes only logging and emits
the actual delay selected by `GenerateRandomDelay()` for exact subtraction from
the packet-derived Parent Request to Parent Response interval.

## Timing

The timing matches the ESPHome stock test configuration:

- Routers are created first.
- Router settling delay: 300 s.
- The child is then created.
- Child attach observation delay: 5 s.
- The child's observed current parent is removed with OTNS `del <node-id>`.
- Post-removal observation delay: 360 s.

## Geometry

All nodes are placed close together on one horizontal line with
`MeterPerUnit = 0.1`. Adjacent integer coordinates are therefore 10 cm apart.

| Scenario | Router positions | Mobile position |
|---|---|---|
| 2 routers | `(0,0)`, `(2,0)` | `(1,0)` |
| 3 routers | `(0,0)`, `(1,0)`, `(3,0)` | `(2,0)` |
| 4 routers | `(0,0)`, `(1,0)`, `(3,0)`, `(4,0)` | `(2,0)` |

## ESPHome Stock Correspondence

The ESPHome stock child explicitly disables MTD periodic parent search with:

```yaml
CONFIG_OPENTHREAD_PARENT_SEARCH_MTD: n
```

For the closest OTNS-MAPS equivalent, run these scenarios with the local
PPS-disabled MTD binary and record `--parent-search-config disabled`:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/static/med_static_parent_removal_4routers.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd \
  --parent-search-config disabled \
  --otns-watch-level info
```

The `--otns-watch-level info` flag is optional for ordinary summary metrics, but
is required if ParentRank log parsing should produce `parent_rank_<timestamp>.csv`.
