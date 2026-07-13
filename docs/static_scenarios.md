# Static Parent-Removal Scenarios

The static scenarios mirror the structure of the local ESPHome stock
switch-parent tests in `ESPHome-Thread-ED-Switch-Parent/testing`.

## Scenario Matrix

- `scenarios/static/med_static_parent_removal_2routers.yaml`
- `scenarios/static/med_static_parent_removal_3routers.yaml`
- `scenarios/static/med_static_parent_removal_4routers.yaml`

Each scenario uses stock OpenThread behavior, one static Minimal End Device, and
2, 3, or 4 router-capable nodes.

## Timing

The timing matches the ESPHome stock test configuration:

- Routers are created first.
- Router settling delay: 300 s.
- The child is then created.
- Child attach observation delay: 5 s.
- The child's observed current parent is removed with OTNS `del <node-id>`.
- Post-removal observation delay: 360 s.

## Geometry

All nodes are placed close together on one horizontal line. Router spacing is
150 OTNS coordinate units, which is 15 m with the default
`MeterPerUnit = 0.1`.

| Scenario | Router positions | Mobile position |
|---|---|---|
| 2 routers | `(300,300)`, `(450,300)` | `(375,300)` |
| 3 routers | `(300,300)`, `(450,300)`, `(600,300)` | `(375,300)` |
| 4 routers | `(300,300)`, `(450,300)`, `(600,300)`, `(750,300)` | `(375,300)` |

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
