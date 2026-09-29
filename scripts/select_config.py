#!/usr/bin/env python3
"""Select a configuration by geometric-mean IPC on training workloads only."""
import argparse
import csv
import json
import math
from pathlib import Path

def select(rows):
    if not rows or any(r['split']!='train' for r in rows):
        raise ValueError('selection requires a nonempty training-only CSV; do not tune on test data')
    groups={}
    for row in rows:
        ipc=float(row['ipc'])
        if not math.isfinite(ipc) or ipc<=0: raise ValueError('IPC must be finite and positive')
        group=groups.setdefault(row['configuration'],{})
        if row['workload'] in group: raise ValueError('duplicate workload/configuration')
        group[row['workload']]=ipc
    workloads=set(next(iter(groups.values())))
    if any(set(group)!=workloads for group in groups.values()): raise ValueError('all configurations must cover identical workloads')
    scores={name:math.exp(sum(math.log(x) for x in values.values())/len(values)) for name,values in groups.items()}
    best=min(scores,key=lambda name:(-scores[name],name))
    return best,scores

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True)
    p.add_argument('--config',type=Path,default=Path('configs/sweep.json'))
    p.add_argument('--output',type=Path,default=Path('build/selected.json'))
    args=p.parse_args()
    with args.csv.open() as f: best,scores=select(list(csv.DictReader(f)))
    configs=json.loads(args.config.read_text())
    if not isinstance(configs,list): configs=[configs]
    chosen=[c for c in configs if c['executable_name']==best]
    if len(chosen)!=1: raise ValueError('selected executable absent/duplicated in config')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(chosen[0],indent=2)+'\n')
    print(json.dumps({'selected':best,'training_geomean_ipc':scores},indent=2))
if __name__=='__main__': main()
