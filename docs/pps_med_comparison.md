# Calibrated MED PPS Comparison

## Purpose

This experiment isolates OpenThread Periodic Parent Search (PPS) in the calibrated MED mobility scenario before any MAPS policy is implemented.

Scenario:

```text
scenarios/calibrated_mobile_parent_switch.yaml
```

Comparison arms:

```text
stock-med-pps-off
stock-med-pps-on
```

The current/default MED build is not treated as a third independent arm. It is classified as `equivalent_to: stock-med-pps-on` because the local simulation platform config defines `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE 1` when the build does not pass an explicit value.

## Build provenance

- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- PPS-off MTD binary: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
- PPS-on MTD binary: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`
- Build details: [`pps_build_variants.md`](pps_build_variants.md)

## Commands run

PPS off:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name med-pps-off \
  --firmware-variant stock-med-pps-off \
  --thread-device-type med \
  --parent-search-config disabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd \
  --build-config-source 'cmake -G "Unix Makefiles" ... -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0 -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0; make ot-cli-mtd' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

PPS on:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name med-pps-on \
  --firmware-variant stock-med-pps-on \
  --thread-device-type med \
  --parent-search-config enabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd \
  --build-config-source 'cmake -G "Unix Makefiles" ... -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1 -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1; make ot-cli-mtd' \
  --openthread-commit 7874555efb1772bad66049ab06a78a2ce0c925f3 \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c
```

Replay rendering:

```bash
python3 scripts/replay_to_mp4.py <artifact>/<replay>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 80 \
  --video-fps 8 \
  --show-log-panel \
  --log-lines 10
```

## Artifact locations

- PPS off: `results/calibrated_mobile_parent_switch_med-pps-off/20260710-020657-run01/20260710-020657-run01/`
- PPS on: `results/calibrated_mobile_parent_switch_med-pps-on/20260710-020715-run01/20260710-020715-run01/`

Each directory contains CSV, summary JSON, replay, replay metadata JSON, MP4, node logs, manifest, and README.

## Metric comparison

| Metric | stock-med-pps-off | stock-med-pps-on | Interpretation |
|---|---:|---:|---|
| Initial parent | router_a | router_a | Both started from Router A |
| Final parent | router_b | router_b | Both eventually selected Router B |
| First switch time (s) | 1440.0 | 1100.0 | PPS-on switched earlier in this run |
| Switch count | 1 | 1 | No extra parent changes were observed |
| Switch position x | 900.0 | 715.385 | PPS-on switched before reaching Router B |
| Total outage (s) | 140.0 | 0.0 | PPS-on avoided inferred outage in this run |
| Packet delivery ratio | 0.833333 | 0.5 | PPS-on had lower aggregate ping delivery despite no inferred outage |
| Oscillation events | 0 | 0 | No A-B-A oscillation observed |
| Parent sequence | router_a, router_b | router_a, router_b | Same compact parent sequence |
| MLE Parent Changes | not parsed | not parsed | Raw counters are retained in CSV/logs |
| MLE Attach Attempts | in CSV/logs | in CSV/logs | Analyze directly from `mle_counters_json` if needed |
| Result classification | switch_observed | switch_observed | Both runs observed one switch |

## Interpretation

For this single calibrated MED run, explicit PPS-on caused the MED to switch earlier than PPS-off and eliminated the runner's inferred outage window. It did not increase observed switch count or oscillation.

The aggregate packet delivery ratio was lower for PPS-on because the run had fewer successful ping replies overall. That should be interpreted cautiously: the packet probes are useful for this MED benchmark, but a single run is not a statistical result.

## Limitations

- This is a single-run comparison, not a repeated experiment.
- The default build classification is based on compile-time configuration inspection, not a separate benchmark arm.
- MLE Parent Changes are not yet promoted to first-class analysis metrics; raw MLE counters and trace logs are preserved.
- Replay rendering worked, but the MP4 is visual evidence only. The CSV and JSON summaries are the metric sources.

## Next step

Run repeated trials for both explicit MED variants, then extend the PPS on/off comparison to FED and SED profiles.
