# OTNS CLI compatibility notes

This note records the OTNS CLI behavior validated for the OTNS-MAPS baseline benchmark runner.

## Validated on

- Date: 2026-07-07 UTC
- Repository: `OTNS-MAPS`
- Local OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1`
- Local OTNS workdir: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`

## Launch-style findings

- Explicit command with `--otns-workdir` works.
- `otns` on `PATH` with `--otns-workdir` works.
- Launching without `--otns-workdir` failed in this setup with:
  - `Error: exec: "ot-cli-ftd": executable file not found in $PATH`

That failure matters because the local OTNS checkout uses bundled relative node executables. In this environment, `--otns-workdir` is required unless the OTNS node binaries are independently available on `PATH`.

## Command findings

These commands were validated against a real OTNS installation:

- `add`
- `move`
- `time`
- `radiomodel`
- `node <id> "state"`
- `node <id> "rloc16"`
- `node <id> "parent"`
- `node <id> "counters ip"`
- `node <id> "counters mle"`
- `scan`
- `ping`

Observed behavior:

- `add`, `time`, `radiomodel`, and the `node <id> ...` queries returned synchronous line output ending in `Done`.
- `move` accepts integer coordinates. Float coordinates failed with:
  - `unexpected token "100.5" (expected <int>)`
- `ping` itself returns `Done` immediately.
- Ping results are emitted during the following `go` command.
- `scan` is not a simple synchronous query in this setup.
- `scan <node-id>` may not return rows immediately.
- Scan rows, when available, are emitted during the following `go` command and are prefixed with `Node<id>`.

## Benchmark-runner implications

- The runner now uses pipe-based OTNS command execution instead of TTY-style prompt scraping.
- That change avoids readline prompt redraw noise from the OTNS CLI.
- The benchmark still leaves scan-derived RSSI/LQI fields empty in live mode.
- That is intentional for now because live `scan` behavior is background/asynchronous and not stable enough yet for per-sample collection inside the baseline runner.

## Reproduce

Run:

```bash
python3 scripts/validate_otns_cli.py \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns
```
