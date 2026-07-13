# Phase 12 directed parent-switch reference artifacts

This collection contains checksum-verified OTNS reference artifacts:

- `mcast`: one four-router multicast selected-parent run;
- `ucast`: one four-router unicast selected-parent run;
- `ucast_fastpr`: one four-router fast-response unicast run;
- `repeated-fastpr-2routers`: three fast-response runs with OTNS seeds
  3221–3223.

Every run reached its requested target and exported complete native timing.

Verify the individual runs:

```bash
python3 scripts/verify_artifact.py results/directed_parent_switch_phase12/20260714-002000-experiment/mcast
python3 scripts/verify_artifact.py results/directed_parent_switch_phase12/20260714-002000-experiment/ucast
python3 scripts/verify_artifact.py results/directed_parent_switch_phase12/20260714-002000-experiment/ucast_fastpr
```

Verify the repeated experiment and all nested runs:

```bash
python3 scripts/verify_artifact.py results/directed_parent_switch_phase12/20260714-002000-experiment/repeated-fastpr-2routers
```

See `docs/reproducible_artifacts.md` for build, execution, provenance, and
timing-source details.
