#!/usr/bin/env python3
"""Generate deterministic small synthetic workloads; these are NOT SAT solver traces."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

NAMES = ['always_taken', 'never_taken', 'alternating', 'loop_7', 'loop_31', 'loop_127',
         'correlated', 'random_branch', 'phase_change', 'streaming', 'hot_set',
         'conflict', 'pointer_chase', 'scan_pollution', 'mixed_loops', 'skewed_hotset']
# Pinned ChampSim input_instr: 8-byte IP, 8 bytes branch/register fields, six u64 addresses.
INSTRUCTION = struct.Struct('<Q8B6Q')
assert INSTRUCTION.size == 64

def events(name, count, seed=2023):
    if name not in NAMES:
        raise ValueError(f'unknown workload {name}')
    rng = random.Random(seed + NAMES.index(name))
    last = False
    for i in range(count):
        pc = 0x400000 + (i % 16) * 4
        address = 0x100000 + (i % 256) * 64
        taken = i % 7 != 6
        if name == 'always_taken': taken = True
        elif name == 'never_taken': taken = False
        elif name == 'alternating': taken = bool(i % 2); pc = 0x400000
        elif name.startswith('loop_'):
            period = int(name.split('_')[1]); taken = i % period != period-1; pc = 0x400000
        elif name == 'correlated': taken = last if i % 2 else rng.random() < .5
        elif name == 'random_branch': taken = rng.random() < .5
        elif name == 'phase_change': taken = bool((i // 1000) % 2)
        elif name == 'streaming': address = 0x100000 + i * 64
        elif name == 'hot_set': address = 0x100000 + (rng.randrange(32) if rng.random() < .95 else rng.randrange(8192)) * 64
        elif name == 'conflict': address = 0x100000 + (i % 12) * 64 * 64
        elif name == 'pointer_chase': address = 0x100000 + ((i * 1543) % 8192) * 64
        elif name == 'scan_pollution': address = 0x100000 + (i % 128 if i % 8 else i + 8192) * 64
        elif name == 'mixed_loops': taken = i % (13 if (i // 1000) % 2 else 29) != 0
        elif name == 'skewed_hotset': address = 0x100000 + int(rng.random() ** 5 * 2048) * 64
        last = taken
        yield ('B', pc, taken)
        yield ('M', address, False)

def binary(record, i):
    kind, value, taken = record
    if kind == 'B':
        # IP destination + IP/flags inputs identify a conditional branch.
        return INSTRUCTION.pack(value, 1, int(taken), 26, 0, 26, 25, 0, 0, 0, 0, 0, 0, 0, 0)
    return INSTRUCTION.pack(0x800000, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, value, 0, 0, 0)

def generate(out, count, seed):
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in NAMES:
        trace = out / f'{name}.champsimtrace'
        with (out / f'{name}.txt').open('w') as text, trace.open('wb') as raw:
            text.write('# synthetic; not a captured SAT solver workload\n')
            for i, record in enumerate(events(name, count, seed)):
                kind, value, taken = record
                text.write(f'{kind} {value:x}' + (f' {int(taken)}' if kind == 'B' else '') + '\n')
                raw.write(binary(record, i))
        manifest.append({'name': name, 'path': trace.name, 'sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
                         'kind': 'synthetic', 'split': 'test', 'source': 'scripts/synthetic.py', 'instructions': count * 2})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Generated {len(NAMES)} synthetic workloads, {count*2} instructions each, seed {seed}')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=Path('build/synthetic'))
    p.add_argument('--count', type=int, default=10000, help='branch+memory pairs per workload')
    p.add_argument('--seed', type=int, default=2023)
    args = p.parse_args()
    if args.count <= 0: p.error('count must be positive')
    generate(args.out, args.count, args.seed)

if __name__ == '__main__': main()
