# OTNS-MAPS baseline benchmark design

## Research goal

The first milestone is a stock-behaviour reference benchmark for OpenThread under mobility. The goal is to measure how late, unstable, or costly parent switching is when one mobile end device moves from one candidate parent toward another in OTNS.

This benchmark is intentionally not a new parent-selection algorithm. It measures unmodified OpenThread behaviour only.

## Scenario design

The repository currently carries three closely related stock scenarios:

- `baseline_mobile_parent_switch` is the original reference setup.
- `calibrated_mobile_parent_switch` delays Router B introduction so the mobile node first has time to attach to Router A before movement begins.
- `sed_mobile_parent_switch` applies the delayed-router idea to a mobile Sleepy End Device and shifts primary observability away from ping replies.

All scenarios use three nodes:

- Router A
- Router B
- one mobile end device

The original baseline uses a direct two-router topology with the movement path defined in [`../scenarios/baseline_mobile_parent_switch.yaml`](../scenarios/baseline_mobile_parent_switch.yaml).

The calibrated variant is defined in [`../scenarios/calibrated_mobile_parent_switch.yaml`](../scenarios/calibrated_mobile_parent_switch.yaml). It uses a pre-movement stabilization phase:

1. Router A and the mobile MED are created first.
2. The mobile MED is allowed to attach to Router A.
3. Router B is introduced later.
4. A further settle period runs before movement starts.

This keeps the benchmark within stock OTNS/OpenThread behavior while making initial attachment to Router A much more likely.

The initial baseline and calibrated switch-attempt scenarios use a MED instead of a regular SED. OTNS CLI documentation notes that a regular SED typically does not respond to ping traffic, which makes packet-delivery measurement less direct for a first benchmark.

The SED variant is defined in [`../scenarios/sed_mobile_parent_switch.yaml`](../scenarios/sed_mobile_parent_switch.yaml). It keeps the delayed Router B introduction, changes the mobile node type to `sed`, and records explicit observability metadata:

- `device_profile: sleepy_end_device`
- `packet_probe_reliable: false`
- `primary_parent_observation: parent_command`

This keeps the benchmark aligned with what a regular stock SED actually exposes in OTNS. Future work can add CSL or `ssed` experiments if reliable packet-response probing becomes necessary.

## RF propagation model

The runner prefers OTNS `MutualInterference` because OTNS documents that it models decreasing RSSI with distance and includes CCA/interference behaviour. If unavailable, the runner falls back in this order:

1. `MIDisc`
2. `Ideal_Rssi`
3. `Ideal`

If a fallback is used, it is recorded in the run summary JSON.

## Mobility model

The mobility model is a deterministic linear trajectory. The mobile node position is updated every fixed simulation interval. This keeps the scenario reproducible and simple enough for a baseline comparison.

## Metrics collected

Per sample, the benchmark attempts to capture:

1. Simulation time
2. Mobile node position
3. Mobile node role/state
4. Current parent information, when OT CLI exposes it
5. Parent switch events inferred from a change in observed parent identity
6. Packet-delivery success and RTT from fixed ping probes
7. Visible candidate-parent RSSI/LQI from scan output, when available
8. IPv6 and MLE counter snapshots, when exposed by the node CLI

The runner writes:

- `results/baseline_run_<timestamp>.csv`
- `results/baseline_summary_<timestamp>.json`
- `results/replays/<scenario_name>_<timestamp>.replay` when replay capture is enabled
- `results/replays/<scenario_name>_<timestamp>.replay.json` when replay capture is enabled

For reproducibility and downstream tooling checks, the repository includes three curated committed artifact sets:

- `examples/real-baseline/baseline_run_example.csv`
- `examples/real-baseline/baseline_summary_example.json`
- `examples/switch-attempt/baseline_run_switch_attempt.csv`
- `examples/switch-attempt/baseline_summary_switch_attempt.json`
- `examples/sed-baseline/baseline_run_sed_example.csv`
- `examples/sed-baseline/baseline_summary_sed_example.json`

The `results/` directory is for local generated outputs. The `examples/real-baseline/` directory preserves the original no-switch reference artifact. The `examples/switch-attempt/` directory stores a calibrated stock-switch attempt artifact.
The `examples/sed-baseline/` directory stores a real SED reference artifact that emphasizes parent observation over ping observability.

Repeated experiments can be launched with `scripts/run_repeated_baseline.py`. They write one experiment directory under `results/repeated/`, with one subdirectory per run and a top-level manifest for traceability.

Scratch outputs under `results/` remain ignored by Git. Curated benchmark evidence can be copied into tracked `artifacts/` directories when `--copy-results-to-artifact` is used. That export keeps CSV, summary JSON, replay, replay metadata, and a manifest together for later comparison work.
Replay-derived GIFs are scratch outputs as well and default to `results/gifs/`.

## Known limitations

Several limitations are currently explicit:

