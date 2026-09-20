# Reproduce the cross-variant residual analysis

Run from the OTNS-MAPS repository on branch `revised-solution-fast-attach-based` with the hardware repository checked out alongside it:

```bash
git rev-parse HEAD
git -C ../ESPHome-Thread-ED-Switch-Parent rev-parse HEAD
tshark --version

.venv/bin/python analysis/analyze_cross_variant_platform_residuals.py \
  --hardware-results ../ESPHome-Thread-ED-Switch-Parent/testing/results/n100-comparison-2026-09 \
  --output-dir results/cross-variant-platform-residual-analysis-20260920 \
  --workers 16 \
  --bootstrap-iterations 5000
```

Expected input revisions:

```text
OTNS-MAPS: 7bf760e127f58ed38d57ac9413b1408744ce27b8
ESPHome-Thread-ED-Switch-Parent: c269aca295e621253878384364b13a87525a497e
OpenThread data/build revision: a12ff0d0f54fd41954b45047fcdd08f302731c5f
```

The run used TShark 4.2.2. The hardware analyzer may generate absent cached `*_all_packets_*.csv` and `*_attach_mle_*.csv` files beside captures; these are derivative decode caches and are not analysis inputs committed here.

Verify generated payload checksums:

```bash
cd results/cross-variant-platform-residual-analysis-20260920
sha256sum -c checksums.sha256
```

The script fails if a required result directory is absent, a hardware cell does not contain exactly 100 runs, a selected run has no complete sequence, a capture is missing, or the normalized total is not exactly 3,000 rows.
