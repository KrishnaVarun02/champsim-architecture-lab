#!/usr/bin/env python3
"""Run pinned ChampSim configurations with checked trace identities and ROI stats."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def read_manifest(path, warmup, instructions):
    manifest=json.loads(path.read_text())
    if not isinstance(manifest,list) or not manifest: raise ValueError('manifest must be a nonempty list')
    names=set()
    for item in manifest:
        for key in ['name','path','sha256','kind','split','source','instructions']:
            if key not in item: raise ValueError(f'missing manifest field {key}')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', item['name']) or item['name'] in names: raise ValueError('trace names must be unique safe file names')
        names.add(item['name'])
        if item['kind'] not in ['synthetic','external']: raise ValueError('kind must be synthetic or external')
        if item['split'] not in ['train','validation','test']: raise ValueError('split must be train, validation, or test')
        if item['instructions'] < warmup+instructions+128: raise ValueError('trace shorter than preliminary minimum: requested interval + 128 instructions')
        trace=(path.parent/item['path']).resolve()
        if digest(trace)!=item['sha256']: raise ValueError(f'SHA256 mismatch: {trace}')
        item['_trace']=trace
    return manifest

def validate_log(path):
    # The simulator can read ahead beyond the retired-instruction boundary.
    # A manifest length margin alone cannot guarantee that it will not recycle.
    with path.open() as log:
        if any('Reached end of trace' in line for line in log):
            raise ValueError(f'trace exhausted/recycled during simulation; use a longer trace or reduce the interval (log: {path})')

def metrics(data):
    phases=[x for x in data if x['name']=='Simulation']
    if len(phases)!=1: raise ValueError('expected one Simulation phase')
    roi=phases[0]['roi']; core=roi['cores'][0]
    n=core['instructions']; cycles=core['cycles']
    if n<=0 or cycles<=0: raise ValueError('empty simulation interval')
    misses=sum(core['mispredict'].values())
    llc=roi['LLC']; hits=sum(llc['LOAD']['hit'])+sum(llc['RFO']['hit'])
    cache_misses=sum(llc['LOAD']['miss'])+sum(llc['RFO']['miss'])
    return {'instructions':n,'cycles':cycles,'ipc':n/cycles,'branch_misses':misses,'branch_mpki':1000*misses/n,
            'llc_demand_hits':hits,'llc_demand_misses':cache_misses,'llc_demand_hit_rate':hits/(hits+cache_misses) if hits+cache_misses else None,
            'llc_average_miss_latency_cycles':llc['miss latency']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--bin-dir',type=Path,default=ROOT/'.deps/champsim/bin')
    p.add_argument('--config',type=Path,default=ROOT/'configs/sweep.json')
    p.add_argument('--warmup',type=int,default=1000)
    p.add_argument('--instructions',type=int,default=10000)
    p.add_argument('--out',type=Path,default=ROOT/'build/champsim-runs')
    p.add_argument('--split',choices=['train','validation','test'])
    args=p.parse_args()
    if args.warmup < 0 or args.instructions<=0: p.error('invalid instruction interval')
    manifest=read_manifest(args.manifest.resolve(),args.warmup,args.instructions)
    configs=json.loads(args.config.read_text())
    if isinstance(configs,dict): configs=[configs]
    args.out.mkdir(parents=True,exist_ok=True)
    # Never leave a prior successful CSV looking like results for a failed rerun.
    (args.out/'summary.csv').unlink(missing_ok=True)
    rows=[]
    for trace in manifest:
        if args.split and args.split!=trace['split']: continue
        for config in configs:
            name=config['executable_name']
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',name): raise ValueError('unsafe executable name')
            prefix=args.out/f'{trace["name"]}__{name}'
            output=Path(str(prefix)+'.json').resolve()
            command=[str((args.bin_dir/name).resolve()),'--warmup-instructions',str(args.warmup),
                     '--simulation-instructions',str(args.instructions),'--json',str(output),str(trace['_trace'])]
            log_path=Path(str(prefix)+'.log')
            Path(str(prefix)+'.command.json').write_text(json.dumps(command,indent=2)+'\n')
            with log_path.open('w') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            validate_log(log_path)
            values=metrics(json.loads(output.read_text()))
            row={'workload':trace['name'],'kind':trace['kind'],'split':trace['split'],'configuration':name,'trace_sha256':trace['sha256'],**values}
            rows.append(row)
            print(f'{trace["name"]} {name}: IPC={values["ipc"]:.4f}',flush=True)
    if not rows: raise ValueError('no selected traces')
    with (args.out/'summary.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (args.out/'config.json').write_text(json.dumps(configs,indent=2)+'\n')
    print(f'Wrote {len(rows)} measured simulation rows to {args.out / "summary.csv"}')

if __name__=='__main__': main()