- OTNS upstream currently has an open issue that a direct `"Set Parent"` event is not emitted from OTNS/OpenThread issue tracking, so switch events are inferred from observed parent state rather than consumed as a first-class simulator event.
- Parent details depend on OpenThread CLI support for the `parent` command and its output format.
- Candidate-parent RSSI/LQI is derived from `scan` output when possible, but scan visibility can differ from actual parent-selection internals.
- In the current validated OTNS setup, `scan` behaves as a background/asynchronous command rather than a simple synchronous query. Live CSV output currently leaves scan-derived fields empty rather than depending on unstable per-sample scan capture. See [`otns_cli_compatibility.md`](otns_cli_compatibility.md).
- For a regular SED, OTNS can expose parent information and MLE counters, but packet probes are not reliable evidence of reachability. The SED scenario therefore treats the `parent` command as the primary attachment observation path and does not equate 100% ping loss with disconnection.
- The validated real SED example remained attached to `router_a` for the full path even after Router B was introduced and became spatially closer. That is useful evidence about observed stock OpenThread behavior under the tested parameters, but it is not proof that SED parent switching never occurs.
- Replay capture is non-fatal by design. If replay capture is requested but no replay file is found, the benchmark still preserves CSV and summary outputs and records the missing replay as a note.
- Plot generation in `analysis/analyze_baseline.py` is optional and only enabled when `matplotlib` is installed.
- Real OTNS execution was validated in the local workspace on July 7, 2026 using a local OTNS checkout, explicit OTNS workdir, and headless OTNS launch flags.
- The committed example artifact is a single representative run, not a repeated experiment and not a statistically meaningful dataset.
- Even the calibrated scenario can remain a no-switch run on some executions. That variability is part of the observed stock OpenThread behavior under the tested OTNS conditions.

## How to run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
```

Calibrated stock-switch attempt:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Calibrated stock-switch attempt with replay capture and tracked artifact export:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name calibrated-med-switch-observed \
  --firmware-variant stock-openthread \
  --openthread-commit <sha> \
  --otns-commit <sha>
```

SED stock benchmark:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/sed_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Mock smoke test:

```bash
python3 scripts/run_baseline.py --mock
```

Analyze results:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv
```

Run repeated experiments:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 5 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Aggregate a repeated-run experiment:

```bash
python3 analysis/analyze_baseline.py results/repeated/<experiment-name>
```

Run repeated experiments with replay capture and tracked artifact export:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 3 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name calibrated-med-repeated-demo \
  --firmware-variant stock-openthread \
  --openthread-commit <sha> \
  --otns-commit <sha>
```

Generate plots when `matplotlib` is installed:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv --plot-dir results/plots
```

To validate the committed example artifact:

```bash
python3 analysis/analyze_baseline.py examples/real-baseline/baseline_run_example.csv
python3 analysis/analyze_baseline.py examples/switch-attempt/baseline_run_switch_attempt.csv
python3 analysis/analyze_baseline.py examples/sed-baseline/baseline_run_sed_example.csv
```

## Validation checklist

- `python3 scripts/run_baseline.py --mock`
- `python3 analysis/analyze_baseline.py results/baseline_run_*.csv`
- Real OTNS launch test with `otns`
- Real baseline run with `python3 scripts/run_baseline.py`
- Calibrated replay capture run with `python3 scripts/run_baseline.py --scenario scenarios/calibrated_mobile_parent_switch.yaml --otns-command '/path/to/otns -web=false -autogo=false -speed 1' --otns-workdir /path/to/ot-ns --capture-replay --copy-results-to-artifact --artifact-name calibrated-med-switch-observed`
- Confirm a replay file and replay metadata JSON are created
- Confirm tracked outputs are copied into `artifacts/`
- Confirm CSV and JSON outputs are created
- Confirm parent-switch events are populated when a switch occurs
- Confirm packet-delivery metrics are populated
- Confirm outage metrics are populated

## Replay interpretation

Replay files can be replayed with:

```bash
otns-replay artifacts/<artifact-name>/replay/<captured-file>.replay
```

Replay files can also be rendered into a GIF via the OTNS web UI with:

```bash
python3 scripts/replay_to_gif.py \
  artifacts/<artifact-name>/replay/<captured-file>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --gif-frame-duration-ms 500 \
  --show-log-panel
```

That script launches `otns-replay`, opens one persistent headless Chrome session, captures repeated screenshots through the Chrome DevTools protocol, and stitches the frames into a GIF with Pillow.
`--replay-speed` normalizes the replay into a temporary constant-speed copy before playback, `--cover-full-replay` spaces the captures across that normalized replay timeline, `--end-device-y-offset` carries a consistent visual separation from routers across rendered artifacts, and `--show-log-panel` overlays the replay-visible OTNS log categories as a readable log strip.

Replay metadata records scenario, firmware label, OpenThread commit, OTNS commit, command, workdir, and the associated CSV and summary file paths. That metadata is necessary for future stock-vs-modified firmware comparisons because the replay file alone does not explain what build or benchmark context produced it.

## Baseline interpretation

The main questions this benchmark should answer are:

- When does the mobile node stop preferring Router A?
- How long does it take before it attaches via Router B?
- Is there a measurable outage or degraded packet-delivery window?
- Does parent switching happen once, or does the device oscillate between candidate parents?
- For a SED, does parent observation remain stable even when packet probes are uninformative?

This baseline will later act as the comparison point for any mobility-aware parent-switching policy introduced in OTNS-MAPS.
