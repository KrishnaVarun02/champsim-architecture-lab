# Provenance and reproducibility

This repository is a new educational implementation built from a project brief.
It does not contain a recovered Spring 2022 submission. No historical results,
SAT-solver speedups, or experiments on external large-scale traces are asserted.
All checked-in measured results are labeled synthetic.

The original implementation in `include/`, `src/`, `scripts/`, and native
`champsim/` adapters is MIT licensed. The predictor implements selected ideas
from [André Seznec, The L-TAGE Branch Predictor (2007)](https://jilp.org/vol9/v9paper6.pdf).
It is an L-TAGE-style implementation, not the paper's exact CBP competition design.

The build script downloads these sources into ignored `.deps/`, preserving their
upstream licenses. No upstream simulator or dependency implementation is copied
into this repository. The included ChampSim license is retained as a convenience.

| Upstream | Pin | License |
|---|---|---|
| [ChampSim](https://github.com/ChampSim/ChampSim) | `410cee62d9c429c043ea611325ce00e6c303be2a` | Apache-2.0 |
| [fmt](https://github.com/fmtlib/fmt) 11.1.4 | `123913715afeb8a437e6388b4473fcc4753e1c9a` | MIT |
| [CLI11](https://github.com/CLIUtils/CLI11) 2.5.0 | `4160d259d961cd393fd8d67590a8c7d210207348` | BSD-3-Clause |
| [nlohmann/json](https://github.com/nlohmann/json) 3.12.0 | `55f93686c01528224f448c19128836e7df245f72` | MIT |

Simulator research reference: Gober et al., [The Championship Simulator:
Architectural Simulation for Education and Competition](https://arxiv.org/abs/2210.14324), 2022.
API source of truth is the pinned `branch/gshare`, `replacement/lru`,
`inc/modules.h`, `inc/trace_instruction.h`, `src/ooo_cpu.cc`, and
`src/json_printer.cc`. [Official module documentation](https://champsim.github.io/ChampSim/master/Modules.html)
may evolve after this pin.

The bootstrap uses fmt and CLI11 in their supported header-only modes and writes
an additional generated make fragment to link only compression libraries. It
never patches upstream simulation source code. ChampSim's normal vcpkg build
works too: configure with `--module-dir /absolute/path/to/this/repo/champsim` and
one of the supplied JSON files, then run upstream `make`.
