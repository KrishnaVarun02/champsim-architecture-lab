#!/usr/bin/env python3
"""Functional counts only: this runner does not model cycles or report IPC."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--traces',type=Path,default=ROOT/'build/synthetic')
    p.add_argument('--output',type=Path,default=ROOT/'results/synthetic.csv')
    args=p.parse_args()
    rows=[]
    for trace in sorted(args.traces.glob('*.txt')):
        values=json.loads(subprocess.check_output([str(ROOT/'build/bench'),str(trace)],text=True))
        rows.append({'workload':trace.stem,'kind':'synthetic',**values})
    if not rows: raise SystemExit('no input traces found')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(f'Wrote functional counts for {len(rows)} synthetic workloads to {args.output}')
if __name__=='__main__': main()
