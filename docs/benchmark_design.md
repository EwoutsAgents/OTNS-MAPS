# OTNS-MAPS baseline benchmark design

## Research goal

The first milestone is a stock-behaviour reference benchmark for OpenThread under mobility. The goal is to measure how late, unstable, or costly parent switching is when one mobile end device moves from one candidate parent toward another in OTNS.

This benchmark is intentionally not a new parent-selection algorithm. It measures unmodified OpenThread behaviour only.

## Scenario design

The active benchmark matrix uses three simple parent-switch scenarios:

- [`../scenarios/med_simple_parent_switch.yaml`](../scenarios/med_simple_parent_switch.yaml)
- [`../scenarios/fed_simple_parent_switch.yaml`](../scenarios/fed_simple_parent_switch.yaml)
- [`../scenarios/sed_simple_parent_switch.yaml`](../scenarios/sed_simple_parent_switch.yaml)

All three use three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and an asymmetric attachment-gated path. Router A is placed at `(350, 300)`, Router B at `(875, 300)`, Router C at `(1400, 300)`, and the mobile path runs from `(350, 360)` to `(1600, 360)`. OTNS `MeterPerUnit = 0.1` makes this a 125 m movement path; 25 one-second movement steps target 5 m/s, followed by a 320 s end dwell. The mobile is created near Router A, the runner waits until Router A is observed as parent, then Router B and Router C are introduced before movement begins.

The post-activation settle phase is monitored for parent changes. If the mobile changes parent after Router B/C activation but before movement sampling begins, the summary records `pre_movement_parent_events` and classifies the run as `pre_movement_switch_observed` when no later in-window switch is present. This keeps early PPS or attach behavior visible instead of mislabeling the first movement sample as merely unexpected.

The scenario details, activation timing, device observability, and old-name compatibility notes are maintained in [`scenarios.md`](scenarios.md). The runner sets each node to `txpower 0` during initialization and verifies the value with `txpower` when possible. It sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router; this records parent-path reachability and RTT. For SED, parent-command output remains the primary attachment signal.

Detach/recovery behavior is classified separately from ordinary no-switch behavior. Summary JSON records detach count, first detach and reattach time/position, reattach latency, final mobile state, whether the run ended detached, and one of `no_detach`, `detached_no_reattach`, `detached_reattached_same_parent`, or `detached_reattached_new_parent`. This prevents endpoint detach failures from being hidden inside generic no-switch classifications.

Older committed artifacts may reference the previous scenario names `baseline_mobile_parent_switch`, `calibrated_mobile_parent_switch`, `fed_mobile_parent_switch`, and `sed_mobile_parent_switch`. The original baseline scenario was a historical smoke/reference scenario and is no longer part of the active benchmark matrix. Results generated under the old wider geometry are historical and should not be mixed with new simple-scenario results without labeling the geometry difference.

## Periodic Parent Search comparison

Periodic Parent Search (PPS) is OpenThread's built-in mechanism that lets an attached child periodically search for a better parent. The MED PPS milestone isolates this stock behavior before any MAPS policy is implemented.

The active comparison is:

- PPS off: `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0`
- PPS on: `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1` and `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`

The current/default local MED build is classified separately as a discovery result. In the validated local checkout, the default MTD build is equivalent by configuration to `stock-med-pps-on` because `openthread/examples/platforms/simulation/openthread-core-simulation-config.h` defines `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE 1` when no explicit build flag overrides it.

Build provenance and exact commands are recorded in [`pps_build_variants.md`](pps_build_variants.md). The archived single-run calibrated MED comparison is recorded in [`pps_med_comparison.md`](pps_med_comparison.md), the archived 10-run MED follow-up is recorded in [`pps_med_repeated_comparison.md`](pps_med_repeated_comparison.md), and the archived FED/SED profile extension is recorded in [`pps_fed_sed_comparison.md`](pps_fed_sed_comparison.md). These archived comparisons used the older wider geometry. The single-run MED tracked artifacts are:

The active simple-geometry 10-run PPS matrix is recorded in [`simple_pps_matrix.md`](simple_pps_matrix.md).

- `../results/.archive/calibrated_mobile_parent_switch_med-pps-off/20260710-020657-run01/20260710-020657-run01/`
- `../results/.archive/calibrated_mobile_parent_switch_med-pps-on/20260710-020715-run01/20260710-020715-run01/`

Each artifact includes CSV, summary JSON, replay, replay metadata JSON, MP4, node logs, manifest, and README.

The repeated MED PPS artifacts are:

- `../results/.archive/calibrated_mobile_parent_switch_med-pps-off-repeated/20260710-023301-experiment/`
- `../results/.archive/calibrated_mobile_parent_switch_med-pps-on-repeated/20260710-023336-experiment/`

The archived repeated result shows earlier median switch timing and lower median outage for PPS-on, but similar mean switch timing and no oscillation in either variant.

The FED/SED PPS extension artifacts are:

- `../results/.archive/fed_mobile_parent_switch_fed-pps-off/20260710-104510-run01/20260710-104510-run01/`
- `../results/.archive/fed_mobile_parent_switch_fed-pps-on/20260710-104523-run01/20260710-104523-run01/`
- `../results/.archive/sed_mobile_parent_switch_sed-pps-off/20260710-104537-run01/20260710-104537-run01/`
- `../results/.archive/sed_mobile_parent_switch_sed-pps-on/20260710-104550-run01/20260710-104550-run01/`

The repeated FED/SED PPS extension artifacts are:

