# Repeated Calibrated MED PPS Comparison

This page describes archived 10-run results from the older wide-geometry calibrated MED scenario. The current active MED scenario is `scenarios/med_simple_parent_switch.yaml`; the current repeated simple-geometry PPS matrix is recorded in [`simple_pps_matrix.md`](simple_pps_matrix.md). Do not mix these metrics with simple-scenario metrics without labeling the geometry difference.

This experiment repeats the calibrated MED Periodic Parent Search comparison from [`pps_med_comparison.md`](pps_med_comparison.md). It remains a stock OpenThread experiment: no MAPS policy or alternate parent-selection algorithm is implemented.

## Design

- Scenario: `scenarios/calibrated_mobile_parent_switch.yaml`
- Repeat count: 10 runs per variant
- Device profile: `mobile_end_device`
- Thread device type: `med`
- Radio model selected by the runner: `MutualInterference`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`

The two explicit stock MTD binaries were:

- PPS off: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- PPS on: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`

The current/default local MED build remains classified as `equivalent_to: stock-med-pps-on` by compile-time configuration inspection. It is not treated as a third repeated-run benchmark arm.

## Commands

PPS off:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 10 \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name med-pps-off-repeated \
  --firmware-variant stock-med-pps-off \
  --thread-device-type med \
  --parent-search-config disabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd \
  --build-config-source 'docs/pps_build_variants.md#pps-disabled' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

PPS on:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 10 \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name med-pps-on-repeated \
  --firmware-variant stock-med-pps-on \
  --thread-device-type med \
  --parent-search-config enabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd \
  --build-config-source 'docs/pps_build_variants.md#pps-enabled' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

Representative MP4s were rendered with:

```bash
python3 scripts/replay_to_mp4.py <replay-file> \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 80 \
  --video-fps 8 \
  --show-log-panel \
  --log-lines 10
```

## Artifacts

The original repeated MED artifacts were pruned from the repository during the
results cleanup. Keep the aggregate table below as a historical note only. The
current tracked artifacts live under the active `results/*simple_parent_switch*`
directories and are summarized in [`simple_pps_matrix.md`](simple_pps_matrix.md).

## Aggregate Comparison

| Metric | stock-med-pps-off repeated | stock-med-pps-on repeated | Interpretation |
|---|---:|---:|---|
| Run count | 10 | 10 | Matched experiment size |
| Switch-observed rate | 0.8 | 0.7 | PPS-off switched in one more run |
| Mean first switch time (s) | 1230.0 | 1231.428571 | Mean switch timing was effectively the same |
| Median first switch time (s) | 1320.0 | 1120.0 | PPS-on median switch was earlier |
| IQR first switch time (s) | 480.0 | 330.0 | PPS-on switch timing was less spread among switch-observed runs |
| Mean switch position x | 766.66675 | 779.853429 | Mean switch position was similar |
| Median switch position x | 858.9745 | 735.897 | PPS-on median spatial reaction was earlier |
| Mean total outage (s) | 158.0 | 144.0 | PPS-on had slightly lower mean outage |
| Median total outage (s) | 140.0 | 100.0 | PPS-on had lower median outage |
| Mean packet delivery ratio | 0.452083 | 0.59375 | PPS-on had higher mean delivery in repeated runs |
| Median packet delivery ratio | 0.453125 | 0.453125 | Median delivery was equal |
| Mean switch count | 0.8 | 0.7 | Neither variant exceeded one switch in a run |
| Oscillation rate | 0.0 | 0.0 | No oscillation observed |

## Interpretation

The repeated result only partially supports the single-run observation. PPS-on still shows an earlier median first switch time, earlier median switch position, lower median outage, and higher mean packet delivery ratio. However, the mean first switch time is essentially unchanged, PPS-on had fewer switch-observed runs, and the median packet delivery ratio was identical.

Across these 10-run samples, PPS-on changed stock behavior but did not produce a uniformly dominant outcome. The strongest repeated evidence is that PPS-on can move the typical observed switch earlier without adding oscillation in this calibrated MED scenario.

## Limitations

- This is a 10-run repeated experiment, not a broad statistical campaign.
- OTNS simulation behavior and packet probing still depend on the calibrated scenario and the selected radio model.
- Only MED/MTD behavior is covered here.
- The comparison uses explicit stock OpenThread compile-time PPS variants only; it does not evaluate MAPS.
- Representative MP4s are visual evidence. CSV and JSON summaries are the metric sources.

## Next Step

Extend PPS on/off comparison to FED and SED profiles after the MED repeated baseline remains reproducible.
