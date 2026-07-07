# OTNS-MAPS baseline benchmark design

## Research goal

The first milestone is a stock-behaviour reference benchmark for OpenThread under mobility. The goal is to measure how late, unstable, or costly parent switching is when one mobile end device moves from one candidate parent toward another in OTNS.

This benchmark is intentionally not a new parent-selection algorithm. It measures unmodified OpenThread behaviour only.

## Scenario design

The baseline scenario uses three nodes:

- Router A
- Router B
- one mobile MED

The mobile node starts near Router A and gradually moves toward Router B in fixed position increments. The movement path is deterministic and defined in [`scenarios/baseline_mobile_parent_switch.yaml`](/home/ewout/.openclaw/workspace-softwaredeveloper/OTNS-MAPS/scenarios/baseline_mobile_parent_switch.yaml:1).

The initial baseline uses a MED instead of a regular SED. OTNS CLI documentation notes that a regular SED typically does not respond to ping traffic, which makes packet-delivery measurement less direct for a first benchmark. A later extension can add a dedicated SED or CSL-based scenario once the baseline harness is stable.

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

## Known limitations

Several limitations are currently explicit:

- OTNS upstream currently has an open issue that a direct `"Set Parent"` event is not emitted from OTNS/OpenThread issue tracking, so switch events are inferred from observed parent state rather than consumed as a first-class simulator event.
- Parent details depend on OpenThread CLI support for the `parent` command and its output format.
- Candidate-parent RSSI/LQI is derived from `scan` output when possible, but scan visibility can differ from actual parent-selection internals.
- A MED is used for the baseline packet-delivery probe. That means this first benchmark is a mobility baseline for stock OpenThread attachment and parent switching, not a low-power-optimized SED study yet.
- Plot generation in `analysis/analyze_baseline.py` is optional and only enabled when `matplotlib` is installed.
- In the current local workspace where this scaffold was created, `otns` was not available on `PATH`, so only the mock mode of the runner was smoke-tested here.

## How to run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
```

Mock smoke test:

```bash
python3 scripts/run_baseline.py --mock
```

Analyze results:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv
```

## Baseline interpretation

The main questions this benchmark should answer are:

- When does the mobile node stop preferring Router A?
- How long does it take before it attaches via Router B?
- Is there a measurable outage or degraded packet-delivery window?
- Does parent switching happen once, or does the device oscillate between candidate parents?

This baseline will later act as the comparison point for any mobility-aware parent-switching policy introduced in OTNS-MAPS.
