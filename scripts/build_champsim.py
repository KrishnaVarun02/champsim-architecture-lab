#!/usr/bin/env python3
"""Fetch pinned upstream/dependency sources and compile native ChampSim modules."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'champsim': ('https://github.com/ChampSim/ChampSim.git', '410cee62d9c429c043ea611325ce00e6c303be2a'),
    'fmt': ('https://github.com/fmtlib/fmt.git', '123913715afeb8a437e6388b4473fcc4753e1c9a'),
    'cli11': ('https://github.com/CLIUtils/CLI11.git', '4160d259d961cd393fd8d67590a8c7d210207348'),
    'json': ('https://github.com/nlohmann/json.git', '55f93686c01528224f448c19128836e7df245f72'),
}

def run(command, cwd=None):
    subprocess.run([str(x) for x in command], cwd=cwd, check=True)

def checkout(path, url, revision):
    if not (path / '.git').exists():
        path.mkdir(parents=True, exist_ok=True)
        run(['git', 'init', '-q', path])
        run(['git', '-C', path, 'remote', 'add', 'origin', url])
        run(['git', '-C', path, 'fetch', '--depth', '1', 'origin', revision])
        run(['git', '-C', path, 'checkout', '--detach', 'FETCH_HEAD'])
    actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision:
        raise SystemExit(f'{path} is at {actual}; expected {revision}. Use a fresh --deps directory.')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deps', type=Path, default=ROOT / '.deps')
    p.add_argument('--config', type=Path, default=ROOT / 'configs/sweep.json')
    p.add_argument('--jobs', type=int, default=2)
    args = p.parse_args()
    dep = args.deps.resolve()
    for name, (url, pin) in PINS.items():
        checkout(dep / name, url, pin)
    upstream = dep / 'champsim'
    # fmt and CLI11 officially support header-only use. Only compression libraries
    # need linking; this generated make fragment leaves upstream source untouched.
    fragment = upstream / 'archlab.options.mk'
    fragment.write_text('override LDLIBS := -llzma -lz -lbz2\n')
    prefix = '/opt/homebrew' if Path('/opt/homebrew/include/lzma.h').exists() else '/usr'
    cppflags = ' '.join(['-DFMT_HEADER_ONLY'] + [f'-I{dep / name / inc}' for name, inc in [('fmt','include'),('cli11','include'),('json','single_include')]])
    if ' ' in str(dep) or ' ' in str(ROOT):
        raise SystemExit('ChampSim make integration currently requires checkout paths without spaces.')
    run(['python3','config.sh','--no-compile-all-modules','--module-dir',ROOT / 'champsim',args.config.resolve()], cwd=upstream)
    run(['make','-f','Makefile','-f',fragment,f'-j{args.jobs}',f'TRIPLET_DIR={prefix}', f'CPPFLAGS={cppflags}',f'CXX={os.environ.get("CXX", "c++")}'], cwd=upstream)
    print(f'Built native ChampSim executables in {upstream / "bin"}')

if __name__ == '__main__':
    main()
