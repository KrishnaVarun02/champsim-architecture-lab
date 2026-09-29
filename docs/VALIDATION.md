# Validation

Validated locally on macOS arm64 using Apple clang 21.0.0, Python 3.14, and pinned
ChampSim `410cee62d9c429c043ea611325ce00e6c303be2a`.

| Check | Result |
|---|---|
| Standalone C++17 compilation | Passed |
| C++ unit suite | Passed: eviction order, tie breaking, fill reset, set isolation, invalid geometry, loop/alternating learning, deterministic updates |
| Python unittest suite | Passed: synthetic encoding/determinism, manifest identity/length, invalid text input, ROI extraction, trace-recycling rejection, training-only complete-grid selection |
| AddressSanitizer + UndefinedBehaviorSanitizer on C++ unit suite | Passed |
| Native upstream simulator compilation | Passed for all nine configurations |
| Full native sweep | Completed 16 workloads × 9 configurations = 144 runs |
| Repeat-run reproducibility | Rebuilt the final native modules and reproduced all 16 L-TAGE + LRU rows exactly |
| Native results integrity | 144 unique workload/configuration rows; positive IPC; at least 10,000 retired instructions per row; all 144 raw logs pass the runtime no-recycling guard |
| Short-trace regression | A native 11,128-instruction trace with 1,000 warmup + 10,000 ROI passes the preliminary length minimum but reaches EOF; the runner rejects it and emits no summary CSV |

`results/synthetic.csv` contains cold-start functional counters for 16 workloads,
10,000 branch events and 10,000 memory accesses each. It contains no IPC estimate.
`results/champsim-synthetic.csv` contains the real simulator's measured ROI values
using 1,000 warmup and 10,000 requested simulation instructions. `results/provenance.json`
records pins, compiler, platform, requested interval, configuration hash and every
synthetic trace hash. The binary instruction traces and complete upstream logs,
JSON and command records are reproducibly generated in ignored `build/`.

Example measured rows (illustrative, not general speedup claims):

| Synthetic workload | Configuration | IPC | Branch MPKI | LLC demand misses |
|---|---|---:|---:|---:|
| alternating | bimodal + LRU | 0.456892 | 238.1 | 0 |
| alternating | L-TAGE + LRU | 0.510673 | 0.0 | 0 |
| skewed_hotset | L-TAGE + LRU | 0.200831 | 0.0 | 1700 |
| skewed_hotset | L-TAGE + LFU | 0.206682 | 0.0 | 1650 |
| skewed_hotset | L-TAGE + FIFO | 0.197930 | 0.0 | 1721 |

These small experiments exercise learning and cache policy differences. They also
show why fewer branch misses do not guarantee an IPC gain on a memory-bound trace.
They are not application-quality benchmark evidence. Real SAT solver traces,
large-scale external trace validation, physical implementation cost, and results
on Linux CI are not claimed as locally completed. CI is supplied for repeatable
Linux unit, sanitizer, native build and full synthetic-sweep verification.
