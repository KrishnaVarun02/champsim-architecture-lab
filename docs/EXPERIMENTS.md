# Experiments and SAT-solver trace workflow

## Functional versus timing results

`build/bench` reads `B hexadecimal_pc 0|1` branch records and `M hexadecimal_address`
memory records. It reports cold-start direction mispredictions and cache misses.
The standalone bimodal baseline matches the upstream 16,384-entry, modulo-16,381
index and strongly-not-taken initial counter state. Its cache is 64 sets × 8 ways × 64 bytes, with no hierarchy or prefetcher. It has no
pipeline model and therefore does not calculate IPC or latency.

Native ChampSim provides timing. The sweep uses its default single out-of-order
core and unchanged defaults except for branch predictor and these compact caches:
L1D = 64 sets × 4 ways, L2C = 64 sets × 4 ways, LLC = 64 sets × 8 ways. Small cache
sizes make synthetic capacity/replacement behavior visible. All three replacement
policies run at the LLC; other cache replacement policies remain upstream defaults.
This is an experimental configuration, not a claim to model a particular CPU.

`branch_mpki` is ChampSim's combined direction/target branch misprediction count
per thousand retired instructions. Standalone `ltage_misses` is direction-only.
`llc_demand_hit_rate` uses LOAD+RFO hit/miss counters (merged misses are kept in the
raw JSON). `llc_average_miss_latency_cycles` is upstream's average over non-prefetch
fills, including its accounting for all demand types. Missing denominators are
null/blank, never zero latency. Simulator boundaries can retire a few instructions
beyond the requested count; all ratios use actual retired counts.

## Synthetic dataset

`scripts/synthetic.py` emits 16 deterministic branch/memory patterns in text and
64-byte little-endian ChampSim trace formats. Fixed seed = 2023. Patterns include
fixed-trip loops, correlations, phase changes, random branches, streaming, a hot
set, conflicts, scan pollution and a skewed hot set. They are small synthetic
instruction streams, not compiled applications, SAT solver captures, or evidence
of performance on large real workloads. Register dependencies/PCs are simplified.

## Bring actual SAT traces

Capture x86 SAT solver instruction streams with the upstream `tracer/` workflow,
or supply existing standard ChampSim traces for which you have usage rights.
Keep solver name/version, CNF instance identifier, solver seed, capture interval,
tracer version and trace source in the manifest/source notes. Do not redistribute
restricted traces. This repository deliberately does not invent SAT trace results.

A manifest is a nonempty JSON list. Paths are relative to the manifest; absolute
paths also work. For every trace provide:

```json
[
  {
    "name": "solver-instance-train-01",
    "path": "traces/solver-instance.champsimtrace.xz",
    "sha256": "REPLACE_WITH_SHA256_OF_THE_COMPRESSED_FILE",
    "kind": "external",
    "split": "train",
    "source": "solver/version, CNF source, tracer/version, capture interval, seed",
    "instructions": 1000000000
  }
]
```

Compute SHA256 with `shasum -a 256 FILE` or `sha256sum FILE`. Instruction count must
be the actual count before compression. The runner checks identity and requires
at least warmup + simulation + 128 instructions as a preliminary minimum. This
margin does **not** guarantee that recycling will be avoided: the frontend and
in-flight pipeline can read beyond the retired-instruction boundary. After each
simulation, the runner rejects any log containing ChampSim's `Reached end of trace`
marker, even when the process exits successfully. Supply a longer trace or reduce
the interval if this occurs. Rejected runs retain raw logs/commands/JSON for
inspection, but produce no summary CSV; a previous CSV at that output location is
removed at the beginning of a rerun.

The runner cannot independently verify user-supplied instruction-count metadata
for compressed external traces. Uncompressed synthetic counts are tested at
generation; the runtime log check is required for every kind of trace.

Use at least 13 representative, sufficiently long external traces for an actual
large-trace study. Choose disjoint solver/instance families for train, validation,
and test rather than selecting the winner on held-out data. The longer-history
variant changes history coverage (maximum 192 → 1000 branches) at equal table
entry counts; it is a candidate for correlation-heavy workloads, not a proven SAT
optimization. Equal entries do not guarantee equal physical hardware storage,
access latency, or power.

```sh
python3 scripts/build_champsim.py
python3 scripts/run_champsim.py --manifest /path/to/sat-manifest.json \
  --warmup 200000000 --instructions 500000000 --split train --out build/sat-train
python3 scripts/select_config.py --csv build/sat-train/summary.csv \
  --output build/selected.json
python3 scripts/run_champsim.py --manifest /path/to/sat-manifest.json \
  --config build/selected.json --warmup 200000000 --instructions 500000000 \
  --split validation --out build/sat-validation
python3 scripts/run_champsim.py --manifest /path/to/sat-manifest.json \
  --config build/selected.json --warmup 200000000 --instructions 500000000 \
  --split test --out build/sat-test
```

The selector requires training-only data and a complete workload/configuration
grid. It chooses highest geometric-mean IPC. Compare the frozen choice against a
separate baseline run on the same held-out traces and intervals. Record per-trace
speedup and geomean speedup; do not infer universal latency gains from a hit rate.
Each run saves raw upstream JSON, stdout log, command JSON, configuration JSON,
trace hash and a CSV of measured ROI results. Inputs, pin, compiler, machine and
commands should accompany any published benchmark result.
