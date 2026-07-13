# Reproducible Directed Parent-Switch Artifacts

Phase 12 packages directed OTNS results as self-describing, checksum-verified
artifacts. A bundle can be inspected without relying on the scratch directory
that produced it.

## Build provenance

The native binaries are built by the ESPHome parent-switch repository:

```bash
export OPENTHREAD_REPOSITORY=/path/to/full/openthread-clone
export OTNS_RFSIM_DIR=/path/to/ot-ns/ot-rfsim
export OTNS_VARIANT_ROOT=/new/output/directory
export NINJA_BIN=/path/to/ninja  # only when ninja is not on PATH

/path/to/ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh
```

The script checks out OpenThread `a12ff0d0f54fd41954b45047fcdd08f302731c5f`,
creates isolated stock, preferred-parent, and preferred-parent-fast-response
source trees, applies the appropriate patch series, builds the RFSIM MTD/FTD
executables, and prints their SHA-256 fingerprints.

The Phase 12 artifacts use:

```text
stock MTD       bfb2ef7b9400ff0899769a5e5658f20f0812b57ca7ece335ecb9b1266c3040a5
preferred MTD   dd6d97f5418bd7f35b1674f32687faa6116afc65d198436070e2cca8bdba3627
stock FTD       6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a
fastpr FTD      7bc3917e1d80d8f57258b9eb20ce5049351b772dd4da84058cd8391bd0e6c260
```

## Exporting a run

Use the normal directed runner with replay, node logging, and tracked export:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/directed/med_directed_ucast_fastpr_4routers.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 0 -seed 3214 -pcap off' \
  --otns-workdir /path/to/ot-ns \
  --node-binary-path /path/to/preferred-parent-mtd-pps-off/ot-cli-mtd \
  --node-binary-profile preferred-parent \
  --ftd-node-binary-path /path/to/fastpr-ftd/ot-cli-ftd \
  --ftd-node-binary-profile fastpr \
  --parent-search-config disabled \
  --build-config-source /path/to/build_otns_native_variants.sh \
  --firmware-source-repo /path/to/ESPHome-Thread-ED-Switch-Parent \
  --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f \
  --otns-commit 099a6c26cb1d2b8749d3171d5cdd8597fc71049c \
  --otns-watch-level info \
  --capture-replay \
  --copy-results-to-artifact \
  --commit-artifact-dir /new/artifact/directory
```

The exact command for a recorded run is stored in `manifest.json` as
`runner_command` and `runner_invocation`.

Repeated experiments should set `--otns-seed-base`. Run 1 uses that seed and
each subsequent run increments it by one. The scenario's `random_seed` remains
the independent target-selection seed.

## Bundle layout

Each run contains:

```text
README.md
manifest.json
checksums.sha256
scenario.yaml
baseline_run_<token>.csv
baseline_summary_<token>.json
preferred_parent_events_<token>.csv
<scenario>_<token>.replay
<scenario>_<token>.replay.json
node_log_<name>_<id>.log
parent_rank_<token>.csv       # only when ParentRank events are present
```

The manifest records repository revisions and tracked-dirty state, binary paths
and hashes, build profiles, OpenThread/OTNS revisions, both random seeds, timing
sources, classifications, and artifact-relative payload references. Absolute
scratch paths are retained only under replay metadata's `source_paths` audit
field.

Repeated experiment directories add an aggregate summary, top-level scenario,
experiment manifests, and one independently verified run bundle per repetition.

## Integrity verification

Verify one run or a repeated experiment recursively:

```bash
python3 scripts/verify_artifact.py /path/to/artifact
```

Verification checks:

- the complete payload inventory and SHA-256 file digests;
- packaged scenario fingerprint;
- required run files and artifact-relative references;
- summary/manifest classification, seed, and timing agreement;
- complete protocol timing for directed runs;
- local executable fingerprints when the recorded binaries are available;
- every nested run in a repeated experiment.

Changing any checksummed payload causes verification to fail.

## Phase 12 reference artifacts

The committed reference collection is
`results/directed_parent_switch_phase12/20260714-002000-experiment/`.
It contains one four-router multicast, unicast, and fast-response run plus a
three-run, two-router fast-response repeated experiment.

All six runs reached the selected target and exported complete native timing.
The four-router full-attach times were 441.320 ms, 441.064 ms, and 19.200 ms for
multicast, unicast, and fast-response unicast respectively. The repeated
fast-response full-attach times were 19.200 ms, 25.600 ms, and 19.520 ms.

## Timing and platform limits

Protocol intervals use the node-local RFSIM microsecond clock. Parent deletion
uses global simulator time, and final-parent confirmation uses one-second
polling. These clocks are not mixed. Hardware PCAP and OTNS native events share
semantic boundaries but not timing precision or radio/execution behavior.

The recorded OTNS source reports a tracked change in its OpenThread submodule.
The Phase 12 binaries were built from the separately isolated Track A
OpenThread source stated above, and the artifacts recorded zero `ParentRank`
events. The dirty submodule state therefore does not imply an unidentified
change to the packaged native binaries; their hashes are authoritative.

## Clean-checkout validation

A fresh local clone of OTNS-MAPS commit `8a24698` verified all three
four-router bundles and the repeated experiment without modification. A new
four-router fast-response run was then launched from that clean checkout using
OTNS seed 3214 and the packaged scenario/build provenance.

The reproduction matched the reference on:

- target-selection seed 2923 and OTNS seed 3214;
- selected target `router_d`;
- `selected_target_reached` classification;
- all five node executable profiles and SHA-256 fingerprints;
- Parent Request to Response: 9.072 ms;
- Response to Child ID Request: 0.000 ms;
- Child ID Request to Response: 10.128 ms;
- full attach: 19.200 ms.

The reproduced artifact independently passed `scripts/verify_artifact.py` with
all 13 payload files and five available executable fingerprints checked.
