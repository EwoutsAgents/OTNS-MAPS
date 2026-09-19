# Reproduction commands

The validation used the local OTNS binary, OpenThread commit
`a12ff0d0f54fd41954b45047fcdd08f302731c5f`, and the corrected
`fast-attach-ucast-1` MTD/FTD binaries.

## Single-run smoke test

```bash
.venv/bin/python scripts/run_baseline.py \
  --scenario scenarios/directed/med_directed_ucast_fast_attach_1_2routers.yaml \
  --results-dir results/smoke/fast-attach-ucast-1-pcap-smoke-20260919 \
  --timestamp-token 20260919T091500Z \
  --directed-random-seed 9101 \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -listen localhost:30000 -seed 9101 -pcap off' \
  --otns-runtime-dir results/smoke/fast-attach-ucast-1-pcap-smoke-20260919/otns_runtime \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level note \
  --firmware-variant otns-fast-attach-ucast-1-pcap \
  --thread-device-type med --parent-search-config disabled \
  --node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-mtd \
  --node-binary-profile fast-attach-ucast-1 \
  --ftd-node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd \
  --ftd-node-binary-profile fast-attach-ucast-1 \
  --firmware-source-repo ../ESPHome-Thread-ED-Switch-Parent \
  --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f \
  --otns-commit 099a6c2 \
  --copy-results-to-artifact \
  --commit-artifact-dir results/fast-attach-ucast-1-pcap-smoke-20260919
```

The input deliberately says `-pcap off`; the directed runner records the
effective command as `-pcap wpan` and preserves the capture.

## Repeated campaigns

For each `N` in `2 3 4`, the campaign command was:

```bash
.venv/bin/python scripts/run_repeated_baseline.py \
  --scenario "scenarios/directed/med_directed_ucast_fast_attach_1_${N}routers.yaml" \
  --results-dir results/smoke \
  --experiment-name "fast-attach-ucast-1-${N}routers-pcap-validation-20260919" \
  --repeat-count 102 --jobs 8 --listen-port-base "$PORT_BASE" \
  --otns-seed-base 10001 --target-seed-base 1701 \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -pcap off' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level note \
  --firmware-variant otns-fast-attach-ucast-1-pcap \
  --thread-device-type med --parent-search-config disabled \
  --node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-mtd \
  --node-binary-profile fast-attach-ucast-1 \
  --ftd-node-binary-path /tmp/otns-variant-build-parent-Cbhg/variants/fast-attach-ucast-1/build/bin/ot-cli-ftd \
  --ftd-node-binary-profile fast-attach-ucast-1 \
  --firmware-source-repo ../ESPHome-Thread-ED-Switch-Parent \
  --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f \
  --otns-commit 099a6c2
```

`PORT_BASE` was `32000`, `33200`, and `34400` for 2, 3, and 4 routers.
The primary campaigns produced 102, 101, and 98 accepted PCAP sequences. Five
additional 4-router attempts used ports starting at 36000, OTNS seed 11001,
and target seed 2801; all five were accepted.

## Comparison generation

```bash
.venv/bin/python analysis/compare_fast_attach_pcap.py \
  --campaign 2=results/smoke/fast-attach-ucast-1-2routers-pcap-validation-20260919 \
  --campaign 3=results/smoke/fast-attach-ucast-1-3routers-pcap-validation-20260919 \
  --campaign 4=results/smoke/fast-attach-ucast-1-4routers-pcap-validation-20260919 \
  --campaign 4=results/smoke/fast-attach-ucast-1-4routers-pcap-replacements-20260919 \
  --hardware-csv ../ESPHome-Thread-ED-Switch-Parent/testing/results/n100-comparison-2026-09/analysis/results.csv \
  --output-dir results/fast-attach-ucast-1-n100-pcap-comparison-20260919 \
  --limit 100
```