- `../results/.archive/fed_mobile_parent_switch_fed-pps-off-repeated/20260710-163436-experiment/`
- `../results/.archive/fed_mobile_parent_switch_fed-pps-on-repeated/20260710-163514-experiment/`
- `../results/.archive/sed_mobile_parent_switch_sed-pps-off-repeated/20260710-163933-experiment/`
- `../results/.archive/sed_mobile_parent_switch_sed-pps-on-repeated/20260710-164008-experiment/`

## RF propagation model

The runner prefers OTNS `MutualInterference` because OTNS documents that it models decreasing RSSI with distance and includes CCA/interference behaviour. If unavailable, the runner falls back in this order:

1. `MIDisc`
2. `Ideal_Rssi`
3. `Ideal`

If a fallback is used, it is recorded in the run summary JSON.

When `--capture-sim-ping-rss` is enabled, the runner attaches simulator-level RSS/LQI fields to each ping probe row. The current implementation uses the documented fallback `otns_model_derived_at_ping`: it derives RSS from the OTNS `MutualInterference` 3GPP indoor model at the exact ping source/destination positions and sample time, using the configured source TX power. This is simulator-model RSS tied to ping events. It is not OpenThread neighbor-table RSS, parent-command link quality, Link Metrics, scan RSS, or application-level ping output.

## Mobility model

The mobility model is a deterministic linear trajectory. The mobile node position is updated every fixed simulation interval. This keeps the scenario reproducible and simple enough for a baseline comparison.

## Metrics collected

Per sample, the benchmark attempts to capture:

1. Simulation time
2. Mobile node position
3. Mobile node role/state
4. Current parent information, when OT CLI exposes it
5. Parent switch events inferred from a change in observed parent identity
6. Pre-movement parent changes during post-activation settle
7. Packet-delivery success and RTT from the mobile-to-current-parent ping probe
8. Optional simulator-model RSS/LQI attached to each ping event when `--capture-sim-ping-rss` is enabled
9. Visible candidate-parent RSSI/LQI from scan output, when available
10. IPv6 and MLE counter snapshots, when exposed by the node CLI

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

Scratch outputs under `results/` remain ignored by Git. Curated benchmark evidence can be copied into tracked nested `results/<scenario>_<variant>/<run-id>/<run-id>/` directories when `--copy-results-to-artifact` is used. That export keeps CSV, summary JSON, replay, replay metadata, and a manifest together for later comparison work.
Replay-derived MP4s are stored beside the replay file in the same tracked run directory by default.
If `--otns-watch-level` is enabled for a real OTNS run, the run directory also keeps one raw `node_log_<name>_<node-id>.log` file per simulated device without parsing those logs into benchmark metrics.

## Known limitations

Several limitations are currently explicit:

- OTNS upstream currently has an open issue that a direct `"Set Parent"` event is not emitted from OTNS/OpenThread issue tracking, so switch events are inferred from observed parent state rather than consumed as a first-class simulator event.
- Parent details depend on OpenThread CLI support for the `parent` command and its output format.
- Candidate-parent RSSI/LQI is derived from `scan` output when possible, but scan visibility can differ from actual parent-selection internals.
- Per-ping simulator RSS currently uses model-derived OTNS `MutualInterference` calculations because the exported replay/log artifacts do not expose receive RSS/LQI events for direct per-ping matching.
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
  --scenario scenarios/med_simple_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Calibrated stock-switch attempt with replay capture and tracked artifact export:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/med_simple_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name switch-observed \
  --firmware-variant stock-openthread \
  --openthread-commit <sha> \
  --otns-commit <sha>
```

SED stock benchmark:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/sed_simple_parent_switch.yaml \
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
  --scenario scenarios/med_simple_parent_switch.yaml \
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
  --scenario scenarios/med_simple_parent_switch.yaml \
  --repeat-count 3 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name repeated-demo \
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
- Calibrated replay capture run with `python3 scripts/run_baseline.py --scenario scenarios/med_simple_parent_switch.yaml --otns-command '/path/to/otns -web=false -autogo=false -speed 1' --otns-workdir /path/to/ot-ns --capture-replay --copy-results-to-artifact --artifact-name switch-observed`
- Watch-enabled raw node-log capture run with `python3 scripts/run_baseline.py --scenario scenarios/med_simple_parent_switch.yaml --otns-command '/path/to/otns -web=false -autogo=false -speed 1' --otns-workdir /path/to/ot-ns --otns-watch-level info`
- Confirm a replay file and replay metadata JSON are created
- Confirm tracked outputs are copied into `results/<scenario>_<variant>/<run-id>/<run-id>/`
- Confirm CSV and JSON outputs are created
- Confirm per-device `node_log_<name>_<node-id>.log` files are created when watch is enabled
- Confirm parent-switch events are populated when a switch occurs
- Confirm packet-delivery metrics are populated
- Confirm outage metrics are populated

## Replay interpretation

Replay files can be replayed with:

```bash
otns-replay results/<scenario>_<variant>/<run-id>/<run-id>/<captured-file>.replay
```

Replay files can also be rendered into an MP4 via the OTNS web UI with:

```bash
python3 scripts/replay_to_mp4.py \
  results/<scenario>_<variant>/<run-id>/<run-id>/<captured-file>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --video-fps 3 \
  --show-log-panel
```

That script launches `otns-replay`, opens one persistent headless Chrome session, captures repeated screenshots through the Chrome DevTools protocol, and encodes the frames into an MP4 with `ffmpeg`.
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
