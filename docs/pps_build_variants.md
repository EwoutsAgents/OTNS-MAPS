# OpenThread PPS Build Variants

This note records how the local OTNS/OpenThread checkout controls Periodic Parent Search (PPS) for the calibrated MED benchmark.

## Purpose

Periodic Parent Search is OpenThread's built-in mechanism that lets an attached child periodically look for a better parent. The MED benchmark isolates PPS before any MAPS work so the project can distinguish stock OpenThread behavior from a future mobility-aware policy.

## Local source paths

- OTNS checkout: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- OpenThread checkout: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/openthread`
- OpenThread commit: `7874555efb1772bad66049ab06a78a2ce0c925f3`
- OTNS commit: `099a6c26cb1d2b8749d3171d5cdd8597fc71049c`
- OpenThread default: `openthread/src/core/config/parent_search.h`
- Simulation platform override: `openthread/examples/platforms/simulation/openthread-core-simulation-config.h`
- RFSIM project config: `ot-rfsim/src/openthread-core-rfsim-config.h`
- Local MTD build outputs:
  - PPS off: `ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd`
  - PPS on: `ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd`

## Configuration finding

`openthread/src/core/config/parent_search.h` defines:

```c
#ifndef OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE
#define OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE OPENTHREAD_FTD
#endif
```

For a plain MTD build that would resolve to disabled. The local simulation platform header `openthread/examples/platforms/simulation/openthread-core-simulation-config.h` overrides it:

```c
#ifndef OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE
#define OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE 1
#endif
```

The existing `ot-rfsim/build/latest/compile_commands.json` does not pass an explicit `-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=...` for `ot-cli-mtd`, so the current/default MED build resolves through the simulation platform override to PPS enabled.

Related PPS defaults in `openthread/src/core/config/parent_search.h`:

```c
#define OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL (9 * 60)
#define OPENTHREAD_CONFIG_PARENT_SEARCH_BACKOFF_INTERVAL (10 * 60 * 60)
#define OPENTHREAD_CONFIG_PARENT_SEARCH_RSS_THRESHOLD -65
#define OPENTHREAD_CONFIG_PARENT_SEARCH_RESELECT_TIMEOUT (90 * 60)
#define OPENTHREAD_CONFIG_PARENT_SEARCH_RSS_MARGIN 7
```

The PPS-off/on builds in this milestone change only `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; the interval, threshold, timeout, margin, and backoff values remain stock defaults.

Default classification:

```json
{
  "firmware_variant": "stock-default",
  "parent_search_config": "observed",
  "equivalent_to": "stock-med-pps-on"
}
```

## How OTNS chooses the MED binary

OTNS maps `add med`, `add sed`, and `add ssed` to its MTD executable. This is implemented in `cli/CmdRunner.go`, where `MED`, `SED`, `SSED`, and `MTD` select `ec.Mtd`.

The local default executable lookup was:

```bash
cd /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns
/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 <<'EOF'
!exe
!exit
EOF
```

The relevant output was:

```text
mtd: ot-cli-mtd
Detected MTD path      : ./ot-rfsim/ot-versions/ot-cli-mtd
```

For PPS experiments, `scripts/run_baseline.py --node-binary-path ...` sends `exe mtd "<path>"` to OTNS before any `add med` command. Routers still use the default FTD binary.

## Build commands

`ninja` was not installed in this environment, so the OTNS helper script `ot-rfsim/script/build` could not be used directly because it hardcodes `-GNinja`. The explicit variants were built with the same options using CMake's Unix Makefiles generator.

Common options:

```bash
COMMON_OPTS=(
  -DCMAKE_BUILD_TYPE=Debug
  -DOT_PLATFORM=external
  -DOT_FULL_LOGS=ON
  -DOT_VENDOR_NAME=OpenThread.io
  -DOT_VENDOR_SW_VERSION=2.0.0
  -DOT_JOINER=ON
  -DOT_COAP=ON
  -DOT_COAPS=ON
  -DOT_COMMISSIONER=ON
  -DOT_ECDSA=ON
  -DOT_NETDIAG_CLIENT=ON
  -DOT_MESH_DIAG=ON
  -DOT_SERVICE=ON
  -DOT_MLE_MAX_CHILDREN=10
  -DOT_THREAD_VERSION=1.4
  -DOT_VENDOR_MODEL=RFSIM-Node-v1.4.0
  -DOT_BACKBONE_ROUTER=OFF
  -DOT_BACKBONE_ROUTER_MULTICAST_ROUTING=OFF
  -DOT_BORDER_ROUTER=ON
  -DOT_BORDER_ROUTING=OFF
  -DOT_BORDER_ROUTING_DHCP6_PD=OFF
  -DOT_BORDER_ROUTING_COUNTERS=OFF
  -DOT_NAT64_BORDER_ROUTING=OFF
  -DOT_MLR=ON
  -DOT_COAP_BLOCK=OFF
  -DOT_DNSSD_SERVER=OFF
  -DOT_NETDATA_PUBLISHER=ON
  -DOT_SRP_SERVER=OFF
  -DOT_TREL=OFF
  -DOT_TCP=ON
  -DOT_POWER_SUPPLY=EXTERNAL
  -DOT_DEVICE_PROP_LEADER_WEIGHT=ON
  -DOT_HISTORY_TRACKER=OFF
  -DOT_BLE_TCAT=ON
)
```

PPS disabled:

```bash
cd /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim
rm -rf build/stock-med-pps-off ../openthread/build/ot-rfsim-stock-med-pps-off
mkdir -p build/stock-med-pps-off
cd build/stock-med-pps-off
OTNS_NODE_TYPE=stock-med-pps-off cmake -G "Unix Makefiles" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  "${COMMON_OPTS[@]}" \
  -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0 \
  -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0 \
  ../..
make -j"$(getconf _NPROCESSORS_ONLN)" ot-cli-mtd
```

PPS enabled:

```bash
cd /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim
rm -rf build/stock-med-pps-on ../openthread/build/ot-rfsim-stock-med-pps-on
mkdir -p build/stock-med-pps-on
cd build/stock-med-pps-on
OTNS_NODE_TYPE=stock-med-pps-on cmake -G "Unix Makefiles" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  "${COMMON_OPTS[@]}" \
  -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1 \
  -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1 \
  ../..
make -j"$(getconf _NPROCESSORS_ONLN)" ot-cli-mtd
```

## Verification

Build hashes:

```text
167df12b5aafd643d50e25f921d25fd7858b7b5476cc39ac26d71a735ced159b  ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd
cd816d5c84a0b98298dfa0e1599a8146949bb0148b5c642eff6b203049b6f075  ot-rfsim/build/stock-med-pps-on/bin/ot-cli-mtd
3011a33cc285ad7959de4d410fe1e2f44ff7c74023b76148909d6a102a4e5174  ot-rfsim/ot-versions/ot-cli-mtd
```

Compile command verification:

```bash
rg -n "OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0" \
  /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/compile_commands.json

rg -n "OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=1" \
  /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-on/compile_commands.json
```

OTNS executable override verification:

```bash
cd /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns
/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 <<'EOF'
!exe mtd "/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd"
!exe
!exit
EOF
```

The output reported the explicit PPS-off path as `Detected MTD path`.
