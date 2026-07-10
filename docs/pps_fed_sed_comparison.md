# FED and SED PPS Comparison

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

## Artifacts

- FED PPS off: `results/fed_mobile_parent_switch_fed-pps-off/20260710-104510-run01/20260710-104510-run01/`
- FED PPS on: `results/fed_mobile_parent_switch_fed-pps-on/20260710-104523-run01/20260710-104523-run01/`
- SED PPS off: `results/sed_mobile_parent_switch_sed-pps-off/20260710-104537-run01/20260710-104537-run01/`
- SED PPS on: `results/sed_mobile_parent_switch_sed-pps-on/20260710-104550-run01/20260710-104550-run01/`

Each artifact includes CSV, summary JSON, replay, replay metadata JSON, MP4, node logs, manifest, and README.

## Metrics

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

## Interpretation

For this single FED run, PPS-on switched much earlier than PPS-off, but the inferred outage duration was higher and packet delivery was slightly lower. No oscillation appeared.

For this single SED run, PPS-on also switched earlier than PPS-off and recorded one better-parent attach attempt. SED packet delivery ratios remain low because regular SED ping response is unreliable in OTNS; parent attachment and switching are interpreted primarily from the parent command and child state.

These are single-run profile extensions. They confirm that the FED and SED scaffolds can run with explicit PPS variants, but they do not replace repeated experiments.

## Limitations

- This is single-run evidence for FED and SED.
- FED uses the FTD executable family for both the mobile FED and routers in OTNS.
- SED packet delivery ratio is not a reliable connectivity metric.
- Scan-derived RSSI/LQI fields are still omitted because live OTNS scan compatibility is inconsistent in this setup.
- No MAPS behavior is implemented.

## Next Step

Run repeated FED and SED PPS-off/on trials if these single-run profile results should be strengthened the same way MED was.
