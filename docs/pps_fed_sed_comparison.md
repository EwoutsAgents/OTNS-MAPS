# FED and SED PPS Comparison

This page describes archived FED/SED PPS results from the older wide-geometry scenarios. The current active scenarios are `scenarios/fed_simple_parent_switch.yaml` and `scenarios/sed_simple_parent_switch.yaml`; the current repeated simple-geometry PPS matrix is recorded in [`simple_pps_matrix.md`](simple_pps_matrix.md). Do not mix these metrics with simple-scenario metrics without labeling the geometry difference.

This milestone extends the stock OpenThread PPS-off vs PPS-on comparison beyond MED to FED and SED profiles. It does not implement MAPS.

## Scope

- FED scenario: `scenarios/fed_mobile_parent_switch.yaml`
- SED scenario: `scenarios/sed_mobile_parent_switch.yaml`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- Radio model selected by the runner: `MutualInterference`

## Build Provenance

SED uses the existing explicit MTD PPS binaries:

- PPS off: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- PPS on: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`

FED uses explicit FTD PPS binaries:

- PPS off: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-off/bin/ot-cli-ftd`
- PPS on: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-on/bin/ot-cli-ftd`

OTNS maps `fed` and router nodes to the FTD executable family. The FED comparison therefore uses `--ftd-node-binary-path`, which also changes the router FTD executable for the run. This is documented as a limitation. The intended PPS behavioral difference remains the mobile FED's child-side parent search behavior.

## Run Commands

FED PPS off:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/fed_mobile_parent_switch.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name fed-pps-off \
  --firmware-variant stock-fed-pps-off \
  --thread-device-type fed \
  --parent-search-config disabled \
  --ftd-node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-fed-pps-off/bin/ot-cli-ftd \
  --build-config-source 'docs/pps_build_variants.md#fed-pps-disabled' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

FED PPS on used the same command with `fed-pps-on`, `stock-fed-pps-on`, `--parent-search-config enabled`, and the `stock-fed-pps-on/bin/ot-cli-ftd` binary.

SED PPS off:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/sed_mobile_parent_switch.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name sed-pps-off \
  --firmware-variant stock-sed-pps-off \
  --thread-device-type sed \
  --parent-search-config disabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd \
  --build-config-source 'docs/pps_build_variants.md#pps-disabled' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

SED PPS on used the same command with `sed-pps-on`, `stock-sed-pps-on`, `--parent-search-config enabled`, and the `stock-med-pps-on/bin/ot-cli-mtd` binary.

## Single-Run Artifacts

- FED PPS off: `results/.archive/fed_mobile_parent_switch_fed-pps-off/20260710-104510-run01/20260710-104510-run01/`
- FED PPS on: `results/.archive/fed_mobile_parent_switch_fed-pps-on/20260710-104523-run01/20260710-104523-run01/`
- SED PPS off: `results/.archive/sed_mobile_parent_switch_sed-pps-off/20260710-104537-run01/20260710-104537-run01/`
- SED PPS on: `results/.archive/sed_mobile_parent_switch_sed-pps-on/20260710-104550-run01/20260710-104550-run01/`

Each artifact includes CSV, summary JSON, replay, replay metadata JSON, MP4, node logs, manifest, and README.

## Single-Run Metrics

| Metric | FED PPS off | FED PPS on | SED PPS off | SED PPS on |
|---|---:|---:|---:|---:|
| Initial parent | router_a | router_a | router_a | router_a |
| Final parent | router_b | router_b | router_b | router_b |
| First switch time (s) | 1200.0 | 540.0 | 1350.0 | 1110.0 |
| Switch position x | 817.949 | 141.026 | 703.429 | 502.286 |
| Switch count | 1 | 1 | 1 | 1 |
| Total outage (s) | 100.0 | 140.0 | 0.0 | 0.0 |
| Packet delivery ratio | 0.447917 | 0.427083 | 0.013889 | 0.013889 |
| Oscillation events | 0 | 0 | 0 | 0 |
| MLE parent changes | 1 | 1 | 1 | 1 |
| MLE attach attempts | 3 | 2 | 2 | 2 |
| MLE better-parent attach attempts | 0 | 0 | 0 | 1 |

## Repeated Artifacts

The repeated profile extension uses 10 runs per variant with the same explicit stock PPS binaries:

- FED PPS off: `results/.archive/fed_mobile_parent_switch_fed-pps-off-repeated/20260710-163436-experiment/`
- FED PPS on: `results/.archive/fed_mobile_parent_switch_fed-pps-on-repeated/20260710-163514-experiment/`
- SED PPS off: `results/.archive/sed_mobile_parent_switch_sed-pps-off-repeated/20260710-163933-experiment/`
- SED PPS on: `results/.archive/sed_mobile_parent_switch_sed-pps-on-repeated/20260710-164008-experiment/`

Each repeated artifact includes 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, an aggregate summary, a manifest, and one representative MP4.

## Repeated Metrics

| Metric | FED PPS off x10 | FED PPS on x10 | SED PPS off x10 | SED PPS on x10 |
|---|---:|---:|---:|---:|
| Switch-observed rate | 1.0 | 0.9 | 0.5 | 0.8 |
| Mean first switch time (s) | 948.0 | 1035.555556 | 1398.0 | 1290.0 |
| SD first switch time (s) | 430.420983 | 328.142923 | 165.136307 | 159.552947 |
| Median first switch time (s) | 750.0 | 1120.0 | 1350.0 | 1320.0 |
| Mean switch position x | 493.8463 | 612.820556 | 743.6574 | 653.143125 |
| SD switch position x | 358.410499 | 290.638467 | 138.400249 | 133.720492 |
| Mean total outage (s) | 178.0 | 138.0 | 12.0 | 3.0 |
| SD total outage (s) | 107.269132 | 81.894241 | 37.947332 | 9.486833 |
| Median total outage (s) | 170.0 | 120.0 | 0.0 | 0.0 |
| Mean packet delivery ratio | 0.501042 | 0.5625 | 0.008333 | 0.005556 |
| SD packet delivery ratio | 0.120226 | 0.245474 | 0.017568 | 0.007172 |
| Median packet delivery ratio | 0.458334 | 0.4375 | 0.0 | 0.0 |
| Mean switch count | 1.6 | 1.2 | 0.5 | 1.0 |
| SD switch count | 0.966092 | 0.788811 | 0.527046 | 0.816497 |
| Oscillation rate | 0.0 | 0.1 | 0.0 | 0.0 |

## Interpretation

For this single FED run, PPS-on switched much earlier than PPS-off, but the inferred outage duration was higher and packet delivery was slightly lower. No oscillation appeared.

For this single SED run, PPS-on also switched earlier than PPS-off and recorded one better-parent attach attempt. SED packet delivery ratios remain low because regular SED ping response is unreliable in OTNS; parent attachment and switching are interpreted primarily from the parent command and child state.

The repeated FED results do not reproduce the single-run early-switch result for PPS-on. In the 10-run aggregate, PPS-off switches earlier by mean and median timing, while PPS-on has lower mean/median outage and higher mean packet delivery ratio. FED switch counts are higher for PPS-off, while PPS-on has one oscillation run.

The repeated SED results show PPS-on switching in more runs and earlier by mean and median timing. SED packet delivery remains too low to use as primary evidence; parent-command observation remains the main SED signal.

## Limitations

- FED and SED now have 10-run repeated artifacts, but this is still a small sample.
- FED uses the FTD executable family for both the mobile FED and routers in OTNS.
- SED packet delivery ratio is not a reliable connectivity metric.
- For SED, OTNS can return `InvalidState` for the parent command when the mobile node has no valid parent. The runner records empty parent fields for those samples instead of treating that as a failed experiment.
- Scan-derived RSSI/LQI fields are still omitted because live OTNS scan compatibility is inconsistent in this setup.
- No MAPS behavior is implemented.

## Next Step

Use the MED, FED, and SED repeated baselines to decide whether the next experiment should tune stock OpenThread parameters or begin a separate MAPS policy implementation.
