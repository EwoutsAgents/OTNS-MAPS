# Reproduction commands

Build the native variants with the updated hardware/reference repository:

```bash
export OPENTHREAD_REPOSITORY=/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/openthread
export OTNS_RFSIM_DIR=/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim
export OTNS_VARIANT_ROOT=/tmp/otns-fast-attach-corrected-variants
export NINJA_BIN=/home/ewout/.openclaw/workspace-softwaredeveloper/ESPHome-Thread-ED-Switch-Parent/testing/.platformio-core/fast-attach/tools/tool-ninja/ninja
../ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh
```

For each `N` in `2 3 4`, run the gated campaign with distinct port bases:

```bash
.venv/bin/python scripts/run_repeated_baseline.py \
  --scenario "scenarios/static/med_static_parent_removal_${N}routers.yaml" \
  --results-dir results/smoke \
  --experiment-name "fast-attach-corrected-${N}routers-pcap-validation-20260919" \
  --repeat-count 102 --jobs 8 --listen-port-base "$PORT_BASE" \
  --otns-seed-base "$SEED_BASE" \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 0 -pcap off' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level note \
  --firmware-variant otns-fast-attach-corrected-pcap \
  --thread-device-type med --parent-search-config disabled \
  --node-binary-path /tmp/otns-fast-attach-corrected-variants/fast-attach/build/bin/ot-cli-mtd \
  --node-binary-profile fast-attach \
  --ftd-node-binary-path /tmp/otns-fast-attach-corrected-variants/fast-attach/build/bin/ot-cli-ftd \
  --ftd-node-binary-profile fast-attach \
  --build-config-source ../ESPHome-Thread-ED-Switch-Parent/scripts/build_otns_native_variants.sh \
  --firmware-source-repo ../ESPHome-Thread-ED-Switch-Parent \
  --openthread-commit a12ff0d0f54fd41954b45047fcdd08f302731c5f \
  --otns-commit 099a6c2
```

The validation used port bases `60000`, `61200`, and `62400`, and seed bases
`102000`, `103000`, and `104000` for 2, 3, and 4 routers.

Generate the comparison:

```bash
.venv/bin/python analysis/compare_fast_attach_pcap.py \
  --variant fast-attach \
  --campaign 2=results/smoke/fast-attach-corrected-2routers-pcap-validation-20260919 \
  --campaign 3=results/smoke/fast-attach-corrected-3routers-pcap-validation-20260919 \
  --campaign 4=results/smoke/fast-attach-corrected-4routers-pcap-validation-20260919 \
  --hardware-csv ../ESPHome-Thread-ED-Switch-Parent/testing/results/n100-comparison-2026-09/analysis/results.csv \
  --output-dir results/fast-attach-corrected-n100-pcap-comparison-20260919 \
  --limit 100
```
